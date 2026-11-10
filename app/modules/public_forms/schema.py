"""Local-dev schema guard for the public_forms tables.

Alembic auto-migration only runs on Render (RENDER env). Local SQLite dev
databases predate newer columns, so each additive column needs a
dialect-aware ensure step — same pattern as
app/core/module_overrides.py::ensure_schema and
app/core/features.py::ensure_schema (AGENTS.md Known Failure #20).

Currently covers: voice_posts flag columns (public-driven review,
20261110_voice_post_flags on Postgres).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Column name -> DDL fragment appended after `ALTER TABLE voice_posts ADD COLUMN`.
# Keep in sync with VoicePost in app/models/models.py and the Alembic
# migration; SQLite accepts these same simple types.
_VOICE_POST_FLAG_COLUMNS = {
    "flag_count": "INTEGER NOT NULL DEFAULT 0",
    "flag_reasons": "TEXT",  # JSON stored as TEXT on SQLite
    "flagged_at": "TIMESTAMP",
}


async def ensure_voice_post_flag_columns(db: "AsyncSession") -> None:
    """Add the voice_posts flag columns if they are missing.

    Idempotent — safe to call on every startup. On PostgreSQL this is a
    no-op when Alembic has applied 20261110_voice_post_flags; the check
    also heals a Postgres DB that somehow drifted ahead of migrations.
    """
    dialect = getattr(db.bind, "dialect", None)
    dialect_name = getattr(dialect, "name", "") if dialect else ""

    try:
        if dialect_name == "postgresql":
            result = await db.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='voice_posts'"
                )
            )
            existing = {row[0] for row in result.fetchall()}
        else:
            result = await db.execute(text("PRAGMA table_info(voice_posts)"))
            existing = {row[1] for row in result.fetchall()}

        if not existing:
            # voice_posts table does not exist yet — create_all will make it
            # with the full model definition; nothing to ALTER.
            return

        added = []
        for col, ddl in _VOICE_POST_FLAG_COLUMNS.items():
            if col in existing:
                continue
            await db.execute(text(f"ALTER TABLE voice_posts ADD COLUMN {col} {ddl}"))
            added.append(col)

        await db.commit()
        if added:
            logger.info("public_forms: added voice_posts columns %s", added)
    except Exception as exc:
        await db.rollback()
        logger.warning("public_forms: voice_posts flag-column ensure failed: %s", exc)
