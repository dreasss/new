from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import TicketStatus, UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TicketCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=3, max_length=5000)


class TicketCommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class TicketAssignRequest(BaseModel):
    assigned_user_id: int = Field(gt=0)


class TicketStatusRequest(BaseModel):
    status: TicketStatus


class TicketCloseRequest(BaseModel):
    resolution_comment: str = Field(min_length=3, max_length=5000)


class TicketRatingRequest(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole


class TicketResponse(BaseModel):
    id: int
    owner_user_id: int
    assigned_user_id: int | None
    subject: str
    description: str
    status: TicketStatus
    created_at: datetime
    updated_at: datetime


class TicketCommentResponse(BaseModel):
    id: int
    ticket_id: int
    author_user_id: int
    content: str
    created_at: datetime


class TicketHistoryResponse(BaseModel):
    id: int
    ticket_id: int
    actor_user_id: int | None
    action: str
    from_status: TicketStatus | None
    to_status: TicketStatus | None
    metadata_json: str
    correlation_id: str
    created_at: datetime


class SSOConfigUpsertRequest(BaseModel):
    provider_type: str
    enabled: bool
    config: dict


class SSOConfigResponse(BaseModel):
    id: int
    provider_type: str
    enabled: bool
    config: dict


class SpeakerEnrollRequest(BaseModel):
    audio_sample_b64: str = Field(min_length=16)
    consent: bool
    user_id: int | None = None


class SpeakerIdentifyRequest(BaseModel):
    phone_number: str = Field(min_length=5, max_length=32)
    audio_sample_b64: str = Field(min_length=16)


class SpeakerIdentifyResponse(BaseModel):
    user_id: int | None
    confidence: float
    reasons: list[str]
    consent_required: bool = False


class SpeakerEnrollResponse(BaseModel):
    user_id: int
    samples_count: int
    consent_given: bool


class TicketCreatePortalRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=3, max_length=5000)
    channel: str = Field(default="web", max_length=32)


class SystemSettingRequest(BaseModel):
    config: dict


class SystemSettingResponse(BaseModel):
    section: str
    config: dict
