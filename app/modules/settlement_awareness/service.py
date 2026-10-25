"""Settlement Awareness service — records, gates, and the tag-match surface.

The rules that matter (Part 3B + the task spec, made mechanical):

- ``create_record`` always lands ``Unresolved`` — intake can never skip the
  queue no matter what fields are passed.
- ``resolve_record`` refuses unless every hard gate is satisfied: source_url
  present, fabrication_check passed, ai_generated False, attested_by names a
  human, and ``news_*`` authorities carry a ``primary_source_url``.
- ``surfaceable`` is re-checked inside every consumer query — a record that
  regresses (unverified, stale >90 days) stops surfacing by itself
  (ADR-0009 auto-hide; no placeholder, no last-known-good).
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utc import utc_now
from app.modules.context_engine.taxonomy import ALL_SUBJECTS
from app.modules.settlement_awareness.models import (
    RECORD_KINDS,
    SECONDARY_AUTHORITY_PREFIX,
    SettlementOrCaseRecord,
)

logger = logging.getLogger(__name__)

RECHECK_INTERVAL_DAYS = 90


class GateError(ValueError):
    """Raised when a Part 3B gate field is missing or invalid."""


def _today() -> str:
    return utc_now().strftime("%Y-%m-%d")


def _norm_citation(text: str) -> str:
    """Lowercase, strip everything that isn't a letter or digit — so
    'Minn. Stat. § 504B.178' and '504b178' match."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def surfaceable(record: SettlementOrCaseRecord, today: str | None = None) -> bool:
    """The read-side gate. Everything a consumer can ever show passes here."""
    if record.resolution_status != "Resolved":
        return False
    if not record.source_url or not record.fabrication_check:
        return False
    if record.ai_generated or not record.attested_by:
        return False
    if not record.is_verified:
        return False
    if not record.last_verified_date:
        return False
    try:
        from datetime import datetime as _dt
        last_dt = _dt.strptime(record.last_verified_date, "%Y-%m-%d")
    except ValueError:
        return False
    if (utc_now().replace(tzinfo=None) - last_dt).days > RECHECK_INTERVAL_DAYS:
        return False
    return True


def to_public_dict(record: SettlementOrCaseRecord) -> dict:
    """The only shape a consumer ever sees — no intake internals leak."""
    return {
        "record_id": record.record_id,
        "record_kind": record.record_kind,
        "title": record.title,
        "parties": record.parties,
        "jurisdiction": record.jurisdiction,
        "subject": record.subject,
        "citation": record.citation,
        "headline": record.headline,
        "relief_summary": record.relief_summary,
        "source_url": record.source_url,
        "primary_source_url": record.primary_source_url,
        "source_authority": record.source_authority,
        "last_verified_date": record.last_verified_date,
        "disclaimer": (
            "These are real public outcomes, shown for awareness — not a "
            "prediction of your result. Get legal advice from a qualified "
            "attorney."
        ),
    }


async def create_record(
    db: AsyncSession,
    *,
    title: str,
    subject: str,
    source_url: str,
    record_kind: str = "settlement",
    parties: str | None = None,
    jurisdiction: str = "MN",
    citation: str | None = None,
    headline: str | None = None,
    relief_summary: str | None = None,
    primary_source_url: str | None = None,
    source_authority: str | None = None,
    attested_by: str | None = None,
) -> SettlementOrCaseRecord:
    """Intake. Always lands Unresolved — nothing skips the gate."""
    if subject not in ALL_SUBJECTS:
        raise GateError(f"subject must be a taxonomy value, got {subject!r}")
    if record_kind not in RECORD_KINDS:
        raise GateError(f"record_kind must be one of {RECORD_KINDS}")
    if not source_url or not source_url.strip():
        raise GateError("source_url is required — a record with no source "
                        "can never resolve")
    record = SettlementOrCaseRecord(
        record_id=f"scr_{uuid.uuid4().hex[:16]}",
        record_kind=record_kind,
        title=title.strip(),
        parties=parties,
        jurisdiction=jurisdiction,
        citation=citation,
        subject=subject,
        headline=headline,
        relief_summary=relief_summary,
        source_url=source_url.strip(),
        primary_source_url=primary_source_url,
        source_authority=source_authority,
        resolution_status="Unresolved",
        ai_generated=False,   # hard — intake may not assert otherwise
        attested_by=attested_by,
        fabrication_check=False,
        is_verified=False,
    )
    db.add(record)
    await db.flush()
    return record


async def resolve_record(
    db: AsyncSession,
    record_id: str,
    *,
    attested_by: str,
    fabrication_check: bool,
    resolution_method: str = "manual operator verification",
) -> SettlementOrCaseRecord:
    """Operator resolves a record after verifying the source by hand.

    Every gate field must be satisfied here — this is the write-side of the
    Part 3B contract for this record type."""
    record = await _get(db, record_id)
    if not record:
        raise KeyError(record_id)
    problems: list[str] = []
    if not record.source_url:
        problems.append("source_url empty")
    if not fabrication_check:
        problems.append("fabrication_check not passed")
    if record.ai_generated:
        problems.append("ai_generated must be false")
    if not attested_by or not attested_by.strip():
        problems.append("attested_by must name a human")
    if (record.source_authority or "").lower().startswith(
            SECONDARY_AUTHORITY_PREFIX) and not record.primary_source_url:
        problems.append("news_* source requires primary_source_url")
    if problems:
        raise GateError("cannot resolve: " + "; ".join(problems))
    record.attested_by = attested_by.strip()
    record.fabrication_check = True
    record.resolution_status = "Resolved"
    record.resolution_method = resolution_method
    today = _today()
    record.resolved_date = today
    record.last_verified_date = today
    record.next_recheck_date = (
        utc_now() + timedelta(days=RECHECK_INTERVAL_DAYS)).strftime("%Y-%m-%d")
    record.is_verified = True
    record.verified_at = utc_now().replace(tzinfo=None)
    await db.flush()
    return record


async def record_recheck(
    db: AsyncSession,
    record_id: str,
    *,
    source_still_live: bool,
    verified_by: str,
) -> SettlementOrCaseRecord:
    """Weekly/90-day recheck result. A dead source flips is_verified off —
    the record auto-hides from surfacing without needing a delete."""
    record = await _get(db, record_id)
    if not record:
        raise KeyError(record_id)
    if not verified_by or not verified_by.strip():
        raise GateError("verified_by must name a human")
    record.is_verified = bool(source_still_live)
    if source_still_live:
        record.last_verified_date = _today()
        record.next_recheck_date = (
            utc_now() + timedelta(days=RECHECK_INTERVAL_DAYS)
        ).strftime("%Y-%m-%d")
        record.verified_at = utc_now().replace(tzinfo=None)
    await db.flush()
    return record


async def related(
    db: AsyncSession,
    *,
    subject: str | None = None,
    citation: str | None = None,
) -> list[dict]:
    """The consumer surface. Tag- or citation-matched, surfaceable only.

    Returns [] when nothing qualifies — silence beats fabrication."""
    rows = (await db.execute(
        select(SettlementOrCaseRecord)
        .where(SettlementOrCaseRecord.resolution_status == "Resolved")
    )).scalars().all()
    if subject:
        rows = [r for r in rows if r.subject == subject]
    if citation:
        needle = _norm_citation(citation)
        if needle:
            rows = [r for r in rows if r.citation and
                    (needle in _norm_citation(r.citation)
                     or _norm_citation(r.citation) in needle)]
        else:
            rows = []
    today = _today()
    return [to_public_dict(r) for r in rows if surfaceable(r, today)]


async def due_for_recheck(db: AsyncSession) -> list[dict]:
    """Worklist for the weekly pass: Resolved records whose next_recheck_date
    is today or past, or that have gone >90 days unverified."""
    today = _today()
    rows = (await db.execute(
        select(SettlementOrCaseRecord)
        .where(SettlementOrCaseRecord.resolution_status == "Resolved")
    )).scalars().all()
    due = [r for r in rows
           if (r.next_recheck_date and r.next_recheck_date <= today)
           or not r.is_verified]
    return [
        {
            "record_id": r.record_id,
            "title": r.title,
            "source_url": r.source_url,
            "last_verified_date": r.last_verified_date,
            "next_recheck_date": r.next_recheck_date,
            "is_verified": r.is_verified,
        }
        for r in due
    ]


async def get_surfaceable(db: AsyncSession,
                          record_id: str) -> dict | None:
    record = await _get(db, record_id)
    if record is None or not surfaceable(record):
        return None
    return to_public_dict(record)


async def _get(db: AsyncSession,
               record_id: str) -> SettlementOrCaseRecord | None:
    return (await db.execute(
        select(SettlementOrCaseRecord)
        .where(SettlementOrCaseRecord.record_id == record_id)
    )).scalar_one_or_none()
