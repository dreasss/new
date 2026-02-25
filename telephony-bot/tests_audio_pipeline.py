import base64
from pathlib import Path

import app.main as main_mod
import pytest
from app.fsm import CallFSM
from app.main import maybe_enroll_speaker, maybe_identify_speaker, process_ari_event
from app.recordings import get_wav_path


@pytest.fixture(autouse=True)
def reset_state() -> None:
    main_mod.sessions.clear()
    main_mod.channel_to_call.clear()
    main_mod.recording_meta.clear()


def _write_real_wav(path: Path, min_size: int = 512) -> None:
    if min_size < 12:
        min_size = 12
    content = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + (b"\x00" * (min_size - 12))
    path.write_bytes(content)


@pytest.mark.asyncio
async def test_identify_skipped_without_real_wav(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    call_id = "c1"
    main_mod.sessions[call_id] = CallFSM(call_id=call_id)
    main_mod.sessions[call_id].data["caller"] = "+79990000003"

    payloads: list[tuple[str, dict]] = []

    async def fake_core_post(path: str, payload: dict) -> dict:
        payloads.append((path, payload))
        return {}

    monkeypatch.setattr(main_mod, "core_post", fake_core_post)

    missing_wav = str(tmp_path / "missing.wav")
    await maybe_identify_speaker(call_id, missing_wav)

    assert len(payloads) == 1
    assert payloads[0][0] == "/api/v1/call-logs"
    assert payloads[0][1]["event_type"] == "speaker_identify_skipped"


@pytest.mark.asyncio
async def test_enroll_skipped_without_real_wav(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    call_id = "c2"
    fsm = CallFSM(call_id=call_id)
    fsm.data.update(
        {
            "needs_consent": "1",
            "consent_answer": "1",
            "consent_user_id": "7",
            "speaker_sample_path": str(tmp_path / "missing.wav"),
        }
    )
    main_mod.sessions[call_id] = fsm

    payloads: list[tuple[str, dict]] = []

    async def fake_core_post(path: str, payload: dict) -> dict:
        payloads.append((path, payload))
        return {}

    monkeypatch.setattr(main_mod, "core_post", fake_core_post)

    await maybe_enroll_speaker(call_id)

    assert len(payloads) == 1
    assert payloads[0][0] == "/api/v1/call-logs"
    assert payloads[0][1]["event_type"] == "speaker_enroll_skipped"


@pytest.mark.asyncio
async def test_recording_finished_builds_b64_and_calls_identify(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    call_id = "c3"
    channel_id = "ch3"
    rec_name = "c3__fio__20260220T000000000000Z"
    wav_path = Path(get_wav_path(rec_name))
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    _write_real_wav(wav_path, min_size=1024)

    fsm = CallFSM(call_id=call_id)
    fsm.data["caller"] = "+79990000003"
    main_mod.sessions[call_id] = fsm
    main_mod.channel_to_call[channel_id] = call_id
    main_mod.recording_meta[rec_name] = {"channel_id": channel_id, "call_id": call_id, "step": "FIO", "wav_path": str(wav_path)}

    monkeypatch.setattr("app.recordings.RECORDINGS_DIR", str(tmp_path))
    monkeypatch.setattr(main_mod, "stt_mode", "dtmf_fallback")

    payloads: list[tuple[str, dict]] = []

    async def fake_core_post(path: str, payload: dict) -> dict:
        payloads.append((path, payload))
        if path == "/api/v1/speaker/identify":
            return {"consent_required": True, "user_id": 99}
        if path == "/api/v1/call-logs":
            return {"ok": True}
        return {}

    monkeypatch.setattr(main_mod, "core_post", fake_core_post)

    await process_ari_event({"type": "RecordingFinished", "recording": {"name": rec_name}})

    identify_calls = [p for p in payloads if p[0] == "/api/v1/speaker/identify"]
    assert len(identify_calls) == 1
    identify_payload = identify_calls[0][1]
    assert identify_payload["phone_number"] == "+79990000003"
    audio_b64 = identify_payload["audio_sample_b64"]
    assert len(audio_b64) > 100
    decoded = base64.b64decode(audio_b64)
    assert decoded.startswith(b"RIFF")

    assert main_mod.sessions[call_id].data["speaker_sample_path"] == str(wav_path)
    assert main_mod.sessions[call_id].data["needs_consent"] == "1"
    assert main_mod.sessions[call_id].data["consent_user_id"] == "99"
