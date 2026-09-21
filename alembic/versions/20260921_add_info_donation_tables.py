"""add info_donation tables (post-resolution opt-in info donation)

Revision ID: 20260921_info_donation
Revises: 20260915_vault_checks
Create Date: 2026-09-21 00:00:00.000000

Two tables backing the "help the next tenant" donation flow:
- info_donation_profiles — per-user resolution gate, prompt dismissal, and
  the versioned informed-consent record.
- info_donation_items — one row per donated answer (aggregate-only,
  per-item opt-in, withdrawable; free text held in moderation).

Spec: docs/blueprints/info_donation_blueprint.md +
handoffs/info-donation-possibilities-2026-09-19.md
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260921_info_donation'
down_revision: Union[str, Sequence[str], None] = '20260915_vault_checks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: init_db() runs Base.metadata.create_all during startup and
    # may have already created these tables. Create only what is missing.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'info_donation_profiles' not in existing_tables:
        op.create_table(
            'info_donation_profiles',
            sa.Column('user_id', sa.String(length=128), nullable=False),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolved_source', sa.String(length=60), nullable=True),
            sa.Column('prompt_dismissed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('consent_version', sa.String(length=40), nullable=True),
            sa.Column('consented_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('consent_revoked_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('user_id'),
        )

    if 'info_donation_items' not in existing_tables:
        op.create_table(
            'info_donation_items',
            sa.Column('id', sa.String(length=40), nullable=False),
            sa.Column('user_id', sa.String(length=128), nullable=False),
            sa.Column('item_key', sa.String(length=60), nullable=False),
            sa.Column('value_json', sa.Text(), nullable=False),
            sa.Column('moderation', sa.String(length=20), nullable=False),
            sa.Column('moderated_by', sa.String(length=128), nullable=True),
            sa.Column('moderated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'item_key', name='uq_info_donation_user_item'),
        )
        op.create_index('ix_info_donation_items_user_id', 'info_donation_items', ['user_id'])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())
    if 'info_donation_items' in existing_tables:
        op.drop_table('info_donation_items')
    if 'info_donation_profiles' in existing_tables:
        op.drop_table('info_donation_profiles')
