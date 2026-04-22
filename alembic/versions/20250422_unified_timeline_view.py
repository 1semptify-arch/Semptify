"""
Unified Timeline View & Indexes

Revision ID: 20250422_unified_timeline
Revises: 81c36d8f2466
Create Date: 2025-04-22

This migration creates:
1. unified_timeline database view for aggregated chronology queries
2. GIN indexes on vault_items JSONB columns
3. Composite indexes for common timeline queries
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20250422_unified_timeline'
down_revision = '81c36d8f2466'
branch_labels = None
depends_on = None


def upgrade():
    # Create unified timeline view
    op.execute(text("""
        CREATE OR REPLACE VIEW unified_timeline AS
        WITH all_items AS (
            -- Documents
            SELECT 
                d.id,
                d.user_id,
                'document'::text as item_type,
                d.filename as title,
                d.description,
                d.document_type as item_subtype,
                d.uploaded_at as semptify_entry_time,
                d.uploaded_at as record_time,
                NULL::timestamp with time zone as event_time,
                FALSE as is_evidence,
                'normal'::text as urgency,
                d.tags,
                'upload'::text as source
            FROM documents d
            
            UNION ALL
            
            -- Timeline events
            SELECT 
                te.id,
                te.user_id,
                'timeline_event'::text as item_type,
                te.title,
                te.description,
                te.event_type as item_subtype,
                te.created_at as semptify_entry_time,
                te.event_date as record_time,
                te.event_date as event_time,
                te.is_evidence,
                COALESCE(te.urgency, 
                    CASE WHEN te.is_deadline THEN 'high' ELSE 'normal' END
                ) as urgency,
                NULL as tags,
                'manual'::text as source
            FROM timeline_events te
            
            UNION ALL
            
            -- Calendar events
            SELECT 
                ce.id,
                ce.user_id,
                'calendar_event'::text as item_type,
                ce.title,
                ce.description,
                ce.event_type as item_subtype,
                ce.created_at as semptify_entry_time,
                ce.start_datetime as record_time,
                ce.start_datetime as event_time,
                ce.is_critical as is_evidence,
                CASE WHEN ce.is_critical THEN 'critical' ELSE 'high' END as urgency,
                NULL as tags,
                'calendar'::text as source
            FROM calendar_events ce
            
            UNION ALL
            
            -- Vault items
            SELECT 
                vi.item_id::text,
                vi.user_id,
                'vault_item'::text as item_type,
                COALESCE(vi.title, vi.item_type) as title,
                vi.summary as description,
                vi.item_type as item_subtype,
                vi.semptify_entry_time,
                vi.record_time,
                vi.event_time,
                (vi.status = 'verified') as is_evidence,
                COALESCE(vi.severity, 'normal') as urgency,
                array_to_string(vi.tags, ',') as tags,
                COALESCE(vi.source, 'vault') as source
            FROM vault_items vi
        )
        SELECT * FROM all_items
        WHERE user_id IS NOT NULL;
    """))
    
    # GIN indexes for JSONB search
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_vault_items_metadata_gin 
        ON vault_items USING GIN (item_metadata jsonb_path_ops);
    """))
    
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_vault_items_tags_gin 
        ON vault_items USING GIN (tags);
    """))
    
    # Composite indexes for timeline queries
    op.create_index(
        'idx_documents_user_uploaded',
        'documents',
        ['user_id', sa.text('uploaded_at DESC')]
    )
    
    op.create_index(
        'idx_timeline_events_user_date',
        'timeline_events',
        ['user_id', sa.text('event_date DESC')]
    )
    
    op.create_index(
        'idx_calendar_events_user_start',
        'calendar_events',
        ['user_id', sa.text('start_datetime DESC')]
    )
    
    # Index on vault_items for the three timestamps
    op.create_index(
        'idx_vault_items_user_event_time',
        'vault_items',
        ['user_id', sa.text('event_time DESC')]
    )
    
    op.create_index(
        'idx_vault_items_user_record_time',
        'vault_items',
        ['user_id', sa.text('record_time DESC')]
    )


def downgrade():
    # Drop view
    op.execute(text("DROP VIEW IF EXISTS unified_timeline"))
    
    # Drop indexes
    op.drop_index('idx_documents_user_uploaded', table_name='documents')
    op.drop_index('idx_timeline_events_user_date', table_name='timeline_events')
    op.drop_index('idx_calendar_events_user_start', table_name='calendar_events')
    op.drop_index('idx_vault_items_user_event_time', table_name='vault_items')
    op.drop_index('idx_vault_items_user_record_time', table_name='vault_items')
    op.execute(text("DROP INDEX IF EXISTS idx_vault_items_metadata_gin"))
    op.execute(text("DROP INDEX IF EXISTS idx_vault_items_tags_gin"))
