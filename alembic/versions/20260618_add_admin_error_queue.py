"""add_admin_error_queue

Revision ID: 20260618_add_admin_error_queue
Revises: 20260616_add_missing_tables
Create Date: 2026-06-18

Table admin_error_queue stores errors reported from the admin dashboard
for Cascade to fix. Enables automated error tracking without manual copy-paste.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260618_add_admin_error_queue"
down_revision: str | Sequence[str] | None = "20260616_add_missing_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_error_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("section", sa.String(length=100), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="medium"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_error_queue_status", "admin_error_queue", ["status"], unique=False)
    op.create_index("ix_admin_error_queue_priority", "admin_error_queue", ["priority"], unique=False)
    op.create_index("ix_admin_error_queue_timestamp", "admin_error_queue", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_error_queue_timestamp", table_name="admin_error_queue")
    op.drop_index("ix_admin_error_queue_priority", table_name="admin_error_queue")
    op.drop_index("ix_admin_error_queue_status", table_name="admin_error_queue")
    op.drop_table("admin_error_queue")
