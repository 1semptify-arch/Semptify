"""Force widen sessions.user_id to VARCHAR(256) — production emergency fix

The Render DB still has sessions.user_id as VARCHAR(24), causing
'value too long' on INSERT for HMAC-signed user IDs (~66 chars).
Previous migrations in the widen chain may have been skipped due to
a branch dependency mismatch. This migration uses a direct SQL ALTER
with no existing_type assumption so it is safe to run regardless of
current column width.

Revision ID: 20250508_force_widen_sessions_user_id
Revises: 20250507_merge_and_widen_final
Create Date: 2026-05-08
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "20250508_force_widen_sessions_user_id"
down_revision: str | Sequence[str] | None = "20250507_merge_and_widen_final"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE sessions ALTER COLUMN user_id TYPE VARCHAR(256)")
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE VARCHAR(256)")
    op.execute("ALTER TABLE storage_configs ALTER COLUMN user_id TYPE VARCHAR(256)")


def downgrade() -> None:
    pass
