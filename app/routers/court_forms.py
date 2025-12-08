"""
Court Forms Router
==================
API endpoints for generating court forms:
- Answer to Eviction Complaint
- Motion to Dismiss
- Motion for Continuance
- Counterclaim
- Request for Hearing

Integrates with FormDataHub for auto-filling.
"""

import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.core.security import require_user, StorageUser
from app.services.court_form_generator import form_generator
from app.core.event_bus import event_bus, EventType as BusEventType

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/forms", tags=["Court Forms"])


# =============================================================================
# Request/Response Models
# =============================================================================

class FormGenerateRequest(BaseModel):
    """Request to generate a court form."""
    form_type: str  # answer_to_complaint, motion_to_dismiss, etc.
    case_data: Optional[dict] = None  # Override/supplement auto-filled data
    defenses: Optional[List[str]] = None  # Defense types to include
    output_format: str = "html"  # html, pdf, text


class FormResponse(BaseModel):
    """Response with generated form."""
    form_type: str
    title: str
    description: str
    format: str
    content: str  # HTML/text content or base64 PDF
    fields_used: List[str]
    generated_at: str


class FormTypeInfo(BaseModel):
    """Information about a form type."""
    type: str
    title: str
    description: str


class DefenseInfo(BaseModel):
    """Information about a defense type."""
    type: str
    title: str
    statute: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/types", response_model=List[FormTypeInfo])
async def list_form_types():
    """
    List all available court form types.
    
    Returns list of forms that can be generated:
    - answer_to_complaint: Answer to Eviction Complaint
    - motion_to_dismiss: Motion to Dismiss
    - motion_for_continuance: Motion for Continuance
    - counterclaim: Counterclaim
    - request_for_hearing: Request for Hearing
    """
    return form_generator.get_available_forms()


@router.get("/defenses", response_model=List[DefenseInfo])
async def list_defense_types():
    """
    List all available defense types for Answer forms.
    
    Returns defenses with their legal citations:
    - improper_notice: Notice defects
    - retaliation: Retaliatory eviction
    - habitability: Warranty of habitability
    - improper_service: Service defects
    - rent_escrow: Rent paid/escrowed
    - discrimination: Fair housing violations
    - waiver: Landlord waived right to evict
    - cure_within_time: Violation cured
    """
    return form_generator.get_available_defenses()


@router.post("/generate", response_model=FormResponse)
async def generate_form(
    request: FormGenerateRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Generate a court form with auto-filled data.
    
    Form will be populated from FormDataHub + any provided case_data.
    For Answer forms, include defense types to add defense paragraphs.
    
    Example:
    ```json
    {
        "form_type": "answer_to_complaint",
        "defenses": ["improper_notice", "habitability", "retaliation"],
        "output_format": "html"
    }
    ```
    """
    # Get case data from FormDataHub
    case_data = {}
    
    try:
        from app.services.form_data import get_form_data_service
        form_service = get_form_data_service(user.user_id)
        if form_service:
            hub_data = await form_service.get_full_data()
            case_data.update(hub_data)
    except Exception as e:
        logger.warning(f"Could not load FormDataHub: {e}")
    
    # Override with provided case_data
    if request.case_data:
        case_data.update(request.case_data)
    
    # Add user info
    case_data.setdefault("defendant_name", user.user_id)
    
    # Generate form
    result = await form_generator.generate_form(
        form_type=request.form_type,
        case_data=case_data,
        defenses=request.defenses,
        output_format=request.output_format,
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Convert bytes to base64 for PDF
    content = result["content"]
    if isinstance(content, bytes):
        import base64
        content = base64.b64encode(content).decode('utf-8')
    
    return FormResponse(
        form_type=result["form_type"],
        title=result["title"],
        description=result["description"],
        format=result["format"],
        content=content,
        fields_used=result["fields_used"],
        generated_at=result["generated_at"],
    )

    # Publish event to brain/event bus
    await event_bus.publish(BusEventType.COURT_FORM_GENERATED, {
        "user_id": user.user_id,
        "form_type": result["form_type"],
        "title": result["title"],
        "generated_at": result["generated_at"],
    })

    return response


@router.get("/generate/{form_type}", response_class=HTMLResponse)
async def generate_form_html(
    form_type: str,
    defenses: Optional[str] = None,  # Comma-separated defense types
    user: StorageUser = Depends(require_user),
):
    """
    Generate a court form and return HTML directly.
    
    Useful for preview in browser or embedding in UI.
    
    Query params:
    - defenses: Comma-separated list of defense types
    
    Example: /api/forms/generate/answer_to_complaint?defenses=improper_notice,habitability
    """
    # Get case data
    case_data = {}
    
    try:
        from app.services.form_data import get_form_data_service
        form_service = get_form_data_service(user.user_id)
        if form_service:
            hub_data = await form_service.get_full_data()
            case_data.update(hub_data)
    except Exception as e:
        logger.warning(f"Could not load FormDataHub: {e}")
    
    case_data.setdefault("defendant_name", user.user_id)
    
    # Parse defenses
    defense_list = defenses.split(",") if defenses else None
    
    # Generate HTML form
    result = await form_generator.generate_form(
        form_type=form_type,
        case_data=case_data,
        defenses=defense_list,
        output_format="html",
    )
    
    if "error" in result:
        return HTMLResponse(f"<h1>Error</h1><p>{result['error']}</p>", status_code=400)
    
    return HTMLResponse(result["content"])


@router.get("/download/{form_type}")
async def download_form_pdf(
    form_type: str,
    defenses: Optional[str] = None,
    user: StorageUser = Depends(require_user),
):
    """
    Generate and download a court form as PDF.
    
    Returns PDF file for download/printing.
    """
    # Get case data
    case_data = {}
    
    try:
        from app.services.form_data import get_form_data_service
        form_service = get_form_data_service(user.user_id)
        if form_service:
            hub_data = await form_service.get_full_data()
            case_data.update(hub_data)
    except Exception as e:
        logger.warning(f"Could not load FormDataHub: {e}")
    
    case_data.setdefault("defendant_name", user.user_id)
    
    # Parse defenses
    defense_list = defenses.split(",") if defenses else None
    
    # Generate PDF
    result = await form_generator.generate_form(
        form_type=form_type,
        case_data=case_data,
        defenses=defense_list,
        output_format="pdf",
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    content = result["content"]
    
    # Determine content type
    if isinstance(content, bytes):
        media_type = "application/pdf"
        filename = f"{form_type}_{datetime.now().strftime('%Y%m%d')}.pdf"
    else:
        # Fallback to HTML
        media_type = "text/html"
        filename = f"{form_type}_{datetime.now().strftime('%Y%m%d')}.html"
        content = content.encode('utf-8')
    
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/preview")
async def preview_form(
    request: FormGenerateRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Preview form data mapping without generating full form.
    
    Shows which fields will be populated and from where.
    Useful for debugging data flow.
    """
    from app.services.court_form_generator import FORM_MAPPINGS
    
    if request.form_type not in FORM_MAPPINGS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown form type. Available: {list(FORM_MAPPINGS.keys())}"
        )
    
    mapping = FORM_MAPPINGS[request.form_type]
    
    # Get case data
    case_data = {}
    try:
        from app.services.form_data import get_form_data_service
        form_service = get_form_data_service(user.user_id)
        if form_service:
            hub_data = await form_service.get_full_data()
            case_data.update(hub_data)
    except Exception:
        pass
    
    if request.case_data:
        case_data.update(request.case_data)
    
    # Show field mapping
    field_preview = {}
    for form_field, source_fields in mapping["fields"].items():
        value = None
        source = None
        for src in source_fields:
            if src in case_data and case_data[src]:
                value = case_data[src]
                source = src
                break
        
        field_preview[form_field] = {
            "value": value,
            "source": source,
            "possible_sources": source_fields,
            "populated": value is not None,
        }
    
    return {
        "form_type": request.form_type,
        "title": mapping["title"],
        "description": mapping["description"],
        "sections": mapping.get("sections", []),
        "fields": field_preview,
        "defenses_requested": request.defenses,
        "available_case_data": list(case_data.keys()),
    }


@router.get("/quick-answer")
async def quick_generate_answer(
    case_number: Optional[str] = None,
    defendant_name: Optional[str] = None,
    defenses: str = "improper_notice",
    user: StorageUser = Depends(require_user),
):
    """
    Quick endpoint to generate Answer to Eviction Complaint.
    
    Query params:
    - case_number: Override case number
    - defendant_name: Override defendant name  
    - defenses: Comma-separated defense types (default: improper_notice)
    
    Returns HTML form ready for printing.
    """
    case_data = {}
    
    try:
        from app.services.form_data import get_form_data_service
        form_service = get_form_data_service(user.user_id)
        if form_service:
            hub_data = await form_service.get_full_data()
            case_data.update(hub_data)
    except Exception:
        pass
    
    if case_number:
        case_data["case_number"] = case_number
    if defendant_name:
        case_data["defendant_name"] = defendant_name
    
    case_data.setdefault("defendant_name", user.user_id)
    
    defense_list = defenses.split(",") if defenses else ["improper_notice"]
    
    result = await form_generator.generate_form(
        form_type="answer_to_complaint",
        case_data=case_data,
        defenses=defense_list,
        output_format="html",
    )
    
    return HTMLResponse(result["content"])
