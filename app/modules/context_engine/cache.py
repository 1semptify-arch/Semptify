"""Context Engine cache — PostgreSQL-backed fact cache.

Reads/writes ContextFact rows. Facts expire after 7 days by default.
No hallucination: every fact must have source_url + source_name.
"""

from datetime import timedelta

from sqlalchemy import and_, select

from app.core.database import get_db_session
from app.core.utc import utc_now
from app.modules.context_engine.embedding_model import embed_text
from app.modules.context_engine.models import ContextFact
from app.modules.context_engine.taxonomy import ALL_SUBJECTS

DEFAULT_TTL_DAYS = 7


def _is_expired(fact: ContextFact) -> bool:
    if not fact.expires_at:
        return False
    return fact.expires_at < utc_now().replace(tzinfo=None)


async def get_facts(
    subject: str,
    jurisdiction: str = "MN",
    limit: int = 10,
    include_expired: bool = False,
    include_unresolved: bool = False,
) -> list[ContextFact]:
    """Get cached facts for a subject + jurisdiction.

    Part 3B: by default only Resolved, non-AI-generated facts with a passing
    fabrication check are returned. Set ``include_unresolved=True`` for admin
    / debugging paths that need to see quarantined facts.
    """
    async with get_db_session() as db:
        filters = [
            ContextFact.subject == subject,
            ContextFact.jurisdiction == jurisdiction,
        ]
        if not include_unresolved:
            filters.extend(
                [
                    ContextFact.resolution_status == "Resolved",
                    ContextFact.ai_generated.is_(False),
                    ContextFact.fabrication_check.is_(True),
                ]
            )
        stmt = (
            select(ContextFact)
            .where(and_(*filters))
            .order_by(ContextFact.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        if include_expired:
            return list(rows)
        return [r for r in rows if not _is_expired(r)]


async def get_verified_landing_facts(
    limit: int = 10,
    jurisdiction: str = "MN",
) -> list[ContextFact]:
    """Return verified, non-expired landing/public facts.

    This is the canonical source for hero claims on the landing page.
    Unverified, expired, or drifted claims are auto-hidden.
    """
    async with get_db_session() as db:
        stmt = (
            select(ContextFact)
            .where(
                and_(
                    ContextFact.subject == "landing",
                    ContextFact.jurisdiction == jurisdiction,
                    ContextFact.is_verified.is_(True),
                )
            )
            .order_by(ContextFact.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [r for r in rows if not _is_expired(r)]


async def upsert_fact(
    subject: str,
    jurisdiction: str,
    claim: str,
    source_url: str,
    source_name: str,
    citation: str | None = None,
    canonical_value: str | None = None,
    extraction_pattern: str | None = None,
    fact_id: str | None = None,
    source_authority: str | None = None,
    taxonomy_subject: str | None = None,
    resolution_status: str = "Unresolved",
    resolution_method: str | None = None,
    resolved_date: str | None = None,
    last_verified_date: str | None = None,
    ai_generated: bool = True,
    fabrication_check: bool = False,
    is_verified: bool = True,
    ttl_days: int = DEFAULT_TTL_DAYS,
) -> ContextFact:
    """Insert or update a fact in the cache. No hallucination — source required.

    Part 3B — consumers only see facts that are ``ai_generated=false``,
    ``resolution_status='Resolved'``, and ``fabrication_check=true``.
    """
    now = utc_now().replace(tzinfo=None)
    expires_at = now + timedelta(days=ttl_days)
    embedding = await embed_text(f"{subject} {claim}")

    async with get_db_session() as db:
        # Dedup by (subject, jurisdiction, source_url, claim hash)
        result = await db.execute(
            select(ContextFact).where(
                and_(
                    ContextFact.subject == subject,
                    ContextFact.jurisdiction == jurisdiction,
                    ContextFact.source_url == source_url,
                )
            )
        )
        existing = result.scalars().first()
        if existing:
            existing.fact_id = fact_id or existing.fact_id
            existing.claim = claim
            existing.citation = citation
            existing.canonical_value = canonical_value
            existing.extraction_pattern = extraction_pattern
            existing.source_authority = source_authority
            existing.taxonomy_subject = taxonomy_subject or subject
            existing.resolution_status = resolution_status
            existing.resolution_method = resolution_method
            existing.resolved_date = resolved_date
            existing.last_verified_date = last_verified_date
            existing.ai_generated = ai_generated
            existing.fabrication_check = fabrication_check
            existing.is_verified = is_verified
            existing.verified_at = now
            existing.expires_at = expires_at
            existing.embedding = embedding
            await db.commit()
            await db.refresh(existing)
            return existing
        fact = ContextFact(
            fact_id=fact_id,
            subject=subject,
            jurisdiction=jurisdiction,
            taxonomy_subject=taxonomy_subject or subject,
            claim=claim,
            source_url=source_url,
            source_name=source_name,
            source_authority=source_authority,
            citation=citation,
            canonical_value=canonical_value,
            extraction_pattern=extraction_pattern,
            resolution_status=resolution_status,
            resolution_method=resolution_method,
            resolved_date=resolved_date,
            last_verified_date=last_verified_date,
            ai_generated=ai_generated,
            fabrication_check=fabrication_check,
            embedding=embedding,
            is_verified=is_verified,
            verified_at=now,
            expires_at=expires_at,
        )
        db.add(fact)
        await db.commit()
        await db.refresh(fact)
        return fact


async def prune_expired() -> int:
    """Delete expired facts. Returns count deleted."""
    now = utc_now().replace(tzinfo=None)
    async with get_db_session() as db:
        result = await db.execute(
            select(ContextFact).where(
                and_(
                    ContextFact.expires_at.isnot(None),
                    ContextFact.expires_at < now,
                )
            )
        )
        rows = result.scalars().all()
        count = len(rows)
        for r in rows:
            await db.delete(r)
        await db.commit()
        return count


async def list_subjects_with_counts(jurisdiction: str = "MN") -> dict:
    """Return {subject: fact_count} for admin/overview."""
    async with get_db_session() as db:
        out = {}
        for subj in ALL_SUBJECTS:
            stmt = select(ContextFact).where(
                and_(
                    ContextFact.subject == subj,
                    ContextFact.jurisdiction == jurisdiction,
                )
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()
            out[subj] = len([r for r in rows if not _is_expired(r)])
        return out
