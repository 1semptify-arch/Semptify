"""add vault review_state and document_share tables

Revision ID: 8b393a99538e
Revises: 66d6454b5b5d
Create Date: 2026-07-25 17:44:30.056651

Made idempotent 2026-08-25: a prior session hit an error because
document_shares already existed partway through this migration and
worked around it by hand-patching review_state_json directly onto
Neon instead of fixing this script. That left environments where this
revision is stamped as applied but review_state_json was never
actually added (Known Failure Registry #15 pattern). Both steps below
now check-before-act so re-running this migration, or running it
against a DB that already has one of the two objects, is a no-op for
that object instead of a hard failure.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8b393a99538e'
down_revision: Union[str, Sequence[str], None] = '66d6454b5b5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    # Add review_state_json to vault_index for Document Center field confirmations,
    # but only if it isn't already there.
    existing_columns = {col["name"] for col in inspector.get_columns("vault_index")}
    if "review_state_json" not in existing_columns:
        op.add_column('vault_index', sa.Column('review_state_json', sa.Text(), nullable=True))

    # Create document_shares table for real DC sharing, but only if it doesn't exist.
    if not inspector.has_table("document_shares"):
        op.create_table(
            'document_shares',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('owner_user_id', sa.String(128), nullable=False),
            sa.Column('vault_id', sa.String(36), nullable=False),
            sa.Column('recipient_identifier', sa.String(255), nullable=False),
            sa.Column('scope', sa.String(20), nullable=False),
            sa.Column('message', sa.Text(), nullable=True),
            sa.Column('share_token', sa.String(64), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('accessed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('access_count', sa.Integer(), nullable=False, default=0),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_document_shares_owner_user_id', 'document_shares', ['owner_user_id'])
        op.create_index('ix_document_shares_vault_id', 'document_shares', ['vault_id'])
        op.create_index('ix_document_shares_share_token', 'document_shares', ['share_token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_document_shares_share_token', table_name='document_shares')
    op.drop_index('ix_document_shares_vault_id', table_name='document_shares')
    op.drop_index('ix_document_shares_owner_user_id', table_name='document_shares')
    op.drop_table('document_shares')
    op.drop_column('vault_index', 'review_state_json')
