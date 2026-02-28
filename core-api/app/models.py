import enum
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UserRole(str, enum.Enum):
    USER = "user"
    SUPPORT = "support"
    ADMIN = "admin"


class TicketStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_USER = "WAITING_USER"
    DELEGATED = "DELEGATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SSOProviderType(str, enum.Enum):
    OIDC = "OIDC"
    SAML = "SAML"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    sso_subject: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assigned_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="web")
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus, name="ticket_status"), default=TicketStatus.NEW, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    owner = relationship("User", foreign_keys=[owner_user_id])
    assigned = relationship("User", foreign_keys=[assigned_user_id])


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class TicketHistory(Base):
    __tablename__ = "ticket_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[TicketStatus | None] = mapped_column(Enum(TicketStatus, name="ticket_status"), nullable=True)
    to_status: Mapped[TicketStatus | None] = mapped_column(Enum(TicketStatus, name="ticket_status"), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class TicketRating(Base):
    __tablename__ = "ticket_ratings"
    __table_args__ = (UniqueConstraint("ticket_id", name="uq_ticket_ratings_ticket_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_voice_profiles_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    external_profile_id: Mapped[str] = mapped_column(String(255), nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    embedding_vector: Mapped[str | None] = mapped_column(Text, nullable=True)
    samples_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


Index("ix_users_phone_number", User.phone_number)
Index("ix_tickets_owner_user_id", Ticket.owner_user_id)
Index("ix_tickets_assigned_user_id", Ticket.assigned_user_id)
Index("ix_tickets_status", Ticket.status)
Index("ix_ticket_comments_ticket_id", TicketComment.ticket_id)
Index("ix_ticket_history_ticket_id", TicketHistory.ticket_id)
Index("ix_ticket_history_correlation_id", TicketHistory.correlation_id)
Index("ix_call_logs_call_id", CallLog.call_id)
Index("ix_call_logs_correlation_id", CallLog.correlation_id)


class SSOProviderConfig(Base):
    __tablename__ = "sso_provider_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_type: Mapped[SSOProviderType] = mapped_column(Enum(SSOProviderType, name="sso_provider_type"), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


Index("ix_sso_provider_configs_enabled", SSOProviderConfig.enabled)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


Index("ix_tickets_channel", Ticket.channel)