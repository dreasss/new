import app.main as main_mod
import pytest
from app.fsm import CallFSM, Step


@pytest.fixture(autouse=True)
def clean_state() -> None:
    main_mod.settings_cache.clear()
    main_mod.sessions.clear()


@pytest.mark.asyncio
async def test_load_runtime_settings_populates_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_core_get(path: str) -> dict:
        section = path.rsplit("/", 1)[-1]
        return {"config": {"section": section}}

    monkeypatch.setattr(main_mod, "core_get", fake_core_get)
    await main_mod.load_runtime_settings()

    assert main_mod.settings_cache["phrases"]["section"] == "phrases"
    assert main_mod.settings_cache["speechkit"]["section"] == "speechkit"
    assert main_mod.settings_cache["telephony"]["section"] == "telephony"


@pytest.mark.asyncio
async def test_play_text_prompt_uses_runtime_phrases_and_speech(monkeypatch: pytest.MonkeyPatch) -> None:
    main_mod.settings_cache["phrases"] = {Step.GREETING.value: "Новая фраза"}
    main_mod.settings_cache["speechkit"] = {"voice": "jane", "speed": 1.2, "volume": 10}

    synth_calls: list[dict] = []
    ari_calls: list[dict] = []

    class DummyTTS:
        async def synthesize(self, text: str, voice: str, speed: float, volume: int, key_hint: str) -> str:
            synth_calls.append({"text": text, "voice": voice, "speed": speed, "volume": volume, "key_hint": key_hint})
            return "sound:custom_tts/test"

    class DummyAri:
        async def post(self, path: str, params=None):
            ari_calls.append({"path": path, "params": params})
            return {}

    monkeypatch.setattr(main_mod, "tts_adapter", DummyTTS())
    monkeypatch.setattr(main_mod, "ari", DummyAri())

    await main_mod.play_text_prompt("call-1", "ch-1", Step.GREETING)

    assert synth_calls[0]["text"] == "Новая фраза"
    assert synth_calls[0]["voice"] == "jane"
    assert synth_calls[0]["speed"] == 1.2
    assert synth_calls[0]["volume"] == 10
    assert ari_calls[0]["params"]["media"] == "sound:custom_tts/test"


@pytest.mark.asyncio
async def test_handoff_on_incomplete_uses_runtime_telephony(monkeypatch: pytest.MonkeyPatch) -> None:
    call_id = "c-handoff"
    channel_id = "ch-handoff"

    fsm = CallFSM(call_id=call_id)
    fsm.step = Step.FIO
    fsm.retries[Step.FIO] = 1
    main_mod.sessions[call_id] = fsm
    main_mod.settings_cache["telephony"] = {"handoff_on_incomplete": True}

    class DummyAri:
        def __init__(self):
            self.calls = []

        async def post(self, path: str, params=None):
            self.calls.append(("post", path, params))
            return {}

        async def delete(self, path: str):
            self.calls.append(("delete", path, None))

    async def fake_play(call: str, ch: str, step: Step):
        return None

    async def fake_log(call_id: str, event_type: str, payload: dict):
        return None

    dummy = DummyAri()
    monkeypatch.setattr(main_mod, "ari", dummy)
    monkeypatch.setattr(main_mod, "play_text_prompt", fake_play)
    monkeypatch.setattr(main_mod, "write_call_log", fake_log)

    await main_mod.handle_step_input(call_id, channel_id, "")

    assert ("post", f"/channels/{channel_id}/continue", None) in dummy.calls
    assert not any(call[0] == "delete" for call in dummy.calls)
