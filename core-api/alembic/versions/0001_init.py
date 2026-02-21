"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2025-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


user_role = sa.Enum("user", "support", "admin", name="user_role")
ticket_status = sa.Enum(
    "NEW",
    "IN_PROGRESS",
    "WAITING_USER",
    "DELEGATED",
    "RESOLVED",
    "CLOSED",
    name="ticket_status",
)


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    ticket_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", ticket_status, nullable=False, server_default="NEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "ticket_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "ticket_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("from_status", ticket_status, nullable=True),
        sa.Column("to_status", ticket_status, nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "ticket_ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("score BETWEEN 1 AND 5", name="ck_ticket_ratings_score_range"),
        sa.UniqueConstraint("ticket_id", name="uq_ticket_ratings_ticket_id"),
    )

    op.create_table(
        "voice_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_profile_id", sa.String(length=255), nullable=False),
        sa.Column("consent_given", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", name="uq_voice_profiles_user_id"),
    )

    op.create_table(
        "call_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("call_id", sa.String(length=128), nullable=False),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_tickets_owner_user_id", "tickets", ["owner_user_id"])
    op.create_index("ix_tickets_assigned_user_id", "tickets", ["assigned_user_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_ticket_comments_ticket_id", "ticket_comments", ["ticket_id"])
    op.create_index("ix_ticket_history_ticket_id", "ticket_history", ["ticket_id"])
    op.create_index("ix_ticket_history_correlation_id", "ticket_history", ["correlation_id"])
    op.create_index("ix_call_logs_call_id", "call_logs", ["call_id"])
    op.create_index("ix_call_logs_correlation_id", "call_logs", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_call_logs_correlation_id", table_name="call_logs")
    op.drop_index("ix_call_logs_call_id", table_name="call_logs")
    op.drop_index("ix_ticket_history_correlation_id", table_name="ticket_history")
    op.drop_index("ix_ticket_history_ticket_id", table_name="ticket_history")
    op.drop_index("ix_ticket_comments_ticket_id", table_name="ticket_comments")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_assigned_user_id", table_name="tickets")
    op.drop_index("ix_tickets_owner_user_id", table_name="tickets")

    op.drop_table("call_logs")
    op.drop_table("voice_profiles")
    op.drop_table("ticket_ratings")
    op.drop_table("ticket_history")
    op.drop_table("ticket_comments")
    op.drop_table("tickets")
    op.drop_table("users")

    ticket_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
