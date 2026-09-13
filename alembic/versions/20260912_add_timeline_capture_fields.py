"""add quick-capture context fields to timeline_events

Revision ID: 20260912_tl_capture
Revises: 35e49b1cefed
Create Date: 2026-09-12 00:00:00.000000

/api/tenant/capture passes who_involved, location, and
attached_document_ids to TimelineEvent — columns that never existed, so
the endpoint 500'd on every submit. These nullable columns make the
quick-capture record (mobile: photo/audio/call logs) real.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260912_tl_capture'
down_revision: Union[str, Sequence[str], None] = '35e49b1cefed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('timeline_events', sa.Column('who_involved', sa.String(255), nullable=True))
    op.add_column('timeline_events', sa.Column('location', sa.String(255), nullable=True))
    op.add_column('timeline_events', sa.Column('attached_document_ids', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('timeline_events', 'attached_document_ids')
    op.drop_column('timeline_events', 'location')
    op.drop_column('timeline_events', 'who_involved')
