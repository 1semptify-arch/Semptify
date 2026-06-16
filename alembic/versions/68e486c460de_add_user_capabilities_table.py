"""add_user_capabilities_table

Revision ID: 68e486c460de
Revises: 20260615_drop_cert_events_user_fk
Create Date: 2026-06-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '68e486c460de'
down_revision: Union[str, Sequence[str], None] = '20260615_drop_cert_events_user_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_capabilities table."""
    op.create_table(
        'user_capabilities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=256), nullable=False),
        sa.Column('module_name', sa.String(length=256), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('granted_by', sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_capabilities_expires_at', 'user_capabilities', ['expires_at'], unique=False)
    op.create_index('ix_user_capabilities_is_active', 'user_capabilities', ['is_active'], unique=False)
    op.create_index('ix_user_capabilities_module_name', 'user_capabilities', ['module_name'], unique=False)
    op.create_index('ix_user_capabilities_source', 'user_capabilities', ['source'], unique=False)
    op.create_index('ix_user_capabilities_user_id', 'user_capabilities', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop user_capabilities table."""
    op.drop_index('ix_user_capabilities_user_id', table_name='user_capabilities')
    op.drop_index('ix_user_capabilities_source', table_name='user_capabilities')
    op.drop_index('ix_user_capabilities_module_name', table_name='user_capabilities')
    op.drop_index('ix_user_capabilities_is_active', table_name='user_capabilities')
    op.drop_index('ix_user_capabilities_expires_at', table_name='user_capabilities')
    op.drop_table('user_capabilities')
