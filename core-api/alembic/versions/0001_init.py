# Updated Alembic Migration

"""This migration updates default values for server_default parameters and corrects PostgreSQL syntax in the Alembic versioning file."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'xxxx_revision'
Down_revision = 'xxxx_down_revision'
Branch_labels = None
Depends_on = None


def upgrade():
    """Apply new defaults and syntax correction"""
    op.alter_column('your_table_name', 'your_column_name',  # replace with actual column
                server_default=sa.text('new_default_value'),  # ensure the new default is valid
                existing_type=sa.String())  # replace with actual type


def downgrade():
    """Revert changes"""
    op.alter_column('your_table_name', 'your_column_name',  # replace with actual column
                server_default=sa.text('old_default_value'),  # revert to old value
                existing_type=sa.String())  # replace with actual type
