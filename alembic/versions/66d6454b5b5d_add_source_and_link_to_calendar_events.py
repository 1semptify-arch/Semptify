"""add source and linked_record_id to calendar_events

Revision ID: 66d6454b5b5d
Revises: af166c97288d
Create Date: 2026-07-20 07:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '66d6454b5b5d'
down_revision: str | Sequence[str] | None = 'af166c97288d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add source, linked_record_id, and updated_at columns to calendar_events."""
    op.add_column('calendar_events', sa.Column('source', sa.String(length=50), nullable=True))
    op.add_column('calendar_events', sa.Column('linked_record_id', sa.String(length=255), nullable=True))
    op.add_column('calendar_events', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove source, linked_record_id, and updated_at columns from calendar_events."""
    op.drop_column('calendar_events', 'updated_at')
    op.drop_column('calendar_events', 'linked_record_id')
    op.drop_column('calendar_events', 'source')
