"""add document_access_logs table

Revision ID: 20260923_doc_access_logs
Revises: 20260921_find_help
Create Date: 2026-09-23 00:00:00.000000

Adds `document_access_logs` — an append-only audit trail for cross-party
access to tenant documents (advocate/legal roles viewing, annotating,
reviewing, or deleting overlays on a tenant's file). `vault_audit_logs`
cannot carry this because it is keyed to `vault_items.item_id` while
advocate-facing document access is keyed to `documents.id` (string).

Rows are write-once; no API exposes update or delete.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260923_doc_access_logs'
down_revision: Union[str, Sequence[str], None] = '20260921_find_help'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_access_logs',
        sa.Column('log_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('actor_user_id', sa.String(length=128), nullable=False),
        sa.Column('actor_role', sa.String(length=20), nullable=True),
        sa.Column('tenant_user_id', sa.String(length=128), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('outcome', sa.String(length=20), nullable=False),
        sa.Column('detail', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('log_id'),
    )
    op.create_index('ix_document_access_logs_actor_user_id', 'document_access_logs', ['actor_user_id'])
    op.create_index('ix_document_access_logs_tenant_user_id', 'document_access_logs', ['tenant_user_id'])
    op.create_index('ix_document_access_logs_document_id', 'document_access_logs', ['document_id'])
    op.create_index('ix_document_access_logs_timestamp', 'document_access_logs', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_document_access_logs_timestamp', table_name='document_access_logs')
    op.drop_index('ix_document_access_logs_document_id', table_name='document_access_logs')
    op.drop_index('ix_document_access_logs_tenant_user_id', table_name='document_access_logs')
    op.drop_index('ix_document_access_logs_actor_user_id', table_name='document_access_logs')
    op.drop_table('document_access_logs')
