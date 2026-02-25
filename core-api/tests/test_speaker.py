import base64
import io
import wave

import pytest
from app.db.database import Base
from app.models import User, UserRole
from app.services.speaker import LocalSpeakerRecognizer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def make_wav_b64(freq: float, sr: int = 16000, duration: float = 0.5) -> str:
    import array
    import math

    total = int(sr * duration)
    data = array.array("h")
    for n in range(total):
        val = int(12000 * math.sin(2 * math.pi * freq * n / sr))
        data.append(val)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    local = sessionmaker(bind=engine)
    session = local()
    yield session
    session.close()


def test_enroll_forbidden_without_consent(db: Session) -> None:
    user = User(email="u@a", password_hash="x", role=UserRole.USER, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    recognizer = LocalSpeakerRecognizer()
    with pytest.raises(Exception):
        recognizer.enroll(db, user.id, make_wav_b64(440.0), consent=False, correlation_id="r1")


def test_enroll_increments_samples_count(db: Session) -> None:
    user = User(email="u2@a", password_hash="x", role=UserRole.USER, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    recognizer = LocalSpeakerRecognizer()
    p1 = recognizer.enroll(db, user.id, make_wav_b64(440.0), consent=True, correlation_id="r2")
    assert p1.samples_count == 1
    p2 = recognizer.enroll(db, user.id, make_wav_b64(442.0), consent=True, correlation_id="r3")
    assert p2.samples_count == 2


def test_identify_phone_match_vs_voice_match(db: Session) -> None:
    u1 = User(
        email="caller@a",
        password_hash="x",
        role=UserRole.USER,
        is_active=True,
        phone_number="+100",
    )
    u2 = User(
        email="other@a",
        password_hash="x",
        role=UserRole.USER,
        is_active=True,
        phone_number="+200",
    )
    db.add_all([u1, u2])
    db.commit()
    db.refresh(u1)
    db.refresh(u2)

    recognizer = LocalSpeakerRecognizer()
    recognizer.enroll(db, u1.id, make_wav_b64(440.0), consent=True, correlation_id="r4")
    recognizer.enroll(db, u2.id, make_wav_b64(900.0), consent=True, correlation_id="r5")

    res = recognizer.identify(db, "+100", make_wav_b64(440.0), correlation_id="r6")
    assert res.user_id == u1.id
    assert "phone_match_voice_match" in res.reasons

    res2 = recognizer.identify(db, "+100", make_wav_b64(900.0), correlation_id="r7")
    assert res2.user_id == u2.id
    assert "voice_match" in res2.reasons
