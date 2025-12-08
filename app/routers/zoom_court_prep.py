"""
Zoom Court Preparation Router
=============================
API endpoints for virtual court hearing preparation:
- Hearing prep checklist
- Audio/video test guidance
- Document access test
- Opening statement generator
- Evidence organization
- Question preparation
- Quick reference panel
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_user, StorageUser
from app.core.event_bus import event_bus, EventType as BusEventType

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/zoom-court", tags=["Zoom Court Prep"])


# =============================================================================
# Models
# =============================================================================

class ChecklistItem(BaseModel):
    """Single checklist item."""
    id: str
    category: str
    title: str
    description: str
    completed: bool = False
    priority: str = "medium"  # high, medium, low
    due_before: Optional[str] = None  # "1_hour", "1_day", "3_days"


class HearingPrepChecklist(BaseModel):
    """Complete hearing preparation checklist."""
    hearing_date: Optional[str]
    hearing_time: Optional[str]
    hearing_type: str
    items: List[ChecklistItem]
    completion_percent: float
    ready_status: str  # ready, almost_ready, not_ready


class OpeningStatement(BaseModel):
    """Generated opening statement."""
    full_text: str
    key_points: List[str]
    time_estimate: str
    tips: List[str]


class QuickReference(BaseModel):
    """Quick reference panel data."""
    case_number: str
    hearing_date: str
    hearing_time: str
    court_name: str
    key_dates: List[Dict[str, str]]
    violations_summary: List[str]
    legal_citations: List[Dict[str, str]]
    evidence_list: List[Dict[str, Any]]
    important_numbers: Dict[str, str]


class TechCheckResult(BaseModel):
    """Technology check results."""
    category: str
    items: List[Dict[str, Any]]
    recommendations: List[str]


# =============================================================================
# Checklist Templates
# =============================================================================

PREP_CHECKLIST = [
    # Technology - 1 day before
    {"id": "tech_zoom", "category": "technology", "title": "Install/Update Zoom", 
     "description": "Ensure Zoom is installed and updated to latest version", "priority": "high", "due_before": "1_day"},
    {"id": "tech_audio", "category": "technology", "title": "Test Audio", 
     "description": "Test microphone and speakers. Use headphones to prevent echo", "priority": "high", "due_before": "1_day"},
    {"id": "tech_video", "category": "technology", "title": "Test Video", 
     "description": "Test camera. Position with good lighting (light in front, not behind)", "priority": "high", "due_before": "1_day"},
    {"id": "tech_internet", "category": "technology", "title": "Check Internet", 
     "description": "Test internet speed. Use ethernet if possible. Have backup (phone hotspot)", "priority": "high", "due_before": "1_day"},
    {"id": "tech_power", "category": "technology", "title": "Charge Devices", 
     "description": "Charge laptop/phone. Have charger plugged in during hearing", "priority": "medium", "due_before": "1_day"},
    {"id": "tech_backup", "category": "technology", "title": "Backup Device Ready", 
     "description": "Have phone ready as backup if computer fails", "priority": "medium", "due_before": "1_day"},
    
    # Environment - 1 hour before
    {"id": "env_quiet", "category": "environment", "title": "Quiet Location", 
     "description": "Find quiet room. Tell others not to disturb. Turn off notifications", "priority": "high", "due_before": "1_hour"},
    {"id": "env_background", "category": "environment", "title": "Professional Background", 
     "description": "Plain wall or use virtual background. Remove distractions", "priority": "medium", "due_before": "1_hour"},
    {"id": "env_lighting", "category": "environment", "title": "Good Lighting", 
     "description": "Face a window or lamp. Avoid backlighting", "priority": "medium", "due_before": "1_hour"},
    
    # Documents - 3 days before
    {"id": "doc_organize", "category": "documents", "title": "Organize Evidence", 
     "description": "Have all documents labeled and in order. Know file locations", "priority": "high", "due_before": "3_days"},
    {"id": "doc_share", "category": "documents", "title": "Practice Screen Share", 
     "description": "Practice sharing documents in Zoom. Know which screen to share", "priority": "high", "due_before": "1_day"},
    {"id": "doc_print", "category": "documents", "title": "Print Key Documents", 
     "description": "Have printed copies of most important documents as backup", "priority": "medium", "due_before": "1_day"},
    {"id": "doc_quickref", "category": "documents", "title": "Quick Reference Ready", 
     "description": "Have key dates, amounts, and case number written down", "priority": "high", "due_before": "1_hour"},
    
    # Preparation - 3 days before
    {"id": "prep_opening", "category": "preparation", "title": "Prepare Opening Statement", 
     "description": "Write brief opening statement (1-2 minutes). Practice out loud", "priority": "high", "due_before": "3_days"},
    {"id": "prep_defenses", "category": "preparation", "title": "Review Defenses", 
     "description": "Know your main defenses and supporting evidence for each", "priority": "high", "due_before": "3_days"},
    {"id": "prep_questions", "category": "preparation", "title": "Prepare Questions", 
     "description": "Write questions for landlord/witnesses. Review what to expect", "priority": "medium", "due_before": "3_days"},
    {"id": "prep_practice", "category": "preparation", "title": "Practice Testimony", 
     "description": "Practice answering likely questions out loud", "priority": "medium", "due_before": "1_day"},
    
    # Day of Hearing
    {"id": "day_dress", "category": "day_of", "title": "Dress Appropriately", 
     "description": "Dress as you would for in-person court. Business casual minimum", "priority": "medium", "due_before": "1_hour"},
    {"id": "day_early", "category": "day_of", "title": "Join 15 Minutes Early", 
     "description": "Enter waiting room 15 minutes before start time", "priority": "high", "due_before": "hearing"},
    {"id": "day_name", "category": "day_of", "title": "Display Name Correct", 
     "description": "Set Zoom display name to your legal name", "priority": "high", "due_before": "1_hour"},
    {"id": "day_mute", "category": "day_of", "title": "Mute When Not Speaking", 
     "description": "Stay muted until asked to speak. Unmute before responding", "priority": "high", "due_before": "hearing"},
]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/checklist", response_model=HearingPrepChecklist)
async def get_prep_checklist(
    hearing_date: Optional[str] = None,
    hearing_type: str = "eviction",
    user: StorageUser = Depends(require_user),
):
    """
    Get hearing preparation checklist with completion status.
    
    Items are organized by priority based on time until hearing.
    """
    # Try to get hearing date from FormDataHub
    actual_hearing_date = hearing_date
    actual_hearing_time = None
    
    if not actual_hearing_date:
        try:
            from app.services.form_data import get_form_data_service
            form_service = get_form_data_service(user.user_id)
            if form_service:
                data = await form_service.get_full_data()
                actual_hearing_date = data.get("hearing_date")
                actual_hearing_time = data.get("hearing_time")
        except Exception:
            pass
    
    # Build checklist items
    items = []
    for item in PREP_CHECKLIST:
        items.append(ChecklistItem(
            id=item["id"],
            category=item["category"],
            title=item["title"],
            description=item["description"],
            completed=False,  # Would be loaded from user's saved progress
            priority=item["priority"],
            due_before=item.get("due_before"),
        ))
    
    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: priority_order.get(x.priority, 1))
    
    completion = sum(1 for i in items if i.completed) / len(items) * 100 if items else 0
    
    if completion >= 90:
        ready_status = "ready"
    elif completion >= 60:
        ready_status = "almost_ready"
    else:
        ready_status = "not_ready"
    
    return HearingPrepChecklist(
        hearing_date=actual_hearing_date,
        hearing_time=actual_hearing_time,
        hearing_type=hearing_type,
        items=items,
        completion_percent=completion,
        ready_status=ready_status,
    )

    # Publish event to brain/event bus
    await event_bus.publish(BusEventType.ZOOM_PREP_STARTED, {
        "user_id": user.user_id,
        "hearing_date": actual_hearing_date,
        "completion_percent": completion,
        "ready_status": ready_status,
    })

    return checklist


@router.post("/checklist/{item_id}/complete")
async def mark_checklist_complete(
    item_id: str,
    completed: bool = True,
    user: StorageUser = Depends(require_user),
):
    """Mark a checklist item as complete/incomplete."""
    # Would save to database in production
    return {
        "status": "success",
        "item_id": item_id,
        "completed": completed,
        "message": f"Item {'completed' if completed else 'uncompleted'}",
    }


@router.get("/tech-check", response_model=List[TechCheckResult])
async def get_tech_check_guide(
    user: StorageUser = Depends(require_user),
):
    """
    Get detailed technology check guide.
    
    Returns step-by-step instructions for each tech requirement.
    """
    return [
        TechCheckResult(
            category="Zoom Setup",
            items=[
                {"step": 1, "action": "Download Zoom", "link": "https://zoom.us/download", "done": False},
                {"step": 2, "action": "Create free account if needed", "done": False},
                {"step": 3, "action": "Update to latest version (Help > Check for Updates)", "done": False},
                {"step": 4, "action": "Test audio in Settings > Audio", "done": False},
                {"step": 5, "action": "Test video in Settings > Video", "done": False},
            ],
            recommendations=[
                "Use computer instead of phone if possible",
                "Use headphones to prevent echo",
                "Zoom link will be in court notice or email",
            ]
        ),
        TechCheckResult(
            category="Audio Setup",
            items=[
                {"step": 1, "action": "Test microphone: Settings > Audio > Test Mic", "done": False},
                {"step": 2, "action": "Test speakers: Settings > Audio > Test Speaker", "done": False},
                {"step": 3, "action": "Use headphones/earbuds to prevent echo", "done": False},
                {"step": 4, "action": "Speak at normal volume, not too close to mic", "done": False},
            ],
            recommendations=[
                "Wired headphones more reliable than Bluetooth",
                "If using phone, hold steady or use stand",
                "Mute when not speaking to avoid background noise",
            ]
        ),
        TechCheckResult(
            category="Video Setup",
            items=[
                {"step": 1, "action": "Position camera at eye level", "done": False},
                {"step": 2, "action": "Face a window or lamp (light in front of you)", "done": False},
                {"step": 3, "action": "Plain background or use virtual background", "done": False},
                {"step": 4, "action": "Frame head and shoulders in view", "done": False},
            ],
            recommendations=[
                "Look at camera, not screen, when speaking",
                "Avoid sitting in front of bright window (backlight)",
                "Remove distracting items from background",
            ]
        ),
        TechCheckResult(
            category="Internet Connection",
            items=[
                {"step": 1, "action": "Test speed at speedtest.net (need 5+ Mbps)", "done": False},
                {"step": 2, "action": "Use ethernet cable if possible", "done": False},
                {"step": 3, "action": "Sit close to WiFi router", "done": False},
                {"step": 4, "action": "Close other apps/browser tabs", "done": False},
                {"step": 5, "action": "Have phone hotspot ready as backup", "done": False},
            ],
            recommendations=[
                "Ask others not to stream video during your hearing",
                "If video freezes, turn off camera to save bandwidth",
                "Keep phone charged as backup connection",
            ]
        ),
    ]


@router.get("/opening-statement", response_model=OpeningStatement)
async def generate_opening_statement(
    user: StorageUser = Depends(require_user),
):
    """
    Generate an opening statement based on case data.
    
    Creates a brief, professional opening statement covering:
    - Who you are
    - Brief summary of dispute
    - Your main defenses
    - What you're asking for
    """
    # Get case data
    case_data = {}
    try:
        from app.services.form_data import get_form_data_service
        form_service = get_form_data_service(user.user_id)
        if form_service:
            case_data = await form_service.get_full_data()
    except Exception:
        pass
    
    # Build opening statement
    defendant_name = case_data.get("defendant_name", case_data.get("tenant_name", "[Your Name]"))
    case_number = case_data.get("case_number", "[Case Number]")
    landlord_name = case_data.get("plaintiff_name", case_data.get("landlord_name", "the landlord"))
    
    # Get defenses
    defenses = case_data.get("defenses", [])
    if isinstance(defenses, str):
        defenses = [defenses]
    
    # Build key points
    key_points = [
        f"I am {defendant_name}, the defendant in case {case_number}",
        "I am here to defend against this eviction",
    ]
    
    defense_summaries = []
    if "improper_notice" in defenses or not defenses:
        defense_summaries.append("The notice I received was defective")
        key_points.append("Notice was improper under Minnesota law")
    if "habitability" in defenses:
        defense_summaries.append("The rental unit has serious habitability issues")
        key_points.append("Landlord failed to maintain habitable conditions")
    if "retaliation" in defenses:
        defense_summaries.append("This eviction is retaliatory")
        key_points.append("Eviction filed in retaliation for complaints")
    if "rent_paid" in defenses or "rent_escrow" in defenses:
        defense_summaries.append("I have paid or properly escrowed all rent due")
        key_points.append("Rent has been paid or escrowed")
    
    key_points.append("I ask the court to dismiss this eviction")
    
    # Generate full text
    defense_text = ". ".join(defense_summaries) if defense_summaries else "I have valid defenses to this eviction"
    
    full_text = f"""Your Honor, my name is {defendant_name}, and I am the defendant in case number {case_number}.

I am here today to defend against {landlord_name}'s eviction complaint. {defense_text}.

I have documents and evidence to support my defenses, which I would like to present to the Court.

I respectfully ask the Court to deny the eviction and allow me to remain in my home. Thank you."""
    
    return OpeningStatement(
        full_text=full_text,
        key_points=key_points,
        time_estimate="1-2 minutes",
        tips=[
            "Speak clearly and at a moderate pace",
            "Address the judge as 'Your Honor'",
            "Stay calm and professional",
            "Don't interrupt - you'll have your turn",
            "It's okay to refer to notes",
            "If you don't understand, ask for clarification",
        ]
    )


@router.get("/quick-reference", response_model=QuickReference)
async def get_quick_reference(
    user: StorageUser = Depends(require_user),
):
    """
    Get quick reference panel with all key information.
    
    Everything you need at a glance during the hearing:
    - Case info
    - Key dates
    - Violation summary
    - Legal citations
    - Evidence list
    """
    # Get case data
    case_data = {}
    try:
        from app.services.form_data import get_form_data_service
        form_service = get_form_data_service(user.user_id)
        if form_service:
            case_data = await form_service.get_full_data()
    except Exception:
        pass
    
    # Build key dates
    key_dates = []
    if case_data.get("lease_start"):
        key_dates.append({"label": "Lease Start", "date": str(case_data["lease_start"])})
    if case_data.get("notice_date"):
        key_dates.append({"label": "Notice Received", "date": str(case_data["notice_date"])})
    if case_data.get("filing_date"):
        key_dates.append({"label": "Complaint Filed", "date": str(case_data["filing_date"])})
    if case_data.get("hearing_date"):
        key_dates.append({"label": "Hearing Date", "date": str(case_data["hearing_date"])})
    
    # Build violations summary
    violations = case_data.get("violations", [])
    if isinstance(violations, str):
        violations = [violations]
    
    # Legal citations for common defenses
    legal_citations = [
        {"statute": "Minn. Stat. § 504B.321", "topic": "Notice Requirements", 
         "summary": "Landlord must give proper written notice"},
        {"statute": "Minn. Stat. § 504B.161", "topic": "Habitability",
         "summary": "Landlord must maintain fit and habitable premises"},
        {"statute": "Minn. Stat. § 504B.441", "topic": "Retaliation",
         "summary": "Landlord cannot evict in retaliation for complaints"},
        {"statute": "Minn. Stat. § 504B.385", "topic": "Rent Escrow",
         "summary": "Tenant may escrow rent for habitability issues"},
    ]
    
    # Evidence list (would come from documents)
    evidence_list = [
        {"item": "Lease Agreement", "page": "1-5", "relevance": "Terms of tenancy"},
        {"item": "Notice Received", "page": "6", "relevance": "Notice defects"},
        {"item": "Rent Receipts", "page": "7-10", "relevance": "Payment history"},
        {"item": "Complaint Photos", "page": "11-15", "relevance": "Condition issues"},
        {"item": "Communication Log", "page": "16-20", "relevance": "Notice to landlord"},
    ]
    
    return QuickReference(
        case_number=case_data.get("case_number", "[CASE NUMBER]"),
        hearing_date=str(case_data.get("hearing_date", "[DATE]")),
        hearing_time=case_data.get("hearing_time", "[TIME]"),
        court_name=case_data.get("court_name", "Dakota County District Court"),
        key_dates=key_dates,
        violations_summary=violations,
        legal_citations=legal_citations,
        evidence_list=evidence_list,
        important_numbers={
            "HOME Line (Free Legal Help)": "612-728-5767",
            "Legal Aid": "612-334-5970",
            "Court Clerk": case_data.get("court_phone", "[COURT PHONE]"),
        }
    )


@router.get("/practice-questions")
async def get_practice_questions(
    user: StorageUser = Depends(require_user),
):
    """
    Get practice questions to prepare for hearing.
    
    Common questions landlord's attorney or judge may ask.
    """
    return {
        "categories": [
            {
                "name": "Basic Questions",
                "questions": [
                    {"question": "What is your name and address?", 
                     "tip": "State your full legal name clearly"},
                    {"question": "Do you currently live at the property?",
                     "tip": "Answer yes or no, then briefly explain if needed"},
                    {"question": "When did you move in?",
                     "tip": "Give the month and year"},
                    {"question": "Did you sign a lease?",
                     "tip": "If yes, mention you have a copy"},
                ]
            },
            {
                "name": "Rent Questions",
                "questions": [
                    {"question": "What is your monthly rent?",
                     "tip": "State the exact amount"},
                    {"question": "Are you current on rent?",
                     "tip": "Be honest. If behind, explain circumstances"},
                    {"question": "When did you last pay rent?",
                     "tip": "Have payment records ready to show"},
                    {"question": "How do you usually pay rent?",
                     "tip": "Check, money order, cash, etc."},
                ]
            },
            {
                "name": "Notice Questions",
                "questions": [
                    {"question": "Did you receive a notice to vacate?",
                     "tip": "Describe how and when you received it"},
                    {"question": "When did you receive the notice?",
                     "tip": "Be specific about the date"},
                    {"question": "How was the notice delivered?",
                     "tip": "Posted on door, mailed, handed to you, etc."},
                ]
            },
            {
                "name": "Defense Questions",
                "questions": [
                    {"question": "Why do you believe you should not be evicted?",
                     "tip": "State your main defense clearly"},
                    {"question": "Do you have evidence to support your defense?",
                     "tip": "Be ready to show documents"},
                    {"question": "Have you reported any problems with the unit?",
                     "tip": "If yes, explain when and how"},
                ]
            },
        ],
        "tips": [
            "Listen to the entire question before answering",
            "Answer only what is asked - don't volunteer extra information",
            "If you don't understand, ask for the question to be repeated",
            "It's okay to say 'I don't know' or 'I don't remember'",
            "Stay calm even if questions seem unfair",
            "Don't argue with the landlord's attorney",
        ]
    }


@router.get("/courtroom-etiquette")
async def get_courtroom_etiquette(
    user: StorageUser = Depends(require_user),
):
    """
    Get courtroom etiquette guide for Zoom hearings.
    """
    return {
        "before_hearing": [
            "Join the Zoom meeting 15 minutes early",
            "Test your audio and video one more time",
            "Have all documents open and ready to share",
            "Close unnecessary programs and browser tabs",
            "Put phone on silent (unless using as backup)",
            "Let others in your home know not to disturb you",
        ],
        "during_hearing": [
            "Address the judge as 'Your Honor'",
            "Stay muted when not speaking",
            "Wait to be recognized before speaking",
            "Speak clearly and at a moderate pace",
            "Look at the camera when speaking",
            "Don't interrupt anyone, especially the judge",
            "Stand when the judge enters (even on Zoom)",
        ],
        "what_not_to_do": [
            "Don't eat, drink, or chew gum on camera",
            "Don't have side conversations",
            "Don't make faces or react visibly",
            "Don't use your phone during the hearing",
            "Don't argue with the other party directly",
            "Don't speak over others",
        ],
        "if_technical_issues": [
            "Stay calm - technical issues happen",
            "If you lose connection, rejoin immediately",
            "If you can't rejoin, call the court clerk",
            "Have the court's phone number ready",
            "The judge will usually wait briefly for reconnection",
        ],
    }
