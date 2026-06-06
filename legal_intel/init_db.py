#!/usr/bin/env python3
"""
Initialize the legal_intel database tables.
Run this after setting up PostgreSQL to create the schema.
"""

import asyncio
from app.db import engine
from app.models import Base

async def init_db():
    """Create all tables in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables created successfully")

if __name__ == "__main__":
    asyncio.run(init_db())
