"""
Guided Intake Router - Conversational intake process for gathering user situation
Asks questions like an attorney/advocate would to understand the tenant's needs
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.request_utils import get_request_user_id
from app.core.security import get_current_user
from app.core.user_context import UserContext
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/guided-intake", tags=["Guided Intake"])


class IntakeData(BaseModel):
    """User's intake information gathered through guided conversation"""
    intake_data: dict[str, Any]
    completed_at: str | None = None


class IntakeSummary(BaseModel):
    """Summary of user's situation for case building"""
    primary_concern: str | None = None
    situation_description: str | None = None
    timeline_start: str | None = None
    urgency_level: str | None = None
    urgent_date: str | None = None
    housing_type: str | None = None
    lease_status: str | None = None
    available_documents: list[str] = []
    desired_outcome: str | None = None
    additional_info: str | None = None
    completed_at: str | None = None


# In-memory storage (will be replaced with cloud storage)
_intake_storage: dict[str, IntakeSummary] = {}


@router.post("/save")
async def save_intake(
    data: IntakeData,
    request: Request,
    user: UserContext | None = Depends(get_current_user)
):
    """
    Save user's intake information from the guided conversation.
    This data helps build their case and identify relevant resources.
    """
    try:
        intake = data.intake_data

        # Transform intake data into structured summary
        summary = IntakeSummary(
            primary_concern=intake.get('primaryConcern'),
            situation_description=intake.get('situation'),
            timeline_start=intake.get('timelineStart'),
            urgency_level=intake.get('urgency'),
            urgent_date=intake.get('urgentDate'),
            housing_type=intake.get('housingType'),
            lease_status=intake.get('leaseStatus'),
            available_documents=intake.get('documents', []),
            desired_outcome=intake.get('goals'),
            additional_info=intake.get('additionalInfo'),
            completed_at=data.completed_at or utc_now().isoformat()
        )

        # Get user ID (from cookie if not authenticated)
        user_id = user.user_id if user else get_request_user_id(request)

        # Store for user
        _intake_storage[user_id] = summary

        logger.info(f"Intake saved for user {user_id[:4]}*** - concern: {summary.primary_concern}")

        # Determine urgency flags
        is_urgent = summary.urgency_level in ['court_soon', 'deadline', 'move_out']

        return {
            "success": True,
            "message": "Your information has been saved securely",
            "summary": {
                "primary_concern": get_concern_display(summary.primary_concern),
                "is_urgent": is_urgent,
                "next_steps": get_next_steps(summary)
            }
        }

    except Exception as e:
        logger.error(f"Error saving intake: {e}")
        raise HTTPException(status_code=500, detail="Failed to save intake information")


@router.get("/summary")
async def get_intake_summary(
    request: Request,
    user: UserContext | None = Depends(get_current_user)
):
    """Get the user's intake summary if they've completed the guided intake."""
    user_id = user.user_id if user else get_request_user_id(request)
    summary = _intake_storage.get(user_id)

    if not summary:
        return {
            "completed": False,
            "message": "No intake information found. Complete the guided intake to get started."
        }

    return {
        "completed": True,
        "summary": summary.model_dump(),
        "recommended_modules": get_recommended_modules(summary)
    }


@router.get("/status")
async def get_intake_status(
    request: Request,
    user: UserContext | None = Depends(get_current_user)
):
    """Check if user has completed intake."""
    user_id = user.user_id if user else get_request_user_id(request)
    has_intake = user_id in _intake_storage

    return {
        "completed": has_intake,
        "redirect_to": "/dashboard" if has_intake else "/static/intake/guide.html"
    }


def get_concern_display(concern: str | None) -> str:
    """Convert concern ID to display text."""
    concern_map = {
        'eviction': 'Eviction Defense',
        'repairs': 'Repairs & Living Conditions',
        'rent': 'Rent Issues',
        'harassment': 'Landlord Behavior',
        'lease': 'Lease Questions',
        'other': 'General Housing Help'
    }
    return concern_map.get(concern, 'Housing Assistance')


def get_next_steps(summary: IntakeSummary) -> list[str]:
    """Generate personalized next steps based on intake."""
    steps = []

    # Urgent matters first
    if summary.urgency_level in ['court_soon', 'deadline', 'move_out']:
        steps.append("◆ Review your urgent deadline and available legal resources")

    # Based on primary concern
    if summary.primary_concern == 'eviction':
        steps.append("● Review the eviction process timeline for Minnesota")
        steps.append("● Gather any notices you've received from your landlord")
        steps.append("▸ Explore your legal defenses")

    elif summary.primary_concern == 'repairs':
        steps.append("● Document current conditions with photos")
        steps.append("● Draft a repair request letter to your landlord")
        steps.append("▸ Learn about rent escrow options")

    elif summary.primary_concern == 'rent':
        steps.append("◆ Review your rent payment history")
        steps.append("● Check if rent increases follow MN law")
        steps.append("● Explore rental assistance programs")

    elif summary.primary_concern == 'harassment':
        steps.append("● Start a log of incidents")
        steps.append("● Review your lease for landlord entry rules")
        steps.append("▸ Learn about tenant protection laws")

    elif summary.primary_concern == 'lease':
        steps.append("● Upload your lease for analysis")
        steps.append("● Review common lease issues in MN")
        steps.append("▸ Get help understanding lease terms")

    # Document gathering
    if 'none' in summary.available_documents or not summary.available_documents:
        steps.append("● Start building your evidence file")

    return steps[:5]  # Return top 5 most relevant


def get_recommended_modules(summary: IntakeSummary) -> list[dict[str, str]]:
    """Recommend Semptify modules based on intake."""
    modules = []

    if summary.primary_concern == 'eviction':
        modules.extend([
            {"id": "eviction_defense", "name": "Eviction Defense", "icon": "◆"},
            {"id": "timeline", "name": "Timeline Builder", "icon": "◆"},
            {"id": "law_library", "name": "MN Eviction Law", "icon": "○"}
        ])

    elif summary.primary_concern == 'repairs':
        modules.extend([
            {"id": "evidence", "name": "Evidence Collection", "icon": "●"},
            {"id": "complaint_wizard", "name": "File a Complaint", "icon": "●"},
            {"id": "law_library", "name": "Habitability Rights", "icon": "○"}
        ])

    elif summary.primary_concern == 'harassment':
        modules.extend([
            {"id": "incident_log", "name": "Incident Logger", "icon": "●"},
            {"id": "complaint_wizard", "name": "File a Complaint", "icon": "●"},
            {"id": "law_library", "name": "Tenant Protections", "icon": "○"}
        ])

    # Always recommend these
    modules.extend([
        {"id": "documents", "name": "Document Vault", "icon": "●"},
        {"id": "calendar", "name": "Deadlines & Dates", "icon": "◆"}
    ])

    # Deduplicate by id
    seen = set()
    unique_modules = []
    for m in modules:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique_modules.append(m)

    return unique_modules[:6]
