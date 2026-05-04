"""
Database Sync: Local SQLite ↔ Neon PostgreSQL
Usage: python scripts/sync_db.py [export|import]
"""
import json
import asyncio
import argparse
from datetime import datetime

async def export_local():
    """Export local SQLite data to JSON."""
    from app.core.database import get_db
    from app.models.models import User, Session, Document, TimelineEvent
    
    async for db in get_db():
        data = {
            "exported_at": datetime.now().isoformat(),
            "users": [],
            "sessions": [],
            "documents": [],
            "events": []
        }
        
        # Export users
        result = await db.execute("SELECT * FROM users")
        for row in result.mappings():
            data["users"].append(dict(row))
        
        # Export sessions
        result = await db.execute("SELECT * FROM sessions")
        for row in result.mappings():
            data["sessions"].append(dict(row))
        
        with open("db_export.json", "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Exported {len(data['users'])} users, {len(data['sessions'])} sessions")
        return

async def import_to_neon():
    """Import JSON to Neon PostgreSQL."""
    # Set NEON_DATABASE_URL env var first
    import os
    os.environ["DATABASE_URL"] = os.getenv("NEON_DATABASE_URL")
    
    from app.core.database import get_db
    
    with open("db_export.json", "r") as f:
        data = json.load(f)
    
    async for db in get_db():
        # Insert users
        for user in data["users"]:
            await db.execute("""
                INSERT INTO users (id, created_at, role)
                VALUES (:id, :created_at, :role)
                ON CONFLICT (id) DO NOTHING
            """, user)
        
        await db.commit()
        print(f"Imported {len(data['users'])} users to Neon")
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["export", "import"])
    args = parser.parse_args()
    
    if args.action == "export":
        asyncio.run(export_local())
    elif args.action == "import":
        asyncio.run(import_to_neon())
