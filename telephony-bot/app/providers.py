import hashlib
# codex/define-architecture-for-support-system-j19u82
import logging
=======
# codex/define-architecture-for-support-system-e3u2rv
import logging

# main
# main
import os
import struct
import wave
from pathlib import Path
from typing import Protocol

import httpx

# codex/define-architecture-for-support-system-j19u82
=======
# codex/define-architecture-for-support-system-e3u2rv
# main
logger = logging.getLogger(__name__)


class ProviderConfigError(RuntimeError):
    pass


# codex/define-architecture-for-support-system-j19u82
=======
# main

# main
class TTSProviderAdapter(Protocol):
    async def synthesize(self, text: str, voice: str, speed: float, volume: int, key_hint: str) -> str:
        """Return media URI for Asterisk playback, e.g. sound:custom_tts/file"""


class STTProviderAdapter(Protocol):
# codex/define-architecture-for-support-system-j19u82
    async def transcribe(self, wav_path: str) -> str: ...

=======
# codex/define-architecture-for-support-system-e3u2rv
    async def transcribe(self, wav_path: str) -> str: ...

    async def transcribe(self, wav_path: str) -> str:
        ...
# main

# main

class LocalFileTTSAdapter:
    def __init__(self, sounds_dir: str) -> None:
        self.sounds_dir = Path(sounds_dir)
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

    async def synthesize(self, text: str, voice: str, speed: float, volume: int, key_hint: str) -> str:  # noqa: ARG002
        safe = hashlib.sha1(f"{key_hint}:{text}".encode()).hexdigest()[:16]
        wav_path = self.sounds_dir / f"{safe}.wav"
        if not wav_path.exists():
            self._generate_tone_wav(wav_path, seed=safe)
        return f"sound:custom_tts/{safe}"

    @staticmethod
    def _generate_tone_wav(path: Path, seed: str) -> None:
        framerate = 16000
        duration = 0.45
        amplitude = 9000
        freq = 440 + (sum(ord(c) for c in seed) % 240)
        samples = int(framerate * duration)
        with wave.open(str(path), "wb") as wavf:
            wavf.setnchannels(1)
            wavf.setsampwidth(2)
            wavf.setframerate(framerate)
            frames = bytearray()
            for i in range(samples):
                import math

                val = int(amplitude * math.sin(2 * math.pi * freq * i / framerate))
                frames += struct.pack("<h", val)
            wavf.writeframes(bytes(frames))


class SpeechKitTTSAdapter:
    def __init__(self, api_key: str, folder_id: str, sounds_dir: str) -> None:
        self.api_key = api_key
        self.folder_id = folder_id
        self.sounds_dir = Path(sounds_dir)
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

    async def synthesize(self, text: str, voice: str, speed: float, volume: int, key_hint: str) -> str:
        safe = hashlib.sha1(f"{key_hint}:{text}".encode()).hexdigest()[:16]
        wav_path = self.sounds_dir / f"{safe}.wav"
        payload = {
            "text": text,
            "lang": "ru-RU",
            "voice": voice,
            "speed": str(speed),
            "volume": str(volume),
            "format": "lpcm",
            "sampleRateHertz": "16000",
            "folderId": self.folder_id,
        }
# codex/define-architecture-for-support-system-j19u82
        logger.info(
            "speechkit_tts_request folder_id=%s voice=%s speed=%s volume=%s key_hint=%s", self.folder_id, voice, speed, volume, key_hint
        )
=======
# codex/define-architecture-for-support-system-e3u2rv
        logger.info(
            "speechkit_tts_request folder_id=%s voice=%s speed=%s volume=%s key_hint=%s", self.folder_id, voice, speed, volume, key_hint
        )

# main
# main
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
                data=payload,
                headers={"Authorization": f"Api-Key {self.api_key}"},
            )
        response.raise_for_status()
        pcm = response.content
        with wave.open(str(wav_path), "wb") as wavf:
            wavf.setnchannels(1)
            wavf.setsampwidth(2)
            wavf.setframerate(16000)
            wavf.writeframes(pcm)
        return f"sound:custom_tts/{safe}"


class SpeechKitSTTAdapter:
    def __init__(self, api_key: str, folder_id: str) -> None:
        self.api_key = api_key
        self.folder_id = folder_id

    async def transcribe(self, wav_path: str) -> str:
        with open(wav_path, "rb") as f:
            audio = f.read()
# codex/define-architecture-for-support-system-j19u82
        params: dict[str, str | int] = {
=======
# codex/define-architecture-for-support-system-e3u2rv
        params: dict[str, str | int] = {

        params = {
# main
# main
            "lang": "ru-RU",
            "folderId": self.folder_id,
            "format": "lpcm",
            "sampleRateHertz": 16000,
        }
# codex/define-architecture-for-support-system-j19u82
        logger.info("speechkit_stt_request folder_id=%s wav_path=%s bytes=%s", self.folder_id, wav_path, len(audio))
=======
# codex/define-architecture-for-support-system-e3u2rv
        logger.info("speechkit_stt_request folder_id=%s wav_path=%s bytes=%s", self.folder_id, wav_path, len(audio))

# main
# main
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize",
                params=params,
                content=audio,
                headers={"Authorization": f"Api-Key {self.api_key}"},
            )
        response.raise_for_status()
        body = response.json()
        return body.get("result", "").strip()


class EmptySTTAdapter:
    async def transcribe(self, wav_path: str) -> str:  # noqa: ARG002
        return ""


# codex/define-architecture-for-support-system-j19u82
=======
# codex/define-architecture-for-support-system-e3u2rv
# main
def _require_speechkit_credentials(mode: str, key: str, folder: str) -> None:
    if mode == "speechkit" and (not key or not folder):
        raise ProviderConfigError("SpeechKit provider requested but SPEECHKIT_API_KEY/SPEECHKIT_FOLDER_ID are missing")


# codex/define-architecture-for-support-system-j19u82
=======

# main
# main
def build_tts_adapter() -> tuple[TTSProviderAdapter, str]:
    mode = os.getenv("TTS_PROVIDER", "asterisk_assets")
    key = os.getenv("SPEECHKIT_API_KEY", "")
    folder = os.getenv("SPEECHKIT_FOLDER_ID", "")
    sounds_dir = os.getenv("BOT_SOUNDS_DIR", "/shared/sounds/custom_tts")
# codex/define-architecture-for-support-system-j19u82
    _require_speechkit_credentials(mode, key, folder)
    if mode == "speechkit":
=======
# codex/define-architecture-for-support-system-e3u2rv
    _require_speechkit_credentials(mode, key, folder)
    if mode == "speechkit":

    if mode == "speechkit" and key and folder:
# main
# main
        return SpeechKitTTSAdapter(key, folder, sounds_dir), "speechkit"
    return LocalFileTTSAdapter(sounds_dir), "local_assets"


def build_stt_adapter() -> tuple[STTProviderAdapter, str]:
    mode = os.getenv("STT_PROVIDER", "test_dtmf")
    key = os.getenv("SPEECHKIT_API_KEY", "")
    folder = os.getenv("SPEECHKIT_FOLDER_ID", "")
# codex/define-architecture-for-support-system-j19u82
    _require_speechkit_credentials(mode, key, folder)
    if mode == "speechkit":
=======
# codex/define-architecture-for-support-system-e3u2rv
    _require_speechkit_credentials(mode, key, folder)
    if mode == "speechkit":

    if mode == "speechkit" and key and folder:
# main
# main
        return SpeechKitSTTAdapter(key, folder), "speechkit"
    return EmptySTTAdapter(), "dtmf_fallback"
