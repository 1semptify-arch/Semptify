"""
Drop extracted_data_json column from vault_index table.

This migration removes the last DB column that stored user extracted content.
After this migration, VaultIndexDB contains ONLY:
  - vault_id, user_id (ownership)
  - filename, safe_filename, sha256_hash, file_size, mime_type (file identity)
  - storage_path, provider_file_id, storage_provider (cloud location)
  - document_type, description, tags (light classification metadata)
  - certificate_id, registry_id, integrity_status (certification references)
  - processed (boolean state flag — no content, just "yes/no")
  - source_module, uploaded_at, updated_at (audit timestamps)

All extracted user content (dates, parties, amounts, summary, OCR text) now
lives EXCLUSIVELY in overlay JSON files in the user's cloud storage, managed
by UnifiedOverlayManager.

Usage:
  python scripts/drop_extracted_data_column.py

Safe to re-run — checks if column exists before dropping.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.core.database import get_engine
from sqlalchemy import text


async def drop_extracted_data_column():
    engine = get_engine()
    async with engine.begin() as conn:
        # Check if column exists (PostgreSQL)
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='vault_index' AND column_name='extracted_data_json'"
        ))
        if result.fetchone():
            print("Dropping vault_index.extracted_data_json column...")
            await conn.execute(text("ALTER TABLE vault_index DROP COLUMN extracted_data_json"))
            print("OK: extracted_data_json column dropped.")
        else:
            print("SKIP: vault_index.extracted_data_json column does not exist (already migrated).")


if __name__ == "__main__":
    asyncio.run(drop_extracted_data_column())
