import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models.models import Base

async def main():
    engine = create_async_engine('postgresql+asyncpg://semptify:semptify@localhost:5432/semptify')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created!')

asyncio.run(main())
