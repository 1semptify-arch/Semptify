"""increase_sessions_user_id_column_size

Revision ID: cacc26689cdf
Revises: 20250506_add_mndes_and_vault_index
Create Date: 2026-05-06 03:08:51.147186

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cacc26689cdf"
down_revision: str | Sequence[str] | None = "81c36d8f2466"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    VALID_TABLES = {"sessions"}
    table = "sessions"
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table name: {table}")
    op.execute("ALTER TABLE IF EXISTS sessions ALTER COLUMN user_id TYPE VARCHAR(256)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE IF EXISTS sessions ALTER COLUMN user_id TYPE VARCHAR(24)")
