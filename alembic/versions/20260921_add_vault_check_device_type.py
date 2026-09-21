"""add device_type column to vault_checks

Revision ID: 20260921_vc_device_type
Revises: 20260915_vault_checks
Create Date: 2026-09-21 00:00:00.000000

Nullable device_type ('mobile'/'tablet'/'desktop') on per-attempt vault
verification rows. Recorded only for roles whose role_configs/{role}.json
opts in via record_device_type — tenant and unknown roles stay NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260921_vc_device_type'
down_revision: Union[str, Sequence[str], None] = '20260915_vault_checks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: init_db() runs Base.metadata.create_all during startup and
    # may have already added this column. Add only what is missing.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'vault_checks' not in set(insp.get_table_names()):
        return
    cols = {c['name'] for c in insp.get_columns('vault_checks')}
    if 'device_type' not in cols:
        op.add_column('vault_checks', sa.Column('device_type', sa.String(20), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'vault_checks' not in set(insp.get_table_names()):
        return
    cols = {c['name'] for c in insp.get_columns('vault_checks')}
    if 'device_type' in cols:
        op.drop_column('vault_checks', 'device_type')
