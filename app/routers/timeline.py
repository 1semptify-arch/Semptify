"""
Timeline Router (Database-backed)
Event tracking and history for tenant journey.

Now integrated with DocumentHub for auto-syncing timeline events from documents.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_user, StorageUser
from app.core.utc import utc_now
from app.core.document_hub import get_document_hub
from app.models.models import TimelineEvent as TimelineEventModel, Document as DocumentModel
from app.services.timeline_builder import TimelineBuilder, extract_timeline_from_text


router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

VALID_EVENT_TYPES = ["notice", "payment", "maintenance", "communication", "court", "other"]


class TimelineEventCreate(BaseModel):
    """Create a new timeline event."""
    event_type: str = Field(..., description="Type: notice, payment, maintenance, communication, court, other")
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    event_date: str = Field(..., description="ISO format date when event occurred")
    document_id: Optional[str] = Field(None, description="Link to a vault document")
    overlay_record_ids: List[str] = Field(default_factory=list, description="Preferred overlay references for document context")
    is_evidence: bool = Field(False, description="Mark as evidence for court")


class TimelineEventUpdate(BaseModel):
    """Update an existing timeline event."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    event_date: Optional[str] = None
    document_id: Optional[str] = None
    overlay_record_ids: Optional[List[str]] = None
    is_evidence: Optional[bool] = None


class TimelineEventResponse(BaseModel):
    """Timeline event response."""
    id: str
    event_type: str
    title: str
    description: Optional[str] = None
    event_date: str
    document_id: Optional[str] = None
    overlay_record_ids: List[str] = []
    is_evidence: bool
    created_at: str


class TimelineListResponse(BaseModel):
    """List of timeline events."""
    events: list[TimelineEventResponse]
    total: int


# =============================================================================
# Helper Functions
# =============================================================================

def _parse_date(date_str: str) -> datetime:
    """Parse ISO date string to datetime."""
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {date_str}")


def _model_to_response(event: TimelineEventModel) -> TimelineEventResponse:
    """Convert database model to response schema."""
    overlay_record_ids = _get_overlay_record_ids(event.document_id)
    return TimelineEventResponse(
        id=event.id,
        event_type=event.event_type or "other",
        title=event.title,
        description=event.description,
        event_date=event.event_date.isoformat() if event.event_date else "",
        document_id=event.document_id,
        overlay_record_ids=overlay_record_ids,
        is_evidence=event.is_evidence or False,
        created_at=event.created_at.isoformat() if event.created_at else "",
    )


def _resolve_document_id_from_overlay_ids(overlay_record_ids: Optional[List[str]], fallback_document_id: Optional[str]) -> Optional[str]:
    """Resolve vault document reference from overlay IDs, fallback to provided document_id."""
    if fallback_document_id:
        return fallback_document_id
    if not overlay_record_ids:
        return None

    try:
        from app.services.document_overlay_service import document_overlay_service
    except Exception:
        return None

    for overlay_id in overlay_record_ids:
        overlay = document_overlay_service.get_overlay(overlay_id)
        if overlay and overlay.vault_id:
            return overlay.vault_id
    return None


def _get_overlay_record_ids(document_id: Optional[str]) -> list[str]:
    if not document_id:
        return []
    try:
        from app.services.document_overlay_service import document_overlay_service

        overlays = document_overlay_service.list_overlays(vault_id=document_id)
        return [record.overlay_id for record in overlays]
    except Exception:
        return []


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/",
    response_model=TimelineEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    event: TimelineEventCreate,
    user: StorageUser = Depends(require_user),
):
    """
    Create a new timeline event.

    Events track important moments in your tenant journey:
    - Notices received or sent
    - Rent payments
    - Maintenance requests
    - Communications with landlord
    - Court dates or filings
    """
    if event.event_type not in VALID_EVENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event_type. Must be one of: {VALID_EVENT_TYPES}"
        )

    event_date = _parse_date(event.event_date)
    resolved_document_id = _resolve_document_id_from_overlay_ids(event.overlay_record_ids, event.document_id)

    async with get_db_session() as session:
        db_event = TimelineEventModel(
            id=str(uuid.uuid4()),
            user_id=user.user_id,
            event_type=event.event_type,
            title=event.title,
            description=event.description,
            event_date=event_date,
            document_id=resolved_document_id,
            is_evidence=event.is_evidence,
            created_at=datetime.utcnow(),
        )
        session.add(db_event)
        await session.commit()
        await session.refresh(db_event)
        
        # Emit brain event for timeline update
        try:
            from app.services.positronic_brain import get_brain, BrainEvent, EventType as BrainEventType, ModuleType
            brain = get_brain()
            await brain.emit(BrainEvent(
                event_type=BrainEventType.TIMELINE_EVENT_ADDED,
                source_module=ModuleType.TIMELINE,
                data={
                    "event_id": db_event.id,
                    "event_type": db_event.event_type,
                    "title": db_event.title,
                    "event_date": db_event.event_date.isoformat() if db_event.event_date else None,
                    "is_evidence": db_event.is_evidence
                },
                user_id=user.user_id
            ))
        except Exception:
            pass  # Brain integration is optional
        
        return _model_to_response(db_event)
@router.get("/", response_model=TimelineListResponse)
async def list_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    evidence_only: bool = Query(False, description="Only show evidence-marked events"),
    start_date: Optional[str] = Query(None, description="Filter events after this date (ISO)"),
    end_date: Optional[str] = Query(None, description="Filter events before this date (ISO)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: StorageUser = Depends(require_user),
):
    """
    List timeline events with optional filtering.
    
    Events come from two sources:
    1. User's vault documents (auto-generated based on document type/date)
    2. Manually created timeline events
    
    Events are returned in reverse chronological order (newest first).
    """
    from app.models.models import Document as DocumentModel
    
    async with get_db_session() as session:
        # Get timeline events from database
        query = select(TimelineEventModel).where(
            TimelineEventModel.user_id == user.user_id
        )

        # Apply filters to manual events
        if event_type:
            query = query.where(TimelineEventModel.event_type == event_type)
        if evidence_only:
            query = query.where(TimelineEventModel.is_evidence == True)
        if start_date:
            start_dt = _parse_date(start_date)
            query = query.where(TimelineEventModel.event_date >= start_dt)
        if end_date:
            end_dt = _parse_date(end_date)
            query = query.where(TimelineEventModel.event_date <= end_dt)

        result = await session.execute(query)
        manual_events = result.scalars().all()
        
        # Get documents from vault to generate timeline events
        doc_query = select(DocumentModel).where(
            DocumentModel.user_id == user.user_id
        )
        doc_result = await session.execute(doc_query)
        documents = doc_result.scalars().all()
        
        # Convert documents to timeline events
        doc_events = []
        doc_type_to_event_type = {
            "notice": "notice",
            "lease": "other",
            "legal": "court",
            "correspondence": "communication",
            "photo": "other",
            "receipt": "payment",
            "payment": "payment",
        }
        
        for doc in documents:
            doc_event_type = doc_type_to_event_type.get(doc.document_type, "other")
            
            # Apply event_type filter
            if event_type and doc_event_type != event_type:
                continue
            
            # Apply date filters
            doc_date = doc.uploaded_at
            if start_date:
                start_dt = _parse_date(start_date)
                if doc_date < start_dt:
                    continue
            if end_date:
                end_dt = _parse_date(end_date)
                if doc_date > end_dt:
                    continue
            
            # Skip if evidence_only and not marked (docs are evidence by default)
            # All vault documents are considered potential evidence
            
            doc_events.append(TimelineEventResponse(
                id=f"doc_{doc.id}",
                event_type=doc_event_type,
                title=f"Document: {doc.original_filename}",
                description=doc.description or f"Uploaded {doc.document_type or 'document'}: {doc.original_filename}",
                event_date=doc_date.isoformat() if doc_date else "",
                document_id=doc.id,
                overlay_record_ids=_get_overlay_record_ids(doc.id),
                is_evidence=True,  # All vault docs are potential evidence
                created_at=doc_date.isoformat() if doc_date else "",
            ))
        
        # Combine manual events and document events
        all_events = [_model_to_response(e) for e in manual_events] + doc_events
        
        # Sort by event_date descending
        all_events.sort(key=lambda e: e.event_date, reverse=True)
        
        # Apply pagination
        total = len(all_events)
        paginated_events = all_events[offset:offset + limit]

        return TimelineListResponse(
            events=paginated_events,
            total=total,
        )
@router.get("/{event_id}", response_model=TimelineEventResponse)
async def get_event(
    event_id: str,
    user: StorageUser = Depends(require_user),
):
    """Get a specific timeline event."""
    async with get_db_session() as session:
        query = select(TimelineEventModel).where(
            and_(
                TimelineEventModel.id == event_id,
                TimelineEventModel.user_id == user.user_id
            )
        )
        result = await session.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return _model_to_response(event)


@router.patch("/{event_id}", response_model=TimelineEventResponse)
async def update_event(
    event_id: str,
    updates: TimelineEventUpdate,
    user: StorageUser = Depends(require_user),
):
    """Update a timeline event."""
    async with get_db_session() as session:
        query = select(TimelineEventModel).where(
            and_(
                TimelineEventModel.id == event_id,
                TimelineEventModel.user_id == user.user_id
            )
        )
        result = await session.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Update fields
        update_data = updates.model_dump(exclude_unset=True)
        overlay_record_ids = update_data.pop("overlay_record_ids", None)
        if overlay_record_ids is not None:
            update_data["document_id"] = _resolve_document_id_from_overlay_ids(
                overlay_record_ids,
                update_data.get("document_id"),
            )
        
        # Parse event_date if provided
        if "event_date" in update_data and update_data["event_date"]:
            update_data["event_date"] = _parse_date(update_data["event_date"])
        
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
    """Delete a timeline event."""
    async with get_db_session() as session:
        query = select(TimelineEventModel).where(
            and_(
                TimelineEventModel.id == event_id,
                TimelineEventModel.user_id == user.user_id
            )
        )
        result = await session.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        await session.delete(event)
        await session.commit()


@router.get("/types/summary")
async def event_type_summary(
    user: StorageUser = Depends(require_user),
):
    """
    Get a summary of events by type.
    Useful for dashboard widgets.
    """
    async with get_db_session() as session:
        # Get all events for user
        query = select(TimelineEventModel).where(
            TimelineEventModel.user_id == user.user_id
        )
        result = await session.execute(query)
        events = result.scalars().all()

        summary = {}
        for event in events:
            event_type = event.event_type or "other"
            if event_type not in summary:
                summary[event_type] = {"count": 0, "evidence_count": 0}
            summary[event_type]["count"] += 1
            if event.is_evidence:
                summary[event_type]["evidence_count"] += 1

        return {
            "summary": summary,
            "total_events": len(events),
            "total_evidence": sum(1 for e in events if e.is_evidence),
        }


# =============================================================================
# Auto-Build Timeline from Documents
# =============================================================================

class AutoBuildRequest(BaseModel):
    """Request to auto-build timeline from document text."""
    text: str = Field(..., description="Document text to extract events from")
    document_id: Optional[str] = Field(None, description="Source document ID")
    filename: Optional[str] = Field(None, description="Source filename")
    document_type: Optional[str] = Field(None, description="Type of document (notice, lease, etc.)")
    auto_save: bool = Field(True, description="Automatically save extracted events to timeline")


class ExtractedEventResponse(BaseModel):
    """An extracted timeline event."""
    id: str
    event_type: str
    title: str
    description: str
    event_date: Optional[str]
    event_date_text: str
    is_deadline: bool
    is_evidence: bool
    urgency: str
    confidence: float
    source_document_id: Optional[str]
    source_filename: Optional[str]


class AutoBuildResponse(BaseModel):
    """Response from auto-build timeline."""
    events: List[ExtractedEventResponse]
    total_events_found: int
    total_deadlines_found: int
    events_saved: int
    earliest_date: Optional[str]
    latest_date: Optional[str]
    warnings: List[str]


@router.post("/auto-build", response_model=AutoBuildResponse)
async def auto_build_timeline(
    request: AutoBuildRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Automatically extract timeline events from document text.
    
    This endpoint analyzes document text for dates and events,
    then optionally saves them to the user's timeline.
    
    Perfect for:
    - Processing uploaded documents
    - Building case history from evidence
    - Identifying deadlines from notices
    """
    builder = TimelineBuilder()
    result = await builder.build_from_text(
        text=request.text,
        document_id=request.document_id,
        filename=request.filename,
        document_type=request.document_type,
    )
    
    events_saved = 0
    
    # Save events to database if requested
    if request.auto_save and result.events:
        async with get_db_session() as session:
            for event in result.events:
                if event.event_date:
                    db_event = TimelineEventModel(
                        id=event.id,
                        user_id=user.user_id,
                        event_type=event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
                        title=event.title,
                        description=event.description,
                        event_date=datetime.combine(event.event_date, datetime.min.time()),
                        document_id=event.source_document_id,
                        is_evidence=event.is_evidence,
                        created_at=utc_now(),
                    )
                    session.add(db_event)
                    events_saved += 1
            
            await session.commit()
    
    # Convert to response format
    response_events = [
        ExtractedEventResponse(
            id=e.id,
            event_type=e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type),
            title=e.title,
            description=e.description,
            event_date=e.event_date.isoformat() if e.event_date else None,
            event_date_text=e.event_date_text,
            is_deadline=e.is_deadline,
            is_evidence=e.is_evidence,
            urgency=e.urgency,
            confidence=e.confidence,
            source_document_id=e.source_document_id,
            source_filename=e.source_filename,
        )
        for e in result.events
    ]
    
    return AutoBuildResponse(
        events=response_events,
        total_events_found=result.total_events_found,
        total_deadlines_found=result.total_deadlines_found,
        events_saved=events_saved,
        earliest_date=result.earliest_date.isoformat() if result.earliest_date else None,
        latest_date=result.latest_date.isoformat() if result.latest_date else None,
        warnings=result.warnings,
    )


@router.post("/auto-build/preview")
async def preview_auto_build(
    request: AutoBuildRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Preview timeline events without saving.
    
    Same as auto-build but doesn't persist to database.
    Use this to show users what will be extracted before committing.
    """
    # Force auto_save off for preview
    request.auto_save = False
    
    builder = TimelineBuilder()
    result = await builder.build_from_text(
        text=request.text,
        document_id=request.document_id,
        filename=request.filename,
        document_type=request.document_type,
    )
    
    return {
        "preview": True,
        "events": [e.to_dict() for e in result.events],
        "total_events_found": result.total_events_found,
        "total_deadlines_found": result.total_deadlines_found,
        "earliest_date": result.earliest_date.isoformat() if result.earliest_date else None,
        "latest_date": result.latest_date.isoformat() if result.latest_date else None,
        "warnings": result.warnings,
    }


@router.post("/auto-build/from-document/{document_id}")
async def auto_build_from_document(
    document_id: str,
    auto_save: bool = Query(True, description="Save events to timeline"),
    user: StorageUser = Depends(require_user),
):
    """
    Auto-build timeline from an existing vault document.
    
    Fetches the document text and extracts timeline events.
    """
    from app.models.models import Document as DocumentModel
    
    async with get_db_session() as session:
        # Get the document
        query = select(DocumentModel).where(
            and_(
                DocumentModel.id == document_id,
                DocumentModel.user_id == user.user_id
            )
        )
        result = await session.execute(query)
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get document text (from extracted_text or content)
        text = document.extracted_text or ""
        if not text and document.content:
            text = document.content.decode('utf-8', errors='ignore') if isinstance(document.content, bytes) else str(document.content)
        
        if not text:
            raise HTTPException(status_code=400, detail="Document has no extractable text")
        
        # Build timeline
        builder = TimelineBuilder()
        build_result = await builder.build_from_text(
            text=text,
            document_id=document_id,
            filename=document.filename,
            document_type=document.document_type,
        )
        
        events_saved = 0
        
        # Save events if requested
        if auto_save and build_result.events:
            for event in build_result.events:
                if event.event_date:
                    db_event = TimelineEventModel(
                        id=event.id,
                        user_id=user.user_id,
                        event_type=event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
                        title=event.title,
                        description=event.description,
                        event_date=datetime.combine(event.event_date, datetime.min.time()),
                        document_id=document_id,
                        is_evidence=True,
                        created_at=utc_now(),
                    )
                    session.add(db_event)
                    events_saved += 1
            
            await session.commit()
        
        return {
            "document_id": document_id,
            "document_filename": document.filename,
            "events": [e.to_dict() for e in build_result.events],
            "total_events_found": build_result.total_events_found,
            "total_deadlines_found": build_result.total_deadlines_found,
            "events_saved": events_saved,
            "warnings": build_result.warnings,
        }


# =============================================================================
# Document Hub Integration - Auto-sync timeline from all documents
# =============================================================================

@router.get("/from-documents")
async def get_timeline_from_documents(
    user: StorageUser = Depends(require_user),
):
    """
    Get timeline events extracted from all uploaded documents.
    
    Returns events found in your documents, sorted chronologically.
    These events are NOT yet saved to your timeline.
    Use POST /sync-documents to add them.
    """
    hub = get_document_hub()
    events = hub.get_timeline_events(user.user_id)
    case_data = hub.get_case_data(user.user_id)
    
    # Enhance events with additional extracted data
    enhanced_events = []
    for event in events:
        enhanced_events.append({
            **event,
            "source": "document_extraction",
            "is_evidence": True,
        })
    
    # Add key dates as events
    if case_data.notice_date:
        enhanced_events.append({
            "id": "doc_notice",
            "date": case_data.notice_date,
            "title": "Eviction Notice Received",
            "description": "Notice date extracted from documents",
            "category": "notice",
            "source": "document_extraction",
            "is_evidence": True,
        })
    
    if case_data.hearing_date:
        enhanced_events.append({
            "id": "doc_hearing",
            "date": case_data.hearing_date,
            "title": "Court Hearing",
            "description": f"Hearing scheduled{' at ' + case_data.hearing_time if case_data.hearing_time else ''}",
            "category": "court",
            "source": "document_extraction",
            "is_evidence": False,
        })
    
    # Sort by date
    enhanced_events.sort(key=lambda x: x.get("date", "9999"))
    
    return {
        "events": enhanced_events,
        "total_events": len(enhanced_events),
        "documents_analyzed": case_data.document_count,
        "sync_available": len(enhanced_events) > 0,
    }


class TimelineSyncResult(BaseModel):
    """Result of syncing timeline from documents."""
    synced: int
    skipped: int
    total_timeline_events: int
    synced_event_ids: List[str]


@router.post("/sync-documents", response_model=TimelineSyncResult)
async def sync_timeline_from_documents(
    overwrite: bool = Query(False, description="Overwrite existing events with same title"),
    include_deadlines: bool = Query(True, description="Include deadline events"),
    user: StorageUser = Depends(require_user),
):
    """
    Sync timeline events from uploaded documents to your timeline.
    
    This creates timeline events from:
    - Dates mentioned in documents
    - Key dates (notice date, hearing date)
    - Action items with deadlines
    
    Events with duplicate titles are skipped unless overwrite=true.
    All synced events are marked with source='document_extraction'.
    """
    hub = get_document_hub()
    doc_events = hub.get_timeline_events(user.user_id)
    case_data = hub.get_case_data(user.user_id)
    
    synced = 0
    skipped = 0
    synced_ids = []
    
    async with get_db_session() as session:
        # Get existing event titles
        query = select(TimelineEventModel.title).where(
            TimelineEventModel.user_id == user.user_id
        )
        result = await session.execute(query)
        existing_titles = {row[0] for row in result.fetchall()}
        
        all_events = list(doc_events)
        
        # Add key dates as events
        if case_data.notice_date:
            all_events.append({
                "date": case_data.notice_date,
                "title": "Eviction Notice Received",
                "description": "Notice date extracted from documents",
                "category": "notice",
            })
        
        if case_data.hearing_date:
            all_events.append({
                "date": case_data.hearing_date,
                "title": "Court Hearing",
                "description": f"Hearing scheduled{' at ' + case_data.hearing_time if case_data.hearing_time else ''}",
                "category": "court",
            })
        
        # Add action item deadlines
        if include_deadlines:
            for action in case_data.action_items:
                if action.get("deadline"):
                    all_events.append({
                        "date": action["deadline"],
                        "title": action.get("title", "Deadline"),
                        "description": action.get("description", ""),
                        "category": "deadline",
                    })
        
        for event in all_events:
            title = event.get("title", "")
            
            # Skip if exists and not overwriting
            if title in existing_titles and not overwrite:
                skipped += 1
                continue
            
            # Delete existing if overwriting
            if title in existing_titles and overwrite:
                delete_query = select(TimelineEventModel).where(
                    and_(
                        TimelineEventModel.user_id == user.user_id,
                        TimelineEventModel.title == title
                    )
                )
                del_result = await session.execute(delete_query)
                existing_event = del_result.scalar_one_or_none()
                if existing_event:
                    await session.delete(existing_event)
            
            # Parse date
            date_str = event.get("date", "")
            try:
                event_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    event_dt = datetime.strptime(date_str, "%Y-%m-%d")
                except (ValueError, TypeError):
                    skipped += 1
                    continue
            
            # Determine event type
            category = event.get("category", "other")
            event_type_map = {
                "notice": "notice",
                "court": "court",
                "hearing": "court",
                "deadline": "court",
                "payment": "payment",
                "maintenance": "maintenance",
                "communication": "communication",
            }
            event_type = event_type_map.get(category, "other")
            
            # Create event
            event_id = str(uuid.uuid4())
            db_event = TimelineEventModel(
                id=event_id,
                user_id=user.user_id,
                event_type=event_type,
                title=title,
                description=f"[Auto-synced] {event.get('description', '')}",
                event_date=event_dt,
                document_id=event.get("document_id"),
                is_evidence=True,
                created_at=utc_now(),
            )
            session.add(db_event)
            synced += 1
            synced_ids.append(event_id)
        
        await session.commit()
        
        # Get total count
        count_query = select(func.count()).select_from(TimelineEventModel).where(
            TimelineEventModel.user_id == user.user_id
        )
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
    
    return TimelineSyncResult(
        synced=synced,
        skipped=skipped,
        total_timeline_events=total,
        synced_event_ids=synced_ids,
    )


@router.get("/combined")
async def get_combined_timeline(
    user: StorageUser = Depends(require_user),
):
    """
    Get combined timeline from database and documents.
    
    Merges saved timeline events with document-extracted events,
    showing a complete picture of your case history.
    """
    hub = get_document_hub()
    doc_events = hub.get_timeline_events(user.user_id)
    case_data = hub.get_case_data(user.user_id)
    
    combined = []
    
    # Get database events
    async with get_db_session() as session:
        query = select(TimelineEventModel).where(
            TimelineEventModel.user_id == user.user_id
        ).order_by(TimelineEventModel.event_date.asc())
        
        result = await session.execute(query)
        db_events = result.scalars().all()
        
        for event in db_events:
            combined.append({
                "id": event.id,
                "date": event.event_date.isoformat() if event.event_date else "",
                "title": event.title,
                "description": event.description,
                "category": event.event_type,
                "source": "database",
                "is_evidence": event.is_evidence,
                "document_id": event.document_id,
            })
    
    # Add document events not yet synced
    db_titles = {e["title"] for e in combined}
    for event in doc_events:
        if event.get("title") not in db_titles:
            combined.append({
                "id": event.get("id", f"doc_{uuid.uuid4().hex[:8]}"),
                "date": event.get("date", ""),
                "title": event.get("title", "Event"),
                "description": event.get("description", ""),
                "category": event.get("category", "other"),
                "source": "document_extraction",
                "is_evidence": True,
                "document_id": event.get("document_id"),
                "not_synced": True,
            })
    
    # Sort by date
    combined.sort(key=lambda x: x.get("date", "9999"))
    
    return {
        "timeline": combined,
        "total_events": len(combined),
        "synced_events": len([e for e in combined if e.get("source") == "database"]),
        "unsynced_events": len([e for e in combined if e.get("not_synced")]),
        "documents_analyzed": case_data.document_count,
    }

@router.get("/export/pdf")
async def export_timeline_pdf(
    user: StorageUser = Depends(require_user),
):
    """
    Export the user's timeline as a PDF document.
    
    Generates a formatted PDF with all timeline events, sorted chronologically.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from io import BytesIO
    
    # Get all timeline events
    async with get_db_session() as session:
        query = select(TimelineEventModel).where(
            TimelineEventModel.user_id == user.user_id
        ).order_by(TimelineEventModel.event_date.asc())
        result = await session.execute(query)
        events = result.scalars().all()
        
        # Also get document events
        doc_query = select(DocumentModel).where(
            DocumentModel.user_id == user.user_id
        )
        doc_result = await session.execute(doc_query)
        documents = doc_result.scalars().all()
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    event_title_style = ParagraphStyle(
        'EventTitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=5,
        textColor=colors.blue
    )
    
    # Build PDF content
    content = []
    
    # Title
    content.append(Paragraph("Case Timeline Export", title_style))
    content.append(Spacer(1, 12))
    
    # Summary
    total_events = len(events) + len(documents)
    content.append(Paragraph(f"Total Events: {total_events}", styles['Normal']))
    content.append(Paragraph(f"Manual Events: {len(events)}", styles['Normal']))
    content.append(Paragraph(f"Document Events: {len(documents)}", styles['Normal']))
    content.append(Spacer(1, 20))
    
    # Events table data
    table_data = [['Date', 'Type', 'Title', 'Description', 'Evidence']]
    
    # Add manual events
    for event in events:
        date_str = event.event_date.strftime('%Y-%m-%d') if event.event_date else 'No Date'
        table_data.append([
            date_str,
            event.event_type or 'other',
            event.title,
            event.description or '',
            'Yes' if event.is_evidence else 'No'
        ])
    
    # Add document events
    for doc in documents:
        date_str = doc.uploaded_at.strftime('%Y-%m-%d') if doc.uploaded_at else 'No Date'
        doc_type = doc.document_type or 'document'
        table_data.append([
            date_str,
            doc_type,
            f"Document: {doc.original_filename}",
            doc.description or f"Uploaded {doc_type}",
            'Yes'  # All documents are evidence
        ])
    
    # Create table
    if len(table_data) > 1:
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        content.append(table)
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=timeline_export.pdf'}
    )


@router.post("/share")
async def create_timeline_share_link(
    user: StorageUser = Depends(require_user),
):
    """
    Create a shareable link for the timeline.
    
    Returns a public URL that can be shared with others to view the timeline.
    The link expires after 7 days.
    """
    import secrets
    from datetime import datetime, timedelta
    
    # Generate a secure token
    share_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    # Store the share token (in a real app, this would be in a database)
    # For now, we'll use a simple in-memory store
    if not hasattr(router, 'share_tokens'):
        router.share_tokens = {}
    
    router.share_tokens[share_token] = {
        'user_id': user.user_id,
        'created_at': datetime.utcnow(),
        'expires_at': expires_at
    }
    
    # Generate the share URL
    base_url = "http://localhost:8000"  # In production, get from config
    share_url = f"{base_url}/timeline/shared/{share_token}"
    
    return {
        "share_url": share_url,
        "expires_at": expires_at.isoformat(),
        "token": share_token
    }


@router.get("/shared/{share_token}")
async def get_shared_timeline(
    share_token: str,
):
    """
    View a shared timeline (public endpoint, no auth required).
    
    Shows the timeline events for the shared case.
    """
    # Check if token exists and is valid
    if not hasattr(router, 'share_tokens') or share_token not in router.share_tokens:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    
    share_data = router.share_tokens[share_token]
    
    # Check expiration
    if datetime.utcnow() > share_data['expires_at']:
        # Clean up expired token
        del router.share_tokens[share_token]
        raise HTTPException(status_code=410, detail="Share link has expired")
    
    user_id = share_data['user_id']
    
    # Get timeline events for the shared user
    async with get_db_session() as session:
        # Get manual events
        query = select(TimelineEventModel).where(
            TimelineEventModel.user_id == user_id
        ).order_by(TimelineEventModel.event_date.asc())
        result = await session.execute(query)
        events = result.scalars().all()
        
        # Get document events
        doc_query = select(DocumentModel).where(
            DocumentModel.user_id == user_id
        )
        doc_result = await session.execute(doc_query)
        documents = doc_result.scalars().all()
    
    # Format for display
    timeline_events = []
    
    # Manual events
    for event in events:
        timeline_events.append({
            "id": event.id,
            "date": event.event_date.isoformat() if event.event_date else None,
            "type": event.event_type or "other",
            "title": event.title,
            "description": event.description,
            "is_evidence": event.is_evidence or False,
            "source": "manual"
        })
    
    # Document events
    for doc in documents:
        doc_type = doc.document_type or "document"
        timeline_events.append({
            "id": f"doc_{doc.id}",
            "date": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "type": doc_type,
            "title": f"Document: {doc.original_filename}",
            "description": doc.description or f"Uploaded {doc_type}",
            "is_evidence": True,
            "source": "document"
        })
    
    # Sort by date
    timeline_events.sort(key=lambda x: x.get("date") or "9999-99-99")
    
    return {
        "timeline": timeline_events,
        "total_events": len(timeline_events),
        "shared_by": "Anonymous",  # Could add user name if needed
        "expires_at": share_data['expires_at'].isoformat()
    }