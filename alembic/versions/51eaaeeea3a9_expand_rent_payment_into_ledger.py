"""expand rent_payments into a full account ledger

Revision ID: 51eaaeeea3a9
Revises: aaebf71fa17a
Create Date: 2026-07-20 06:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "51eaaeeea3a9"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "aaebf71fa17a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ledger fields to rent_payments and relax due_date/status nullability."""
    op.add_column(
        "rent_payments",
        sa.Column("entry_type", sa.String(length=20), nullable=False, server_default=sa.text("'payment'")),
    )
    op.add_column("rent_payments", sa.Column("period_covered", sa.String(length=20), nullable=True))
    op.add_column(
        "rent_payments",
        sa.Column("source", sa.String(length=20), nullable=False, server_default=sa.text("'user_entered'")),
    )
    op.add_column("rent_payments", sa.Column("overlay_link", sa.String(length=255), nullable=True))
    op.alter_column("rent_payments", "due_date", nullable=True)
    op.alter_column("rent_payments", "status", nullable=True)


def downgrade() -> None:
    """Remove ledger fields from rent_payments and restore nullability."""
    op.alter_column("rent_payments", "status", nullable=False)
    op.alter_column("rent_payments", "due_date", nullable=False)
    op.drop_column("rent_payments", "overlay_link")
    op.drop_column("rent_payments", "source")
    op.drop_column("rent_payments", "period_covered")
    op.drop_column("rent_payments", "entry_type")
