"""Initialize PostgreSQL database with all tables."""
import asyncio
import sys
sys.path.insert(0, ".")

# Import all models to register them with Base
from app.models.models import *
from app.core.database import get_engine, Base


async def create_tables():
    """Create all tables in PostgreSQL."""
    engine = get_engine()
    
    print(f"📦 Registered tables: {len(Base.metadata.tables)}")
    for table in Base.metadata.tables:
        print(f"   - {table}")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("\n✅ All tables created in PostgreSQL!")


if __name__ == "__main__":
    asyncio.run(create_tables())
