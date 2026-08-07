"""merge oauth force_fresh and vault provider_file_id branches

Revision ID: 5e5eb5eb51d0
Revises: 20260520_add_force_fresh_to_oauth_state, 20260601_add_provider_file_id_vault_index
Create Date: 2026-06-06 17:13:26.946715

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e5eb5eb51d0"
down_revision: str | Sequence[str] | None = (
    "20260520_add_force_fresh_to_oauth_state",
    "20260601_add_provider_file_id_vault_index",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
