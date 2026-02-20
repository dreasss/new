"""speaker profile fields and user phone

Revision ID: 0003_speaker
Revises: 0002_sso
Create Date: 2025-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_speaker"
down_revision = "0002_sso"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_users_phone_number", "users", ["phone_number"])
    op.create_index("ix_users_phone_number", "users", ["phone_number"])

    op.add_column("voice_profiles", sa.Column("embedding_vector", sa.Text(), nullable=True))
    op.add_column("voice_profiles", sa.Column("samples_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("voice_profiles", "samples_count")
    op.drop_column("voice_profiles", "embedding_vector")

    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_constraint("uq_users_phone_number", "users", type_="unique")
    op.drop_column("users", "phone_number")
