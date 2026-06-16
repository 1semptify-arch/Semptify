"""add_admin_audit_logs_and_document_annotations

Revision ID: 20260616_add_missing_tables
Revises: 68e486c460de
Create Date: 2026-06-16

Tables admin_audit_logs and document_annotations were defined in models.py
but had no migration — they did not exist on Render PostgreSQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260616_add_missing_tables'
down_revision: Union[str, Sequence[str], None] = '68e486c460de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'admin_audit_logs',
        sa.Column('log_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('admin_user_id', sa.String(length=256), nullable=False),
        sa.Column('admin_role', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target_user', sa.String(length=256), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('log_id'),
    )
    op.create_index('ix_admin_audit_logs_admin_user_id', 'admin_audit_logs', ['admin_user_id'], unique=False)
    op.create_index('ix_admin_audit_logs_action', 'admin_audit_logs', ['action'], unique=False)
    op.create_index('ix_admin_audit_logs_target_user', 'admin_audit_logs', ['target_user'], unique=False)
    op.create_index('ix_admin_audit_logs_timestamp', 'admin_audit_logs', ['timestamp'], unique=False)

    op.create_table(
        'document_annotations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('footnote_number', sa.Integer(), nullable=False),
        sa.Column('category_number', sa.Integer(), nullable=False),
        sa.Column('extraction_code', sa.String(length=10), nullable=False),
        sa.Column('highlight_text', sa.Text(), nullable=False),
        sa.Column('annotation_note', sa.Text(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('position_x', sa.Float(), nullable=False),
        sa.Column('position_y', sa.Float(), nullable=False),
        sa.Column('position_width', sa.Float(), nullable=False),
        sa.Column('position_height', sa.Float(), nullable=False),
        sa.Column('linked_event_id', sa.String(length=36), nullable=True),
        sa.Column('detection_method', sa.String(length=20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_document_annotations_document_id', 'document_annotations', ['document_id'], unique=False)
    op.create_index('ix_document_annotations_user_id', 'document_annotations', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_document_annotations_user_id', table_name='document_annotations')
    op.drop_index('ix_document_annotations_document_id', table_name='document_annotations')
    op.drop_table('document_annotations')

    op.drop_index('ix_admin_audit_logs_timestamp', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_target_user', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_action', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_admin_user_id', table_name='admin_audit_logs')
    op.drop_table('admin_audit_logs')
