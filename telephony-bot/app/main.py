import asyncio
import base64
import json
import os
import re
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

import httpx
import websockets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.fsm import CallFSM, Step
from app.providers import LocalFileTTSAdapter, build_stt_adapter, build_tts_adapter
from app.recordings import get_wav_path, is_valid_wav, start_recording

app = FastAPI(title="telephony-bot")

ARI_URL = os.getenv("ASTERISK_ARI_BASE_URL", "http://asterisk:8088/ari")
ARI_WS = ARI_URL.replace("http://", "ws://").replace("https://", "wss://")
ARI_USER = os.getenv("ASTERISK_ARI_USERNAME", "ari_user")
ARI_PASSWORD = os.getenv("ASTERISK_ARI_PASSWORD", "ari_pass")
ARI_APP = os.getenv("ASTERISK_APP_NAME", "support_bot")
CORE_API_URL = os.getenv("CORE_API_URL", "http://core-api:8000")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "dev-service-token")
TEST_MODE = os.getenv("INTEGRATIONS_TEST_MODE", "true").lower() == "true"
DEFAULT_HANDOFF = os.getenv("BOT_HANDOFF_ON_INCOMPLETE", "false").lower() == "true"

PROMPT_TEXTS = {
    Step.GREETING: "Здравствуйте! Это бот техподдержки.",
    Step.FIO: "Назовите ваше ФИО.",
    Step.DEPARTMENT: "Укажите отдел.",
    Step.CABINET: "Укажите кабинет.",
    Step.PROBLEM: "Опишите проблему.",
    Step.EXTRA: "Есть ли дополнительная информация?",
    Step.CONFIRM: "Подтвердите данные. Нажмите 1 для подтверждения.",
    Step.INCOMPLETE: "Недостаточно данных для создания заявки.",
    Step.COMPLETE: "Спасибо, заявка создана.",
}

state = {"connected": False, "last_error": "not checked", "tts_provider": "", "stt_provider": ""}
sessions: dict[str, CallFSM] = {}
channel_to_call: dict[str, str] = {}
dtmf_buffer: dict[str, str] = defaultdict(str)
recording_meta: dict[str, dict[str, str]] = {}
settings_cache: dict[str, dict] = {}
fallback_tts_adapter = LocalFileTTSAdapter(os.getenv("BOT_SOUNDS_DIR", "/shared/sounds/custom_tts"))


def normalize_text(step: Step, value: str) -> str:
    text = value.strip()
    if step == Step.FIO:
        text = " ".join(word.capitalize() for word in text.split())
    elif step == Step.DEPARTMENT:
        text = re.sub(r"\bотд\b", "отдел", text.lower())
    elif step == Step.CABINET:
        text = text.replace("кабинет", "").strip()
    return text


def wav_file_to_b64(wav_path: str) -> str | None:
    is_valid, _ = is_valid_wav(wav_path)
    if not is_valid:
        return None
    with open(wav_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("ascii")


@dataclass
class AriClient:
    base_url: str
    user: str
    password: str

    async def post(self, path: str, params: dict[str, Any] | None = None) -> dict:
        async with httpx.AsyncClient(timeout=20.0, auth=(self.user, self.password)) as client:
            response = await client.post(f"{self.base_url}{path}", params=params)
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail=response.text)
            return response.json() if response.text else {}

    async def delete(self, path: str) -> None:
        async with httpx.AsyncClient(timeout=20.0, auth=(self.user, self.password)) as client:
            await client.delete(f"{self.base_url}{path}")


ari = AriClient(ARI_URL, ARI_USER, ARI_PASSWORD)
tts_adapter, tts_mode = build_tts_adapter()
stt_adapter, stt_mode = build_stt_adapter()
state["tts_provider"] = tts_mode
state["stt_provider"] = stt_mode


class AriEvent(BaseModel):
    type: str
    call_id: str
    text: str | None = None


async def core_post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            f"{CORE_API_URL}{path}",
            json=payload,
            headers={"X-Service-Token": SERVICE_TOKEN},
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=r.text)
        return r.json()


async def core_get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{CORE_API_URL}{path}", headers={"X-Service-Token": SERVICE_TOKEN})
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=r.text)
        return r.json()


async def load_runtime_settings() -> None:
    for section in ["phrases", "speechkit", "telephony"]:
        try:
            body = await core_get(f"/api/v1/service/settings/{section}")
            settings_cache[section] = body.get("config", {})
        except Exception:
            settings_cache[section] = {}


async def write_call_log(call_id: str, event_type: str, payload: dict) -> None:
    await core_post("/api/v1/call-logs", {"call_id": call_id, "event_type": event_type, **payload})


async def play_text_prompt(call_id: str, channel_id: str, step: Step) -> None:
    phrases = settings_cache.get("phrases", {})
    speech = settings_cache.get("speechkit", {})
    text = phrases.get(step.value, PROMPT_TEXTS[step])
    voice = speech.get("voice", os.getenv("SPEECHKIT_VOICE", "ermil"))
    speed = float(speech.get("speed", os.getenv("SPEECHKIT_SPEED", "1.0")))
    volume = int(speech.get("volume", os.getenv("SPEECHKIT_VOLUME", "0")))

    try:
        media = await tts_adapter.synthesize(text=text, voice=voice, speed=speed, volume=volume, key_hint=step.value)
    except Exception as exc:
        await write_call_log(call_id, "tts_error", {"provider": state["tts_provider"], "error": str(exc), "step": step.value})
        if not TEST_MODE:
            raise
        media = await fallback_tts_adapter.synthesize(text=text, voice=voice, speed=speed, volume=volume, key_hint=f"fallback-{step.value}")
        await write_call_log(call_id, "tts_fallback", {"provider": "local_assets", "step": step.value, "media": media})

    await ari.post(f"/channels/{channel_id}/play", params={"media": media})


async def start_step_recording(call_id: str, channel_id: str, step: Step) -> str:
    rec_name = start_recording(call_id, channel_id, step)
    wav_path = get_wav_path(rec_name)
    recording_meta[rec_name] = {"channel_id": channel_id, "call_id": call_id, "step": step.value, "wav_path": wav_path}
    await ari.post(
        f"/channels/{channel_id}/record",
        params={
            "name": rec_name,
            "format": "wav",
            "maxDurationSeconds": 6,
            "beep": "false",
            "ifExists": "overwrite",
            "terminateOn": "none",
        },
    )
    await write_call_log(call_id, "recording_started", {"recording_name": rec_name, "step": step.value, "audio_path": wav_path})
    return rec_name


async def maybe_identify_speaker(call_id: str, wav_path: str) -> None:
    fsm = sessions[call_id]
    if fsm.data.get("speaker_identify_done") == "1":
        return

    audio_b64 = wav_file_to_b64(wav_path)
    if not audio_b64:
        await write_call_log(call_id, "speaker_identify_skipped", {"reason": "missing_or_short_audio", "audio_path": wav_path})
        return

    caller = fsm.data.get("caller", "")
    identify = await core_post("/api/v1/speaker/identify", {"phone_number": caller, "audio_sample_b64": audio_b64})
    fsm.data["speaker_identify_done"] = "1"
    fsm.data["speaker_sample_path"] = wav_path
    fsm.data["speaker_sample_size"] = str(len(audio_b64))

    if identify.get("consent_required"):
        fsm.data["needs_consent"] = "1"
        if identify.get("user_id"):
            fsm.data["consent_user_id"] = str(identify["user_id"])

    await write_call_log(
        call_id,
        "speaker_identified",
        {
            "audio_path": wav_path,
            "audio_b64_size": len(audio_b64),
            "phone_number": caller,
            "result": identify,
        },
    )


async def maybe_enroll_speaker(call_id: str) -> None:
    fsm = sessions[call_id]
    if not (fsm.data.get("needs_consent") == "1" and fsm.data.get("consent_answer") == "1" and fsm.data.get("consent_user_id")):
        return

    sample_path = fsm.data.get("speaker_sample_path", "")
    audio_b64 = wav_file_to_b64(sample_path) if sample_path else None
    if not audio_b64:
        await write_call_log(call_id, "speaker_enroll_skipped", {"reason": "missing_or_short_audio", "audio_path": sample_path})
        return

    await core_post(
        "/api/v1/speaker/enroll",
        {
            "consent": True,
            "user_id": int(fsm.data["consent_user_id"]),
            "audio_sample_b64": audio_b64,
        },
    )
    await write_call_log(
        call_id,
        "speaker_enrolled",
        {
            "user_id": int(fsm.data["consent_user_id"]),
            "audio_path": sample_path,
            "audio_b64_size": len(audio_b64),
        },
    )


async def handle_step_input(call_id: str, channel_id: str, utterance: str | None) -> None:
    fsm = sessions[call_id]
    cleaned = normalize_text(fsm.step, utterance or "") if utterance else utterance
    prev = fsm.step
    new_step = fsm.consume(cleaned)
    await write_call_log(call_id, "fsm_transition", {"from": prev.value, "to": new_step.value, "input": cleaned})

    telephony_cfg = settings_cache.get("telephony", {})
    handoff = bool(telephony_cfg.get("handoff_on_incomplete", DEFAULT_HANDOFF))

    if new_step == Step.INCOMPLETE:
        await play_text_prompt(call_id, channel_id, Step.INCOMPLETE)
        if handoff:
            await ari.post(f"/channels/{channel_id}/continue")
        else:
            await ari.delete(f"/channels/{channel_id}")
        return

    if new_step == Step.COMPLETE:
        subject = f"Заявка от {fsm.data.get('fio', 'неизвестно')}"
        description = (
            f"Отдел: {fsm.data.get('department', '')}; Кабинет: {fsm.data.get('cabinet', '')}; "
            f"Проблема: {fsm.data.get('problem', '')}; Доп.инфо: {fsm.data.get('extra', '')}"
        )
        ticket = await core_post("/api/v1/tickets", {"subject": subject, "description": description, "channel": "voice"})
        await write_call_log(call_id, "ticket_created", {"ticket_id": ticket.get("id")})

        await maybe_enroll_speaker(call_id)

        await play_text_prompt(call_id, channel_id, Step.COMPLETE)
        await ari.delete(f"/channels/{channel_id}")
        return

    await play_text_prompt(call_id, channel_id, new_step)
    if new_step in {Step.FIO, Step.DEPARTMENT, Step.CABINET, Step.PROBLEM, Step.EXTRA}:
        await start_step_recording(call_id, channel_id, new_step)


async def process_ari_event(event: dict) -> None:
    event_type = event.get("type")
    if event_type == "StasisStart":
        ch = event["channel"]
        channel_id = ch["id"]
        call_id = channel_id
        channel_to_call[channel_id] = call_id
        sessions[call_id] = CallFSM(call_id=call_id)
        sessions[call_id].data["caller"] = ch.get("caller", {}).get("number", "")
        await load_runtime_settings()
        await ari.post(f"/channels/{channel_id}/answer")
        await write_call_log(call_id, "call_started", {"caller": ch.get("caller", {}).get("number", "")})
        await handle_step_input(call_id, channel_id, "start")

    elif event_type == "ChannelDtmfReceived":
        channel_id = event["channel"]["id"]
        call_id = channel_to_call.get(channel_id)
        if not call_id:
            return
        digit = event.get("digit", "")
        if digit == "#":
            value = dtmf_buffer[channel_id]
            dtmf_buffer[channel_id] = ""
            fsm = sessions[call_id]
            if fsm.data.get("needs_consent") == "1" and "consent_answer" not in fsm.data:
                fsm.data["consent_answer"] = value or "2"
                await write_call_log(call_id, "speaker_consent_answer", {"answer": fsm.data["consent_answer"]})
                await play_text_prompt(call_id, channel_id, fsm.step)
                if fsm.step in {Step.FIO, Step.DEPARTMENT, Step.CABINET, Step.PROBLEM, Step.EXTRA}:
                    await start_step_recording(call_id, channel_id, fsm.step)
                return
            await handle_step_input(call_id, channel_id, value)
        else:
            dtmf_buffer[channel_id] += digit

    elif event_type == "RecordingFinished":
        rec = event.get("recording", {})
        rec_name = rec.get("name", "")
        rec_meta = recording_meta.get(rec_name)
        if not rec_meta:
            return

        call_id = rec_meta["call_id"]
        channel_id = rec_meta["channel_id"]
        wav_path = rec_meta.get("wav_path", get_wav_path(rec_name))
        wav_exists = os.path.exists(wav_path)
        wav_size = os.path.getsize(wav_path) if wav_exists else 0
        is_valid_audio, invalid_reason = is_valid_wav(wav_path)

        await write_call_log(
            call_id,
            "recording_finished",
            {
                "recording_name": rec_name,
                "step": rec_meta["step"],
                "audio_path": wav_path,
                "audio_exists": wav_exists,
                "audio_size_bytes": wav_size,
                "audio_valid": is_valid_audio,
                "audio_invalid_reason": invalid_reason if not is_valid_audio else "",
            },
        )

        await maybe_identify_speaker(call_id, wav_path)

        text = ""
        if stt_mode == "speechkit":
            try:
                text = await stt_adapter.transcribe(wav_path)
                await write_call_log(call_id, "stt_result", {"text": text, "provider": "speechkit", "audio_path": wav_path})
            except Exception as exc:
                await write_call_log(
                    call_id,
                    "stt_error",
                    {"error": str(exc), "provider": "speechkit", "audio_path": wav_path},
                )
                if not TEST_MODE:
                    raise
        if text:
            await handle_step_input(call_id, channel_id, text)


async def ari_listener() -> None:
    ws_url = f"{ARI_WS}/events?app={ARI_APP}&api_key={ARI_USER}:{ARI_PASSWORD}"
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                state["connected"] = True
                state["last_error"] = ""
                async for message in ws:
                    await process_ari_event(json.loads(message))
        except Exception as exc:
            state["connected"] = False
            state["last_error"] = str(exc)
            await asyncio.sleep(2)


@app.on_event("startup")
async def startup() -> None:
    app.state.listener = asyncio.create_task(ari_listener())


@app.on_event("shutdown")
async def shutdown() -> None:
    app.state.listener.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.listener


@app.get("/health")
async def health() -> dict[str, Any]:
    if not state["connected"]:
        raise HTTPException(status_code=503, detail={"status": "degraded", "reason": state["last_error"]})
    return {"status": "ok", "ari": "connected", "tts": state["tts_provider"], "stt": state["stt_provider"], "test_mode": TEST_MODE}


@app.post("/test-call")
async def test_call() -> dict[str, Any]:
    data = await ari.post(
        "/channels",
        {
            "endpoint": "Local/test@support-test",
            "extension": "s",
            "context": "support-test",
            "priority": 1,
            "app": ARI_APP,
            "callerId": "+79990000003",
            "timeout": 30,
        },
    )
    return {"status": "originated", "channel_id": data.get("id")}


@app.post("/ari/events")
async def manual_event(event: AriEvent) -> dict[str, Any]:
    if event.call_id not in sessions:
        sessions[event.call_id] = CallFSM(call_id=event.call_id)
    if event.type == "Advance":
        sessions[event.call_id].consume(event.text)
    return {"call_id": event.call_id, "step": sessions[event.call_id].step.value, "data": sessions[event.call_id].data}
