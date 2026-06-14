"""Merge dual heads before FEMS tables

Revision ID: 20260614_merge_heads_before_fems
Revises: 20260609_add_pattern_records, 5e5eb5eb51d0
Create Date: 2026-06-14 00:00:00.000000

"""
from alembic import op

revision = '20260614_merge_heads_before_fems'
down_revision = ('20260609_add_pattern_records', '5e5eb5eb51d0')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
