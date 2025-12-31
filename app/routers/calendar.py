"""
Calendar Router (Database-backed)
Scheduling, deadlines, and reminders.

Now integrated with DocumentHub for auto-syncing dates from uploaded documents.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_user, StorageUser
from app.core.utc import utc_now
from app.core.document_hub import get_document_hub
from app.models.models import CalendarEvent as CalendarEventModel


router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

VALID_EVENT_TYPES = ["deadline", "hearing", "reminder", "appointment", "rent_due"]

class CalendarEventCreate(BaseModel):
    """Create a calendar event or deadline."""
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    start_datetime: str = Field(..., description="ISO format datetime")
    end_datetime: Optional[str] = Field(None, description="ISO format datetime (optional)")
    all_day: bool = False
    event_type: str = Field(..., description="Type: deadline, hearing, reminder, appointment, rent_due")
    is_critical: bool = Field(False, description="Critical events affect intensity engine")
    reminder_days: Optional[int] = Field(None, ge=0, le=30, description="Days before to remind")


class CalendarEventUpdate(BaseModel):
    """Update a calendar event."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    all_day: Optional[bool] = None
    event_type: Optional[str] = None
    is_critical: Optional[bool] = None
    reminder_days: Optional[int] = Field(None, ge=0, le=30)


class CalendarEventResponse(BaseModel):
    """Calendar event response."""
    id: str
    title: str
    description: Optional[str] = None
    start_datetime: str
    end_datetime: Optional[str] = None
    all_day: bool
    event_type: str
    is_critical: bool
    reminder_days: Optional[int] = None
    created_at: str


class CalendarListResponse(BaseModel):
    """List of calendar events."""
    events: list[CalendarEventResponse]
    total: int


class UpcomingDeadlinesResponse(BaseModel):
    """Upcoming deadlines summary."""
    critical: list[CalendarEventResponse]
    upcoming: list[CalendarEventResponse]
    days_to_next_critical: Optional[int] = None


# =============================================================================
# Helper Functions
# =============================================================================

def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string to datetime."""
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid datetime format: {dt_str}")


def _model_to_response(event: CalendarEventModel) -> CalendarEventResponse:
    """Convert database model to response schema."""
    return CalendarEventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        start_datetime=event.start_datetime.isoformat() if event.start_datetime else "",
        end_datetime=event.end_datetime.isoformat() if event.end_datetime else None,
        all_day=event.all_day or False,
        event_type=event.event_type or "reminder",
        is_critical=event.is_critical or False,
        reminder_days=event.reminder_days,
        created_at=event.created_at.isoformat() if event.created_at else "",
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
    user: StorageUser = Depends(require_user),
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
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event_type. Must be one of: {VALID_EVENT_TYPES}"
        )

    start_dt = _parse_datetime(event.start_datetime)
    end_dt = _parse_datetime(event.end_datetime) if event.end_datetime else None

    async with get_db_session() as session:
        db_event = CalendarEventModel(
            id=str(uuid.uuid4()),
            user_id=user.user_id,
            title=event.title,
            description=event.description,
            start_datetime=start_dt,
            end_datetime=end_dt,
            all_day=event.all_day,
            event_type=event.event_type,
            is_critical=event.is_critical,
            reminder_days=event.reminder_days,
            created_at=datetime.utcnow(),
        )
        session.add(db_event)
        await session.commit()
        await session.refresh(db_event)
        
        # Emit brain event for calendar update
        try:
            from app.services.positronic_brain import get_brain, BrainEvent, EventType as BrainEventType, ModuleType
            brain = get_brain()
            event_type_brain = BrainEventType.CALENDAR_HEARING_SCHEDULED if event.event_type == "hearing" else BrainEventType.CALENDAR_DEADLINE_APPROACHING
            await brain.emit(BrainEvent(
                event_type=event_type_brain,
                source_module=ModuleType.CALENDAR,
                data={
                    "event_id": db_event.id,
                    "title": db_event.title,
                    "event_type": db_event.event_type,
                    "start_datetime": db_event.start_datetime.isoformat() if db_event.start_datetime else None,
                    "is_critical": db_event.is_critical
                },
                user_id=user.user_id
            ))
        except Exception:
            pass  # Brain integration is optional
        
        return _model_to_response(db_event)
@router.get("/", response_model=CalendarListResponse)
async def list_events(
    start: Optional[str] = Query(None, description="Start of date range (ISO)"),
    end: Optional[str] = Query(None, description="End of date range (ISO)"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    critical_only: bool = Query(False, description="Only show critical events"),
    user: StorageUser = Depends(require_user),
):
    """
    List calendar events, optionally filtered by date range and type.
    """
    async with get_db_session() as session:
        query = select(CalendarEventModel).where(
            CalendarEventModel.user_id == user.user_id
        )

        if start:
            start_dt = _parse_datetime(start)
            query = query.where(CalendarEventModel.start_datetime >= start_dt)

        if end:
            end_dt = _parse_datetime(end)
            query = query.where(CalendarEventModel.start_datetime <= end_dt)

        if event_type:
            query = query.where(CalendarEventModel.event_type == event_type)

        if critical_only:
            query = query.where(CalendarEventModel.is_critical == True)

        # Sort by start datetime
        query = query.order_by(CalendarEventModel.start_datetime.asc())
        
        result = await session.execute(query)
        events = result.scalars().all()

        return CalendarListResponse(
            events=[_model_to_response(e) for e in events],
            total=len(events),
        )
@router.get("/upcoming", response_model=UpcomingDeadlinesResponse)
async def upcoming_deadlines(
    days: int = Query(30, ge=1, le=90, description="Look ahead days"),
    user: StorageUser = Depends(require_user),
):
    """
    Get upcoming deadlines and critical events.

    This endpoint is designed for dashboard widgets and the intensity engine.
    """
    now = utc_now()
    cutoff = now + timedelta(days=days)

    async with get_db_session() as session:
        query = select(CalendarEventModel).where(
            and_(
                CalendarEventModel.user_id == user.user_id,
                CalendarEventModel.start_datetime >= now,
                CalendarEventModel.start_datetime <= cutoff
            )
        ).order_by(CalendarEventModel.start_datetime.asc())

        result = await session.execute(query)
        upcoming = result.scalars().all()

        # Separate critical events
        critical = [e for e in upcoming if e.is_critical]

        # Calculate days to next critical
        days_to_next = None
        if critical:
            next_critical_date = critical[0].start_datetime
            # Normalize timezone for comparison
            if next_critical_date.tzinfo is None:
                next_critical_date = next_critical_date.replace(tzinfo=timezone.utc)
            # Compare using naive datetimes to avoid issues
            now_naive = now.replace(tzinfo=None)
            next_naive = next_critical_date.replace(tzinfo=None)
            days_to_next = (next_naive - now_naive).days

        return UpcomingDeadlinesResponse(
            critical=[_model_to_response(e) for e in critical],
            upcoming=[_model_to_response(e) for e in upcoming[:10]],
            days_to_next_critical=days_to_next,
        )


@router.get("/{event_id}", response_model=CalendarEventResponse)
async def get_event(
    event_id: str,
    user: StorageUser = Depends(require_user),
):
    """Get a specific calendar event."""
    async with get_db_session() as session:
        query = select(CalendarEventModel).where(
            and_(
                CalendarEventModel.id == event_id,
                CalendarEventModel.user_id == user.user_id
            )
        )
        result = await session.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return _model_to_response(event)


@router.patch("/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: str,
    updates: CalendarEventUpdate,
    user: StorageUser = Depends(require_user),
):
    """Update a calendar event."""
    async with get_db_session() as session:
        query = select(CalendarEventModel).where(
            and_(
                CalendarEventModel.id == event_id,
                CalendarEventModel.user_id == user.user_id
            )
        )
        result = await session.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        update_data = updates.model_dump(exclude_unset=True)
        
        # Parse datetime fields if provided
        if "start_datetime" in update_data and update_data["start_datetime"]:
            update_data["start_datetime"] = _parse_datetime(update_data["start_datetime"])
        if "end_datetime" in update_data and update_data["end_datetime"]:
            update_data["end_datetime"] = _parse_datetime(update_data["end_datetime"])
        
        for field, value in update_data.items():
            setattr(event, field, value)

        await session.commit()
        await session.refresh(event)
        return _model_to_response(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    user: StorageUser = Depends(require_user),
):
    """Delete a calendar event."""
    async with get_db_session() as session:
        query = select(CalendarEventModel).where(
            and_(
                CalendarEventModel.id == event_id,
                CalendarEventModel.user_id == user.user_id
            )
        )
        result = await session.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        await session.delete(event)
        await session.commit()


# =============================================================================
# Document Hub Integration - Auto-sync dates from uploaded documents
# =============================================================================

class DocumentEventsResponse(BaseModel):
    """Events extracted from documents."""
    events: List[CalendarEventResponse]
    source: str = "document_extraction"
    sync_available: bool
    documents_analyzed: int


@router.get("/from-documents", response_model=DocumentEventsResponse)
async def get_events_from_documents(
    user: StorageUser = Depends(require_user),
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
        events.append(CalendarEventResponse(
            id=event.get("id", ""),
            title=event.get("title", ""),
            description=event.get("description"),
            start_datetime=event.get("date", ""),
            end_datetime=None,
            all_day=True,
            event_type=event.get("type", "reminder"),
            is_critical=event.get("critical", False),
            reminder_days=7 if event.get("critical") else 3,
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
    
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
    synced_event_ids: List[str]


@router.post("/sync-documents", response_model=SyncResult)
async def sync_document_events(
    overwrite: bool = Query(False, description="Overwrite existing events with same title"),
    user: StorageUser = Depends(require_user),
):
    """
    Sync calendar events from uploaded documents to your calendar.
    
    This creates calendar events for:
    - Court hearings
    - Answer deadlines
    - Action items from documents
    
    Events with duplicate titles are skipped unless overwrite=true.
    All synced events are marked with source='document_extraction'.
    """
    hub = get_document_hub()
    doc_events = hub.get_calendar_events(user.user_id)
    
    synced = 0
    skipped = 0
    synced_ids = []
    
    async with get_db_session() as session:
        # Get existing event titles
        query = select(CalendarEventModel.title).where(
            CalendarEventModel.user_id == user.user_id
        )
        result = await session.execute(query)
        existing_titles = {row[0] for row in result.fetchall()}
        
        for event in doc_events:
            title = event.get("title", "")
            
            # Skip if exists and not overwriting
            if title in existing_titles and not overwrite:
                skipped += 1
                continue
            
            # Delete existing if overwriting
            if title in existing_titles and overwrite:
                delete_query = select(CalendarEventModel).where(
                    and_(
                        CalendarEventModel.user_id == user.user_id,
                        CalendarEventModel.title == title
                    )
                )
                del_result = await session.execute(delete_query)
                existing_event = del_result.scalar_one_or_none()
                if existing_event:
                    await session.delete(existing_event)
            
            # Parse date
            date_str = event.get("date", "")
            try:
                start_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                # Try parsing as date only
                try:
                    start_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    skipped += 1
                    continue
            
            # Create event
            event_id = str(uuid.uuid4())
            db_event = CalendarEventModel(
                id=event_id,
                user_id=user.user_id,
                title=title,
                description=f"Auto-synced from documents. {event.get('description', '')}",
                start_datetime=start_dt,
                end_datetime=None,
                all_day=True,
                event_type=event.get("type", "deadline"),
                is_critical=event.get("critical", False),
                reminder_days=7 if event.get("critical") else 3,
                created_at=datetime.now(timezone.utc),
            )
            session.add(db_event)
            synced += 1
            synced_ids.append(event_id)
        
        await session.commit()
        
        # Get total count
        count_query = select(func.count()).select_from(CalendarEventModel).where(
            CalendarEventModel.user_id == user.user_id
        )
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
    
    return SyncResult(
        synced=synced,
        skipped=skipped,
        total_calendar_events=total,
        synced_event_ids=synced_ids,
    )


@router.get("/deadline-summary")
async def get_deadline_summary(
    user: StorageUser = Depends(require_user),
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
    async with get_db_session() as session:
        query = select(CalendarEventModel).where(
            and_(
                CalendarEventModel.user_id == user.user_id,
                CalendarEventModel.start_datetime >= now,
                CalendarEventModel.start_datetime <= cutoff,
                CalendarEventModel.event_type.in_(["deadline", "hearing"])
            )
        ).order_by(CalendarEventModel.start_datetime.asc())
        
        result = await session.execute(query)
        events = result.scalars().all()
        
        for e in events:
            days_until = (e.start_datetime.replace(tzinfo=None) - now.replace(tzinfo=None)).days
            calendar_deadlines.append({
                "id": e.id,
                "title": e.title,
                "date": e.start_datetime.isoformat(),
                "days_until": days_until,
                "is_critical": e.is_critical,
                "type": e.event_type,
                "urgency": "critical" if days_until <= 3 else "high" if days_until <= 7 else "medium",
                "source": "calendar",
            })
    
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
