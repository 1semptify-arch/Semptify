"""Settlement Awareness test fixtures.

Mirrors tests/conftest.py: each test gets an isolated SQLite file with all
Base-registered tables created, so service code runs against real async
SQLAlchemy without touching the configured database.
"""

import os

import pytest


@pytest.fixture(scope="function", autouse=True)
async def setup_test_database(tmp_path):
    from app.core.config import get_settings
    from app.core.database import Base, close_db, get_engine

    # Import models to register them on Base.metadata; do not remove.
    import app.modules.settlement_awareness.models  # noqa: F401

    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file.as_posix()}"

    get_settings.cache_clear()
    await close_db()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await close_db()
