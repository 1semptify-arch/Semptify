"""Reset test user state for a clean onboarding run."""
import asyncio
from app.core.database import get_db_session
from sqlalchemy import text

LIST_TABLES = "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"

async def main():
    async with get_db_session() as db:
        result = await db.execute(text(LIST_TABLES))
        tables = [r[0] for r in result.fetchall()]
        print("Tables:", tables)

        gate_table = None
        for t in tables:
            if "gate" in t.lower():
                gate_table = t
                break

        await db.execute(text("DELETE FROM oauth_states"))
        print("Cleared: oauth_states")

        await db.execute(text("UPDATE users SET completed_groups = ''"))
        print("Cleared: users.completed_groups (all gates reset)")

        await db.commit()
        print("Done — fresh onboarding state ready")

asyncio.run(main())
