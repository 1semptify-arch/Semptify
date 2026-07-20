"""expand rent_payments to account ledger

Revision ID: af166c97288d
Revises: 51eaaeeea3a9
Create Date: 2026-07-20 02:00:54.153273

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'af166c97288d'  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = '51eaaeeea3a9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add updated_at to rent_payments for ledger change tracking."""
    op.add_column('rent_payments', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove updated_at from rent_payments."""
    op.drop_column('rent_payments', 'updated_at')
