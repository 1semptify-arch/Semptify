"""
Semptify 5.0 - Complaint Filing Wizard Router
API endpoints for guided complaint filing with regulatory agencies.
Integrated with Location Service for state-specific agencies.
NOW WITH DATABASE PERSISTENCE.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.core.request_utils import get_request_user_id
from app.core.security import get_optional_user_id, sanitize_user_input
from app.core.utc import utc_now
from app.core.user_context import build_context_for_user_id
from app.services.complaint_wizard import (
    AgencyType,
    ComplaintDraft,
    ComplaintStatus,
    complaint_wizard,
)

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateDraftRequest(BaseModel):
    """Request to create a complaint draft."""

    agency_id: str
    subject: str = ""


class UpdateDraftRequest(BaseModel):
    """Request to update a complaint draft."""

    subject: str | None = None
    description: str | None = None
    incident_dates: list[str] | None = None
    damages_claimed: float | None = None
    relief_sought: str | None = None
    respondent_name: str | None = None
    respondent_company: str | None = None
    respondent_address: str | None = None
    respondent_phone: str | None = None
    timeline_included: bool | None = None
    notes: str | None = None


class AttachDocumentsRequest(BaseModel):
    """Request to attach documents to a draft."""

    document_ids: list[str]


class MarkFiledRequest(BaseModel):
    """Request to mark complaint as filed."""

    confirmation_number: str | None = None


class RecommendAgenciesRequest(BaseModel):
    """Request for agency recommendations."""

    keywords: list[str]


class AgencyResponse(BaseModel):
    """Agency information response."""

    id: str
    name: str
    type: str
    description: str
    jurisdiction: str
    website: str
    filing_url: str | None
    phone: str | None
    email: str | None
    typical_response_days: int
    complaint_types: list[str]
    required_documents: list[str]
    tips: list[str]


# =============================================================================
# Helper: Get User ID from Request
# =============================================================================


def get_user_id_from_request(request: Request, user_id: str | None = None) -> str:
    """Get user ID from authenticated context or the canonical cookie."""
    if user_id:
        return user_id
    return get_request_user_id(request)


# =============================================================================
# Agency Endpoints
# =============================================================================


@router.get("/agencies")
async def list_agencies(
    request: Request,
    agency_type: AgencyType | None = None,
    state: str | None = Query(None, description="State code (e.g., MN). If not provided, uses user's location."),
) -> list[AgencyResponse]:
    """
    List available complaint agencies.

    Agencies are filtered by state. If no state is provided,
    uses the user's location from the Location Service.
    """
    if agency_type:
        agencies = complaint_wizard.get_agencies_by_type(agency_type)
    elif state:
        agencies = complaint_wizard.get_all_agencies(state.upper())
    else:
        # Use location service to get user's state
        user_id = get_user_id_from_request(request)
        agencies = complaint_wizard.get_agencies_for_user(user_id)

    return [
        AgencyResponse(
            id=a.id,
            name=a.name,
            type=a.type.value,
            description=a.description,
            jurisdiction=a.jurisdiction,
            website=a.website,
            filing_url=a.filing_url,
            phone=a.phone,
            email=a.email,
            typical_response_days=a.typical_response_days,
            complaint_types=a.complaint_types,
            required_documents=a.required_documents,
            tips=a.tips,
        )
        for a in agencies
    ]


@router.get("/agencies/{agency_id}")
async def get_agency(agency_id: str) -> AgencyResponse:
    """Get details for a specific agency."""
    agency = complaint_wizard.get_agency(agency_id)
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")

    return AgencyResponse(
        id=agency.id,
        name=agency.name,
        type=agency.type.value,
        description=agency.description,
        jurisdiction=agency.jurisdiction,
        website=agency.website,
        filing_url=agency.filing_url,
        phone=agency.phone,
        email=agency.email,
        typical_response_days=agency.typical_response_days,
        complaint_types=agency.complaint_types,
        required_documents=agency.required_documents,
        tips=agency.tips,
    )


@router.post("/agencies/recommend")
async def recommend_agencies(request: RecommendAgenciesRequest) -> list[AgencyResponse]:
    """Get agency recommendations based on complaint keywords."""
    agencies = complaint_wizard.get_recommended_agencies(request.keywords)

    return [
        AgencyResponse(
            id=a.id,
            name=a.name,
            type=a.type.value,
            description=a.description,
            jurisdiction=a.jurisdiction,
            website=a.website,
            filing_url=a.filing_url,
            phone=a.phone,
            email=a.email,
            typical_response_days=a.typical_response_days,
            complaint_types=a.complaint_types,
            required_documents=a.required_documents,
            tips=a.tips,
        )
        for a in agencies
    ]


@router.get("/agencies/{agency_id}/checklist")
async def get_agency_checklist(agency_id: str) -> dict:
    """Get filing checklist for an agency."""
    checklist = complaint_wizard.get_filing_checklist(agency_id)
    if "error" in checklist:
        raise HTTPException(status_code=404, detail=checklist["error"])
    return checklist


# =============================================================================
# Draft Endpoints
# =============================================================================


@router.post("/drafts")
async def create_draft(
    request_body: CreateDraftRequest,
    request: Request,
    user_id: str | None = Depends(get_optional_user_id),
) -> ComplaintDraft:
    """Create a new complaint draft (persisted to the tenant's cloud vault)."""
    # Get user_id from session or fallback
    uid = get_user_id_from_request(request, user_id)
    user = await build_context_for_user_id(uid)

    # Verify agency exists
    agency = complaint_wizard.get_agency(request_body.agency_id)
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")

    return await complaint_wizard.create_draft_vault(
        user, agency_id=request_body.agency_id, subject=sanitize_user_input(request_body.subject)
    )


@router.get("/drafts")
async def list_drafts(
    request: Request, user_id: str | None = Depends(get_optional_user_id)
) -> list[ComplaintDraft]:
    """List all drafts for a user (from their cloud vault)."""
    uid = get_user_id_from_request(request, user_id)
    user = await build_context_for_user_id(uid)
    return await complaint_wizard.get_user_drafts_vault(user)


@router.get("/drafts/{draft_id}")
async def get_draft(
    draft_id: str, request: Request, user_id: str | None = Depends(get_optional_user_id)
) -> ComplaintDraft:
    """Get a specific draft (from the tenant's cloud vault)."""
    uid = get_user_id_from_request(request, user_id)
    user = await build_context_for_user_id(uid)
    draft = await complaint_wizard.get_draft_vault(user, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.patch("/drafts/{draft_id}")
async def update_draft(
    draft_id: str, request: UpdateDraftRequest, http_request: Request,
    user_id: str | None = Depends(get_optional_user_id),
) -> ComplaintDraft:
    """Update a complaint draft (in the tenant's cloud vault)."""
    uid = get_user_id_from_request(http_request, user_id)
    user = await build_context_for_user_id(uid)
    updates = request.model_dump(exclude_none=True)
    draft = await complaint_wizard.update_draft_vault(user, draft_id, **updates)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.delete("/drafts/{draft_id}")
async def delete_draft(
    draft_id: str, request: Request, user_id: str | None = Depends(get_optional_user_id)
) -> dict:
    """Delete a complaint draft (from the tenant's cloud vault)."""
    uid = get_user_id_from_request(request, user_id)
    user = await build_context_for_user_id(uid)
    success = await complaint_wizard.delete_draft_vault(user, draft_id)
    if not success:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"status": "deleted", "draft_id": draft_id}


@router.post("/drafts/{draft_id}/documents")
async def attach_documents(
    draft_id: str, request: AttachDocumentsRequest, http_request: Request,
    user_id: str | None = Depends(get_optional_user_id),
) -> ComplaintDraft:
    """Attach documents to a draft (in the tenant's cloud vault)."""
    uid = get_user_id_from_request(http_request, user_id)
    user = await build_context_for_user_id(uid)
    draft = await complaint_wizard.attach_documents_vault(user, draft_id, request.document_ids)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.get("/drafts/{draft_id}/preview")
async def preview_complaint(
    draft_id: str, request: Request, user_id: str | None = Depends(get_optional_user_id)
) -> dict:
    """Preview the formatted complaint text."""
    uid = get_user_id_from_request(request, user_id)
    user = await build_context_for_user_id(uid)
    draft = await complaint_wizard.get_draft_vault(user, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    text = complaint_wizard.generate_complaint_text(draft)
    agency = complaint_wizard.get_agency(draft.agency_id)

    return {
        "draft_id": draft_id,
        "agency": agency.name if agency else "Unknown",
        "filing_url": agency.filing_url if agency else None,
        "complaint_text": text,
        "attached_documents": len(draft.attached_document_ids),
        "ready_to_file": bool(draft.subject and draft.description and draft.respondent_name),
    }


@router.get("/drafts/{draft_id}/export")
async def export_complaint(
    draft_id: str,
    request: Request,
    user_id: str | None = Depends(get_optional_user_id),
    format: str = Query("text", description="Export format: text, html, or pdf"),
):
    """Export complaint as text, HTML, or attempt PDF."""
    from fastapi.responses import HTMLResponse, PlainTextResponse

    uid = get_user_id_from_request(request, user_id)
    user = await build_context_for_user_id(uid)
    draft = await complaint_wizard.get_draft_vault(user, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    text = complaint_wizard.generate_complaint_text(draft)
    agency = complaint_wizard.get_agency(draft.agency_id)

    if format == "html":
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Complaint - {draft.subject or "Draft"}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.8; }}
        h1 {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        .section {{ margin: 20px 0; }}
        .section-title {{ font-weight: bold; border-bottom: 1px solid #ccc; margin-bottom: 10px; }}
        pre {{ white-space: pre-wrap; font-family: inherit; }}
    </style>
</head>
<body>
    <h1>FORMAL COMPLAINT</h1>
    <p style="text-align: center;">To: {agency.name if agency else "Agency"}</p>
    <pre>{text}</pre>
</body>
</html>
"""
        return HTMLResponse(content=html_content)

    # Default: plain text
    return PlainTextResponse(content=text, media_type="text/plain")


@router.post("/drafts/{draft_id}/file")
async def mark_complaint_filed(
    draft_id: str, request: MarkFiledRequest, http_request: Request,
    user_id: str | None = Depends(get_optional_user_id),
) -> ComplaintDraft:
    """Mark a complaint as filed (in the tenant's cloud vault)."""
    uid = get_user_id_from_request(http_request, user_id)
    user = await build_context_for_user_id(uid)
    draft = await complaint_wizard.mark_as_filed_vault(user, draft_id, confirmation_number=request.confirmation_number)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


# =============================================================================
# Quick Actions
# =============================================================================


@router.get("/quick-start")
async def quick_start_guide() -> dict:
    """Get quick start guide for filing complaints."""
    return {
        "title": "Complaint Filing Quick Start",
        "steps": [
            {
                "step": 1,
                "title": "Choose Your Target",
                "description": "Select the agency most likely to help with your specific issue",
                "action": "GET /api/complaints/agencies or POST /api/complaints/agencies/recommend",
            },
            {
                "step": 2,
                "title": "Create a Draft",
                "description": "Start your complaint draft with the chosen agency",
                "action": "POST /api/complaints/drafts",
            },
            {
                "step": 3,
                "title": "Fill In Details",
                "description": "Add your complaint details, dates, and respondent info",
                "action": "PATCH /api/complaints/drafts/{id}",
            },
            {
                "step": 4,
                "title": "Attach Evidence",
                "description": "Link your uploaded documents to the complaint",
                "action": "POST /api/complaints/drafts/{id}/documents",
            },
            {
                "step": 5,
                "title": "Preview & File",
                "description": "Review the formatted complaint and file with the agency",
                "action": "GET /api/complaints/drafts/{id}/preview",
            },
            {
                "step": 6,
                "title": "Track Status",
                "description": "Record your filing confirmation and track progress",
                "action": "POST /api/complaints/drafts/{id}/file",
            },
        ],
        "tips": [
            "File with multiple agencies for maximum pressure",
            "The Attorney General handles fraud and deceptive practices",
            "HUD handles housing discrimination specifically",
            "MN Commerce can revoke property manager licenses",
            "BBB complaints become public record",
            "HOME Line offers free tenant advice hotline",
            "Legal Aid can represent you in court for free",
            "City leaders matter too — a factual letter to your council member or mayor routes city departments (see /api/campaign/leader-letter)",
        ],
        "recommended_order": [
            "1. HOME Line (get immediate advice - 612-728-5767)",
            "2. Legal Aid MN (free legal representation)",
            "3. MN Attorney General (strongest enforcement)",
            "4. HUD (if any discrimination involved)",
            "5. MN Commerce (license accountability)",
            "6. City council member or mayor (civic pressure - POST /api/campaign/leader-letter)",
            "7. BBB (public pressure)",
        ],
    }


@router.post("/analyze-case")
async def analyze_case_for_complaints(
    keywords: list[str] = Query(..., description="Keywords describing your situation"),
) -> dict:
    """Analyze your case and recommend complaint strategies."""
    recommended = complaint_wizard.get_recommended_agencies(keywords)

    strategies = []
    for agency in recommended[:5]:
        strategies.append(
            {
                "agency": agency.name,
                "agency_id": agency.id,
                "why": f"Handles: {', '.join(agency.complaint_types[:3])}",
                "filing_url": agency.filing_url,
                "response_time": f"~{agency.typical_response_days} days",
            }
        )

    return {
        "keywords_analyzed": keywords,
        "recommended_strategies": strategies,
        "multi_agency_approach": len(recommended) > 1,
        "advice": (
            "Filing with multiple agencies creates pressure from multiple directions. "
            "Start with Legal Aid for guidance, then file formal complaints with regulatory bodies."
        ),
    }


# =============================================================================
# Wizard Session Endpoints (for guided complaint flow)
#
# Sessions are ephemeral (in-memory, 4h TTL) — nothing personal is stored
# server-side while a tenant walks the steps. Finishing produces a complaint
# draft: persisted to the tenant's own vault when identified, or returned as
# text + filing instructions for an anonymous visitor. Semptify never files
# on the tenant's behalf.
# =============================================================================


class WizardStartRequest(BaseModel):
    """Request to start a complaint wizard session."""

    complaint_type: str


class WizardAnswerRequest(BaseModel):
    """Answer for the current wizard step — fields depend on the step."""

    model_config = {"extra": "allow"}

    complaint_type: str | None = None
    keywords: list[str] | str | None = None
    text: str | None = None
    agency_id: str | None = None
    details: dict | None = None


@router.post("/wizard/start")
async def start_wizard(request: WizardStartRequest) -> dict:
    """Start a guided complaint session; returns the next step's prompt."""
    try:
        return complaint_wizard.wizard_start(request.complaint_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/wizard/{session_id}")
async def get_wizard_session(session_id: str) -> dict:
    """Get current wizard session state (step, prompt, options, collected)."""
    state = complaint_wizard.wizard_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Wizard session not found")
    return state


@router.post("/wizard/{session_id}/answer")
async def answer_wizard(session_id: str, request: WizardAnswerRequest) -> dict:
    """Answer the current step; returns the next step's state."""
    try:
        return complaint_wizard.wizard_answer(session_id, **request.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Wizard session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _filing_instructions(agency) -> list[str]:
    """Honest next steps — the tenant files the complaint themselves."""
    channel = agency.filing_url or agency.website
    steps = ["Review the complaint and edit anything that is missing."]
    if channel:
        steps.append(f"File it with {agency.name}: {channel}")
    elif agency.phone:
        steps.append(f"File it with {agency.name}: call {agency.phone}")
    steps.append(f"{agency.name} typically responds in ~{agency.typical_response_days} days.")
    steps.append("Save any confirmation or tracking number, then mark the draft filed to keep tracking it.")
    return steps


@router.post("/wizard/{session_id}/finish")
async def finish_wizard(
    session_id: str, request: Request, user_id: str | None = Depends(get_optional_user_id)
) -> dict:
    """Finish the wizard and prepare the complaint.

    Identified tenant: a real draft is created in their vault, marked ready.
    Anonymous visitor: the generated complaint text and filing instructions
    are returned without storing anything.
    """
    payload = complaint_wizard.wizard_finish(session_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Wizard session not found")

    agency = complaint_wizard.get_agency(payload["agency_id"]) if payload["agency_id"] else None
    uid = get_user_id_from_request(request, user_id)
    user = await build_context_for_user_id(uid)

    if user is not None:
        draft = await complaint_wizard.create_draft_vault(
            user,
            agency_id=payload["agency_id"],
            subject=sanitize_user_input(payload["subject"]),
            complaint_type=payload["complaint_type"],
        )
        draft = await complaint_wizard.update_draft_vault(
            user,
            draft.id,
            description=payload["description"],
            incident_dates=payload["incident_dates"],
            respondent_name=payload["respondent_name"],
            respondent_company=payload["respondent_company"],
            respondent_address=payload["respondent_address"],
            respondent_phone=payload["respondent_phone"],
            relief_sought=payload["relief_sought"],
            damages_claimed=payload["damages_claimed"],
            status=ComplaintStatus.READY.value,
        )
        return {
            "status": "ready_to_file",
            "draft_id": draft.id,
            "agency": agency.name if agency else None,
            "filing_url": agency.filing_url if agency else None,
            "missing": payload["missing"],
            "next_steps": _filing_instructions(agency) if agency else ["Pick an agency and file the complaint yourself."],
        }

    text = complaint_wizard.generate_complaint_text(
        ComplaintDraft(
            id=session_id,
            user_id="",
            agency_id=payload["agency_id"],
            subject=payload["subject"],
            description=payload["description"],
            incident_dates=payload["incident_dates"],
            respondent_name=payload["respondent_name"],
            respondent_company=payload["respondent_company"],
            respondent_address=payload["respondent_address"],
            respondent_phone=payload["respondent_phone"],
            relief_sought=payload["relief_sought"],
            damages_claimed=payload["damages_claimed"],
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    )
    return {
        "status": "prepared",
        "complaint_text": text,
        "agency": agency.name if agency else None,
        "filing_url": agency.filing_url if agency else None,
        "checklist": complaint_wizard.get_filing_checklist(payload["agency_id"]) if agency else None,
        "missing": payload["missing"],
        "next_steps": _filing_instructions(agency) if agency else ["Pick an agency and file the complaint yourself."],
        "note": "Nothing was filed and nothing was stored. You file it yourself — the steps above say where.",
    }


# =============================================================================
# Submit Complaint Endpoint
# =============================================================================


class SubmitComplaintRequest(BaseModel):
    """Request to prepare a complaint for filing."""

    agency_id: str
    complaint_type: str = "general"
    subject: str = ""
    summary: str | None = None
    detailed_description: str | None = None
    target_type: str | None = None
    target_name: str | None = None
    session_id: str | None = None


@router.post("/submit")
async def submit_complaint(
    request_body: SubmitComplaintRequest,
    request: Request,
    user_id: str | None = Depends(get_optional_user_id),
) -> dict:
    """Prepare a complaint draft for the tenant to file.

    Creates a real draft marked ready — Semptify does not file on the
    tenant's behalf. With a wizard ``session_id``, answers collected in the
    session fill in fields not given explicitly.
    """
    agency = complaint_wizard.get_agency(request_body.agency_id)
    if not agency:
        raise HTTPException(status_code=422, detail="Invalid agency_id")

    collected: dict = {}
    if request_body.session_id:
        collected = complaint_wizard.wizard_finish(request_body.session_id) or {}

    subject = request_body.subject or collected.get("subject") or ""
    description = (
        request_body.detailed_description
        or request_body.summary
        or collected.get("description")
        or ""
    )
    respondent_name = request_body.target_name or collected.get("respondent_name") or ""

    uid = get_user_id_from_request(request, user_id)
    user = await build_context_for_user_id(uid)
    if user is None:
        return {
            "status": "prepared",
            "draft_id": None,
            "agency": agency.name,
            "agency_id": request_body.agency_id,
            "subject": subject,
            "description": description,
            "respondent_name": respondent_name,
            "created_at": utc_now().isoformat(),
            "filing_url": agency.filing_url,
            "next_steps": _filing_instructions(agency),
            "note": "Nothing was filed and nothing was stored. You file it yourself — the steps above say where.",
        }

    draft = await complaint_wizard.create_draft_vault(
        user,
        agency_id=request_body.agency_id,
        subject=sanitize_user_input(subject),
        complaint_type=request_body.complaint_type,
    )
    draft = await complaint_wizard.update_draft_vault(
        user,
        draft.id,
        description=description,
        incident_dates=collected.get("incident_dates") or [],
        respondent_name=respondent_name,
        respondent_company=collected.get("respondent_company") or "",
        respondent_address=collected.get("respondent_address") or "",
        respondent_phone=collected.get("respondent_phone") or "",
        relief_sought=collected.get("relief_sought") or "",
        status=ComplaintStatus.READY.value,
    )
    return {
        "status": "ready_to_file",
        "draft_id": draft.id,
        "agency": agency.name,
        "agency_id": request_body.agency_id,
        "subject": draft.subject,
        "created_at": draft.created_at.isoformat(),
        "filing_url": agency.filing_url,
        "next_steps": _filing_instructions(agency),
    }
