
from fastapi import APIRouter, HTTPException, Request
from app.core.user_id import get_role_from_user_id
from app.models.legal_filing_models import LegalCase, EvidenceItem
from app.services.legal_filing_service import (
    save_case,
    load_case,
    list_cases,
    save_evidence,
    list_evidence,
)

router = APIRouter(prefix="/api/legal-filing", tags=["Legal Filing"])


def _get_user_role(request: Request) -> str:
    user_id = request.cookies.get("semptify_uid", "anonymous")
    role = get_role_from_user_id(user_id)
    # Default to "user" role if parsing fails (e.g., "anonymous" or malformed)
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
