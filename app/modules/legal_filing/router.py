
from fastapi import APIRouter, HTTPException, Request

from app.core.request_utils import get_request_user_id
from app.core.user_id import get_role_from_user_id
from app.models.legal_filing_models import EvidenceItem, LegalCase

from .service import (
    list_cases,
    list_evidence,
    load_case,
    save_case,
    save_evidence,
)

router = APIRouter(prefix="/api/legal-filing", tags=["Legal Filing"])


def _resolve_overlay_context(evidence: EvidenceItem) -> EvidenceItem:
    """Prefer overlay-linked vault and extraction context, fallback to legacy evidence fields.

    Overlay records now live in user cloud storage via the unified overlay
    manager (async, requires storage context).  This sync helper returns
    evidence unchanged; callers that need enriched overlay context should
    query the unified overlay manager from an async endpoint.
    """
    return evidence


def _get_user_role(request: Request) -> str:
    user_id = get_request_user_id(request)
    role = get_role_from_user_id(user_id)
    if not role:
        role = "user"
    return role


def _require_roles(request: Request, allowed_roles):
    role = _get_user_role(request)
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient role privileges")
    return role


@router.get("/cases")
def get_cases(request: Request):
    _require_roles(request, ["user", "manager", "advocate", "legal", "admin"])
    return list_cases()

@router.get("/cases/{case_id}")
def get_case(case_id: str, request: Request):
    _require_roles(request, ["user", "manager", "advocate", "legal", "admin"])
    try:
        return load_case(case_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")


@router.post("/cases")
def create_case(case: LegalCase, request: Request):
    _require_roles(request, ["advocate", "legal", "admin"])
    saved = save_case(case)
    return {"status": "created", "case": saved}


@router.post("/cases/{case_id}/evidence")
def add_evidence(case_id: str, evidence: EvidenceItem, request: Request):
    _require_roles(request, ["advocate", "legal", "admin"])
    if evidence.case_id != case_id:
        raise HTTPException(status_code=400, detail="Mismatch case_id in path and body")
    try:
        _ = load_case(case_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    evidence = _resolve_overlay_context(evidence)
    saved = save_evidence(case_id, evidence)
    return {"status": "evidence added", "evidence": saved}


@router.get("/cases/{case_id}/evidence")
def get_evidence(case_id: str, request: Request):
    _require_roles(request, ["user", "manager", "advocate", "legal", "admin"])
    try:
        _ = load_case(case_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    return list_evidence(case_id)
