from pathlib import Path

import pytest
# codex/define-architecture-for-support-system-cphd8w
=======
# codex/define-architecture-for-support-system-j19u82
=======
# codex/define-architecture-for-support-system-e3u2rv
# main
# main
from app.providers import (
    LocalFileTTSAdapter,
    ProviderConfigError,
    SpeechKitTTSAdapter,
    build_stt_adapter,
    build_tts_adapter,
)


# codex/define-architecture-for-support-system-cphd8w
=======
# codex/define-architecture-for-support-system-j19u82
=======
from app.providers import LocalFileTTSAdapter, SpeechKitTTSAdapter
# main


# main
# main
@pytest.mark.asyncio
async def test_local_tts_creates_playable_media(tmp_path: Path) -> None:
    adapter = LocalFileTTSAdapter(str(tmp_path))
    media = await adapter.synthesize("Привет", "ermil", 1.0, 0, "greeting")
    assert media.startswith("sound:custom_tts/")
    fname = media.split("/")[-1]
    assert (tmp_path / f"{fname}.wav").exists()


@pytest.mark.asyncio
async def test_speechkit_tts_request_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured = {}

    class Resp:
        status_code = 200
        content = b"\x00\x00" * 160

        def raise_for_status(self):
            return None

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, data=None, headers=None):
            captured["url"] = url
            captured["data"] = data
            captured["headers"] = headers
            return Resp()

    monkeypatch.setattr("app.providers.httpx.AsyncClient", lambda timeout: DummyClient())

    adapter = SpeechKitTTSAdapter("k", "f", str(tmp_path))
    media = await adapter.synthesize("Текст", "ermil", 1.0, 0, "k1")

    assert captured["url"].endswith("/tts:synthesize")
    assert captured["headers"]["Authorization"] == "Api-Key k"
    assert captured["data"]["folderId"] == "f"
    assert captured["data"]["text"] == "Текст"
    assert media.startswith("sound:custom_tts/")
# codex/define-architecture-for-support-system-cphd8w
=======
# codex/define-architecture-for-support-system-j19u82
=======
# codex/define-architecture-for-support-system-e3u2rv
# main
# main


def test_speechkit_provider_requires_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "speechkit")
    monkeypatch.setenv("STT_PROVIDER", "speechkit")
    monkeypatch.delenv("SPEECHKIT_API_KEY", raising=False)
    monkeypatch.delenv("SPEECHKIT_FOLDER_ID", raising=False)

    with pytest.raises(ProviderConfigError):
        build_tts_adapter()

    with pytest.raises(ProviderConfigError):
        build_stt_adapter()


def test_test_mode_uses_local_assets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("INTEGRATIONS_TEST_MODE", "true")
    monkeypatch.setenv("TTS_PROVIDER", "asterisk_assets")
    monkeypatch.setenv("STT_PROVIDER", "test_dtmf")
    monkeypatch.setenv("BOT_SOUNDS_DIR", str(tmp_path))

    tts, tts_mode = build_tts_adapter()
    stt, stt_mode = build_stt_adapter()

    assert isinstance(tts, LocalFileTTSAdapter)
    assert tts_mode == "local_assets"
    assert stt_mode == "dtmf_fallback"
    assert stt is not None
# codex/define-architecture-for-support-system-cphd8w
=======
# codex/define-architecture-for-support-system-j19u82
=======

# main
# main
# main
