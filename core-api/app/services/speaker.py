import base64
import io
import json
import math
import wave
from dataclasses import dataclass
from typing import Protocol

from app.models import CallLog, User, VoiceProfile
from fastapi import HTTPException
from sqlalchemy.orm import Session


@dataclass
class IdentifyResult:
    user_id: int | None
    confidence: float
    reasons: list[str]
    consent_required: bool = False


class SpeakerRecognizer(Protocol):
    def enroll(self, db: Session, user_id: int, audio_sample: str, consent: bool, correlation_id: str) -> VoiceProfile: ...

    def identify(self, db: Session, phone_number: str, audio_sample: str, correlation_id: str) -> IdentifyResult: ...


def _decode_wav_features(audio_b64: str) -> list[float]:
    try:
        raw = base64.b64decode(audio_b64)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid base64 audio: {exc}") from exc

    try:
        with wave.open(io.BytesIO(raw), "rb") as wavf:
            frames = wavf.readframes(wavf.getnframes())
            channels = wavf.getnchannels()
            width = wavf.getsampwidth()
            rate = wavf.getframerate()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid wav audio: {exc}") from exc

    if width != 2:
        raise HTTPException(status_code=422, detail="Only 16-bit PCM wav is supported")

    import array

    samples = array.array("h", frames)
    if channels > 1:
        samples = array.array("h", samples[::channels])
    if not samples:
        raise HTTPException(status_code=422, detail="Empty audio sample")

    vals = [s / 32768.0 for s in samples]
    mean_abs = sum(abs(v) for v in vals) / len(vals)
    energy = sum(v * v for v in vals) / len(vals)
    zc = sum(1 for i in range(1, len(vals)) if vals[i - 1] * vals[i] < 0) / max(len(vals) - 1, 1)
    duration = len(vals) / float(rate)
    peak = max(abs(v) for v in vals)
    std = math.sqrt(sum((v) ** 2 for v in vals) / len(vals))
    return [mean_abs, energy, zc, duration, peak, std]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


class LocalSpeakerRecognizer:
    threshold = 0.84

    def enroll(self, db: Session, user_id: int, audio_sample: str, consent: bool, correlation_id: str) -> VoiceProfile:
        if not consent:
            raise HTTPException(status_code=403, detail="Consent is required for voiceprint enrollment")

        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        emb = _decode_wav_features(audio_sample)
        profile = db.query(VoiceProfile).filter(VoiceProfile.user_id == user_id).first()
        if not profile:
            profile = VoiceProfile(
                user_id=user_id,
                provider="local_features",
                external_profile_id=f"local:{user_id}",
                consent_given=True,
                embedding_vector=json.dumps(emb),
                samples_count=1,
            )
        else:
            if not profile.consent_given:
                raise HTTPException(status_code=403, detail="Consent is required for voiceprint enrollment")
            prev = json.loads(profile.embedding_vector) if profile.embedding_vector else [0.0] * len(emb)
            n = max(profile.samples_count, 0)
            merged = [((prev[i] * n) + emb[i]) / (n + 1) for i in range(len(emb))]
            profile.embedding_vector = json.dumps(merged)
            profile.samples_count = n + 1

        db.add(profile)
        db.add(
            CallLog(
                call_id=f"speaker-enroll-{user_id}",
                ticket_id=None,
                event_type="speaker_enroll",
                payload_json=json.dumps({"user_id": user_id, "samples_count": profile.samples_count}),
                correlation_id=correlation_id,
            )
        )
        db.commit()
        db.refresh(profile)
        return profile

    def identify(self, db: Session, phone_number: str, audio_sample: str, correlation_id: str) -> IdentifyResult:
        emb = _decode_wav_features(audio_sample)
        phone_user = db.query(User).filter(User.phone_number == phone_number).first()
        if phone_user:
            phone_profile = db.query(VoiceProfile).filter(VoiceProfile.user_id == phone_user.id).first()
            if not phone_profile or not phone_profile.consent_given:
                db.add(
                    CallLog(
                        call_id=f"speaker-identify-{phone_number}",
                        ticket_id=None,
                        event_type="speaker_identify_consent_required",
                        payload_json=json.dumps({"phone_number": phone_number, "user_id": phone_user.id}),
                        correlation_id=correlation_id,
                    )
                )
                db.commit()
                return IdentifyResult(
                    user_id=phone_user.id,
                    confidence=0.0,
                    reasons=["consent_required"],
                    consent_required=True,
                )

        best_user = None
        best_score = -1.0
        for profile in db.query(VoiceProfile).filter(VoiceProfile.consent_given.is_(True)).all():
            if not profile.embedding_vector:
                continue
            prof_emb = json.loads(profile.embedding_vector)
            score = _cosine(emb, prof_emb)
            if score > best_score:
                best_score = score
                best_user = profile.user_id

        reasons: list[str] = []
        if phone_user and best_user == phone_user.id and best_score >= self.threshold:
            reasons.append("phone_match_voice_match")
            result = IdentifyResult(user_id=best_user, confidence=best_score, reasons=reasons)
        elif best_score >= self.threshold:
            reasons.append("voice_match")
            result = IdentifyResult(user_id=best_user, confidence=best_score, reasons=reasons)
        else:
            if phone_user:
                reasons.append("phone_match_but_voice_low")
            else:
                reasons.append("no_match")
            result = IdentifyResult(user_id=None, confidence=max(best_score, 0.0), reasons=reasons)

        db.add(
            CallLog(
                call_id=f"speaker-identify-{phone_number}",
                ticket_id=None,
                event_type="speaker_identify",
                payload_json=json.dumps(
                    {
                        "phone_number": phone_number,
                        "result_user_id": result.user_id,
                        "confidence": result.confidence,
                        "reasons": result.reasons,
                    }
                ),
                correlation_id=correlation_id,
            )
        )
        db.commit()
        return result
