"""Merge all heads and widen user_id columns to VARCHAR(128)

This migration merges the two Alembic heads:
- 20250506_add_mndes_and_vault_index (main chain)
- 20250507_widen_user_id_columns (widen branch)

And ensures sessions.user_id, users.id, storage_configs.user_id, and all FK
columns are widened to VARCHAR(128) to support the new HMAC-signed user_id
format (~66 chars).

Revision ID: 20250507_merge_and_widen_final
Revises: 20250506_add_mndes_and_vault_index, 20250507_widen_user_id_columns
Create Date: 2026-05-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20250507_merge_and_widen_final'
down_revision: Union[str, Sequence[str], None] = (
    '20250506_add_mndes_and_vault_index',
    '20250507_widen_user_id_columns',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge point — all widening already done by 20250507_widen_user_id_columns."""
    pass


def downgrade() -> None:
    pass