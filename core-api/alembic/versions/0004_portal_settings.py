"""ticket channel and system settings

Revision ID: 0004_portal
Revises: 0003_speaker
Create Date: 2025-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_portal"
down_revision = "0003_speaker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("channel", sa.String(length=32), nullable=False, server_default="web"))
    op.create_index("ix_tickets_channel", "tickets", ["channel"])

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("section", sa.String(length=64), nullable=False, unique=True),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_index("ix_tickets_channel", table_name="tickets")
    op.drop_column("tickets", "channel")
