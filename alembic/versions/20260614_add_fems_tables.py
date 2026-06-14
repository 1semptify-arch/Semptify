"""Add FEMS (Forensic Evidence Management System) tables

Revision ID: 20260614_add_fems_tables
Revises: 20260609_add_pattern_records
Create Date: 2026-06-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260614_add_fems_tables'
down_revision = '20260614_merge_heads_before_fems'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'fems_cases',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('case_number', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), nullable=True, server_default='active'),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('case_number', name='uq_fems_cases_case_number'),
    )
    op.create_index('ix_fems_cases_id', 'fems_cases', ['id'])

    op.create_table(
        'fems_documents',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('fems_cases.id'), nullable=True),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('ingested_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('file_hash', name='uq_fems_documents_file_hash'),
    )
    op.create_index('ix_fems_documents_id', 'fems_documents', ['id'])
    op.create_index('ix_fems_documents_file_hash', 'fems_documents', ['file_hash'])

    op.create_table(
        'fems_chunks',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('fems_documents.id'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
    )
    op.create_index('ix_fems_chunks_id', 'fems_chunks', ['id'])

    op.create_table(
        'fems_phone_numbers',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('number', sa.String(50), nullable=False),
        sa.Column('label', sa.String(200), nullable=True),
        sa.Column('first_seen', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('number', name='uq_fems_phone_numbers_number'),
    )
    op.create_index('ix_fems_phone_numbers_id', 'fems_phone_numbers', ['id'])
    op.create_index('ix_fems_phone_numbers_number', 'fems_phone_numbers', ['number'])

    op.create_table(
        'fems_document_phones',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('fems_documents.id'), nullable=False),
        sa.Column('phone_id', sa.Integer(), sa.ForeignKey('fems_phone_numbers.id'), nullable=False),
    )
    op.create_index('ix_fems_document_phones_id', 'fems_document_phones', ['id'])

    op.create_table(
        'fems_quarantine',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('reason', sa.String(200), nullable=True, server_default='duplicate'),
        sa.Column('quarantined_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_fems_quarantine_id', 'fems_quarantine', ['id'])
    op.create_index('ix_fems_quarantine_file_hash', 'fems_quarantine', ['file_hash'])


def downgrade() -> None:
    op.drop_table('fems_document_phones')
    op.drop_table('fems_quarantine')
    op.drop_table('fems_phone_numbers')
    op.drop_table('fems_chunks')
    op.drop_table('fems_documents')
    op.drop_table('fems_cases')
