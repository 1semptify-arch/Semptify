"""add tags column to timeline_events

Revision ID: 20260913_tl_tags
Revises: 20260912_tl_capture
Create Date: 2026-09-13 00:00:00.000000

Retaliation tracker needs structured subtypes on timeline events —
protected_action ("repair_request", "agency_complaint") and
adverse_action ("eviction_notice", "rent_increase") — so the correlation
analysis can classify events without parsing titles. JSON array of strings,
same Text-JSON pattern as attached_document_ids.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260913_tl_tags'
down_revision: Union[str, Sequence[str], None] = '20260912_tl_capture'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('timeline_events', sa.Column('tags', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('timeline_events', 'tags')
