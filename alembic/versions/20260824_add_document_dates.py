"""add document event and received dates

Revision ID: 20260824_add_document_dates
Revises: 20260820_add_case_overlay_id
Create Date: 2026-08-24

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260824_add_document_dates"
down_revision: Union[str, Sequence[str], None] = "20260820_add_case_overlay_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Semptify treats all user-facing dates as ISO strings; the underlying DB stores
# them as nullable timezone-aware timestamps.
_DATE_COLUMN_KWARGS = {
    "type_": sa.DateTime(timezone=True),
    "nullable": True,
}


def _add_columns(table_name: str) -> None:
    """Add event_date and received_date columns to the given table."""
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("event_date", **_DATE_COLUMN_KWARGS))
            batch_op.add_column(sa.Column("received_date", **_DATE_COLUMN_KWARGS))
    else:
        op.add_column(table_name, sa.Column("event_date", **_DATE_COLUMN_KWARGS))
        op.add_column(table_name, sa.Column("received_date", **_DATE_COLUMN_KWARGS))


def _drop_columns(table_name: str) -> None:
    """Drop event_date and received_date columns from the given table."""
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("received_date")
            batch_op.drop_column("event_date")
    else:
        op.drop_column(table_name, "received_date")
        op.drop_column(table_name, "event_date")


def upgrade() -> None:
    """Add event_date and received_date to documents and vault_index."""
    _add_columns("documents")
    _add_columns("vault_index")


def downgrade() -> None:
    """Remove event_date and received_date from documents and vault_index."""
    _drop_columns("documents")
    _drop_columns("vault_index")
