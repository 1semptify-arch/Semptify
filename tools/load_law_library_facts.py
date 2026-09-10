"""Admin loader: upsert all Law Library entries into Context Engine facts.

This makes the expanded Law Library available to the Page Composer / UI Composer
as verified facts with official source URLs. It is safe to run repeatedly;
``upsert_fact`` deduplicates by (subject, jurisdiction, source_url).

Usage:
    cd modules/app-semptify-fastapi
    .\venv311\Scripts\python.exe tools/load_law_library_facts.py [--jurisdiction MN]
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.modules.context_engine.gatherer import gather_law_library_facts
from app.modules.context_engine.taxonomy import Subject

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _get_all_subjects() -> list[str]:
    """Return the set of Page Composer subjects that have matching Law Library categories."""
    return [
        Subject.TENANT_RIGHTS.value,
        Subject.EVICTION.value,
        Subject.DEPOSIT.value,
        Subject.HABITABILITY.value,
        Subject.RETALIATION.value,
        Subject.DISCRIMINATION.value,
        Subject.LAW_LIBRARY.value,
    ]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Load Law Library into Context Engine")
    parser.add_argument("--jurisdiction", default="MN", help="Jurisdiction to store facts under")
    parser.add_argument("--subject", help="Only load one subject (default: all)")
    args = parser.parse_args()

    subjects = [args.subject] if args.subject else _get_all_subjects()
    total = 0
    for subject in subjects:
        facts = await gather_law_library_facts(subject, args.jurisdiction, limit=200)
        logger.info("Loaded %d facts for subject=%s jurisdiction=%s", len(facts), subject, args.jurisdiction)
        total += len(facts)
    logger.info("Done. Total facts loaded: %d", total)


if __name__ == "__main__":
    asyncio.run(main())
