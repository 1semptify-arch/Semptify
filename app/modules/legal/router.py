"""
Legal API Router
================

Endpoints for legal workspace, court filings, discovery, exhibits, and overlays.
All endpoints require legal or admin role.

Routes:
- GET  /api/legal/matters                       — list matters for current legal user
- POST /api/legal/matters                       — create a new matter
- GET  /api/legal/matters/{matter_id}           — get matter detail
- PATCH /api/legal/matters/{matter_id}          — update matter fields
- GET  /api/legal/matters/{matter_id}/filings   — list court filings
- POST /api/legal/matters/{matter_id}/filings   — add court filing
- PATCH /api/legal/matters/{matter_id}/filings/{filing_id}  — update filing status
- GET  /api/legal/matters/{matter_id}/discovery — list discovery records
- POST /api/legal/matters/{matter_id}/discovery — add discovery record
- PATCH /api/legal/matters/{matter_id}/discovery/{discovery_id}  — update discovery status
- GET  /api/legal/matters/{matter_id}/exhibits  — list exhibits (numbered)
- POST /api/legal/matters/{matter_id}/exhibits  — add exhibit (auto-numbered)
- GET  /api/legal/matters/{matter_id}/overlay   — combined overlay payload
"""

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.request_utils import require_request_user_id
from app.core.user_context import UserRole, get_role_from_user_id
from app.modules.legal import service as legal_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/legal", tags=["Legal"])


# =============================================================================
# Guards
# =============================================================================


def _require_legal(user_id: str) -> None:
    role = get_role_from_user_id(user_id)
    if role not in (UserRole.LEGAL, UserRole.ADVOCATE, UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Only legal, advocate, or admin roles can access this endpoint.",
        )


# =============================================================================
# Request Models
# =============================================================================


class CreateMatterRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    tenant_user_id: str | None = None
    tenant_name: str | None = None
    landlord_name: str | None = None
    address: str | None = None
    notes: str | None = None


class UpdateMatterRequest(BaseModel):
    title: str | None = None
    tenant_name: str | None = None
    landlord_name: str | None = None
    address: str | None = None
    status: str | None = None
    notes: str | None = None


class AddFilingRequest(BaseModel):
    filing_type: str = Field(..., description="complaint, motion, answer, discovery, notice, brief")
    court: str = Field(..., min_length=1, max_length=200)
    docket_number: str | None = None
    filing_date: date | None = None
    notes: str | None = None


class UpdateFilingStatusRequest(BaseModel):
    status: str = Field(..., description="draft, filed, served, rejected")


class AddDiscoveryRequest(BaseModel):
    discovery_type: str = Field(
        ..., description="interrogatories, requests_for_production, requests_for_admission, depositions"
    )
    served_date: date | None = None
    due_date: date | None = None
    notes: str | None = None


class UpdateDiscoveryStatusRequest(BaseModel):
    status: str = Field(..., description="pending, served, responded, overdue")
    response_note: str | None = None


class AddExhibitRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    evidence_item_id: str | None = None
    vault_path: str | None = None
    introduced_on: date | None = None
    notes: str | None = None


_VALID_MATTER_STATUSES = {"open", "closed", "held"}
_VALID_FILING_STATUSES = {"draft", "filed", "served", "rejected"}
_VALID_DISCOVERY_STATUSES = {"pending", "served", "responded", "overdue"}


# =============================================================================
# Matter Endpoints
# =============================================================================


@router.get("/matters")
async def list_matters(request: Request):
    """List all legal matters for the current user."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    matters = legal_svc.list_matters(created_by=user_id)
    return {"matters": [m.model_dump(mode="json") for m in matters], "count": len(matters)}


@router.post("/matters")
async def create_matter(body: CreateMatterRequest, request: Request):
    """Create a new legal matter (workspace)."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    matter = legal_svc.create_matter(
        title=body.title,
        created_by=user_id,
        tenant_user_id=body.tenant_user_id,
        tenant_name=body.tenant_name,
        landlord_name=body.landlord_name,
        address=body.address,
        notes=body.notes,
    )
    logger.info("Legal matter %s created by %s", matter.matter_id, user_id)
    return {"status": "created", "matter": matter.model_dump(mode="json")}


@router.get("/matters/{matter_id}")
async def get_matter(matter_id: str, request: Request):
    """Get a single matter with all related data."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    try:
        matter = legal_svc.load_matter(matter_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matter not found")
    return {
        "matter": matter.model_dump(mode="json"),
        "filings": [f.model_dump(mode="json") for f in legal_svc.list_filings(matter_id)],
        "discovery": [d.model_dump(mode="json") for d in legal_svc.list_discovery(matter_id)],
        "exhibits": [e.model_dump(mode="json") for e in legal_svc.list_exhibits(matter_id)],
    }


@router.patch("/matters/{matter_id}")
async def update_matter(matter_id: str, body: UpdateMatterRequest, request: Request):
    """Update matter fields."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    if body.status and body.status not in _VALID_MATTER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(_VALID_MATTER_STATUSES))}",
        )
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        updated = legal_svc.update_matter(matter_id, **updates)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matter not found")
    return {"status": "updated", "matter": updated.model_dump(mode="json")}


# =============================================================================
# Court Filings
# =============================================================================


@router.get("/matters/{matter_id}/filings")
async def list_filings(matter_id: str, request: Request):
    """List all court filings for a matter."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    try:
        legal_svc.load_matter(matter_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matter not found")
    filings = legal_svc.list_filings(matter_id)
    return {"filings": [f.model_dump(mode="json") for f in filings], "count": len(filings)}


@router.post("/matters/{matter_id}/filings")
async def add_filing(matter_id: str, body: AddFilingRequest, request: Request):
    """Add a court filing to a matter."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    try:
        filing = legal_svc.add_filing(
            matter_id=matter_id,
            filing_type=body.filing_type,
            court=body.court,
            docket_number=body.docket_number,
            filing_date=body.filing_date,
            notes=body.notes,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matter not found")
    logger.info("Filing %s added to matter %s by %s", filing.filing_id, matter_id, user_id)
    return {"status": "created", "filing": filing.model_dump(mode="json")}


@router.patch("/matters/{matter_id}/filings/{filing_id}")
async def update_filing(matter_id: str, filing_id: str, body: UpdateFilingStatusRequest, request: Request):
    """Update a court filing's status."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    if body.status not in _VALID_FILING_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(_VALID_FILING_STATUSES))}",
        )
    try:
        filing = legal_svc.update_filing_status(matter_id, filing_id, body.status)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "updated", "filing": filing.model_dump(mode="json")}


# =============================================================================
# Discovery
# =============================================================================


@router.get("/matters/{matter_id}/discovery")
async def list_discovery(matter_id: str, request: Request):
    """List all discovery records for a matter."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    try:
        legal_svc.load_matter(matter_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matter not found")
    records = legal_svc.list_discovery(matter_id)
    return {"discovery": [d.model_dump(mode="json") for d in records], "count": len(records)}


@router.post("/matters/{matter_id}/discovery")
async def add_discovery(matter_id: str, body: AddDiscoveryRequest, request: Request):
    """Add a discovery record to a matter."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    try:
        rec = legal_svc.add_discovery(
            matter_id=matter_id,
            discovery_type=body.discovery_type,
            served_date=body.served_date,
            due_date=body.due_date,
            notes=body.notes,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matter not found")
    logger.info("Discovery %s added to matter %s by %s", rec.discovery_id, matter_id, user_id)
    return {"status": "created", "discovery": rec.model_dump(mode="json")}


@router.patch("/matters/{matter_id}/discovery/{discovery_id}")
async def update_discovery(matter_id: str, discovery_id: str, body: UpdateDiscoveryStatusRequest, request: Request):
    """Update a discovery record's status."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    if body.status not in _VALID_DISCOVERY_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(_VALID_DISCOVERY_STATUSES))}",
        )
    try:
        rec = legal_svc.update_discovery_status(matter_id, discovery_id, body.status, body.response_note)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "updated", "discovery": rec.model_dump(mode="json")}


# =============================================================================
# Exhibits
# =============================================================================


@router.get("/matters/{matter_id}/exhibits")
async def list_exhibits(matter_id: str, request: Request):
    """List all exhibits for a matter (numbered sequentially)."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    try:
        legal_svc.load_matter(matter_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matter not found")
    exhibits = legal_svc.list_exhibits(matter_id)
    return {"exhibits": [e.model_dump(mode="json") for e in exhibits], "count": len(exhibits)}


@router.post("/matters/{matter_id}/exhibits")
async def add_exhibit(matter_id: str, body: AddExhibitRequest, request: Request):
    """Add an exhibit to a matter. Exhibit number is auto-assigned sequentially."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    try:
        ex = legal_svc.add_exhibit(
            matter_id=matter_id,
            description=body.description,
            evidence_item_id=body.evidence_item_id,
            vault_path=body.vault_path,
            introduced_on=body.introduced_on,
            notes=body.notes,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matter not found")
    logger.info("Exhibit %s (#%d) added to matter %s by %s", ex.exhibit_id, ex.exhibit_number, matter_id, user_id)
    return {"status": "created", "exhibit": ex.model_dump(mode="json")}


# =============================================================================
# Overlay
# =============================================================================


@router.get("/matters/{matter_id}/overlay")
async def matter_overlay(matter_id: str, request: Request):
    """Get combined overlay payload for a matter (filings + discovery + exhibits)."""
    user_id = require_request_user_id(request)
    _require_legal(user_id)
    try:
        legal_svc.load_matter(matter_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Matter not found")
    return legal_svc.matter_overlay_payload(matter_id)
