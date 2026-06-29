"""
Drop document_registry and certification_events tables.

These tables stored certification metadata in our PostgreSQL. Per the stateless
mandate, certification info now lives as a VAULT_UPLOAD_MANIFEST overlay in
the user's cloud storage, managed by UnifiedOverlayManager.

The in-memory document_registry service (app/services/document_registry.py)
still generates SEM-YYYY-NNNNNN-XXXX IDs and computes hashes — that stays.
Only the DB persistence layer is removed.

Usage:
  python scripts/drop_certification_tables.py

Safe to re-run — checks if table exists before dropping.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.core.database import get_engine
from sqlalchemy import text


async def drop_certification_tables():
    engine = get_engine()
    async with engine.begin() as conn:
        # Check if tables exist (PostgreSQL)
        for table_name in ("certification_events", "document_registry"):
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = :name"
            ), {"name": table_name})
            if result.fetchone():
                print(f"Dropping table: {table_name}...")
                await conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                print(f"OK: {table_name} dropped.")
            else:
                print(f"SKIP: {table_name} does not exist (already migrated).")


if __name__ == "__main__":
    asyncio.run(drop_certification_tables())
