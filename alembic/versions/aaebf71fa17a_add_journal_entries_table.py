"""add journal_entries table

Revision ID: aaebf71fa17a
Revises: 573f2a9e816f
Create Date: 2026-07-20 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'aaebf71fa17a'
down_revision: Union[str, Sequence[str], None] = '573f2a9e816f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the journal_entries table for free-form tenant records.

    Made idempotent 2026-08-25: some production databases (e.g. the
    Render-connected `semptifty_db` Neon database) were manually patched
    and already contain a `journal_entries` table while their
    `alembic_version` is still at the previous revision. Creating the table
    again would fail with ``DuplicateTable``. We now create it only if it
    does not already exist, and create the indexes only if they do not
    already exist.
    """
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table('journal_entries'):
        op.create_table(
            'journal_entries',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=128), nullable=False),
            sa.Column('entry_type', sa.String(length=50), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('is_urgent', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('involved_party', sa.String(length=255), nullable=True),
            sa.Column('tags', sa.Text(), nullable=True),
            sa.Column('source', sa.String(length=50), nullable=False, server_default=sa.text("'manual'")),
            sa.Column('document_link', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_journal_entries_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_journal_entries'))
        )

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('journal_entries')}
    if 'ix_journal_entries_user_id' not in existing_indexes:
        op.create_index(op.f('ix_journal_entries_user_id'), 'journal_entries', ['user_id'], unique=False)
    if 'ix_journal_entries_document_link' not in existing_indexes:
        op.create_index(op.f('ix_journal_entries_document_link'), 'journal_entries', ['document_link'], unique=False)


def downgrade() -> None:
    """Drop the journal_entries table."""
    op.drop_index(op.f('ix_journal_entries_user_id'), table_name='journal_entries')
    op.drop_table('journal_entries')
