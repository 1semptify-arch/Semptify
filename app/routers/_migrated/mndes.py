"""
MNDES Router — Minnesota Digital Exhibit System Integration
===========================================================

Endpoints for MNDES compliance validation, exhibit package building,
and submission tracking per MN Supreme Court Order ADM09-8010.

All navigation follows SSOT architecture (app.core.navigation).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pathlib import Path

from app.core.mndes_compliance import (
    MNDES_FILE_TYPES_VERSION,
    MNDES_ORDER_NUMBER,
    MNDES_PORTAL_URL,
    MNDES_SUPPORT_PHONE_METRO,
    MNDES_SUPPORT_PHONE_OTHER,
    MNDES_SUPPORT_HOURS,
    MNDES_USER_WARNINGS,
    mndes_validator,
    get_conversion_action,
)
from app.models.mndes_exhibit import (
    MNDESAttestationRequest,
    MNDESCaseType,
    MNDESExhibitPackage,
    MNDESPackageCreateRequest,
    MNDESSubmissionConfirmRequest,
    MNDESValidateRequest,
)
from app.services.mndes_exhibit_service import mndes_exhibit_service
from app.services.vault_upload_service import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["MNDES — Court Exhibit System"])

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


# ============================================================================
# Guide page (SSOT path: /mndes/guide)
# ============================================================================

@router.get("/mndes/guide", response_class=HTMLResponse)
async def mndes_guide() -> FileResponse:
    """
    Serve the MNDES submission guide (step-by-step).
    SSOT path registered in navigation.COURT_FLOW['mndes_guide'].
    """
    guide_path = _STATIC_DIR / "mndes" / "guide.html"
    if guide_path.exists():
        return FileResponse(str(guide_path))
    return HTMLResponse("<h1>MNDES Guide not found</h1>", status_code=404)


@router.get("/mndes/compliance-guide", response_class=HTMLResponse)
async def mndes_compliance_guide(role: str = "") -> FileResponse:
    """
    Serve the full MNDES compliance reference guide (all roles).
    SSOT path registered in navigation.COURT_FLOW['mndes_compliance_guide'].
    Optional ?role= query param pre-selects the relevant role tab.
    """
    guide_path = _STATIC_DIR / "mndes" / "compliance-guide.html"
    if guide_path.exists():
        return FileResponse(str(guide_path))
    return HTMLResponse("<h1>MNDES Compliance Guide not found</h1>", status_code=404)


# ============================================================================
# File Type Reference
# ============================================================================

@router.get("/api/mndes/acceptable-file-types")
async def get_acceptable_file_types() -> JSONResponse:
    """
    Return the current MNDES Acceptable File Types List.

    This list is governed by MN Supreme Court Order ADM09-8010 §5.
    The State Court Administrator maintains and publishes the official list
    at mncourts.gov/mndes. Semptify mirrors it here for offline validation.
    """
    by_category = mndes_validator.get_accepted_by_category()
    all_types = mndes_validator.get_accepted_extensions()

    return JSONResponse({
        "order_reference": MNDES_ORDER_NUMBER,
        "file_types_version": MNDES_FILE_TYPES_VERSION,
        "official_list_url": "https://mncourts.gov/help-topics/evidence-and-exhibits/minnesota-digital-exhibit-system-mndes",
        "by_category": by_category,
        "all_extensions": all_types,
        "notes": [
            "Do NOT upload zipped or compressed archives.",
            "Upload each exhibit as a separate file.",
            "Files requiring proprietary players must be converted or require a judge exception.",
            "Check mncourts.gov/mndes for the current official list.",
        ],
    })


# ============================================================================
# Single-file compliance check
# ============================================================================

@router.get("/api/mndes/validate-file")
async def validate_file(filename: str, file_size_bytes: Optional[int] = None) -> JSONResponse:
    """
    Validate a single filename for MNDES compliance.

    Checks extension against the Acceptable File Types List and returns
    compliance status, jury-room eligibility, and any required actions.
    """
    result = mndes_validator.validate_for_mndes(filename, file_size_bytes)
    conversion_action = get_conversion_action(result.file_extension) if not result.is_mndes_compliant else None
    return JSONResponse({
        "filename": filename,
        "is_mndes_compliant": result.is_mndes_compliant,
        "file_extension": result.file_extension,
        "file_category": result.file_category,
        "is_jury_room_eligible": result.is_jury_room_eligible,
        "conversion_required": result.conversion_required,
        "judge_exception_required": result.judge_exception_required,
        "is_prohibited": result.is_prohibited,
        "issues": [i.value for i in result.issues],
        "issue_details": result.issue_details,
        "recommended_action": result.recommended_action,
        "conversion_action": conversion_action,
        "file_types_version": result.file_types_version,
        "order_reference": result.order_reference,
    })


# ============================================================================
# Batch validation from vault
# ============================================================================

@router.post("/api/mndes/validate")
async def validate_vault_files(request: MNDESValidateRequest) -> JSONResponse:
    """
    Validate a batch of vault files for MNDES compliance.

    Accepts vault_ids + case metadata. Returns per-file compliance results
    and a package-level summary.

    Note: This endpoint validates file types only. Semptify does not have
    access to actual file bytes at this endpoint — full content scanning
    happens at upload time via file_validator.py.
    """
    if request.is_sealed_case:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "sealed_case",
                "message": MNDES_USER_WARNINGS["sealed_case"],
                "action": "Contact court administration at 651-377-7180",
            },
        )

    results = []
    compliant_count = 0
    jury_eligible_count = 0

    vault_service = get_vault_service()

    for vault_id in request.vault_ids:
        doc = vault_service.get_document(vault_id)
        filename = doc.filename if doc else vault_id
        file_size = doc.file_size if doc else None
        result = mndes_validator.validate_for_mndes(filename, file_size)
        is_compliant = result.is_mndes_compliant
        if is_compliant:
            compliant_count += 1
        if result.is_jury_room_eligible:
            jury_eligible_count += 1

        conversion_action = get_conversion_action(result.file_extension) if not is_compliant else None
        results.append({
            "vault_id": vault_id,
            "filename": filename,
            "is_mndes_compliant": is_compliant,
            "file_extension": result.file_extension,
            "file_category": result.file_category,
            "is_jury_room_eligible": result.is_jury_room_eligible,
            "conversion_required": result.conversion_required,
            "judge_exception_required": result.judge_exception_required,
            "is_prohibited": result.is_prohibited,
            "issues": [i.value for i in result.issues],
            "issue_details": result.issue_details,
            "recommended_action": result.recommended_action,
            "conversion_action": conversion_action,
        })

    warnings = [MNDES_USER_WARNINGS["semptify_not_mndes"]]
    if request.no_contact_order:
        warnings.append(MNDES_USER_WARNINGS["no_contact_order"])

    return JSONResponse({
        "mn_case_number": request.mn_case_number,
        "total_files": len(request.vault_ids),
        "compliant": compliant_count,
        "non_compliant": len(request.vault_ids) - compliant_count,
        "jury_room_eligible": jury_eligible_count,
        "all_clear": compliant_count == len(request.vault_ids),
        "results": results,
        "warnings": warnings,
        "file_types_version": MNDES_FILE_TYPES_VERSION,
        "order_reference": MNDES_ORDER_NUMBER,
    })


# ============================================================================
# Exhibit Package
# ============================================================================

@router.post("/api/mndes/package", response_model=MNDESExhibitPackage)
async def create_exhibit_package(
    request: MNDESPackageCreateRequest,
    req: Request,
) -> JSONResponse:
    """
    Build an MNDES exhibit package for a court case.

    Validates each vault file, assigns exhibit names, flags jury-room
    eligibility, and returns a checklist for submission.

    The user must complete manual upload at the MNDES portal —
    Semptify cannot submit directly (no public API exists).
    """
    if request.is_sealed_case:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "sealed_case",
                "message": MNDES_USER_WARNINGS["sealed_case"],
            },
        )

    user_id = _extract_user_id(req)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    _vault_service = get_vault_service()
    vault_docs = [
        {
            "vault_id": vid,
            "filename": doc.filename if (doc := _vault_service.get_document(vid)) else vid,
            "file_size_bytes": doc.file_size if (doc := _vault_service.get_document(vid)) else None,
        }
        for vid in request.vault_ids
    ]

    try:
        package = mndes_exhibit_service.create_package(request, vault_docs, user_id)
    except Exception as exc:
        logger.error("Failed to create MNDES package: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create exhibit package")

    return JSONResponse(package.dict())


@router.get("/api/mndes/package/{package_id}")
async def get_exhibit_package(package_id: str) -> JSONResponse:
    """Retrieve an exhibit package and its compliance status."""
    package = mndes_exhibit_service.get_package(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return JSONResponse(package.dict())


@router.get("/api/mndes/package/{package_id}/checklist")
async def get_submission_checklist(package_id: str) -> JSONResponse:
    """
    Return the pre-submission checklist for an exhibit package.

    Covers all Order ADM09-8010 requirements the user must satisfy
    before uploading to the MNDES portal.
    """
    try:
        checklist = mndes_exhibit_service.get_submission_checklist(package_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return JSONResponse(checklist)


@router.get("/api/mndes/package/{package_id}/compliance")
async def get_package_compliance(package_id: str) -> JSONResponse:
    """Return compliance summary for a package."""
    try:
        summary = mndes_exhibit_service.get_compliance_summary(package_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return JSONResponse(summary.dict())


# ============================================================================
# Attestation
# ============================================================================

@router.post("/api/mndes/package/attest")
async def apply_attestations(request: MNDESAttestationRequest) -> JSONResponse:
    """
    Record user attestations required before MNDES submission.

    Per Order ADM09-8010 §10: user must confirm no sexual content/nudity.
    Semptify also requires acknowledgment that:
    - Exhibits are not discovery documents
    - Exhibits are not motion/affidavit attachments (those go via eFS)
    - Court will not return digital exhibits
    - Semptify ≠ MNDES submission
    """
    try:
        package = mndes_exhibit_service.apply_attestations(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return JSONResponse({
        "package_id": package.package_id,
        "checklist_complete": package.checklist_complete,
        "message": (
            "Attestations recorded. You may now proceed to upload at the MNDES portal."
            if package.checklist_complete
            else "Some attestations are incomplete. Please review all items."
        ),
        "mndes_portal_url": MNDES_PORTAL_URL,
    })


# ============================================================================
# Submission Confirmation
# ============================================================================

@router.post("/api/mndes/package/confirm-submission")
async def confirm_submission(request: MNDESSubmissionConfirmRequest) -> JSONResponse:
    """
    User confirms they completed manual upload at the MNDES portal.

    Records the MNDES tracking number assigned by the portal.
    This is the final step in the Semptify-MNDES workflow.
    """
    try:
        package = mndes_exhibit_service.confirm_submission(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return JSONResponse({
        "package_id": package.package_id,
        "exhibit_id": request.exhibit_id,
        "mndes_tracking_number": request.mndes_tracking_number,
        "submission_complete": package.mndes_submission_complete,
        "message": (
            "All exhibits confirmed submitted to MNDES."
            if package.mndes_submission_complete
            else "Submission recorded. Confirm remaining exhibits when uploaded."
        ),
        "reminder": MNDES_USER_WARNINGS["not_evidence_until_offered"],
    })


# ============================================================================
# Submission Guide
# ============================================================================

@router.get("/api/mndes/submission-guide")
async def get_submission_guide() -> JSONResponse:
    """
    Return structured step-by-step instructions for submitting exhibits to MNDES.

    This is the authoritative user-facing guide. The static HTML page at
    /mndes/guide also renders this data.
    """
    return JSONResponse({
        "title": "How to Submit Exhibits to MNDES",
        "order_reference": MNDES_ORDER_NUMBER,
        "effective_date": "January 1, 2025",
        "portal_url": MNDES_PORTAL_URL,
        "support": {
            "phone_metro": MNDES_SUPPORT_PHONE_METRO,
            "phone_other": MNDES_SUPPORT_PHONE_OTHER,
            "hours": MNDES_SUPPORT_HOURS,
            "contact_form": "https://www.mncourts.gov/MNDES/Contact.aspx",
        },
        "steps": [
            {
                "step": 1,
                "title": "Prepare your files in Semptify",
                "detail": "Upload documents to your Semptify vault. Use the MNDES compliance checker to confirm all files are on the Acceptable File Types List.",
            },
            {
                "step": 2,
                "title": "Convert any non-compliant files",
                "detail": "Convert proprietary formats to MP4, MP3, PDF, or JPG. If conversion is impossible, contact the presiding judge BEFORE the hearing to request an exception (Order §6).",
            },
            {
                "step": 3,
                "title": "Create an MNDES account (if needed)",
                "detail": f"Register at {MNDES_PORTAL_URL} using your legal name and email. Compatible with Chrome, Edge, and Safari.",
            },
            {
                "step": 4,
                "title": "Log in and find your case",
                "detail": "Enter your full MN case number (e.g. 19WS-CV-24-1234). Omitting dashes is acceptable.",
            },
            {
                "step": 5,
                "title": "Upload each exhibit individually",
                "detail": "Do NOT combine exhibits. Do NOT zip/compress. Upload one file at a time. Give each a descriptive name (e.g. 'Photo of rear door — June 12').",
            },
            {
                "step": 6,
                "title": "Set exhibit visibility",
                "detail": "Set as 'public' unless: (a) medical record in Civil Commitment case, or (b) a court order restricts access. Pre-hearing exhibits are automatically non-public.",
            },
            {
                "step": 7,
                "title": "Share with the opposing party (if required)",
                "detail": "Use MNDES Share function to notify opposing party. If a no-contact order (OFP/HRO/DANCO) is in place, contact court administration for instructions — do NOT use MNDES sharing.",
            },
            {
                "step": 8,
                "title": "Record your MNDES tracking numbers in Semptify",
                "detail": "Each uploaded file gets a unique tracking number in MNDES. Enter it back into Semptify to complete your audit trail.",
            },
            {
                "step": 9,
                "title": "At the hearing: OFFER each exhibit to the judge",
                "detail": "Uploading does NOT automatically make an exhibit evidence. You must ask the judge to admit each exhibit during the hearing.",
            },
            {
                "step": 10,
                "title": "Retain your own copies",
                "detail": "The court will NOT return digital exhibits. Keep original copies on your own device or storage.",
            },
        ],
        "important_limits": [
            "Maximum file size per exhibit: 100 GB (per Dakota County Guidelines)",
            "No zipped or compressed files",
            "No sexual content or nudity — submit as physical exhibit instead",
            "No discovery documents (Alford Packets) unless ordered by judge",
            "No motion/affidavit attachments — use eFile & eServe (eFS) instead",
            "Sealed cases: cannot upload directly — call court admin at 651-377-7180",
            "Certified copies authenticating originals must be physical exhibits",
            "In-camera review exhibits go to judge's chambers, not MNDES",
        ],
        "warnings": list(MNDES_USER_WARNINGS.values()),
    })


# ============================================================================
# Helpers
# ============================================================================

def _extract_user_id(req: Request) -> Optional[str]:
    """Extract user_id from signed cookie. Returns None if not authenticated."""
    try:
        from app.core.user_id import parse_user_id
        raw = req.cookies.get("user_id", "")
        parsed = parse_user_id(raw)
        return parsed.get("user_id") if parsed else None
    except Exception:
        return None


def _stub_vault_lookup(vault_ids: list[str]) -> list[dict]:
    """
    Temporary stub: returns minimal doc dicts from vault_ids.

    In production this should query VaultUploadService or the vault index.
    The filename is extracted from the vault_id prefix until a real lookup
    is wired. The MNDES validator uses filename extension — vault_ids that
    end in an extension (e.g. 'doc_abc123.pdf') will validate correctly.
    """
    return [{"vault_id": vid, "filename": vid, "file_size_bytes": None} for vid in vault_ids]
