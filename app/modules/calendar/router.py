"""
Calendar Router (vault-backed)
Scheduling, deadlines, and reminders.

Events persist as CALENDAR_EVENT overlays in the tenant's own cloud vault
(vault-persistence-migration, Phase 1) — no server DB rows. Still integrated
with DocumentHub for auto-syncing dates from uploaded documents.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.document_hub import get_document_hub
from app.core.event_bus import EventType, event_bus
from app.core.security import StorageUser, yellow_access
from app.core.utc import utc_now
from app.models.unified_overlay_models import UnifiedOverlay
from app.modules.calendar import service
from app.services.calendar_sync import _parse_datetime as _parse_dt
from app.services.calendar_sync import sync_calendar_for_user

logger = logging.getLogger(__name__)


router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

VALID_EVENT_TYPES = [
    "deadline",
    "hearing",
    "reminder",
    "appointment",
    "rent_due",
    "late_fee",
    "action_item",
    "timeline",
]


class CalendarEventCreate(BaseModel):
    """Create a calendar event or deadline."""

    title: str = Field(..., max_length=255)
    description: str | None = None
    start_datetime: str = Field(..., description="ISO format datetime")
    end_datetime: str | None = Field(None, description="ISO format datetime (optional)")
    all_day: bool = False
    event_type: str = Field(..., description="Type: deadline, hearing, reminder, appointment, rent_due")
    is_critical: bool = Field(False, description="Critical events affect intensity engine")
    reminder_days: int | None = Field(None, ge=0, le=30, description="Days before to remind")


class CalendarEventUpdate(BaseModel):
    """Update a calendar event."""

    title: str | None = Field(None, max_length=255)
    description: str | None = None
    start_datetime: str | None = None
    end_datetime: str | None = None
    all_day: bool | None = None
    event_type: str | None = None
    is_critical: bool | None = None
    reminder_days: int | None = Field(None, ge=0, le=30)


class CalendarEventResponse(BaseModel):
    """Calendar event response."""

    id: str
    title: str
    description: str | None = None
    start_datetime: str
    end_datetime: str | None = None
    all_day: bool
    event_type: str
    is_critical: bool
    reminder_days: int | None = None
    source: str | None = None
    linked_record_id: str | None = None
    created_at: str
    updated_at: str | None = None


class CalendarListResponse(BaseModel):
    """List of calendar events."""

    events: list[CalendarEventResponse]
    total: int


class UpcomingDeadlinesResponse(BaseModel):
    """Upcoming deadlines summary."""

    critical: list[CalendarEventResponse]
    upcoming: list[CalendarEventResponse]
    days_to_next_critical: int | None = None


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string to datetime."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid datetime format: {dt_str}")


def _model_to_response(event: UnifiedOverlay) -> CalendarEventResponse:
    """Convert a CALENDAR_EVENT overlay to the response schema."""
    p = event.payload
    return CalendarEventResponse(
        id=event.overlay_id,
        title=p.get("title") or "",
        description=p.get("description"),
        start_datetime=p.get("start_datetime") or "",
        end_datetime=p.get("end_datetime"),
        all_day=bool(p.get("all_day")),
        event_type=p.get("event_type") or "reminder",
        is_critical=bool(p.get("is_critical")),
        reminder_days=p.get("reminder_days"),
        source=p.get("source"),
        linked_record_id=p.get("linked_record_id"),
        created_at=p.get("created_at") or (event.created_at.isoformat() if event.created_at else ""),
        updated_at=p.get("updated_at") or (event.updated_at.isoformat() if event.updated_at else None),
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=CalendarEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    event: CalendarEventCreate,
    user: StorageUser = Depends(yellow_access),
):
    """
    Create a calendar event or deadline.

    Event types:
    - **deadline**: Legal deadline (response due, filing deadline)
    - **hearing**: Court hearing or mediation
    - **reminder**: General reminder
    - **appointment**: Meeting with attorney, inspector, etc.
    - **rent_due**: Rent payment due date
    """
    if event.event_type not in VALID_EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid event_type. Must be one of: {VALID_EVENT_TYPES}")

    start_dt = _parse_datetime(event.start_datetime)
    end_dt = _parse_datetime(event.end_datetime) if event.end_datetime else None

    overlay = await service.create_event(
        user,
        title=event.title,
        description=event.description,
        start_datetime=start_dt,
        end_datetime=end_dt,
        all_day=event.all_day,
        event_type=event.event_type,
        is_critical=event.is_critical,
        reminder_days=event.reminder_days,
        source="manual",
    )

    # Emit brain event for calendar update
    try:
        from app.services.positronic_brain import BrainEvent, EventType as BrainEventType, ModuleType, get_brain

        brain = get_brain()
        event_type_brain = (
            BrainEventType.CALENDAR_HEARING_SCHEDULED
            if event.event_type == "hearing"
            else BrainEventType.CALENDAR_DEADLINE_APPROACHING
        )
        await brain.emit(
            BrainEvent(
                event_type=event_type_brain,
                source_module=ModuleType.CALENDAR,
                data={
                    "event_id": overlay.overlay_id,
                    "title": event.title,
                    "event_type": event.event_type,
                    "start_datetime": start_dt.isoformat() if start_dt else None,
                    "is_critical": event.is_critical,
                },
                user_id=user.user_id,
            )
        )
    except Exception:
        logger.debug("Brain emit failed (optional)", exc_info=True)

    event_bus.publish_sync(
        EventType.HEARING_SCHEDULED if event.event_type == "hearing" else EventType.DEADLINE_ADDED,
        {
            "user_id": user.user_id,
            "event_id": overlay.overlay_id,
            "event_type": event.event_type,
            "is_critical": event.is_critical,
            "narrator": {
                "module": "app.modules.calendar",
                "slot": 1 if event.event_type == "hearing" else (2 if event.event_type == "deadline" else 0),
            },
        },
    )

    return _model_to_response(overlay)


@router.get("/", response_model=CalendarListResponse)
async def list_events(
    start: str | None = Query(None, description="Start of date range (ISO)"),
    end: str | None = Query(None, description="End of date range (ISO)"),
    event_type: str | None = Query(None, description="Filter by event type"),
    critical_only: bool = Query(False, description="Only show critical events"),
    user: StorageUser = Depends(yellow_access),
):
    """
    List calendar events, optionally filtered by date range and type.
    """
    events, total = await service.list_events(
        user,
        start=_parse_datetime(start) if start else None,
        end=_parse_datetime(end) if end else None,
        event_type=event_type,
        critical_only=critical_only,
    )
    return CalendarListResponse(
        events=[_model_to_response(e) for e in events],
        total=total,
    )


@router.get("/upcoming", response_model=UpcomingDeadlinesResponse)
async def upcoming_deadlines(
    days: int = Query(30, ge=1, le=90, description="Look ahead days"),
    user: StorageUser = Depends(yellow_access),
):
    """
    Get upcoming deadlines and critical events.

    This endpoint is designed for dashboard widgets and the intensity engine.
    """
    now = utc_now()
    cutoff = now + timedelta(days=days)

    upcoming, _total = await service.list_events(user, start=now, end=cutoff)

    # Separate critical events
    critical = [e for e in upcoming if e.payload.get("is_critical")]

    # Calculate days to next critical
    days_to_next = None
    if critical:
        next_critical_date = _parse_dt(critical[0].payload.get("start_datetime"))
        if next_critical_date:
            days_to_next = (next_critical_date.replace(tzinfo=None) - now.replace(tzinfo=None)).days

    return UpcomingDeadlinesResponse(
        critical=[_model_to_response(e) for e in critical],
        upcoming=[_model_to_response(e) for e in upcoming[:10]],
        days_to_next_critical=days_to_next,
    )


@router.get("/{event_id}", response_model=CalendarEventResponse)
async def get_event(
    event_id: str,
    user: StorageUser = Depends(yellow_access),
):
    """Get a specific calendar event."""
    overlay = await service.get_event(user, event_id)
    if overlay is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return _model_to_response(overlay)


@router.patch("/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: str,
    updates: CalendarEventUpdate,
    user: StorageUser = Depends(yellow_access),
):
    """Update a calendar event."""
    update_data = updates.model_dump(exclude_unset=True)

    # Parse datetime fields if provided
    if "start_datetime" in update_data and update_data["start_datetime"]:
        update_data["start_datetime"] = _parse_datetime(update_data["start_datetime"])
    if "end_datetime" in update_data and update_data["end_datetime"]:
        update_data["end_datetime"] = _parse_datetime(update_data["end_datetime"])

    overlay = await service.update_event(user, event_id, update_data)
    if overlay is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return _model_to_response(overlay)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    user: StorageUser = Depends(yellow_access),
):
    """Delete a calendar event."""
    if not await service.delete_event(user, event_id):
        raise HTTPException(status_code=404, detail="Event not found")


# =============================================================================
# Document Hub Integration - Auto-sync dates from uploaded documents
# =============================================================================


class DocumentEventsResponse(BaseModel):
    """Events extracted from documents."""

    events: list[CalendarEventResponse]
    source: str = "document_extraction"
    sync_available: bool
    documents_analyzed: int


@router.get("/from-documents", response_model=DocumentEventsResponse)
async def get_events_from_documents(
    user: StorageUser = Depends(yellow_access),
):
    """
    Get calendar events derived from uploaded documents.

    Returns events like:
    - Hearing dates
    - Answer deadlines
    - Action items with deadlines
    - Timeline events with future dates

    These events are NOT yet synced to your calendar.
    Use POST /sync-documents to add them.
    """
    hub = get_document_hub()
    doc_events = hub.get_calendar_events(user.user_id)
    case_data = hub.get_case_data(user.user_id)

    # Convert to CalendarEventResponse format
    events = []
    for event in doc_events:
        events.append(
            CalendarEventResponse(
                id=event.get("id", ""),
                title=event.get("title", ""),
                description=event.get("description"),
                start_datetime=event.get("date", ""),
                end_datetime=None,
                all_day=True,
                event_type=event.get("type", "reminder"),
                is_critical=event.get("critical", False),
                reminder_days=7 if event.get("critical") else 3,
                created_at=utc_now().isoformat(),
            )
        )

    return DocumentEventsResponse(
        events=events,
        source="document_extraction",
        sync_available=len(events) > 0,
        documents_analyzed=case_data.document_count,
    )


class SyncResult(BaseModel):
    """Result of syncing document events to calendar."""

    synced: int
    skipped: int
    total_calendar_events: int
    synced_event_ids: list[str]


@router.post("/sync-documents", response_model=SyncResult)
async def sync_document_events(
    overwrite: bool = Query(False, description="Overwrite existing events with same title"),
    user: StorageUser = Depends(yellow_access),
):
    """
    Sync calendar events derived from documents and the rent ledger.

    This creates calendar events for:
    - Court hearings, answer deadlines, and action items extracted from documents
    - Future timeline events from documents
    - Rent due dates and late-fee / charge trigger dates from the ledger

    Existing auto-synced events are refreshed by default; pass overwrite=false
    to skip events that have already been synced.
    """
    result = await sync_calendar_for_user(user.get_effective_user_id(), overwrite=overwrite)
    _events, total = await service.list_events(user)

    return SyncResult(
        synced=result["total"],
        skipped=result["skipped"],
        total_calendar_events=total,
        synced_event_ids=result["synced_event_ids"],
    )


@router.get("/deadline-summary")
async def get_deadline_summary(
    user: StorageUser = Depends(yellow_access),
):
    """
    Get a summary of deadlines from both calendar and documents.

    Shows combined view of:
    - Deadlines in your calendar
    - Deadlines extracted from documents
    - Days until each deadline
    - Urgency classification
    """
    hub = get_document_hub()
    deadline_info = hub.get_deadline_info(user.user_id)
    hearing_info = hub.get_hearing_info(user.user_id)
    action_items = hub.get_action_items(user.user_id, urgent_only=True)

    # Get calendar deadlines
    now = utc_now()
    cutoff = now + timedelta(days=30)

    calendar_deadlines = []
    range_events, _total = await service.list_events(user, start=now, end=cutoff)
    for e in range_events:
        p = e.payload
        if p.get("event_type") not in ("deadline", "hearing"):
            continue
        start_dt = _parse_dt(p.get("start_datetime"))
        if not start_dt:
            continue
        days_until = (start_dt.replace(tzinfo=None) - now.replace(tzinfo=None)).days
        calendar_deadlines.append(
            {
                "id": e.overlay_id,
                "title": p.get("title") or "",
                "date": p.get("start_datetime"),
                "days_until": days_until,
                "is_critical": bool(p.get("is_critical")),
                "type": p.get("event_type"),
                "urgency": "critical" if days_until <= 3 else "high" if days_until <= 7 else "medium",
                "source": "calendar",
            }
        )

    return {
        "answer_deadline": {
            "date": deadline_info.get("answer_deadline"),
            "days_until": deadline_info.get("days_until"),
            "is_past": deadline_info.get("is_past"),
            "is_urgent": deadline_info.get("is_urgent"),
            "source": "document_extraction",
        },
        "hearing": {
            "date": hearing_info.get("date"),
            "time": hearing_info.get("time"),
            "has_hearing": hearing_info.get("has_hearing"),
            "source": "document_extraction",
        },
        "calendar_deadlines": calendar_deadlines,
        "urgent_actions": action_items,
        "total_upcoming": len(calendar_deadlines),
    }


@router.post("/notify-deadlines")
async def send_deadline_notifications(
    days_ahead: int = Query(7, description="Send notifications for deadlines within this many days"),
    user: StorageUser = Depends(yellow_access),
):
    """
    Send email notifications for upcoming deadlines.

    Checks for critical deadlines within the specified days and sends notifications.
    In a production system, this would send actual emails.
    For now, it creates in-app notifications.
    """
    from app.core.event_bus import send_notification

    # Get upcoming critical events
    cutoff_date = utc_now() + timedelta(days=days_ahead)
    upcoming_events, _total = await service.list_events(
        user, start=utc_now(), end=cutoff_date, critical_only=True
    )

    notifications_sent = 0

    for event in upcoming_events:
        p = event.payload
        start_dt = _parse_dt(p.get("start_datetime"))
        if not start_dt:
            continue
        days_until = (start_dt - utc_now()).days

        # Send in-app notification
        await send_notification(
            title=f"Upcoming Deadline: {p.get('title')}",
            message=f"You have a critical deadline in {days_until} days: {p.get('description') or p.get('title')}",
            level="warning",
            user_id=user.user_id,
        )

        # Email notification: Semptify does NOT store user emails in its database.
        # Users may configure a notification email in their cloud vault settings.
        # For now, skip email — in-app notification is the primary channel.
        # Future: fetch notification_email from user's vault metadata if configured.

        notifications_sent += 1

    from app.services.email_service import _RESEND_API_KEY

    email_status = "configured" if _RESEND_API_KEY else "not_configured"

    return {
        "notifications_sent": notifications_sent,
        "upcoming_deadlines": len(upcoming_events),
        "email_service_status": email_status,
        "message": f"Sent {notifications_sent} deadline notifications.",
    }
