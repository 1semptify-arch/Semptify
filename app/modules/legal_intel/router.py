"""Legal Intel Router — entity/attorney/shell-LLC lookups and cross-entity
pattern analysis.

Ported from app-legal-intel (workflow only — crawlers are NOT ported; see
module notes). Records arrive via the ingest endpoints below; the intel
endpoints answer "who owns this LLC" questions: attorney-by-bar,
entity-by-name, per-actor pattern summaries, and shared-agent/address
shell clustering.

Operator/research workbench — public-record-sourced data, no tenant PII.
"""

import logging
import uuid
from datetime import date as _date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.utc import utc_now
from app.modules.legal_intel.models import (
    IntelAttorney,
    IntelCase,
    IntelDocket,
    IntelEntity,
    IntelRelationship,
)
from app.modules.legal_intel.patterns import (
    compute_attorney_patterns,
    compute_entity_patterns,
    detect_shell_llc_clusters,
)

logger = logging.getLogger(__name__)

legal_intel_router = APIRouter(prefix="/api/legal-intel", tags=["Legal Intel"])


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class EntityCreate(BaseModel):
    name: str = Field(..., min_length=1)
    entity_type: str | None = None  # llc, corp, lp, individual
    sos_id: str | None = None
    registered_agent: str | None = None
    address: str | None = None
    subject_id: str | None = None


class AttorneyCreate(BaseModel):
    name: str = Field(..., min_length=1)
    bar_number: str | None = None
    state: str | None = None
    firm: str | None = None
    last_seen: datetime | None = None


class CaseCreate(BaseModel):
    case_number: str = Field(..., min_length=1)
    court: str | None = None
    case_title: str | None = None
    case_type: str | None = None
    filing_date: _date | None = None
    status: str | None = None
    attorney_id: str | None = None
    entity_id: str | None = None


class DocketCreate(BaseModel):
    date: _date | None = None
    entry_type: str | None = None
    description: str | None = None
    document_url: str | None = None


class RelationshipCreate(BaseModel):
    entity_id: str
    related_entity_id: str
    relationship_type: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Ingest endpoints — how records arrive (crawler port is a separate decision)
# ---------------------------------------------------------------------------


@legal_intel_router.post("/entities")
async def create_entity(body: EntityCreate, db: AsyncSession = Depends(get_db)):
    """Register an entity (landlord LLC, property manager, shell company)."""
    entity = IntelEntity(
        id=str(uuid.uuid4()),
        name=body.name,
        entity_type=body.entity_type,
        sos_id=body.sos_id,
        registered_agent=body.registered_agent,
        address=body.address,
        subject_id=body.subject_id,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return _entity_to_dict(entity)


@legal_intel_router.get("/entities")
async def list_entities(
    name: str | None = Query(None, description="Substring match, case-insensitive"),
    registered_agent: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List registered entities, optionally filtered."""
    stmt = select(IntelEntity).order_by(IntelEntity.name)
    if name:
        stmt = stmt.where(IntelEntity.name.ilike(f"%{name}%"))
    if registered_agent:
        stmt = stmt.where(IntelEntity.registered_agent == registered_agent)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {"entities": [_entity_to_dict(e) for e in rows], "total": len(rows)}


@legal_intel_router.post("/attorneys")
async def create_attorney(body: AttorneyCreate, db: AsyncSession = Depends(get_db)):
    """Register an attorney."""
    attorney = IntelAttorney(
        id=str(uuid.uuid4()),
        name=body.name,
        bar_number=body.bar_number,
        state=body.state,
        firm=body.firm,
        last_seen=body.last_seen,
    )
    db.add(attorney)
    await db.commit()
    await db.refresh(attorney)
    return _attorney_to_dict(attorney)


@legal_intel_router.post("/cases")
async def create_case(body: CaseCreate, db: AsyncSession = Depends(get_db)):
    """Register a court case, optionally linking entity and attorney."""
    for label, model, rid in (
        ("attorney", IntelAttorney, body.attorney_id),
        ("entity", IntelEntity, body.entity_id),
    ):
        if rid and not await db.get(model, rid):
            raise HTTPException(status_code=404, detail=f"{label} not found")
    case = IntelCase(
        id=str(uuid.uuid4()),
        court=body.court,
        case_number=body.case_number,
        case_title=body.case_title,
        case_type=body.case_type,
        filing_date=body.filing_date,
        status=body.status,
        attorney_id=body.attorney_id,
        entity_id=body.entity_id,
        last_crawled=utc_now(),
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return _case_to_dict(case)


@legal_intel_router.get("/cases")
async def list_cases(
    entity_id: str | None = Query(None),
    attorney_id: str | None = Query(None),
    court: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List registered cases, optionally filtered."""
    stmt = select(IntelCase).order_by(IntelCase.filing_date.desc().nullslast())
    if entity_id:
        stmt = stmt.where(IntelCase.entity_id == entity_id)
    if attorney_id:
        stmt = stmt.where(IntelCase.attorney_id == attorney_id)
    if court:
        stmt = stmt.where(IntelCase.court == court)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {"cases": [_case_to_dict(c) for c in rows], "total": len(rows)}


@legal_intel_router.post("/cases/{case_id}/dockets")
async def add_docket(case_id: str, body: DocketCreate, db: AsyncSession = Depends(get_db)):
    """Append a docket entry to a case."""
    if not await db.get(IntelCase, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    docket = IntelDocket(
        id=str(uuid.uuid4()),
        case_id=case_id,
        date=body.date,
        entry_type=body.entry_type,
        description=body.description,
        document_url=body.document_url,
    )
    db.add(docket)
    await db.commit()
    await db.refresh(docket)
    return _docket_to_dict(docket)


@legal_intel_router.get("/cases/{case_id}/dockets")
async def list_dockets(case_id: str, db: AsyncSession = Depends(get_db)):
    """List a case's docket entries."""
    if not await db.get(IntelCase, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    result = await db.execute(
        select(IntelDocket).where(IntelDocket.case_id == case_id).order_by(IntelDocket.date)
    )
    rows = result.scalars().all()
    return {"dockets": [_docket_to_dict(d) for d in rows], "total": len(rows)}


@legal_intel_router.post("/relationships")
async def create_relationship(body: RelationshipCreate, db: AsyncSession = Depends(get_db)):
    """Declare a link between two entities (parent/subsidiary, shared agent…)."""
    if body.entity_id == body.related_entity_id:
        raise HTTPException(status_code=400, detail="An entity cannot relate to itself")
    for rid in (body.entity_id, body.related_entity_id):
        if not await db.get(IntelEntity, rid):
            raise HTTPException(status_code=404, detail="Entity not found")
    rel = IntelRelationship(
        entity_id=body.entity_id,
        related_entity_id=body.related_entity_id,
        relationship_type=body.relationship_type,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return {
        "id": rel.id,
        "entity_id": rel.entity_id,
        "related_entity_id": rel.related_entity_id,
        "relationship_type": rel.relationship_type,
    }


# ---------------------------------------------------------------------------
# Intel endpoints — the ported lookups and pattern analysis
# ---------------------------------------------------------------------------


@legal_intel_router.get("/intel/attorney/by-bar/{bar_number}")
async def get_attorney_by_bar(bar_number: str, db: AsyncSession = Depends(get_db)):
    """Find an attorney by bar number."""
    result = await db.execute(
        select(IntelAttorney).where(IntelAttorney.bar_number == bar_number)
    )
    attorney = result.scalar_one_or_none()
    if not attorney:
        raise HTTPException(status_code=404, detail="Attorney not found")
    return _attorney_to_dict(attorney)


@legal_intel_router.get("/intel/entity/by-name/{entity_name}")
async def get_entity_by_name(entity_name: str, db: AsyncSession = Depends(get_db)):
    """Find an entity by exact name (use /entities?name= for fuzzy search)."""
    result = await db.execute(select(IntelEntity).where(IntelEntity.name == entity_name))
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return _entity_to_dict(entity)


@legal_intel_router.get("/intel/patterns/attorney/{attorney_id}")
async def get_attorney_patterns(attorney_id: str, db: AsyncSession = Depends(get_db)):
    """Pattern summary for an attorney: default/settlement rates, timing, opponents."""
    if not await db.get(IntelAttorney, attorney_id):
        raise HTTPException(status_code=404, detail="Attorney not found")
    return await compute_attorney_patterns(db, attorney_id)


@legal_intel_router.get("/intel/patterns/entity/{entity_id}")
async def get_entity_patterns(entity_id: str, db: AsyncSession = Depends(get_db)):
    """Pattern summary for an entity: litigation footprint and counsel."""
    if not await db.get(IntelEntity, entity_id):
        raise HTTPException(status_code=404, detail="Entity not found")
    return await compute_entity_patterns(db, entity_id)


@legal_intel_router.get("/intel/clusters/shell-llcs")
async def get_shell_llc_clusters(db: AsyncSession = Depends(get_db)):
    """Entities sharing a registered agent or address — possible shell clusters."""
    return await detect_shell_llc_clusters(db)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _entity_to_dict(e: IntelEntity) -> dict[str, Any]:
    return {
        "id": e.id,
        "name": e.name,
        "entity_type": e.entity_type,
        "sos_id": e.sos_id,
        "registered_agent": e.registered_agent,
        "address": e.address,
        "subject_id": e.subject_id,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _attorney_to_dict(a: IntelAttorney) -> dict[str, Any]:
    return {
        "id": a.id,
        "name": a.name,
        "bar_number": a.bar_number,
        "state": a.state,
        "firm": a.firm,
        "last_seen": a.last_seen.isoformat() if a.last_seen else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _case_to_dict(c: IntelCase) -> dict[str, Any]:
    return {
        "id": c.id,
        "court": c.court,
        "case_number": c.case_number,
        "case_title": c.case_title,
        "case_type": c.case_type,
        "filing_date": c.filing_date.isoformat() if c.filing_date else None,
        "status": c.status,
        "attorney_id": c.attorney_id,
        "entity_id": c.entity_id,
        "last_crawled": c.last_crawled.isoformat() if c.last_crawled else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _docket_to_dict(d: IntelDocket) -> dict[str, Any]:
    return {
        "id": d.id,
        "case_id": d.case_id,
        "date": d.date.isoformat() if d.date else None,
        "entry_type": d.entry_type,
        "description": d.description,
        "document_url": d.document_url,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }
