import time
from pathlib import Path

import app.recordings as recordings
import pytest
from app.fsm import Step


def test_start_recording_name_and_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(recordings, "RECORDINGS_DIR", str(tmp_path))
    rec_name = recordings.start_recording("call-1", "channel-1", Step.FIO)

    parts = rec_name.split("__")
    assert len(parts) == 3
    assert parts[0] == "call-1"
    assert parts[1] == "fio"

    wav_path = recordings.get_wav_path(rec_name)
    assert wav_path.startswith(str(tmp_path))
    assert "/call-1/fio/" in wav_path
    assert wav_path.endswith(".wav")


def test_start_recording_has_no_collisions() -> None:
    first = recordings.start_recording("call-2", "channel-2", Step.PROBLEM)
    time.sleep(0.001)
    second = recordings.start_recording("call-2", "channel-2", Step.PROBLEM)
    assert first != second


def test_is_valid_wav_for_valid_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(recordings, "MIN_AUDIO_BYTES", 16)
    path = tmp_path / "ok.wav"
    path.write_bytes(b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + b"\x00" * 32)

    valid, reason = recordings.is_valid_wav(str(path))
    assert valid is True
    assert reason == "ok"


def test_is_valid_wav_for_invalid_header(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(recordings, "MIN_AUDIO_BYTES", 16)
    path = tmp_path / "bad.wav"
    path.write_bytes(b"NOTWAV" + b"\x00" * 32)

    valid, reason = recordings.is_valid_wav(str(path))
    assert valid is False
    assert reason == "invalid_header"


def test_is_valid_wav_for_too_small_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(recordings, "MIN_AUDIO_BYTES", 64)
    path = tmp_path / "small.wav"
    path.write_bytes(b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE")

    valid, reason = recordings.is_valid_wav(str(path))
    assert valid is False
    assert reason == "too_small"
