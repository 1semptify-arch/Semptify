"""Add owner_user_id to FEMS tables for per-user scoping

Revision ID: 20261122_add_fems_owner
Revises: 20250422_unified_timeline, 20260614_add_fems_tables
Create Date: 2026-11-22 00:00:00.000000

Rows written before this migration have NULL owner_user_id and are
therefore hidden from every user (the router filters on owner).
"""
import sqlalchemy as sa

from alembic import op

revision = '20261122_add_fems_owner'
down_revision = ('20250422_unified_timeline', '20260614_add_fems_tables')
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('fems_cases', sa.Column('owner_user_id', sa.String(100), nullable=True))
    op.add_column('fems_documents', sa.Column('owner_user_id', sa.String(100), nullable=True))
    op.add_column('fems_quarantine', sa.Column('owner_user_id', sa.String(100), nullable=True))
    op.create_index('ix_fems_cases_owner_user_id', 'fems_cases', ['owner_user_id'])
    op.create_index('ix_fems_documents_owner_user_id', 'fems_documents', ['owner_user_id'])
    op.create_index('ix_fems_quarantine_owner_user_id', 'fems_quarantine', ['owner_user_id'])


def downgrade() -> None:
    op.drop_index('ix_fems_quarantine_owner_user_id', 'fems_quarantine')
    op.drop_index('ix_fems_documents_owner_user_id', 'fems_documents')
    op.drop_index('ix_fems_cases_owner_user_id', 'fems_cases')
    op.drop_column('fems_quarantine', 'owner_user_id')
    op.drop_column('fems_documents', 'owner_user_id')
    op.drop_column('fems_cases', 'owner_user_id')
