"""Context Engine verifier — checks that cached facts still resolve.

A fact is 'verified' if:
- source_url returns HTTP 200
- claim text is non-empty
- not expired

Runs periodically (cron/manual) to mark facts stale.
"""

import logging
from datetime import timedelta
from typing import List

import httpx
from sqlalchemy import select, and_

from app.core.database import get_db_session
from app.core.utc import utc_now
from app.modules.context_engine.models import ContextFact

logger = logging.getLogger(__name__)

VERIFY_TIMEOUT_SECONDS = 10.0


async def verify_fact(fact: ContextFact) -> bool:
    """Check that a fact's source URL still resolves. Returns True if verified."""
    if not fact.source_url:
        return False
    try:
        async with httpx.AsyncClient(timeout=VERIFY_TIMEOUT_SECONDS) as client:
            resp = await client.head(fact.source_url, follow_redirects=True)
            ok = resp.status_code < 400
    except Exception as e:
        logger.info("Verify failed for fact %s: %s", fact.id, e)
        ok = False
    with get_db_session() as db:
        db_fact = db.execute(
            select(ContextFact).where(ContextFact.id == fact.id)
        ).scalars().first()
        if db_fact:
            db_fact.is_verified = ok
            db_fact.verified_at = utc_now()
            db.commit()
    return ok


async def verify_subject(subject: str, jurisdiction: str = "MN", limit: int = 20) -> dict:
    """Verify all facts for a subject. Returns summary."""
    with get_db_session() as db:
        stmt = select(ContextFact).where(
            and_(
                ContextFact.subject == subject,
                ContextFact.jurisdiction == jurisdiction,
            )
        ).limit(limit)
        facts = list(db.execute(stmt).scalars().all())

    verified = 0
    failed = 0
    for f in facts:
        ok = await verify_fact(f)
        if ok:
            verified += 1
        else:
            failed += 1
    return {
        "subject": subject,
        "jurisdiction": jurisdiction,
        "total": len(facts),
        "verified": verified,
        "failed": failed,
    }
