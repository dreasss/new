import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Tuple

from app.fsm import Step

RECORDINGS_DIR = os.getenv("BOT_RECORDINGS_DIR", "/shared/recordings")
MIN_AUDIO_BYTES = int(os.getenv("BOT_MIN_AUDIO_BYTES", "256"))
_timestamp_lock = Lock()
_last_timestamp = ""


def _next_timestamp() -> str:
    global _last_timestamp
    with _timestamp_lock:
        candidate = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        if candidate <= _last_timestamp:
            candidate = f"{_last_timestamp[:-1]}1Z"
        _last_timestamp = candidate
        return candidate


def _sanitize_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)


def start_recording(call_id: str, channel_id: str, step: Step) -> str:  # noqa: ARG001
    safe_call = _sanitize_part(call_id)
    timestamp = _next_timestamp()
    return f"{safe_call}__{step.value.lower()}__{timestamp}"


def get_wav_path(recording_name: str) -> str:
    parts = recording_name.split("__", 2)
    if len(parts) != 3:
        return str(Path(RECORDINGS_DIR) / f"{recording_name}.wav")
    call_id, step_name, timestamp = parts
    return str(Path(RECORDINGS_DIR) / call_id / step_name / f"{timestamp}.wav")


def is_valid_wav(path: str) -> Tuple[bool, str]:
    wav_path = Path(path)
    if not wav_path.exists():
        return False, "missing"

    data = wav_path.read_bytes()
    if len(data) < MIN_AUDIO_BYTES:
        return False, "too_small"

    if len(data) < 12 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        return False, "invalid_header"

    return True, "ok"
