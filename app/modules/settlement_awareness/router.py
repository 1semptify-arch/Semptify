"""
Settlement Awareness Router
===========================
JSON surface for verified housing-litigation outcome records, plus a
source-gated intake route used by operators.

  - GET  /api/settlement-awareness/related?citation=...&subject=...  consumer surface
  - GET  /api/settlement-awareness/recheck                           weekly worklist
  - POST /api/settlement-awareness/records                           intake (Unresolved only)
  - POST /api/settlement-awareness/resolve/{record_id}               operator resolve
  - POST /api/settlement-awareness/recheck/{record_id}               recheck result

The read path re-runs every record through ``service.surfaceable`` so a
record that regresses (unverified, stale, unresolved) disappears by itself.
There is no public list page and no AI-authored text on the way out.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import require_capability
from app.core.database import get_db
from app.modules.settlement_awareness import service
from app.modules.settlement_awareness.models import RECORD_KINDS

logger = logging.getLogger(__name__)


capability_key = "app.modules.settlement_awareness.router"

router = APIRouter(
    dependencies=[Depends(require_capability(capability_key))],
)


class IntakeRequest(BaseModel):
    """Operator intake payload — lands Unresolved regardless of inputs."""

    title: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    record_kind: str = Field(default="settlement")
    parties: str | None = None
    jurisdiction: str = Field(default="MN")
    citation: str | None = None
    headline: str | None = None
    relief_summary: str | None = None
    primary_source_url: str | None = None
    source_authority: str | None = None
    attested_by: str | None = None


class ResolveRequest(BaseModel):
    attested_by: str = Field(..., min_length=1)
    fabrication_check: bool
    resolution_method: str = "manual operator verification"


class RecheckRequest(BaseModel):
    source_still_live: bool
    verified_by: str = Field(..., min_length=1)


# =============================================================================
# Consumer surface
# =============================================================================


@router.get("/api/settlement-awareness/related", tags=["Settlement Awareness"])
async def get_related(
    citation: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Verified records matching a citation and/or taxonomy subject.

    Empty list when nothing qualifies — silence beats fabrication."""
    if not citation and not subject:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "pass citation and/or subject",
        )
    records = await service.related(db, subject=subject, citation=citation)
    return JSONResponse(content={"records": records, "count": len(records)})


@router.get("/api/settlement-awareness/recheck", tags=["Settlement Awareness"])
async def get_recheck_worklist(db: AsyncSession = Depends(get_db)):
    """Weekly recheck worklist — Resolved records due or unverified."""
    due = await service.due_for_recheck(db)
    return JSONResponse(content={"records": due, "count": len(due)})


# =============================================================================
# Intake + resolution (operator paths)
# =============================================================================


@router.post("/api/settlement-awareness/records", tags=["Settlement Awareness"])
async def post_record(body: IntakeRequest, db: AsyncSession = Depends(get_db)):
    """Intake a record. Always lands Unresolved — the response states the
    gate fields it still needs before anything surfaces."""
    if body.record_kind not in RECORD_KINDS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"record_kind must be one of {RECORD_KINDS}")
    try:
        record = await service.create_record(
            db,
            title=body.title,
            subject=body.subject,
            source_url=body.source_url,
            record_kind=body.record_kind,
            parties=body.parties,
            jurisdiction=body.jurisdiction,
            citation=body.citation,
            headline=body.headline,
            relief_summary=body.relief_summary,
            primary_source_url=body.primary_source_url,
            source_authority=body.source_authority,
            attested_by=body.attested_by,
        )
    except service.GateError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "record_id": record.record_id,
            "resolution_status": record.resolution_status,
            "needs": [
                "fabrication_check passed by a human",
                "attested_by naming the verifying human",
                "resolve via POST /api/settlement-awareness/resolve/{id}",
            ],
        },
    )


@router.post("/api/settlement-awareness/resolve/{record_id}",
             tags=["Settlement Awareness"])
async def post_resolve(
    record_id: str,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resolve a record after manual verification — write-side of the Part
    3B gate. Refuses on any unmet requirement."""
    try:
        record = await service.resolve_record(
            db,
            record_id,
            attested_by=body.attested_by,
            fabrication_check=body.fabrication_check,
            resolution_method=body.resolution_method,
        )
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, record_id)
    except service.GateError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    await db.commit()
    return JSONResponse(content={
        "record_id": record.record_id,
        "resolution_status": record.resolution_status,
        "last_verified_date": record.last_verified_date,
        "next_recheck_date": record.next_recheck_date,
    })


@router.post("/api/settlement-awareness/recheck/{record_id}",
             tags=["Settlement Awareness"])
async def post_recheck(
    record_id: str,
    body: RecheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a recheck result. ``source_still_live=false`` flips
    ``is_verified`` off — the record auto-hides from surfacing."""
    try:
        record = await service.record_recheck(
            db,
            record_id,
            source_still_live=body.source_still_live,
            verified_by=body.verified_by,
        )
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, record_id)
    except service.GateError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    await db.commit()
    return JSONResponse(content={
        "record_id": record.record_id,
        "is_verified": record.is_verified,
        "last_verified_date": record.last_verified_date,
        "next_recheck_date": record.next_recheck_date,
    })
