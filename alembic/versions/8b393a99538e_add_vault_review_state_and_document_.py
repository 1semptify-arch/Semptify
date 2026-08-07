"""add vault review_state and document_share tables

Revision ID: 8b393a99538e
Revises: 66d6454b5b5d
Create Date: 2026-07-25 17:44:30.056651

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b393a99538e"
down_revision: str | Sequence[str] | None = "66d6454b5b5d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add review_state_json to vault_index for Document Center field confirmations
    op.add_column("vault_index", sa.Column("review_state_json", sa.Text(), nullable=True))

    # Create document_shares table for real DC sharing
    op.create_table(
        "document_shares",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("owner_user_id", sa.String(128), nullable=False),
        sa.Column("vault_id", sa.String(36), nullable=False),
        sa.Column("recipient_identifier", sa.String(255), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("share_token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_shares_owner_user_id", "document_shares", ["owner_user_id"])
    op.create_index("ix_document_shares_vault_id", "document_shares", ["vault_id"])
    op.create_index("ix_document_shares_share_token", "document_shares", ["share_token"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_document_shares_share_token", table_name="document_shares")
    op.drop_index("ix_document_shares_vault_id", table_name="document_shares")
    op.drop_index("ix_document_shares_owner_user_id", table_name="document_shares")
    op.drop_table("document_shares")
    op.drop_column("vault_index", "review_state_json")
