from pathlib import Path

import pytest

from app.providers import LocalFileTTSAdapter, SpeechKitTTSAdapter


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
