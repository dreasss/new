"""add sso subject and config table

Revision ID: 0002_sso
Revises: 0001_init
Create Date: 2025-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_sso"
down_revision = "0001_init"
branch_labels = None
depends_on = None

sso_provider_type = sa.Enum("OIDC", "SAML", name="sso_provider_type")


def upgrade() -> None:
    sso_provider_type.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("sso_subject", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_sso_subject", "users", ["sso_subject"])

    op.create_table(
        "sso_provider_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_type", sso_provider_type, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sso_provider_configs_enabled", "sso_provider_configs", ["enabled"])


def downgrade() -> None:
    op.drop_index("ix_sso_provider_configs_enabled", table_name="sso_provider_configs")
    op.drop_table("sso_provider_configs")
    op.drop_constraint("uq_users_sso_subject", "users", type_="unique")
    op.drop_column("users", "sso_subject")
    sso_provider_type.drop(op.get_bind(), checkfirst=True)
