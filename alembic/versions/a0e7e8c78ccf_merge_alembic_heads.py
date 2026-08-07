"""Merge alembic heads

Revision ID: a0e7e8c78ccf
Revises: 20250503_add_package_attestation_tables, 20250504_drop_display
Create Date: 2026-05-06 00:46:53.770915

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0e7e8c78ccf"
down_revision: str | Sequence[str] | None = ("20250503_add_package_attestation_tables", "20250504_drop_display")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
