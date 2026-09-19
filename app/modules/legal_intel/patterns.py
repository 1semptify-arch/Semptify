"""Pattern analysis engine — ported from app-legal-intel.

Keyword-matched docket analysis that answers "who is this actor in court":
default-judgment rate, settlement rate, time-to-first-motion, court
distribution, top opposing entities/attorneys, and shell-LLC clustering
by shared registered agent or address.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.legal_intel.models import (
    IntelAttorney,
    IntelCase,
    IntelDocket,
    IntelEntity,
)

DEFAULT_JUDGMENT_KEYWORDS = [
    "default judgment",
    "judgment by default",
    "entry of default",
    "default entered",
    "notice of default",
]

SETTLEMENT_KEYWORDS = [
    "stipulation of dismissal",
    "settlement agreement",
    "dismissal with prejudice",
    "dismissal without prejudice",
    "stipulation",
    "settlement",
    "mutual dismissal",
]

MOTION_KEYWORDS = [
    "motion",
    "motion to",
    "motion for",
]


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


async def compute_attorney_patterns(db: AsyncSession, attorney_id: str) -> dict[str, Any]:
    """Pattern summary for one attorney: how their cases tend to resolve."""
    q = await db.execute(
        select(IntelCase)
        .options(selectinload(IntelCase.dockets), selectinload(IntelCase.entity))
        .where(IntelCase.attorney_id == attorney_id)
    )
    cases = q.scalars().all()

    total = len(cases)
    if total == 0:
        return {
            "total_cases": 0,
            "default_rate": 0.0,
            "settlement_rate": 0.0,
            "avg_time_to_first_motion_days": None,
            "top_entities": [],
            "court_distribution": {},
        }

    court_distribution: dict[str, int] = {}
    entity_counts: dict[str, int] = {}
    default_count = 0
    settlement_count = 0
    motion_timings: list[int] = []

    for c in cases:
        if c.court:
            court_distribution[c.court] = court_distribution.get(c.court, 0) + 1
        if c.entity and c.entity.name:
            entity_counts[c.entity.name] = entity_counts.get(c.entity.name, 0) + 1

        if c.dockets:
            has_default = False
            has_settlement = False
            first_motion_date = None
            filing_date = _as_date(c.filing_date)

            for d in c.dockets:
                desc = (d.description or "").lower()
                if not has_default and any(k in desc for k in DEFAULT_JUDGMENT_KEYWORDS):
                    has_default = True
                if not has_settlement and any(k in desc for k in SETTLEMENT_KEYWORDS):
                    has_settlement = True
                if first_motion_date is None and d.date and any(k in desc for k in MOTION_KEYWORDS):
                    first_motion_date = _as_date(d.date)

            if has_default:
                default_count += 1
            if has_settlement:
                settlement_count += 1
            if first_motion_date and filing_date:
                days = (first_motion_date - filing_date).days
                if days >= 0:
                    motion_timings.append(days)

    return {
        "total_cases": total,
        "default_rate": default_count / total if total else 0.0,
        "settlement_rate": settlement_count / total if total else 0.0,
        "avg_time_to_first_motion_days": (
            sum(motion_timings) / len(motion_timings) if motion_timings else None
        ),
        "top_entities": sorted(entity_counts, key=entity_counts.get, reverse=True)[:5],
        "court_distribution": court_distribution,
    }


async def compute_entity_patterns(db: AsyncSession, entity_id: str) -> dict[str, Any]:
    """Pattern summary for one entity: litigation footprint and opposing counsel."""
    q = await db.execute(
        select(IntelCase)
        .options(selectinload(IntelCase.attorney))
        .where(IntelCase.entity_id == entity_id)
    )
    cases = q.scalars().all()

    attorney_counts: dict[str, int] = {}
    court_distribution: dict[str, int] = {}
    for c in cases:
        if c.attorney and c.attorney.name:
            attorney_counts[c.attorney.name] = attorney_counts.get(c.attorney.name, 0) + 1
        if c.court:
            court_distribution[c.court] = court_distribution.get(c.court, 0) + 1

    return {
        "total_cases": len(cases),
        "top_attorneys": sorted(attorney_counts, key=attorney_counts.get, reverse=True)[:5],
        "attorney_counts": attorney_counts,
        "court_distribution": court_distribution,
    }


async def detect_shell_llc_clusters(db: AsyncSession) -> dict[str, Any]:
    """Entities sharing a registered agent or address — possible shell clusters."""
    q = await db.execute(select(IntelEntity))
    entities = q.scalars().all()

    agent_clusters: dict[str, list[dict[str, Any]]] = {}
    address_clusters: dict[str, list[dict[str, Any]]] = {}

    for e in entities:
        stub = {"id": e.id, "name": e.name, "entity_type": e.entity_type, "sos_id": e.sos_id}
        if e.registered_agent:
            agent_clusters.setdefault(e.registered_agent, []).append(stub)
        if e.address:
            address_clusters.setdefault(e.address, []).append(stub)

    return {
        "agent_clusters": [
            {"agent": agent, "entities": ents}
            for agent, ents in agent_clusters.items()
            if len(ents) > 1
        ],
        "address_clusters": [
            {"address": addr, "entities": ents}
            for addr, ents in address_clusters.items()
            if len(ents) > 1
        ],
    }
