"""add canonical_value to context_facts

Revision ID: 9f96d6ec5a65
Revises: 8b393a99538e
Create Date: 2026-08-15 05:13:38.330554

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9f96d6ec5a65'
down_revision: str | Sequence[str] | None = '8b393a99538e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add canonical_value column to context_facts for drift detection."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("context_facts")}
    if "canonical_value" not in existing_columns:
        op.add_column(
            'context_facts',
            sa.Column('canonical_value', sa.Text(), nullable=True),
        )


def downgrade() -> None:
    """Drop canonical_value column."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("context_facts")}
    if "canonical_value" in existing_columns:
        op.drop_column('context_facts', 'canonical_value')
