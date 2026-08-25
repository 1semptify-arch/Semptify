"""catch up vault_index.review_state_json if missing

Revision ID: 20260825_vault_review_catchup
Revises: 20260824_add_document_dates
Create Date: 2026-08-25

Some environments (including production Neon) are stamped past
revision 8b393a99538e without actually having review_state_json on
vault_index. That migration originally failed partway through when
document_shares already existed, and a prior session hand-patched the
column onto one database instance instead of fixing the migration
(see BUILD_STATE.md 2026-07-28 and Known Failure Registry #15). That
patch did not stick everywhere, so the column is still missing here
and there, causing UndefinedColumnError on any vault_index query.

8b393a99538e itself has since been made idempotent so this class of
bug cannot recur going forward, but Alembic will not re-run a
migration that is already marked applied. This migration is the
one-time catch-up for databases already past that revision.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "20260825_vault_review_catchup"
down_revision: Union[str, Sequence[str], None] = "20260824_add_document_dates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add review_state_json to vault_index if it is not already there."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("vault_index")}

    if "review_state_json" not in existing_columns:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("vault_index") as batch_op:
                batch_op.add_column(sa.Column("review_state_json", sa.Text(), nullable=True))
        else:
            op.add_column("vault_index", sa.Column("review_state_json", sa.Text(), nullable=True))


def downgrade() -> None:
    """No-op: the column is owned by 8b393a99538e; do not drop it here."""
    pass
