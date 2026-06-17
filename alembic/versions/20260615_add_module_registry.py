"""add module_registry table

Revision ID: 20260615_add_module_registry
Revises: 20260615_drop_cert_events_user_fk
Create Date: 2026-06-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260615_add_module_registry'
down_revision: Union[str, Sequence[str], None] = '20260616_add_missing_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'module_registry',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('display_name', sa.String(length=256), nullable=False, server_default=''),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='unknown'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('dev_mode', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.String(length=32), nullable=True),
        sa.Column('route_prefix', sa.String(length=128), nullable=True),
        sa.Column('depends_on', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_by', sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    # Index for fast lookups
    op.create_index('ix_module_registry_name', 'module_registry', ['name'], unique=True)
    op.create_index('ix_module_registry_status', 'module_registry', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_module_registry_status', table_name='module_registry')
    op.drop_index('ix_module_registry_name', table_name='module_registry')
    op.drop_table('module_registry')
