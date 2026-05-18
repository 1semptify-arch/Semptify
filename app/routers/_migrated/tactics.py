"""
Proactive Tactics Router
AI-powered defense strategy recommendations.

Implements automation from proactive_tactics.md:
- Auto-flag rent escrow when 3+ habitability tags within 30 days
- Suggest retaliation counterclaim if eviction filed <30 days after complaint
- Provide expungement prompt when case dismissed
- Decision tree recommendations
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import require_user
from app.services.proactive_tactics import get_tactics_engine, TacticType, UrgencyLevel


router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class TacticResponse(BaseModel):
    """A recommended tactic."""
    tactic_type: str
    title: str
    urgency: str
    reason: str
    action_items: List[str]
    deadline: Optional[str] = None
    evidence_needed: List[str] = []
    motion_template: Optional[str] = None


class DecisionTreeRequest(BaseModel):
    """Request for decision tree analysis."""
    service_date: Optional[str] = Field(None, description="Date tenant was served (ISO format)")
    hearing_date: Optional[str] = Field(None, description="Scheduled hearing date (ISO format)")
    eviction_filed_date: Optional[str] = Field(None, description="Date eviction was filed")
    case_dismissed: bool = Field(False, description="Was case dismissed?")
    case_settled: bool = Field(False, description="Was case settled favorably?")
    pending_inspection_date: Optional[str] = Field(None, description="Scheduled inspection date")
    rental_assistance_pending: bool = Field(False, description="Is rental assistance pending?")


class DecisionTreeResponse(BaseModel):
    """Response with all applicable tactics."""
    recommendations: List[TacticResponse]
    total: int
    critical_count: int
    high_count: int


class EvidenceChecklistResponse(BaseModel):
    """Evidence preparation checklist."""
    items: List[dict]
    stored_count: int
    total_count: int
    completion_percentage: float


class PreHearingTimelineResponse(BaseModel):
    """Pre-hearing action timeline."""
    hearing_date: str
    days_until_hearing: int
    actions: List[dict]
    overdue_count: int


class HabitabilityAnalysisRequest(BaseModel):
    """Request to analyze habitability issues."""
    # Events will be pulled from user's timeline


class RetaliationAnalysisRequest(BaseModel):
    """Request to analyze potential retaliation."""
    eviction_filed_date: str = Field(..., description="Date eviction was filed (ISO format)")
    protected_activities: List[dict] = Field(
        default_factory=list,
        description="List of protected activities with 'type' and 'date' fields"
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/recommendations", response_model=DecisionTreeResponse)
async def get_recommendations(
    user: dict = Depends(require_user),
):
    """
    Get AI-powered defense recommendations based on case data.
    
    Analyzes:
    - Service timeline for dismissal opportunities
    - Habitability issues for rent escrow
    - Protected activities for retaliation claims
    - Pending evidence for continuance
    - Case outcome for expungement
    """
    from app.services.form_data import get_form_data_service
    
    user_id = getattr(user, 'user_id', 'open-mode-user')
    form_data_svc = get_form_data_service(user_id)
    case_summary = form_data_svc.get_case_summary()
    
    engine = get_tactics_engine()
    
    # Parse dates from case data
    hearing_date = None
    service_date = None
    eviction_filed_date = None
    
    if case_summary.get("hearing_date"):
        try:
            hearing_date = datetime.fromisoformat(case_summary["hearing_date"])
        except ValueError:
            pass
    
    # Get timeline events
    timeline_events = []
    if form_data_svc.form_data and form_data_svc.form_data.timeline_events:
        timeline_events = form_data_svc.form_data.timeline_events
    
    # Run decision tree
    recommendations = engine.run_decision_tree(
        service_date=service_date,
        hearing_date=hearing_date,
        timeline_events=timeline_events,
        eviction_filed_date=eviction_filed_date,
    )
    
    # Count by urgency
    critical = sum(1 for r in recommendations if r.urgency == UrgencyLevel.CRITICAL)
    high = sum(1 for r in recommendations if r.urgency == UrgencyLevel.HIGH)
    
    return DecisionTreeResponse(
        recommendations=[TacticResponse(**r.to_dict()) for r in recommendations],
        total=len(recommendations),
        critical_count=critical,
        high_count=high,
    )


@router.post("/analyze", response_model=DecisionTreeResponse)
async def analyze_case(
    request: DecisionTreeRequest,
    user: dict = Depends(require_user),
):
    """
    Analyze case data and return tactical recommendations.
    
    Decision Tree:
    1. Was service <7 days? → Motion to Dismiss
    2. ≥3 serious habitability issues? → Rent Escrow Motion
    3. Recent protected complaint (<30 days)? → Retaliation Counterclaim
    4. Pending objective evidence? → Continuance Motion
    5. Case dismissed or settled? → Expungement Motion
    """
    from app.services.form_data import get_form_data_service
    
    user_id = getattr(user, 'user_id', 'open-mode-user')
    form_data_svc = get_form_data_service(user_id)
    
    engine = get_tactics_engine()
    
    # Parse dates
    service_date = None
    hearing_date = None
    eviction_filed_date = None
    pending_inspection = None
    
    if request.service_date:
        try:
            service_date = datetime.fromisoformat(request.service_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid service_date format")
    
    if request.hearing_date:
        try:
            hearing_date = datetime.fromisoformat(request.hearing_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hearing_date format")
    
    if request.eviction_filed_date:
        try:
            eviction_filed_date = datetime.fromisoformat(request.eviction_filed_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid eviction_filed_date format")
    
    if request.pending_inspection_date:
        try:
            pending_inspection = datetime.fromisoformat(request.pending_inspection_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid pending_inspection_date format")
    
    # Get timeline events from user data
    timeline_events = []
    if form_data_svc.form_data and form_data_svc.form_data.timeline_events:
        timeline_events = form_data_svc.form_data.timeline_events
    
    # Run full decision tree
    recommendations = engine.run_decision_tree(
        service_date=service_date,
        hearing_date=hearing_date,
        timeline_events=timeline_events,
        eviction_filed_date=eviction_filed_date,
        case_dismissed=request.case_dismissed,
        case_settled=request.case_settled,
        pending_inspection=pending_inspection,
        rental_assistance_pending=request.rental_assistance_pending,
    )
    
    critical = sum(1 for r in recommendations if r.urgency == UrgencyLevel.CRITICAL)
    high = sum(1 for r in recommendations if r.urgency == UrgencyLevel.HIGH)
    
    return DecisionTreeResponse(
        recommendations=[TacticResponse(**r.to_dict()) for r in recommendations],
        total=len(recommendations),
        critical_count=critical,
        high_count=high,
    )


@router.get("/evidence-checklist", response_model=EvidenceChecklistResponse)
async def get_evidence_checklist(
    user: dict = Depends(require_user),
):
    """
    Get the evidence preparation checklist with storage status.
    
    Checks which items have been uploaded to Semptify vault.
    """
    from app.services.document_pipeline import get_document_pipeline
    
    user_id = getattr(user, 'user_id', 'open-mode-user')
    engine = get_tactics_engine()
    pipeline = get_document_pipeline()
    
    # Get user's documents
    documents = pipeline.get_user_documents(user_id)
    doc_list = [{"doc_type": doc.doc_type.value if doc.doc_type else ""} for doc in documents]
    
    # Get checklist with status
    checklist = engine.get_evidence_checklist(doc_list)
    
    stored = sum(1 for item in checklist if item["stored"])
    total = len(checklist)
    
    return EvidenceChecklistResponse(
        items=checklist,
        stored_count=stored,
        total_count=total,
        completion_percentage=round((stored / total) * 100, 1) if total > 0 else 0,
    )


@router.get("/pre-hearing-timeline", response_model=PreHearingTimelineResponse)
async def get_pre_hearing_timeline(
    hearing_date: str,
    user: dict = Depends(require_user),
):
    """
    Get the pre-hearing tactical action timeline.
    
    Shows what to do at each stage leading up to the hearing.
    """
    engine = get_tactics_engine()
    
    try:
        hearing_dt = datetime.fromisoformat(hearing_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hearing_date format. Use ISO format (YYYY-MM-DD)")
    
    actions = engine.get_pre_hearing_timeline(hearing_dt)
    days_until = (hearing_dt - datetime.now()).days
    overdue = sum(1 for a in actions if a.get("overdue", False))
    
    return PreHearingTimelineResponse(
        hearing_date=hearing_date,
        days_until_hearing=days_until,
        actions=actions,
        overdue_count=overdue,
    )


@router.post("/check-retaliation")
async def check_retaliation(
    request: RetaliationAnalysisRequest,
    user: dict = Depends(require_user),
):
    """
    Check for potential retaliation based on protected activities.
    
    Analyzes proximity between protected activities and eviction filing.
    Flags if filing occurred within 30 days of protected activity.
    """
    engine = get_tactics_engine()
    
    try:
        eviction_date = datetime.fromisoformat(request.eviction_filed_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid eviction_filed_date format")
    
    recommendation = engine.analyze_retaliation(
        request.protected_activities,
        eviction_date,
    )
    
    if recommendation:
        return {
            "retaliation_detected": True,
            "recommendation": recommendation.to_dict(),
        }
    
    return {
        "retaliation_detected": False,
        "message": "No retaliation pattern detected based on provided activities.",
    }


@router.post("/check-habitability")
async def check_habitability(
    user: dict = Depends(require_user),
):
    """
    Check habitability issues from timeline for rent escrow eligibility.
    
    Auto-flags rent escrow when 3+ habitability tags within 30 days.
    """
    from app.services.form_data import get_form_data_service
    
    user_id = getattr(user, 'user_id', 'open-mode-user')
    form_data_svc = get_form_data_service(user_id)
    engine = get_tactics_engine()
    
    # Get timeline events
    timeline_events = []
    if form_data_svc.form_data and form_data_svc.form_data.timeline_events:
        timeline_events = form_data_svc.form_data.timeline_events
    
    recommendation = engine.analyze_habitability_issues(timeline_events)
    
    if recommendation:
        return {
            "rent_escrow_recommended": True,
            "recommendation": recommendation.to_dict(),
        }
    
    return {
        "rent_escrow_recommended": False,
        "message": "Less than 3 habitability issues found in past 30 days. Continue documenting any issues.",
        "tip": "Tag repair requests and condition reports as 'habitability' in your timeline.",
    }


@router.get("/service-check")
async def check_service_timeline(
    service_date: str,
    hearing_date: str,
    user: dict = Depends(require_user),
):
    """
    Check if service timeline supports a Motion to Dismiss.
    
    Minnesota requires at least 7 days between service and hearing.
    """
    engine = get_tactics_engine()
    
    try:
        service_dt = datetime.fromisoformat(service_date)
        hearing_dt = datetime.fromisoformat(hearing_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")
    
    recommendation = engine.analyze_service_timeline(service_dt, hearing_dt)
    days_between = (hearing_dt - service_dt).days
    
    if recommendation:
        return {
            "dismissal_opportunity": True,
            "days_between": days_between,
            "required_days": 7,
            "recommendation": recommendation.to_dict(),
        }
    
    return {
        "dismissal_opportunity": False,
        "days_between": days_between,
        "required_days": 7,
        "message": f"Service was {days_between} days before hearing, which meets the 7-day requirement.",
    }
