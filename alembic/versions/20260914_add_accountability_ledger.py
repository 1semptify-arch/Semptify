"""add accountability ledger tables + FK on eviction_timeline_events.subject_id

Revision ID: 20260914_acc_ledger
Revises: 20260913_tl_tags
Create Date: 2026-09-14 00:00:00.000000

Creates the accountability ledger foundation:
  - accountability_subjects (landlords, LLCs, judges, politicians, agencies)
  - accountability_patterns (documented, evidence-backed behavior patterns)
  - political_alignments (campaign donations, voting records, rulings)

Also wires the FK on eviction_timeline_events.subject_id -> accountability_subjects.id,
resolving the placeholder documented in app/models/models.py and the open
decision from handoffs/filedored-housing-accountability-options-2026-09-08.md.

Design doc: handoffs/accountability-platform-design-2026-09-14.md
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260914_acc_ledger'
down_revision: Union[str, Sequence[str], None] = '20260913_tl_tags'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: init_db() runs Base.metadata.create_all during startup and
    # may have already created these tables (this is what happened on prod —
    # the create_table calls below collided and the deploy failed). Skip any
    # table/index/FK that already exists; create only what is missing.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'accountability_subjects' not in existing_tables:
        op.create_table(
            'accountability_subjects',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('subject_type', sa.String(30), nullable=False),
            sa.Column('canonical_name', sa.String(255), nullable=False),
            sa.Column('aliases', sa.Text(), nullable=True),  # JSON array
            sa.Column('jurisdiction', sa.String(10), nullable=False, server_default='MN'),
            sa.Column('metadata_json', sa.Text(), nullable=True),  # JSON
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _ensure_indexes(bind, 'accountability_subjects', {
        'ix_accountability_subjects_subject_type': ['subject_type'],
        'ix_accountability_subjects_canonical_name': ['canonical_name'],
        'ix_accountability_subjects_jurisdiction': ['jurisdiction'],
    })

    if 'accountability_patterns' not in existing_tables:
        op.create_table(
            'accountability_patterns',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('subject_id', sa.String(36), sa.ForeignKey('accountability_subjects.id'), nullable=False),
            sa.Column('pattern_type', sa.String(40), nullable=False),
            sa.Column('severity', sa.String(10), nullable=False, server_default='medium'),
            sa.Column('instance_count', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('evidence_refs', sa.Text(), nullable=True),  # JSON array
            sa.Column('first_observed', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_observed', sa.DateTime(timezone=True), nullable=True),
            sa.Column('jurisdiction', sa.String(10), nullable=False, server_default='MN'),
            sa.Column('legal_basis', sa.String(255), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='documented'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _ensure_indexes(bind, 'accountability_patterns', {
        'ix_accountability_patterns_subject_id': ['subject_id'],
        'ix_accountability_patterns_pattern_type': ['pattern_type'],
        'ix_accountability_patterns_jurisdiction': ['jurisdiction'],
        'ix_accountability_patterns_first_observed': ['first_observed'],
        'ix_accountability_patterns_last_observed': ['last_observed'],
    })

    if 'political_alignments' not in existing_tables:
        op.create_table(
            'political_alignments',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('subject_id', sa.String(36), sa.ForeignKey('accountability_subjects.id'), nullable=False),
            sa.Column('alignment_type', sa.String(30), nullable=False),
            sa.Column('source', sa.String(30), nullable=False),
            sa.Column('source_ref', sa.Text(), nullable=True),  # JSON
            sa.Column('amount', sa.Float(), nullable=True),
            sa.Column('date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('description', sa.String(255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _ensure_indexes(bind, 'political_alignments', {
        'ix_political_alignments_subject_id': ['subject_id'],
        'ix_political_alignments_alignment_type': ['alignment_type'],
        'ix_political_alignments_date': ['date'],
    })

    # Wire the FK on eviction_timeline_events.subject_id (was a placeholder
    # with no FK). Match on the referenced table + column, not the constraint
    # name — create_all may have made it under the auto name
    # eviction_timeline_events_subject_id_fkey.
    if 'eviction_timeline_events' in existing_tables:
        subject_fk_exists = any(
            fk['referred_table'] == 'accountability_subjects'
            and 'subject_id' in fk['constrained_columns']
            for fk in insp.get_foreign_keys('eviction_timeline_events')
        )
        if not subject_fk_exists:
            op.create_foreign_key(
                'fk_eviction_timeline_subject',
                'eviction_timeline_events',
                'accountability_subjects',
                ['subject_id'],
                ['id'],
                ondelete='SET NULL',
            )


def _ensure_indexes(bind, table: str, wanted: dict) -> None:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return
    existing = {ix['name'] for ix in insp.get_indexes(table)}
    for name, columns in wanted.items():
        if name not in existing:
            op.create_index(name, table, columns)


def downgrade() -> None:
    op.drop_constraint('fk_eviction_timeline_subject', 'eviction_timeline_events', type_='foreignkey')
    op.drop_index('ix_political_alignments_date', table_name='political_alignments')
    op.drop_index('ix_political_alignments_alignment_type', table_name='political_alignments')
    op.drop_index('ix_political_alignments_subject_id', table_name='political_alignments')
    op.drop_table('political_alignments')
    op.drop_index('ix_accountability_patterns_last_observed', table_name='accountability_patterns')
    op.drop_index('ix_accountability_patterns_first_observed', table_name='accountability_patterns')
    op.drop_index('ix_accountability_patterns_jurisdiction', table_name='accountability_patterns')
    op.drop_index('ix_accountability_patterns_pattern_type', table_name='accountability_patterns')
    op.drop_index('ix_accountability_patterns_subject_id', table_name='accountability_patterns')
    op.drop_table('accountability_patterns')
    op.drop_index('ix_accountability_subjects_jurisdiction', table_name='accountability_subjects')
    op.drop_index('ix_accountability_subjects_canonical_name', table_name='accountability_subjects')
    op.drop_index('ix_accountability_subjects_subject_type', table_name='accountability_subjects')
    op.drop_table('accountability_subjects')
