#!/usr/bin/env python3
"""Backfill embeddings for all curated content in the Context Engine.

Run once against the current database, then re-run whenever new entries are
added or variant text changes. With ``--force``, regenerates embeddings for
rows that already have one.

Usage:
    .\venv311\Scripts\Activate.ps1
    python scripts/backfill_context_embeddings.py
    python scripts/backfill_context_embeddings.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import UTC, datetime

# Make the repo root importable when the script is run directly.
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)


from sqlalchemy import select

from app.core.database import get_db_session
from app.modules.context_engine.embedding_model import embed_text, load_embedding_model
from app.modules.context_engine.explanation_entries import (
    ContextExplanationEntry,
    _explanation_embedding_text,
)
from app.modules.context_engine.models import ContextFact

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 25


async def _backfill_explanation_entries(force: bool) -> dict:
    updated = 0
    skipped = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    async with get_db_session() as db:
        stmt = select(ContextExplanationEntry)
        if not force:
            stmt = stmt.where(ContextExplanationEntry.embedding.is_(None))
        result = await db.execute(stmt)
        rows = list(result.scalars().all())

    logger.info("Found %s explanation entries to embed", len(rows))

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        async with get_db_session() as db:
            for entry in batch:
                text = _explanation_embedding_text(
                    entry.subject,
                    entry.variant_trust,
                    entry.variant_mechanics,
                    entry.variant_reinforcement,
                    entry.variant_minimal,
                )
                try:
                    embedding = await embed_text(text)
                    if embedding is None:
                        skipped += 1
                        logger.warning("No embedding returned for %s", entry.entry_id)
                        continue
                    entry.embedding = embedding
                    updated += 1
                    db.add(entry)
                except Exception as e:
                    failed += 1
                    failures.append((entry.entry_id, str(e)))
                    logger.exception("Failed to embed %s", entry.entry_id)
            await db.commit()

    return {
        "total": len(rows),
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "failures": failures,
    }


async def _backfill_facts(force: bool) -> dict:
    updated = 0
    skipped = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    async with get_db_session() as db:
        stmt = select(ContextFact)
        if not force:
            stmt = stmt.where(ContextFact.embedding.is_(None))
        result = await db.execute(stmt)
        rows = list(result.scalars().all())

    logger.info("Found %s facts to embed", len(rows))

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        async with get_db_session() as db:
            for fact in batch:
                try:
                    embedding = await embed_text(fact.embedding_text())
                    if embedding is None:
                        skipped += 1
                        logger.warning("No embedding returned for fact %s", fact.id)
                        continue
                    fact.embedding = embedding
                    updated += 1
                    db.add(fact)
                except Exception as e:
                    failed += 1
                    failures.append((str(fact.id), str(e)))
                    logger.exception("Failed to embed fact %s", fact.id)
            await db.commit()

    return {
        "total": len(rows),
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "failures": failures,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill Context Engine embeddings (Problem A)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate embeddings even for rows that already have one.",
    )
    args = parser.parse_args()

    logger.info("Loading embedding model...")
    model = load_embedding_model()
    if model is None:
        logger.error("Embedding model could not be loaded. Aborting.")
        return 1
    logger.info("Embedding model loaded")

    started_at = datetime.now(UTC).isoformat()
    logger.info("Backfill started at %s", started_at)

    explanation_stats = await _backfill_explanation_entries(args.force)
    fact_stats = await _backfill_facts(args.force)

    logger.info("Explanation entries: %(total)s total, %(updated)s updated, %(skipped)s skipped, %(failed)s failed", explanation_stats)
    logger.info("Facts: %(total)s total, %(updated)s updated, %(skipped)s skipped, %(failed)s failed", fact_stats)

    if explanation_stats["failures"]:
        logger.warning("Explanation entry failures: %s", explanation_stats["failures"])
    if fact_stats["failures"]:
        logger.warning("Fact failures: %s", fact_stats["failures"])

    total_updated = explanation_stats["updated"] + fact_stats["updated"]
    total_failed = explanation_stats["failed"] + fact_stats["failed"]

    logger.info("Backfill complete: %s updated, %s failed", total_updated, total_failed)
    return 0 if total_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
