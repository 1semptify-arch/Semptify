#!/usr/bin/env python3
"""Fix PostgreSQL table ownership for Alembic migrations."""

import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import text, create_engine

# Load environment
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=False)

async def fix_permissions():
    """Grant table ownership to semptify user so migrations can run."""
    
    # Get connection details from environment
    db_url = os.getenv("DATABASE_URL", "postgresql://semptify:semptify@localhost:5432/semptify")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "semptify")
    db_user = os.getenv("POSTGRES_USER", "semptify")
    
    print(f"Database: {db_name}")
    print(f"Target user: {db_user}")
    
    # Connect as postgres superuser to grant permissions
    # Try to connect as postgres with default password
    postgres_urls = [
        f"postgresql://postgres:postgres@{db_host}:{db_port}/{db_name}",
        f"postgresql://postgres@{db_host}:{db_port}/{db_name}",  # No password
    ]
    
    engine = None
    for postgres_url in postgres_urls:
        try:
            print(f"\nAttempting connection: {postgres_url.split('@')[1]}")
            engine = create_engine(postgres_url, echo=False)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1;"))
                conn.commit()
            print("✓ Connected as postgres")
            break
        except Exception as e:
            print(f"✗ Failed: {str(e)[:100]}")
            continue
    
    if not engine:
        # Try using the regular database URL as-is
        print(f"\nFalling back to configured database URL")
        try:
            db_url_sync = db_url.replace("+asyncpg", "+psycopg2")
            engine = create_engine(db_url_sync, echo=False)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1;"))
                conn.commit()
            print("✓ Connected with configured URL")
        except Exception as e:
            print(f"✗ Failed: {e}")
            return
    
    # Execute permissions fixes
    try:
        with engine.connect() as conn:
            # Get list of tables
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
            ))
            tables = [row[0] for row in result.fetchall()]
            print(f"\nFound {len(tables)} tables: {', '.join(tables[:5])}...")
            
            # Grant ownership to semptify user for each table
            for table in tables:
                try:
                    cmd = f"ALTER TABLE {table} OWNER TO {db_user};"
                    conn.execute(text(cmd))
                    print(f"✓ Granted ownership: {table}")
                except Exception as e:
                    print(f"⚠ Failed to grant ownership to {table}: {str(e)[:80]}")
            
            conn.commit()
            print("\n✓ All permissions fixed successfully")
            
    except Exception as e:
        print(f"\n✗ Error during permission fix: {e}")
        return
    finally:
        engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_permissions())
