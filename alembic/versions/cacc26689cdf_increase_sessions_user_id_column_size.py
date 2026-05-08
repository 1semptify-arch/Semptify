"""increase_sessions_user_id_column_size

Revision ID: cacc26689cdf
Revises: 20250506_add_mndes_and_vault_index
Create Date: 2026-05-06 03:08:51.147186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cacc26689cdf'
down_revision: Union[str, Sequence[str], None] = '81c36d8f2466'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE IF EXISTS sessions ALTER COLUMN user_id TYPE VARCHAR(256)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE IF EXISTS sessions ALTER COLUMN user_id TYPE VARCHAR(24)")
