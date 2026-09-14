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
