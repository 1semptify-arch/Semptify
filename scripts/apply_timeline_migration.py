"""
Apply timeline migration manually (handles SQLite schema).
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.core.database import get_engine
from sqlalchemy import text


async def apply_migration():
    engine = get_engine()
    async with engine.begin() as conn:
        # Check if view exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='view' AND name='unified_timeline'"
        ))
        if result.fetchone():
            print('⚠️  unified_timeline view already exists, skipping')
        else:
            # Create unified timeline view (SQLite-compatible)
            await conn.execute(text('''
                CREATE VIEW unified_timeline AS
                SELECT 
                    d.id,
                    d.user_id,
                    'document' as item_type,
                    d.filename as title,
                    d.description,
                    d.document_type as item_subtype,
                    d.uploaded_at as semptify_entry_time,
                    d.uploaded_at as record_time,
                    NULL as event_time,
                    FALSE as is_evidence,
                    'normal' as urgency,
                    d.tags,
                    'upload' as source
                FROM documents d
                UNION ALL
                SELECT 
                    te.id,
                    te.user_id,
                    'timeline_event' as item_type,
                    te.title,
                    te.description,
                    te.event_type as item_subtype,
                    te.created_at as semptify_entry_time,
                    te.event_date as record_time,
                    te.event_date as event_time,
                    te.is_evidence,
                    CASE WHEN te.is_deadline THEN 'high' ELSE 'normal' END as urgency,
                    NULL as tags,
                    'manual' as source
                FROM timeline_events te;
            '''))
            print('✅ unified_timeline view created')
        
        # Check alembic_version table
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ))
        if not result.fetchone():
            await conn.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)'))
            print('✅ alembic_version table created')
        
        # Mark migration as applied
        await conn.execute(text('''
            INSERT OR REPLACE INTO alembic_version (version_num) 
            VALUES ('20250422_unified_timeline')
        '''))
        print('✅ Migration 20250422_unified_timeline marked as applied')
        
        print('\n🎉 Migration completed successfully!')


if __name__ == '__main__':
    asyncio.run(apply_migration())
