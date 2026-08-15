"""Seed the landing-page hero fact(s) into the context_facts cache.

Run this after the canonical_value and extraction_pattern columns exist.
The NCCRC representation-gap claim is seeded as verified with a content pattern.
The Calder-Wang/Kim rent-pricing claim is seeded as unverified/flagged because
no final peer-reviewed/published version has been confirmed; the most recent
FTC conference presentation (Feb 24 2026) is the source the verifier will watch.
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
    """Seed the landing-page hero facts."""
    now = utc_now()

    nccrc = await upsert_fact(
        subject="landing",
        jurisdiction="US",
        claim=(
            "More than 80% of landlords have a lawyer in eviction court. "
            "Fewer than 1 in 20 tenants do."
        ),
        source_url="https://civilrighttocounsel.org/about-civil-rtc/",
        source_name="National Coalition for a Civil Right to Counsel (NCCRC)",
        citation="NCCRC, 'About Civil RTC' — nationwide eviction representation rates",
        canonical_value="4% of tenants are represented nationwide, compared to 84% of landlords",
        extraction_pattern=r"\d+% of tenants are represented nationwide, compared to \d+% of landlords",
        ttl_days=7,
    )
    logger.info(
        "Seeded landing fact id=%d subject=%s canonical_value=%s at %s",
        nccrc.id,
        nccrc.subject,
        nccrc.canonical_value,
        now.isoformat(),
    )

    # Unverified/flagged placeholder for the Calder-Wang/Kim rent-pricing figure.
    # The pattern extracts whatever dollar amount the FTC source currently reports;
    # canonical_value is None because a final, peer-reviewed/published version has
    # not been confirmed, and the $25 (JPE R&R / SSRN) vs $53 (FTC 2026-02-24)
    # distinction has not been settled. Do NOT conflate with the White House CEA
    # $70/month estimate, which is a separate study.
    rent = await upsert_fact(
        subject="landing",
        jurisdiction="US",
        claim="Landlords use AI to screen you and software to set your rent.",
        source_url="https://www.ftc.gov/system/files/ftc_gov/pdf/calder-wang_rental_algo_2026_2_24_ftc.pdf",
        source_name="Sophie Calder-Wang (Wharton) and Gi Heung Kim (Boston College)",
        citation="Algorithmic Pricing in Multifamily Rentals: Efficiency Gains or Price Collusion? (FTC, 2026-02-24)",
        canonical_value=None,
        extraction_pattern=r"\$\d+ per month per unit",
        is_verified=False,
        ttl_days=7,
    )
    logger.info(
        "Seeded unverified rent-pricing fact id=%d subject=%s source=%s at %s",
        rent.id,
        rent.subject,
        rent.source_url,
        now.isoformat(),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())
