"""add extraction_pattern to context_facts

Revision ID: 7f002a47b44a
Revises: 9f96d6ec5a65
Create Date: 2026-08-15 06:04:18.003781

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7f002a47b44a'
down_revision: str | Sequence[str] | None = '9f96d6ec5a65'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add extraction_pattern column to context_facts for content-level verification."""
    op.add_column(
        'context_facts',
        sa.Column('extraction_pattern', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop extraction_pattern column."""
    op.drop_column('context_facts', 'extraction_pattern')
