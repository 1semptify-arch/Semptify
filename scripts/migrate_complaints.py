"""
Migration Script: Add new columns to complaints table
Run this to update the database schema for the Complaint Wizard.
"""

import asyncio
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.core.database import get_engine


async def migrate():
    """Add new columns to complaints table if they don't exist."""
    engine = get_engine()
    
    # New columns to add
    new_columns = [
        ("agency_id", "VARCHAR(50) DEFAULT ''"),
        ("subject", "VARCHAR(500) DEFAULT ''"),
        ("incident_dates", "TEXT"),
        ("damages_claimed", "REAL"),
        ("relief_sought", "TEXT"),
        ("target_company", "VARCHAR(255)"),
        ("target_phone", "VARCHAR(50)"),
        ("attached_document_ids", "TEXT"),
        ("timeline_included", "BOOLEAN DEFAULT 0"),
        ("confirmation_number", "VARCHAR(100)"),
        ("notes", "TEXT"),
    ]
    
    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='complaints'"
        ))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("⚠️ complaints table doesn't exist yet. It will be created on app startup.")
            return
        
        # Get existing columns
        result = await conn.execute(text("PRAGMA table_info(complaints)"))
        existing_columns = {row[1] for row in result.fetchall()}
        print(f"📋 Existing columns: {existing_columns}")
        
        # Add missing columns
        for col_name, col_def in new_columns:
            if col_name not in existing_columns:
                try:
                    await conn.execute(text(
                        f"ALTER TABLE complaints ADD COLUMN {col_name} {col_def}"
                    ))
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    print(f"⚠️ Could not add {col_name}: {e}")
            else:
                print(f"   Column exists: {col_name}")
        
        # Create index on agency_id if not exists
        try:
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_complaints_agency_id ON complaints(agency_id)"
            ))
            print("✅ Index on agency_id created/verified")
        except Exception as e:
            print(f"⚠️ Index issue: {e}")
    
    print("\n✅ Migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
