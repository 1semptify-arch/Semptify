"""Add provider_file_id column to vault_index

Revision ID: 20260601_add_provider_file_id_vault_index
Revises: 20250506_add_mndes_and_vault_index
Create Date: 2026-06-01 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260601_add_provider_file_id_vault_index"
down_revision: str | None = "20250506_add_mndes_and_vault_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add provider_file_id nullable column to vault_index
    op.add_column("vault_index", sa.Column("provider_file_id", sa.String(128), nullable=True))
    # Create an index to help lookups by provider id if desired
    op.create_index("ix_vault_index_provider_file_id", "vault_index", ["provider_file_id"])


def downgrade() -> None:
    op.drop_index("ix_vault_index_provider_file_id", table_name="vault_index")
    op.drop_column("vault_index", "provider_file_id")
