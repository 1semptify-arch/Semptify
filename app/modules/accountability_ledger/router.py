"""Accountability Ledger Router — subject registry, patterns, political alignments.

Provides CRUD endpoints for the accountability ledger. Research/admin tier —
no tenant PII, no narrative content. All data is public-record-sourced or
entity-reference only.

Phase 1 (this module): the data model and basic CRUD.
Phase 2 (future): political_tracker data ingestion sits on top of this.
Phase 3 (future, GATED on Brad's legal-characterization decision): the public
registry surface.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.utc import utc_now
from app.modules.accountability_ledger.models import (
    AccountabilityPattern,
    AccountabilitySubject,
    PoliticalAlignment,
    PublicRecordsRequest,
)

logger = logging.getLogger(__name__)

accountability_ledger_router = APIRouter(
    prefix="/api/accountability-ledger",
    tags=["Accountability Ledger"],
)


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class SubjectCreate(BaseModel):
    subject_type: str = Field(..., description="landlord, llc, judge, politician, agency, property_manager")
    canonical_name: str = Field(..., max_length=255)
    aliases: list[str] | None = None
    jurisdiction: str = Field("MN", max_length=10)
    metadata_json: dict[str, Any] | None = None


class PatternCreate(BaseModel):
    subject_id: str
    pattern_type: str = Field(..., description="repeated_fees, retaliatory_eviction, serial_eviction, etc.")
    severity: str = Field("medium", description="low, medium, high, critical")
    instance_count: int = 1
    evidence_refs: list[dict[str, Any]] | None = None
    first_observed: datetime | None = None
    last_observed: datetime | None = None
    jurisdiction: str = "MN"
    legal_basis: str | None = None
    status: str = "documented"


class AlignmentCreate(BaseModel):
    subject_id: str
    alignment_type: str = Field(..., description="campaign_donation, voting_record, ruling_pattern, public_statement")
    source: str = Field(..., description="fec, state_disclosure, leg_tracker, court_records")
    source_ref: dict[str, Any] | None = None
    amount: float | None = None
    date: datetime | None = None
    description: str | None = Field(None, max_length=255)


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------


@accountability_ledger_router.get("/subjects")
async def list_subjects(
    subject_type: str | None = Query(None),
    jurisdiction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List accountability subjects, optionally filtered by type or jurisdiction."""
    stmt = select(AccountabilitySubject)
    if subject_type:
        stmt = stmt.where(AccountabilitySubject.subject_type == subject_type)
    if jurisdiction:
        stmt = stmt.where(AccountabilitySubject.jurisdiction == jurisdiction)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {"subjects": [_subject_to_dict(s) for s in rows], "total": len(rows)}


@accountability_ledger_router.post("/subjects")
async def create_subject(body: SubjectCreate, db: AsyncSession = Depends(get_db)):
    """Create a new accountability subject."""
    subject = AccountabilitySubject(
        id=str(uuid.uuid4()),
        subject_type=body.subject_type,
        canonical_name=body.canonical_name,
        aliases=body.aliases,
        jurisdiction=body.jurisdiction,
        metadata_json=body.metadata_json,
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return _subject_to_dict(subject)


@accountability_ledger_router.get("/subjects/{subject_id}")
async def get_subject(subject_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single accountability subject by ID."""
    subject = await db.get(AccountabilitySubject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return _subject_to_dict(subject)


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------


@accountability_ledger_router.get("/patterns")
async def list_patterns(
    subject_id: str | None = Query(None),
    pattern_type: str | None = Query(None),
    jurisdiction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List documented patterns, optionally filtered."""
    stmt = select(AccountabilityPattern)
    if subject_id:
        stmt = stmt.where(AccountabilityPattern.subject_id == subject_id)
    if pattern_type:
        stmt = stmt.where(AccountabilityPattern.pattern_type == pattern_type)
    if jurisdiction:
        stmt = stmt.where(AccountabilityPattern.jurisdiction == jurisdiction)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {"patterns": [_pattern_to_dict(p) for p in rows], "total": len(rows)}


@accountability_ledger_router.post("/patterns")
async def create_pattern(body: PatternCreate, db: AsyncSession = Depends(get_db)):
    """Document a new accountability pattern for a subject."""
    subject = await db.get(AccountabilitySubject, body.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    pattern = AccountabilityPattern(
        id=str(uuid.uuid4()),
        subject_id=body.subject_id,
        pattern_type=body.pattern_type,
        severity=body.severity,
        instance_count=body.instance_count,
        evidence_refs=body.evidence_refs,
        first_observed=body.first_observed,
        last_observed=body.last_observed,
        jurisdiction=body.jurisdiction,
        legal_basis=body.legal_basis,
        status=body.status,
    )
    db.add(pattern)
    await db.commit()
    await db.refresh(pattern)
    return _pattern_to_dict(pattern)


# ---------------------------------------------------------------------------
# Political Alignments
# ---------------------------------------------------------------------------


@accountability_ledger_router.get("/alignments")
async def list_alignments(
    subject_id: str | None = Query(None),
    alignment_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List political alignments, optionally filtered."""
    stmt = select(PoliticalAlignment)
    if subject_id:
        stmt = stmt.where(PoliticalAlignment.subject_id == subject_id)
    if alignment_type:
        stmt = stmt.where(PoliticalAlignment.alignment_type == alignment_type)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {"alignments": [_alignment_to_dict(a) for a in rows], "total": len(rows)}


@accountability_ledger_router.post("/alignments")
async def create_alignment(body: AlignmentCreate, db: AsyncSession = Depends(get_db)):
    """Record a political alignment (donation, vote, ruling, statement)."""
    subject = await db.get(AccountabilitySubject, body.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    alignment = PoliticalAlignment(
        id=str(uuid.uuid4()),
        subject_id=body.subject_id,
        alignment_type=body.alignment_type,
        source=body.source,
        source_ref=body.source_ref,
        amount=body.amount,
        date=body.date,
        description=body.description,
    )
    db.add(alignment)
    await db.commit()
    await db.refresh(alignment)
    return _alignment_to_dict(alignment)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _subject_to_dict(s: AccountabilitySubject) -> dict[str, Any]:
    return {
        "id": s.id,
        "subject_type": s.subject_type,
        "canonical_name": s.canonical_name,
        "aliases": s.aliases,
        "jurisdiction": s.jurisdiction,
        "metadata": s.metadata_json,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _pattern_to_dict(p: AccountabilityPattern) -> dict[str, Any]:
    return {
        "id": p.id,
        "subject_id": p.subject_id,
        "pattern_type": p.pattern_type,
        "severity": p.severity,
        "instance_count": p.instance_count,
        "evidence_refs": p.evidence_refs,
        "first_observed": p.first_observed.isoformat() if p.first_observed else None,
        "last_observed": p.last_observed.isoformat() if p.last_observed else None,
        "jurisdiction": p.jurisdiction,
        "legal_basis": p.legal_basis,
        "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _alignment_to_dict(a: PoliticalAlignment) -> dict[str, Any]:
    return {
        "id": a.id,
        "subject_id": a.subject_id,
        "alignment_type": a.alignment_type,
        "source": a.source,
        "source_ref": a.source_ref,
        "amount": a.amount,
        "date": a.date.isoformat() if a.date else None,
        "description": a.description,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


# ---------------------------------------------------------------------------
# Public records requests (FOIA / Data Practices / Sunshine tracking)
#
# Ported workflow from app-pmas: file a request, record the statutory
# deadline, track the lifecycle. ``overdue`` is computed on read — an open
# request (submitted/acknowledged) past its deadline reports overdue without
# mutating the stored status.
# ---------------------------------------------------------------------------

_OPEN_REQUEST_STATUSES = ("submitted", "acknowledged")
_REQUEST_STATUSES = _OPEN_REQUEST_STATUSES + ("fulfilled", "denied", "withdrawn")


class RecordRequestCreate(BaseModel):
    agency_target: str = Field(..., min_length=1, description="Agency the request went to")
    records_requested: str = Field(..., min_length=1, description="What records were asked for")
    date_submitted: datetime | None = None
    deadline_date: datetime | None = None
    subject_id: str | None = Field(None, description="Optional accountability_subjects.id for the agency")
    notes: str | None = None


class RecordRequestUpdate(BaseModel):
    status: str | None = Field(None, description="submitted/acknowledged/fulfilled/denied/withdrawn")
    deadline_date: datetime | None = None
    notes: str | None = None
    records_requested: str | None = None


@accountability_ledger_router.get("/requests")
async def list_record_requests(
    status: str | None = Query(None, description="Filter by stored or effective status (incl. overdue)"),
    agency_target: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List tracked public-records requests, newest first.

    ``effective_status`` reports ``overdue`` for open requests past their
    deadline. Filtering by ``status=overdue`` matches on the effective value.
    """
    stmt = select(PublicRecordsRequest).order_by(PublicRecordsRequest.created_at.desc())
    if agency_target:
        stmt = stmt.where(PublicRecordsRequest.agency_target == agency_target)
    if status and status != "overdue":
        stmt = stmt.where(PublicRecordsRequest.status == status)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    now = utc_now()
    items = [_request_to_dict(r, now) for r in rows]
    if status == "overdue":
        items = [i for i in items if i["effective_status"] == "overdue"]
    return {"requests": items, "total": len(items)}


@accountability_ledger_router.post("/requests")
async def create_record_request(body: RecordRequestCreate, db: AsyncSession = Depends(get_db)):
    """Log a new public-records request with its statutory deadline."""
    if body.subject_id:
        subject = await db.get(AccountabilitySubject, body.subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
    req = PublicRecordsRequest(
        id=str(uuid.uuid4()),
        agency_target=body.agency_target,
        records_requested=body.records_requested,
        date_submitted=body.date_submitted or utc_now(),
        deadline_date=body.deadline_date,
        status="submitted",
        notes=body.notes,
        subject_id=body.subject_id,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return _request_to_dict(req)


@accountability_ledger_router.get("/requests/{request_id}")
async def get_record_request(request_id: str, db: AsyncSession = Depends(get_db)):
    """Get one tracked request, with its effective (overdue-aware) status."""
    req = await db.get(PublicRecordsRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return _request_to_dict(req)


@accountability_ledger_router.patch("/requests/{request_id}")
async def update_record_request(
    request_id: str,
    body: RecordRequestUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Advance a request's status or correct its details.

    ``overdue`` is not a settable status — it derives from the deadline.
    """
    req = await db.get(PublicRecordsRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if body.status is not None:
        if body.status not in _REQUEST_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown status '{body.status}'. Valid: {list(_REQUEST_STATUSES)}",
            )
        req.status = body.status
    if body.deadline_date is not None:
        req.deadline_date = body.deadline_date
    if body.notes is not None:
        req.notes = body.notes
    if body.records_requested is not None:
        req.records_requested = body.records_requested
    await db.commit()
    await db.refresh(req)
    return _request_to_dict(req)


def _request_to_dict(r: PublicRecordsRequest, now: datetime | None = None) -> dict[str, Any]:
    return {
        "id": r.id,
        "agency_target": r.agency_target,
        "records_requested": r.records_requested,
        "date_submitted": r.date_submitted.isoformat() if r.date_submitted else None,
        "deadline_date": r.deadline_date.isoformat() if r.deadline_date else None,
        "status": r.status,
        "effective_status": r.effective_status(now),
        "is_overdue": r.effective_status(now) == "overdue",
        "notes": r.notes,
        "subject_id": r.subject_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
