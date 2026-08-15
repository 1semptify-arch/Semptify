"""Seed the landing-page hero fact(s) into the context_facts cache.

Run this after the canonical_value column has been added (Phase A).
It only inserts the NCCRC representation-gap claim; the rent-pricing
claim is intentionally not seeded until Phase B can verify the current figure.
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.utc import utc_now
from app.modules.context_engine.cache import upsert_fact

logger = logging.getLogger(__name__)


async def seed() -> None:
    """Seed the NCCRC representation-gap landing claim."""
    now = utc_now()
    fact = await upsert_fact(
        subject="landing",
        jurisdiction="US",
        claim=(
            "More than 80% of landlords have a lawyer in eviction court. "
            "Fewer than 1 in 20 tenants do."
        ),
        source_url="https://civilrighttocounsel.org/about-civil-rtc/",
        source_name="National Coalition for a Civil Right to Counsel (NCCRC)",
        citation="NCCRC, 'About Civil RTC' — nationwide eviction representation rates",
        canonical_value="84% landlords / 4% tenants",
        ttl_days=7,
    )
    logger.info(
        "Seeded landing fact id=%d subject=%s canonical_value=%s at %s",
        fact.id,
        fact.subject,
        fact.canonical_value,
        now.isoformat(),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())
