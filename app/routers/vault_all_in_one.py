"""
ALL-IN-ONE Unified Evidence Vault — API Router

REST API endpoints for the unified evidence vault.

Endpoints:
- POST /vault/items — Ingest new evidence
- GET /vault/items — Search vault with filtering
- GET /vault/items/{item_id} — Get single item
- PUT /vault/items/{item_id} — Update item
- DELETE /vault/items/{item_id} — Delete item
- GET /vault/timeline — Get timeline view
- POST /vault/incidents — Create incident
- GET /vault/incidents — List incidents
- GET /vault/incidents/{incident_id}/timeline — Incident timeline

All endpoints follow the three-timestamp model and data contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_user_id
from app.services.vault_ingestion import (
    VaultIngestionService,
    IngestionRequest,
    VaultIngestionError,
)
from app.services.vault_search import (
    VaultSearchService,
    SearchCriteria,
    TimelineMode,
    SortOrder,
)
from app.models.models import VaultItem, Incident

router = APIRouter(prefix="/vault", tags=["vault"])


# =============================================================================
# Request/Response Models
# =============================================================================

class VaultItemIngestRequest(BaseModel):
    """Request model for ingesting vault item (enforces data contract)."""
    
    item_type: str = Field(..., description="Document type: lease, notice, photo, email, audio, etc.")
    
    # THREE TIMESTAMPS (REQUIRED)
    event_time: datetime = Field(..., description="Factual time of event occurrence")
    record_time: datetime = Field(..., description="When evidence was created/recorded")
    
    # Metadata (REQUIRED - never null)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Complete preserved metadata (EXIF, headers, extracted fields)"
    )
    
    # Optional fields
    folder: Optional[str] = Field(None, description="Virtual folder path within vault")
    tags: Optional[list[str]] = Field(None, description="Array of searchable tags")
    related_incident_id: Optional[int] = Field(None, description="ID of related incident/case")
    source: Optional[str] = Field(None, description="Source of evidence: upload, email, portal")
    severity: Optional[str] = Field("normal", description="critical, high, normal, low")
    status: Optional[str] = Field("pending", description="pending, verified, disputed, archived")
    file_path: Optional[str] = Field(None, description="Path to stored file in cloud storage")
    title: Optional[str] = Field(None, description="Item title")
    summary: Optional[str] = Field(None, description="AI-generated or user-provided summary")
    location_data: Optional[dict[str, Any]] = Field(None, description="GPS, address, coordinates")


class VaultItemUpdateRequest(BaseModel):
    """Request model for updating vault item (immutable fields protected)."""
    
    folder: Optional[str] = None
    tags: Optional[list[str]] = None
    related_incident_id: Optional[int] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    location_data: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None  # Will be merged, not replaced


class VaultItemResponse(BaseModel):
    """Response model for vault item (includes all three timestamps)."""
    
    item_id: int
    user_id: str
    
    # THREE TIMESTAMPS
    event_time: datetime
    record_time: datetime
    semptify_entry_time: datetime
    
    # Classification
    item_type: str
    folder: Optional[str]
    tags: Optional[list[str]]
    
    # Context
    related_incident_id: Optional[int]
    source: Optional[str]
    severity: Optional[str]
    status: Optional[str]
    
    # Metadata
    metadata: dict[str, Any]
    location_data: Optional[dict[str, Any]]
    
    # Content
    file_path: Optional[str]
    title: Optional[str]
    summary: Optional[str]
    
    # System timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VaultSearchRequest(BaseModel):
    """Request model for vault search."""
    
    query: Optional[str] = Field(None, description="General text search across title, summary")
    metadata_query: Optional[str] = Field(None, description="Deep search in JSONB metadata")
    item_type: Optional[str | list[str]] = Field(None, description="Filter by item type(s)")
    folder: Optional[str] = Field(None, description="Filter by folder")
    tags: Optional[list[str]] = Field(None, description="Filter by tags (all must match)")
    related_incident_id: Optional[int] = Field(None, description="Filter by incident")
    severity: Optional[str | list[str]] = Field(None, description="Filter by severity")
    status: Optional[str | list[str]] = Field(None, description="Filter by status")
    source: Optional[str] = Field(None, description="Filter by source")
    date_from: Optional[datetime] = Field(None, description="Start date for range filter")
    date_to: Optional[datetime] = Field(None, description="End date for range filter")
    timeline_mode: str = Field("event_time", description="event_time, record_time, semptify_entry_time")
    sort_order: str = Field("desc", description="asc or desc")
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


class VaultSearchResponse(BaseModel):
    """Response model for vault search."""
    
    items: list[VaultItemResponse]
    total_count: int
    has_more: bool
    timeline_sequence: list[dict[str, Any]]


class IncidentCreateRequest(BaseModel):
    """Request model for creating incident."""
    
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    incident_type: Optional[str] = Field(None, description="habitability, discrimination, eviction, etc.")
    severity: Optional[str] = Field(None, description="critical, high, normal, low")
    metadata: Optional[dict[str, Any]] = None


class IncidentResponse(BaseModel):
    """Response model for incident."""
    
    incident_id: int
    user_id: str
    title: str
    description: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    status: str
    incident_type: Optional[str]
    severity: Optional[str]
    metadata: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    item_count: int = 0  # Computed field
    
    class Config:
        from_attributes = True


class TimelineResponse(BaseModel):
    """Response model for timeline queries."""
    
    items: list[VaultItemResponse]
    timeline_mode: str
    total_count: int
    sequence: list[dict[str, Any]]


# =============================================================================
# API Endpoints — Vault Items
# =============================================================================

@router.post("/items", response_model=VaultItemResponse)
async def ingest_vault_item(
    request: VaultItemIngestRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Ingest a new item into the unified vault.
    
    Enforces:
    - Data contract (metadata preservation)
    - Three-timestamp model (event_time, record_time, semptify_entry_time)
    - Complete audit logging
    
    Example:
        POST /vault/items
        {
            "item_type": "notice",
            "event_time": "2026-01-15T10:30:00Z",
            "record_time": "2026-01-15T10:30:00Z",
            "metadata": {
                "notice_type": "pay_or_quit",
                "amount_due": 1500.00
            },
            "title": "3-Day Pay or Quit Notice",
            "severity": "critical"
        }
    """
    service = VaultIngestionService(db)
    
    ingestion_request = IngestionRequest(
        user_id=user_id,
        item_type=request.item_type,
        event_time=request.event_time,
        record_time=request.record_time,
        metadata=request.metadata,
        folder=request.folder,
        tags=request.tags,
        related_incident_id=request.related_incident_id,
        source=request.source,
        severity=request.severity,
        status=request.status,
        file_path=request.file_path,
        title=request.title,
        summary=request.summary,
        location_data=request.location_data,
    )
    
    result = await service.ingest(ingestion_request, action_context="api.post_items")
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)
    
    # Refresh to get complete object
    await db.refresh(result.item)
    
    return VaultItemResponse.model_validate(result.item)


@router.get("/items", response_model=VaultSearchResponse)
async def search_vault_items(
    query: Optional[str] = Query(None, description="General text search"),
    metadata_query: Optional[str] = Query(None, description="Deep metadata search"),
    item_type: Optional[str] = Query(None, description="Filter by type"),
    folder: Optional[str] = Query(None, description="Filter by folder"),
    related_incident_id: Optional[int] = Query(None, description="Filter by incident"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    timeline_mode: str = Query("event_time", description="event_time, record_time, semptify_entry_time"),
    sort_order: str = Query("desc", description="asc or desc"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Search vault items with filtering and timeline ordering.
    
    Features:
    - Deep metadata search via JSONB GIN indexes
    - Timeline ordering by any of three timestamps
    - Multi-criteria filtering
    
    Example:
        GET /vault/items?item_type=notice&severity=critical&timeline_mode=event_time
    """
    service = VaultSearchService(db)
    
    criteria = SearchCriteria(
        query=query,
        metadata_query=metadata_query,
        item_type=item_type.split(",") if item_type and "," in item_type else item_type,
        folder=folder,
        related_incident_id=related_incident_id,
        severity=severity,
        status=status,
        date_from=date_from,
        date_to=date_to,
        timeline_mode=TimelineMode(timeline_mode),
        sort_order=SortOrder(sort_order),
        offset=offset,
        limit=limit,
    )
    
    result = await service.search(user_id, criteria)
    
    return VaultSearchResponse(
        items=[VaultItemResponse.model_validate(item) for item in result.items],
        total_count=result.total_count,
        has_more=result.has_more,
        timeline_sequence=result.timeline_sequence,
    )


@router.post("/items/search", response_model=VaultSearchResponse)
async def advanced_search_vault_items(
    request: VaultSearchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Advanced vault search with POST body for complex queries.
    
    Use this when query parameters become too long or complex.
    """
    service = VaultSearchService(db)
    
    criteria = SearchCriteria(
        query=request.query,
        metadata_query=request.metadata_query,
        item_type=request.item_type,
        folder=request.folder,
        tags=request.tags,
        related_incident_id=request.related_incident_id,
        severity=request.severity,
        status=request.status,
        source=request.source,
        date_from=request.date_from,
        date_to=request.date_to,
        timeline_mode=TimelineMode(request.timeline_mode),
        sort_order=SortOrder(request.sort_order),
        offset=request.offset,
        limit=request.limit,
    )
    
    result = await service.search(user_id, criteria)
    
    return VaultSearchResponse(
        items=[VaultItemResponse.model_validate(item) for item in result.items],
        total_count=result.total_count,
        has_more=result.has_more,
        timeline_sequence=result.timeline_sequence,
    )


@router.get("/items/{item_id}", response_model=VaultItemResponse)
async def get_vault_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Get a single vault item by ID."""
    from sqlalchemy import select
    
    result = await db.execute(
        select(VaultItem).where(
            VaultItem.item_id == item_id,
            VaultItem.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Vault item {item_id} not found")
    
    return VaultItemResponse.model_validate(item)


@router.put("/items/{item_id}", response_model=VaultItemResponse)
async def update_vault_item(
    item_id: int,
    request: VaultItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Update vault item (immutable fields protected).
    
    Immutable fields (cannot be updated):
    - item_id, user_id
    - event_time, record_time, semptify_entry_time (three timestamps)
    - created_at
    
    All updates are logged to audit_log with before/after states.
    """
    service = VaultIngestionService(db)
    
    # Build updates dict from non-None fields
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    
    result = await service.update_item(
        item_id=item_id,
        user_id=user_id,
        updates=updates,
        action_context="api.put_items",
    )
    
    if not result.success:
        if "not found" in (result.error_message or "").lower():
            raise HTTPException(status_code=404, detail=result.error_message)
        raise HTTPException(status_code=400, detail=result.error_message)
    
    await db.refresh(result.item)
    return VaultItemResponse.model_validate(result.item)


@router.delete("/items/{item_id}")
async def delete_vault_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Delete vault item (with audit logging).
    
    Note: This is a hard delete. Item and its audit logs are removed.
    Consider archiving instead for production systems.
    """
    service = VaultIngestionService(db)
    
    result = await service.delete_item(
        item_id=item_id,
        user_id=user_id,
        action_context="api.delete_items",
    )
    
    if not result.success:
        if "not found" in (result.error_message or "").lower():
            raise HTTPException(status_code=404, detail=result.error_message)
        raise HTTPException(status_code=400, detail=result.error_message)
    
    return {"success": True, "item_id": item_id, "message": "Item deleted"}


# =============================================================================
# API Endpoints — Timeline Views
# =============================================================================

@router.get("/timeline", response_model=TimelineResponse)
async def get_vault_timeline(
    timeline_mode: str = Query("event_time", description="event_time, record_time, semptify_entry_time"),
    item_type: Optional[str] = Query(None, description="Filter by type"),
    related_incident_id: Optional[int] = Query(None, description="Filter by incident"),
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Get timeline view of vault items.
    
    Timeline modes (three-timestamp model):
    - event_time: Order by when events actually occurred
    - record_time: Order by when evidence was created
    - semptify_entry_time: Order by when items were added to Semptify
    
    Each item includes all three timestamps for UI display.
    """
    service = VaultSearchService(db)
    
    criteria = SearchCriteria(
        item_type=item_type,
        related_incident_id=related_incident_id,
        date_from=date_from,
        date_to=date_to,
        timeline_mode=TimelineMode(timeline_mode),
        sort_order=SortOrder.ASC,  # Timeline is chronological
        limit=limit,
    )
    
    result = await service.search(user_id, criteria)
    
    return TimelineResponse(
        items=[VaultItemResponse.model_validate(item) for item in result.items],
        timeline_mode=timeline_mode,
        total_count=result.total_count,
        sequence=result.timeline_sequence,
    )


# =============================================================================
# API Endpoints — Incidents
# =============================================================================

@router.post("/incidents", response_model=IncidentResponse)
async def create_incident(
    request: IncidentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Create a new incident/case for organizing related evidence."""
    
    incident = Incident(
        user_id=user_id,
        title=request.title,
        description=request.description,
        start_date=request.start_date,
        end_date=request.end_date,
        incident_type=request.incident_type,
        severity=request.severity,
        metadata=request.metadata,
        status="active",
    )
    
    db.add(incident)
    await db.flush()
    await db.refresh(incident)
    
    return IncidentResponse.model_validate(incident)


@router.get("/incidents", response_model=list[IncidentResponse])
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    incident_type: Optional[str] = Query(None, description="Filter by type"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """List all incidents for the user."""
    from sqlalchemy import select, func
    
    query = select(Incident).where(Incident.user_id == user_id)
    
    if status:
        query = query.where(Incident.status == status)
    if incident_type:
        query = query.where(Incident.incident_type == incident_type)
    
    query = query.order_by(Incident.created_at.desc())
    
    result = await db.execute(query)
    incidents = result.scalars().all()
    
    # Calculate item count for each incident
    response_incidents = []
    for incident in incidents:
        # Count items
        count_result = await db.execute(
            select(func.count())
            .select_from(VaultItem)
            .where(VaultItem.related_incident_id == incident.incident_id)
        )
        item_count = count_result.scalar() or 0
        
        resp = IncidentResponse.model_validate(incident)
        resp.item_count = item_count
        response_incidents.append(resp)
    
    return response_incidents


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Get a single incident with item count."""
    from sqlalchemy import select, func
    
    result = await db.execute(
        select(Incident).where(
            Incident.incident_id == incident_id,
            Incident.user_id == user_id,
        )
    )
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    
    # Count items
    count_result = await db.execute(
        select(func.count())
        .select_from(VaultItem)
        .where(VaultItem.related_incident_id == incident_id)
    )
    item_count = count_result.scalar() or 0
    
    resp = IncidentResponse.model_validate(incident)
    resp.item_count = item_count
    return resp


@router.get("/incidents/{incident_id}/timeline", response_model=TimelineResponse)
async def get_incident_timeline(
    incident_id: int,
    timeline_mode: str = Query("event_time", description="event_time, record_time, semptify_entry_time"),
    limit: int = Query(1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Get timeline of all vault items for a specific incident.
    
    This groups related evidence into a coherent chronological narrative.
    """
    service = VaultSearchService(db)
    
    result = await service.get_timeline_by_incident(
        user_id=user_id,
        incident_id=incident_id,
        timeline_mode=TimelineMode(timeline_mode),
    )
    
    return TimelineResponse(
        items=[VaultItemResponse.model_validate(item) for item in result.items],
        timeline_mode=timeline_mode,
        total_count=result.total_count,
        sequence=result.timeline_sequence,
    )


# =============================================================================
# API Endpoints — Deep Search
# =============================================================================

@router.get("/search/metadata")
async def search_by_metadata(
    field: str = Query(..., description="Metadata field name"),
    value: str = Query(..., description="Value to search for"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Deep search by specific metadata field value.
    
    Example:
        GET /vault/search/metadata?field=landlord&value=ABC%20Management
    """
    service = VaultSearchService(db)
    
    result = await service.deep_metadata_search(
        user_id=user_id,
        metadata_field=field,
        value=value,
    )
    
    return {
        "items": [VaultItemResponse.model_validate(item) for item in result.items],
        "total_count": result.total_count,
        "search": {"field": field, "value": value},
    }


@router.get("/search/location")
async def search_by_location(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: float = Query(1000, description="Radius in meters"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Search for items near a geographic location.
    
    Requires items to have location_data.gps.lat/lon fields.
    
    Note: Production systems should use PostGIS for proper geo queries.
    """
    service = VaultSearchService(db)
    
    result = await service.location_search(
        user_id=user_id,
        lat=lat,
        lon=lon,
        radius_meters=radius,
    )
    
    return {
        "items": [VaultItemResponse.model_validate(item) for item in result.items],
        "total_count": result.total_count,
        "search": {"lat": lat, "lon": lon, "radius_meters": radius},
    }
