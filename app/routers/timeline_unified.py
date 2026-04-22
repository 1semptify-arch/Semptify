"""
Unified Interactive Timeline Router
===================================

Aggregates all time-based data sources:
- Documents (upload date)
- Timeline events (event date)
- Calendar events (hearings/deadlines)
- Vault items (evidence with event_time/record_time/entry_time)
- Cloud timeline (events.json)

Features:
- Dynamic date axis switching (event_time, record_time, entry_time, uploaded_at)
- Date range filtering
- Evidence highlighting
- Real-time updates

Date Axes:
- event_time: When the event actually occurred (e.g., date on a notice)
- record_time: When the document was created (e.g., photo taken date)
- entry_time: When the item was added to Semptify (uploaded_at fallback)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Literal
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.id_gen import make_id
from app.core.database import get_db_session
from app.core.security import require_user, StorageUser
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_TIMELINE_EVENTS_FILE
from app.models.models import (
    TimelineEvent as TimelineEventModel,
    Document as DocumentModel,
    CalendarEvent as CalendarEventModel,
    VaultItem,
)
from app.services.unified_overlay_manager import UnifiedOverlayManager


router = APIRouter(prefix="/api/timeline", tags=["Unified Timeline"])


# =============================================================================
# Enums & Constants
# =============================================================================

class DateAxis(str, Enum):
    """Which timestamp to use for timeline sorting/display."""
    EVENT_TIME = "event_time"      # When the event occurred
    RECORD_TIME = "record_time"    # When the document was created
    ENTRY_TIME = "entry_time"      # When uploaded to Semptify
    UPLOADED_AT = "uploaded_at"    # Alias for entry_time (documents)


class ItemType(str, Enum):
    """Types of items that can appear on the timeline."""
    DOCUMENT = "document"
    TIMELINE_EVENT = "timeline_event"
    CALENDAR_EVENT = "calendar_event"
    VAULT_ITEM = "vault_item"
    RENT_PAYMENT = "rent_payment"


class Urgency(str, Enum):
    """Urgency levels for timeline items."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# =============================================================================
# Request/Response Models
# =============================================================================

class TimelineViewRequest(BaseModel):
    """Request parameters for timeline view."""
    date_axis: DateAxis = Field(
        default=DateAxis.EVENT_TIME,
        description="Which date field to sort and display by"
    )
    start_date: Optional[str] = Field(
        None,
        description="ISO date or relative (e.g., '-30d', '-6m', '-1y')"
    )
    end_date: Optional[str] = Field(
        None,
        description="ISO date or relative"
    )
    item_types: List[ItemType] = Field(
        default=[ItemType.DOCUMENT, ItemType.TIMELINE_EVENT, 
                 ItemType.CALENDAR_EVENT, ItemType.VAULT_ITEM],
        description="Which types of items to include"
    )
    evidence_only: bool = Field(
        False,
        description="Only show items marked as evidence"
    )
    urgency_filter: Optional[List[Urgency]] = Field(
        None,
        description="Filter by urgency levels"
    )
    search_query: Optional[str] = Field(
        None,
        description="Search in titles and descriptions"
    )
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class TimelineItem(BaseModel):
    """A single item on the unified timeline."""
    id: str
    item_type: ItemType
    title: str
    description: Optional[str] = None
    
    # Three timestamps (always populated)
    date_display: str  # The primary date based on date_axis
    event_date: Optional[str]  # When it happened
    record_date: Optional[str]  # When created
    entry_date: str  # When added to Semptify
    
    # Classification
    is_evidence: bool = False
    urgency: Urgency = Urgency.NORMAL
    item_subtype: Optional[str] = None  # document_type, event_type, etc.
    
    # UI hints
    icon: str = "file"  # Lucide icon name
    color: str = "gray"  # Tailwind color (red, amber, blue, gray, etc.)
    source: str = "unknown"  # upload, extraction, manual, calendar, vault
    
    # Links
    document_id: Optional[str] = None
    overlay_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    # Additional metadata
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class TimelineFacets(BaseModel):
    """Summary counts by category."""
    by_type: Dict[str, int]
    by_urgency: Dict[str, int]
    by_month: Dict[str, int]  # YYYY-MM


class TimelineViewResponse(BaseModel):
    """Complete timeline view response."""
    items: List[TimelineItem]
    total: int
    date_range: Dict[str, str]  # {start, end}
    date_axis: DateAxis
    facets: TimelineFacets
    has_more: bool


class DateRangeInfo(BaseModel):
    """Information about available date ranges."""
    earliest_event: Optional[str]
    latest_event: Optional[str]
    earliest_record: Optional[str]
    latest_record: Optional[str]
    earliest_entry: Optional[str]
    latest_entry: Optional[str]


# =============================================================================
# Helper Functions
# =============================================================================

def _parse_relative_date(date_str: str, reference: datetime) -> datetime:
    """Parse a date string that might be relative (e.g., '-30d', '-6m')."""
    if not date_str:
        return reference
    
    # Handle relative dates
    if date_str.startswith('-'):
        value = int(date_str[1:-1])
        unit = date_str[-1]
        
        if unit == 'd':
            return reference - timedelta(days=value)
        elif unit == 'w':
            return reference - timedelta(weeks=value)
        elif unit == 'm':
            return reference - timedelta(days=value * 30)
        elif unit == 'y':
            return reference - timedelta(days=value * 365)
    
    # Handle ISO dates
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        # Try just date
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid date format: {date_str}")


def _format_date(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string or None."""
    if not dt:
        return None
    return dt.isoformat()


def _get_icon_and_color(item_type: ItemType, subtype: Optional[str], 
                        is_evidence: bool, urgency: Urgency) -> tuple[str, str]:
    """Get Lucide icon name and Tailwind color for an item."""
    
    # Evidence always gets special treatment
    if is_evidence:
        return "shield", "red"
    
    # Critical urgency
    if urgency == Urgency.CRITICAL:
        return "alert-circle", "red"
    
    # Type-based icons
    icon_map = {
        ItemType.DOCUMENT: "file-text",
        ItemType.TIMELINE_EVENT: "calendar-clock",
        ItemType.CALENDAR_EVENT: "calendar",
        ItemType.VAULT_ITEM: "archive",
        ItemType.RENT_PAYMENT: "credit-card",
    }
    
    # Subtype overrides
    if item_type == ItemType.DOCUMENT and subtype:
        subtype_lower = subtype.lower()
        if 'notice' in subtype_lower:
            return "bell", "amber"
        elif 'lease' in subtype_lower:
            return "home", "blue"
        elif 'photo' in subtype_lower:
            return "camera", "purple"
        elif 'receipt' in subtype_lower or 'payment' in subtype_lower:
            return "receipt", "green"
        elif 'legal' in subtype_lower or 'court' in subtype_lower:
            return "scale", "red"
    
    if item_type == ItemType.TIMELINE_EVENT and subtype:
        subtype_lower = subtype.lower()
        if 'court' in subtype_lower:
            return "gavel", "red"
        elif 'notice' in subtype_lower:
            return "bell", "amber"
        elif 'payment' in subtype_lower:
            return "dollar-sign", "green"
    
    if item_type == ItemType.CALENDAR_EVENT and subtype:
        subtype_lower = subtype.lower()
        if 'hearing' in subtype_lower:
            return "gavel", "red"
        elif 'deadline' in subtype_lower:
            return "clock", "amber"
    
    # Color based on urgency
    color_map = {
        Urgency.HIGH: "orange",
        Urgency.NORMAL: "gray",
        Urgency.LOW: "blue",
    }
    
    return icon_map.get(item_type, "file"), color_map.get(urgency, "gray")


# =============================================================================
# Data Loading Functions
# =============================================================================

async def _load_cloud_timeline_events(user: StorageUser) -> List[Dict[str, Any]]:
    """Load timeline events from user's cloud storage (events.json)."""
    try:
        overlay_mgr = UnifiedOverlayManager(user)
        content = await overlay_mgr.read_file_from_cloud(
            user.user_id,
            VAULT_TIMELINE_EVENTS_FILE
        )
        if content:
            import json
            data = json.loads(content)
            return data.get("events", [])
    except Exception:
        pass
    return []


async def _load_db_documents(
    session: AsyncSession, 
    user_id: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    date_axis: DateAxis
) -> List[TimelineItem]:
    """Load documents from database."""
    query = select(DocumentModel).where(DocumentModel.user_id == user_id)
    
    # Date filtering (documents only have uploaded_at)
    if start_date:
        query = query.where(DocumentModel.uploaded_at >= start_date)
    if end_date:
        query = query.where(DocumentModel.uploaded_at <= end_date)
    
    query = query.order_by(DocumentModel.uploaded_at.desc())
    
    result = await session.execute(query)
    documents = result.scalars().all()
    
    items = []
    for doc in documents:
        uploaded_at = doc.uploaded_at or utc_now()
        
        # Documents don't have separate event/record times from DB
        # Could extract from metadata in future
        event_dt = None
        record_dt = None
        
        # Choose display date based on axis
        if date_axis in (DateAxis.EVENT_TIME, DateAxis.RECORD_TIME):
            # For documents without extraction, use uploaded_at as fallback
            display_dt = uploaded_at
        else:
            display_dt = uploaded_at
        
        icon, color = _get_icon_and_color(
            ItemType.DOCUMENT, doc.document_type, False, Urgency.NORMAL
        )
        
        items.append(TimelineItem(
            id=doc.id,
            item_type=ItemType.DOCUMENT,
            title=doc.filename or doc.original_filename or "Untitled Document",
            description=doc.description,
            date_display=_format_date(display_dt) or "",
            event_date=_format_date(event_dt),
            record_date=_format_date(record_dt),
            entry_date=_format_date(uploaded_at) or "",
            is_evidence=doc.is_privileged or False,  # Could be refined
            urgency=Urgency.NORMAL,
            item_subtype=doc.document_type,
            icon=icon,
            color=color,
            source="upload",
            document_id=doc.id,
            tags=doc.tags.split(",") if doc.tags else [],
        ))
    
    return items


async def _load_db_timeline_events(
    session: AsyncSession,
    user_id: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    date_axis: DateAxis,
    evidence_only: bool
) -> List[TimelineItem]:
    """Load manual timeline events from database."""
    query = select(TimelineEventModel).where(TimelineEventModel.user_id == user_id)
    
    # Filter by evidence
    if evidence_only:
        query = query.where(TimelineEventModel.is_evidence == True)
    
    # Date filtering
    if date_axis == DateAxis.EVENT_TIME:
        filter_col = TimelineEventModel.event_date
    else:
        filter_col = TimelineEventModel.created_at
    
    if start_date:
        query = query.where(filter_col >= start_date)
    if end_date:
        query = query.where(filter_col <= end_date)
    
    query = query.order_by(filter_col.desc())
    
    result = await session.execute(query)
    events = result.scalars().all()
    
    items = []
    for evt in events:
        event_dt = evt.event_date
        entry_dt = evt.created_at or utc_now()
        
        # Choose display date
        if date_axis == DateAxis.EVENT_TIME:
            display_dt = event_dt
        else:
            display_dt = entry_dt
        
        urgency = Urgency(evt.urgency) if evt.urgency else Urgency.NORMAL
        if evt.is_deadline and urgency == Urgency.NORMAL:
            urgency = Urgency.HIGH
        
        icon, color = _get_icon_and_color(
            ItemType.TIMELINE_EVENT, evt.event_type, evt.is_evidence, urgency
        )
        
        items.append(TimelineItem(
            id=evt.id,
            item_type=ItemType.TIMELINE_EVENT,
            title=evt.title,
            description=evt.description,
            date_display=_format_date(display_dt) or "",
            event_date=_format_date(event_dt),
            record_date=_format_date(event_dt),  # Same as event for manual events
            entry_date=_format_date(entry_dt) or "",
            is_evidence=evt.is_evidence or False,
            urgency=urgency,
            item_subtype=evt.event_type,
            icon=icon,
            color=color,
            source="manual",
            document_id=evt.document_id,
            tags=[evt.highlight_color] if evt.highlight_color else [],
            metadata={
                "footnote_number": evt.footnote_number,
                "source_extraction_id": evt.source_extraction_id,
            }
        ))
    
    return items


async def _load_db_calendar_events(
    session: AsyncSession,
    user_id: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    date_axis: DateAxis,
) -> List[TimelineItem]:
    """Load calendar events (deadlines, hearings)."""
    query = select(CalendarEventModel).where(CalendarEventModel.user_id == user_id)
    
    # Date filtering
    if date_axis == DateAxis.EVENT_TIME:
        filter_col = CalendarEventModel.start_datetime
    else:
        filter_col = CalendarEventModel.created_at
    
    if start_date:
        query = query.where(filter_col >= start_date)
    if end_date:
        query = query.where(filter_col <= end_date)
    
    query = query.order_by(filter_col.desc())
    
    result = await session.execute(query)
    events = result.scalars().all()
    
    items = []
    for evt in events:
        event_dt = evt.start_datetime
        entry_dt = evt.created_at or utc_now()
        
        # Choose display date
        if date_axis == DateAxis.EVENT_TIME:
            display_dt = event_dt
        else:
            display_dt = entry_dt
        
        urgency = Urgency.CRITICAL if evt.is_critical else Urgency.HIGH
        
        icon, color = _get_icon_and_color(
            ItemType.CALENDAR_EVENT, evt.event_type, False, urgency
        )
        
        items.append(TimelineItem(
            id=evt.id,
            item_type=ItemType.CALENDAR_EVENT,
            title=evt.title,
            description=evt.description,
            date_display=_format_date(display_dt) or "",
            event_date=_format_date(event_dt),
            record_date=_format_date(event_dt),
            entry_date=_format_date(entry_dt) or "",
            is_evidence=True,  # Court dates are always evidence
            urgency=urgency,
            item_subtype=evt.event_type,
            icon=icon,
            color=color,
            source="calendar",
            metadata={
                "all_day": evt.all_day,
                "end_datetime": _format_date(evt.end_datetime),
                "reminder_days": evt.reminder_days,
            }
        ))
    
    return items


async def _load_db_vault_items(
    session: AsyncSession,
    user_id: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    date_axis: DateAxis,
    evidence_only: bool
) -> List[TimelineItem]:
    """Load vault items (evidence with three timestamps)."""
    query = select(VaultItem).where(VaultItem.user_id == user_id)
    
    # Filter by evidence
    if evidence_only:
        query = query.where(VaultItem.status == "verified")
    
    # Date filtering based on axis
    if date_axis == DateAxis.EVENT_TIME:
        filter_col = VaultItem.event_time
    elif date_axis == DateAxis.RECORD_TIME:
        filter_col = VaultItem.record_time
    else:
        filter_col = VaultItem.semptify_entry_time
    
    if start_date:
        query = query.where(filter_col >= start_date)
    if end_date:
        query = query.where(filter_col <= end_date)
    
    query = query.order_by(filter_col.desc())
    
    result = await session.execute(query)
    items_db = result.scalars().all()
    
    items = []
    for vi in items_db:
        event_dt = vi.event_time
        record_dt = vi.record_time
        entry_dt = vi.semptify_entry_time
        
        # Choose display date
        if date_axis == DateAxis.EVENT_TIME:
            display_dt = event_dt
        elif date_axis == DateAxis.RECORD_TIME:
            display_dt = record_dt
        else:
            display_dt = entry_dt
        
        urgency = Urgency(vi.severity) if vi.severity else Urgency.NORMAL
        
        icon, color = _get_icon_and_color(
            ItemType.VAULT_ITEM, vi.item_type, False, urgency
        )
        
        items.append(TimelineItem(
            id=str(vi.item_id),
            item_type=ItemType.VAULT_ITEM,
            title=vi.title or vi.item_type,
            description=vi.summary,
            date_display=_format_date(display_dt) or "",
            event_date=_format_date(event_dt),
            record_date=_format_date(record_dt),
            entry_date=_format_date(entry_dt) or "",
            is_evidence=vi.status == "verified",
            urgency=urgency,
            item_subtype=vi.item_type,
            icon=icon,
            color=color,
            source=vi.source or "vault",
            document_id=vi.file_path,
            tags=vi.tags or [],
            metadata=vi.item_metadata or {},
        ))
    
    return items


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/unified", response_model=TimelineViewResponse)
async def get_unified_timeline(
    request: TimelineViewRequest,
    user: StorageUser = Depends(require_user),
) -> TimelineViewResponse:
    """
    Get unified interactive timeline view.
    
    Aggregates data from:
    - Documents (upload metadata)
    - Manual timeline events
    - Calendar events (court dates)
    - Vault items (evidence with 3 timestamps)
    - Cloud timeline (events.json) - merged in
    
    **Date Axes:**
    - `event_time`: When the event actually occurred (e.g., date on notice)
    - `record_time`: When the document/photo was created
    - `entry_time`: When it was uploaded to Semptify
    
    **Date Ranges:**
    - Use ISO dates: `2025-01-01`
    - Or relative: `-30d`, `-6m`, `-1y`
    """
    
    # Parse date range
    now = utc_now()
    start_date = _parse_relative_date(request.start_date, now - timedelta(days=365))
    end_date = _parse_relative_date(request.end_date, now)
    
    all_items: List[TimelineItem] = []
    
    async with get_db_session() as session:
        # Load from each source
        if ItemType.DOCUMENT in request.item_types:
            docs = await _load_db_documents(
                session, user.user_id, start_date, end_date, request.date_axis
            )
            all_items.extend(docs)
        
        if ItemType.TIMELINE_EVENT in request.item_types:
            events = await _load_db_timeline_events(
                session, user.user_id, start_date, end_date, 
                request.date_axis, request.evidence_only
            )
            all_items.extend(events)
        
        if ItemType.CALENDAR_EVENT in request.item_types:
            cal_events = await _load_db_calendar_events(
                session, user.user_id, start_date, end_date, request.date_axis
            )
            all_items.extend(cal_events)
        
        if ItemType.VAULT_ITEM in request.item_types:
            vault_items = await _load_db_vault_items(
                session, user.user_id, start_date, end_date,
                request.date_axis, request.evidence_only
            )
            all_items.extend(vault_items)
    
    # TODO: Merge cloud timeline events (events.json)
    # cloud_events = await _load_cloud_timeline_events(user)
    # for ce in cloud_events:
    #     all_items.append(_cloud_event_to_item(ce, request.date_axis))
    
    # Sort by display date (descending = newest first)
    all_items.sort(
        key=lambda x: x.date_display or "",
        reverse=True
    )
    
    # Apply search filter
    if request.search_query:
        query_lower = request.search_query.lower()
        all_items = [
            item for item in all_items
            if query_lower in item.title.lower()
            or (item.description and query_lower in item.description.lower())
            or any(query_lower in tag.lower() for tag in item.tags)
        ]
    
    # Apply urgency filter
    if request.urgency_filter:
        allowed = [u.value for u in request.urgency_filter]
        all_items = [item for item in all_items if item.urgency.value in allowed]
    
    # Pagination
    total = len(all_items)
    paginated = all_items[request.offset : request.offset + request.limit]
    has_more = (request.offset + request.limit) < total
    
    # Calculate facets
    by_type: Dict[str, int] = {}
    by_urgency: Dict[str, int] = {}
    by_month: Dict[str, int] = {}
    
    for item in all_items:
        by_type[item.item_type.value] = by_type.get(item.item_type.value, 0) + 1
        by_urgency[item.urgency.value] = by_urgency.get(item.urgency.value, 0) + 1
        
        # Group by month
        if item.date_display and len(item.date_display) >= 7:
            month_key = item.date_display[:7]  # YYYY-MM
            by_month[month_key] = by_month.get(month_key, 0) + 1
    
    return TimelineViewResponse(
        items=paginated,
        total=total,
        date_range={
            "start": _format_date(start_date) or "",
            "end": _format_date(end_date) or "",
        },
        date_axis=request.date_axis,
        facets=TimelineFacets(
            by_type=by_type,
            by_urgency=by_urgency,
            by_month=by_month,
        ),
        has_more=has_more,
    )


@router.get("/date-range", response_model=DateRangeInfo)
async def get_date_range_info(
    user: StorageUser = Depends(require_user),
) -> DateRangeInfo:
    """
    Get the available date range across all timeline sources.
    
    Useful for setting up the timeline slider/selector on the frontend.
    """
    async with get_db_session() as session:
        # Documents
        doc_result = await session.execute(
            select(
                func.min(DocumentModel.uploaded_at),
                func.max(DocumentModel.uploaded_at)
            ).where(DocumentModel.user_id == user.user_id)
        )
        doc_min, doc_max = doc_result.first() or (None, None)
        
        # Timeline events
        evt_result = await session.execute(
            select(
                func.min(TimelineEventModel.event_date),
                func.max(TimelineEventModel.event_date)
            ).where(TimelineEventModel.user_id == user.user_id)
        )
        evt_min, evt_max = evt_result.first() or (None, None)
        
        # Vault items (all three timestamps)
        vault_result = await session.execute(
            select(
                func.min(VaultItem.event_time),
                func.max(VaultItem.event_time),
                func.min(VaultItem.record_time),
                func.max(VaultItem.record_time),
                func.min(VaultItem.semptify_entry_time),
                func.max(VaultItem.semptify_entry_time),
            ).where(VaultItem.user_id == user.user_id)
        )
        vault_row = vault_result.first()
        
        # Combine all
        all_event = [evt_min] + ([vault_row[0]] if vault_row else [])
        all_record = [vault_row[2] if vault_row else None]
        all_entry = [doc_min, evt_min] + ([vault_row[4]] if vault_row else [])
        
        valid_event = [d for d in all_event if d]
        valid_record = [d for d in all_record if d]
        valid_entry = [d for d in all_entry if d]
        
        return DateRangeInfo(
            earliest_event=_format_date(min(valid_event)) if valid_event else None,
            latest_event=_format_date(max(valid_event)) if valid_event else None,
            earliest_record=_format_date(min(valid_record)) if valid_record else None,
            latest_record=_format_date(max(valid_record)) if valid_record else None,
            earliest_entry=_format_date(min(valid_entry)) if valid_entry else None,
            latest_entry=_format_date(max(valid_entry)) if valid_entry else None,
        )
