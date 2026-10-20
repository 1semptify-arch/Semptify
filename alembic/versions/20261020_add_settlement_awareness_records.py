"""add settlement_or_case_records table

Revision ID: 20261020_settlement_awareness
Revises: 20260923_doc_access_logs
Create Date: 2026-10-20 00:00:00.000000

Adds `settlement_or_case_records` — the Settlement Awareness module's
verified pool of real public housing outcomes (settlements, judgments,
consent decrees, enforcement actions) surfaced next to matching citations
in the Law Linker pop-out.

Every row is a pointer to a real public source, never an AI-authored
interpretation. The read surface re-checks the Part 3B gate on every call:
resolution_status == Resolved, source_url populated, fabrication_check
true, ai_generated false, attested_by naming a human, is_verified true,
and last_verified_date within 90 days. News authorities also require
primary_source_url before a record can resolve. Stale or regressed rows
auto-hide — nothing ever renders a placeholder or stale fallback
(ADR-0009).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261020_settlement_awareness'
down_revision: Union[str, Sequence[str], None] = '20260923_doc_access_logs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'settlement_or_case_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('record_id', sa.String(length=255), nullable=False),
        sa.Column('record_kind', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('parties', sa.String(length=500), nullable=True),
        sa.Column('jurisdiction', sa.String(length=10), nullable=False),
        sa.Column('citation', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=50), nullable=False),
        sa.Column('headline', sa.String(length=300), nullable=True),
        sa.Column('relief_summary', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('primary_source_url', sa.Text(), nullable=True),
        sa.Column('source_authority', sa.String(length=100), nullable=True),
        sa.Column('resolution_status', sa.String(length=20), nullable=False),
        sa.Column('resolution_method', sa.String(length=100), nullable=True),
        sa.Column('resolved_date', sa.String(length=20), nullable=True),
        sa.Column('last_verified_date', sa.String(length=20), nullable=True),
        sa.Column('next_recheck_date', sa.String(length=20), nullable=True),
        sa.Column('ai_generated', sa.Boolean(), nullable=False),
        sa.Column('attested_by', sa.String(length=128), nullable=True),
        sa.Column('fabrication_check', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_id'),
    )
    op.create_index('ix_settlement_or_case_records_record_id',
                    'settlement_or_case_records', ['record_id'])
    op.create_index('ix_settlement_or_case_records_jurisdiction',
                    'settlement_or_case_records', ['jurisdiction'])
    op.create_index('ix_settlement_or_case_records_citation',
                    'settlement_or_case_records', ['citation'])
    op.create_index('ix_settlement_or_case_records_subject',
                    'settlement_or_case_records', ['subject'])
    op.create_index('ix_settlement_or_case_records_next_recheck_date',
                    'settlement_or_case_records', ['next_recheck_date'])
    op.create_index('ix_settlement_records_surface',
                    'settlement_or_case_records',
                    ['subject', 'resolution_status'])


def downgrade() -> None:
    op.drop_index('ix_settlement_records_surface',
                  table_name='settlement_or_case_records')
    op.drop_index('ix_settlement_or_case_records_next_recheck_date',
                  table_name='settlement_or_case_records')
    op.drop_index('ix_settlement_or_case_records_subject',
                  table_name='settlement_or_case_records')
    op.drop_index('ix_settlement_or_case_records_citation',
                  table_name='settlement_or_case_records')
    op.drop_index('ix_settlement_or_case_records_jurisdiction',
                  table_name='settlement_or_case_records')
    op.drop_index('ix_settlement_or_case_records_record_id',
                  table_name='settlement_or_case_records')
    op.drop_table('settlement_or_case_records')
