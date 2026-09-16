"""add vault_checks table (test-before-active gate)

Revision ID: 20260915_vault_checks
Revises: 20260914_acc_ledger
Create Date: 2026-09-15 00:00:00.000000

Per-attempt vault verification records: one row per verification run with
status (not_started/initializing/test_pending/verifying/active/failed),
which named check failed, a plain-language detail, and the per-item results
JSON. completed_groups stays the durable progress marks — this table explains
*why* a vault is or isn't active.

Design doc: handoffs/onboarding-gate-timeline-blueprint-2026-09-15.md §7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260915_vault_checks'
down_revision: Union[str, Sequence[str], None] = '20260914_acc_ledger'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: init_db() runs Base.metadata.create_all during startup and
    # may have already created this table. Create only what is missing.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'vault_checks' not in existing_tables:
        op.create_table(
            'vault_checks',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.String(length=128), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('failed_check', sa.String(length=50), nullable=True),
            sa.Column('detail', sa.Text(), nullable=True),
            sa.Column('checks_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_vault_checks_user_id', 'vault_checks', ['user_id'])
        op.create_index('ix_vault_checks_status', 'vault_checks', ['status'])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'vault_checks' in set(insp.get_table_names()):
        op.drop_table('vault_checks')
