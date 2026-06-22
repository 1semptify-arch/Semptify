"""Context Engine cache — PostgreSQL-backed fact cache.

Reads/writes ContextFact rows. Facts expire after 7 days by default.
No hallucination: every fact must have source_url + source_name.
"""

from datetime import timedelta
from typing import List, Optional

from sqlalchemy import select, and_, or_

from app.core.database import get_db_session
from app.core.utc import utc_now
from app.modules.context_engine.models import ContextFact
from app.modules.context_engine.taxonomy import ALL_SUBJECTS

DEFAULT_TTL_DAYS = 7


def _is_expired(fact: ContextFact) -> bool:
    if not fact.expires_at:
        return False
    return fact.expires_at < utc_now()


def get_facts(
    subject: str,
    jurisdiction: str = "MN",
    limit: int = 10,
    include_expired: bool = False,
) -> List[ContextFact]:
    """Get cached facts for a subject + jurisdiction."""
    with get_db_session() as db:
        stmt = select(ContextFact).where(
            and_(
                ContextFact.subject == subject,
                ContextFact.jurisdiction == jurisdiction,
            )
        ).order_by(ContextFact.created_at.desc()).limit(limit)
        rows = db.execute(stmt).scalars().all()
        if include_expired:
            return list(rows)
        return [r for r in rows if not _is_expired(r)]


def upsert_fact(
    subject: str,
    jurisdiction: str,
    claim: str,
    source_url: str,
    source_name: str,
    citation: Optional[str] = None,
    ttl_days: int = DEFAULT_TTL_DAYS,
) -> ContextFact:
    """Insert or update a fact in the cache. No hallucination — source required."""
    expires_at = utc_now() + timedelta(days=ttl_days)
    with get_db_session() as db:
        # Dedup by (subject, jurisdiction, source_url, claim hash)
        existing = db.execute(
            select(ContextFact).where(
                and_(
                    ContextFact.subject == subject,
                    ContextFact.jurisdiction == jurisdiction,
                    ContextFact.source_url == source_url,
                )
            )
        ).scalars().first()
        if existing:
            existing.claim = claim
            existing.citation = citation
            existing.is_verified = True
            existing.verified_at = utc_now()
            existing.expires_at = expires_at
            db.commit()
            db.refresh(existing)
            return existing
        fact = ContextFact(
            subject=subject,
            jurisdiction=jurisdiction,
            claim=claim,
            source_url=source_url,
            source_name=source_name,
            citation=citation,
            is_verified=True,
            verified_at=utc_now(),
            expires_at=expires_at,
        )
        db.add(fact)
        db.commit()
        db.refresh(fact)
        return fact


def prune_expired() -> int:
    """Delete expired facts. Returns count deleted."""
    now = utc_now()
    with get_db_session() as db:
        rows = db.execute(
            select(ContextFact).where(
                and_(
                    ContextFact.expires_at.isnot(None),
                    ContextFact.expires_at < now,
                )
            )
        ).scalars().all()
        count = len(rows)
        for r in rows:
            db.delete(r)
        db.commit()
        return count


def list_subjects_with_counts(jurisdiction: str = "MN") -> dict:
    """Return {subject: fact_count} for admin/overview."""
    with get_db_session() as db:
        out = {}
        for subj in ALL_SUBJECTS:
            stmt = select(ContextFact).where(
                and_(
                    ContextFact.subject == subj,
                    ContextFact.jurisdiction == jurisdiction,
                )
            )
            rows = db.execute(stmt).scalars().all()
            out[subj] = len([r for r in rows if not _is_expired(r)])
        return out
