"""
Journal router — free-form tenant records.

Endpoints:
- POST   /api/journal              — Create a journal entry
- GET    /api/journal              — List current user's entries
- GET    /api/journal/summary     — Brief summary for dashboards
- GET    /api/journal/{entry_id}  — Get a single entry
- PUT    /api/journal/{entry_id}  — Update an entry
- DELETE /api/journal/{entry_id}  — Delete an entry
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import get_db_session
from app.core.event_bus import EventType, event_bus
from app.core.security import can_access, require_user
from app.core.user_context import UserContext
from app.core.utc import utc_now
from app.models.unified_overlay_models import UnifiedOverlay
from app.modules.journal import service


async def _validate_access(user: UserContext, target_user_id: str) -> None:
    """Validate that the current user can access target_user_id's resources."""
    if user.user_id == target_user_id:
        return
    if user.is_impersonating and user.acting_as == target_user_id:
        async with get_db_session() as db:
            allowed = await can_access(user.user_id, target_user_id, db)
            if not allowed:
                raise HTTPException(status_code=403, detail="Access denied: no active relationship")
        return
    raise HTTPException(status_code=403, detail="Access denied")


router = APIRouter()


VALID_ENTRY_TYPES = {"note", "conversation", "incident", "repair_request", "other"}


def _parse_iso(dt_str: str | None) -> datetime | None:
    """Parse an ISO datetime string to a timezone-aware datetime."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {dt_str}")


def _tags_to_str(tags: list[str] | None) -> str | None:
    if not tags:
        return None
    return ",".join(t.strip() for t in tags if t.strip())


def _tags_from_str(tags_str: str | None) -> list[str]:
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


class JournalEntryCreate(BaseModel):
    """Create a journal entry."""

    entry_type: str = Field(..., description="note, conversation, incident, repair_request, or other")
    title: str = Field(..., min_length=1, max_length=255)
    content: str | None = None
    occurred_at: str | None = Field(None, description="ISO datetime; defaults to now")
    is_urgent: bool = False
    involved_party: str | None = Field(None, max_length=255, description="e.g. landlord, manager, neighbor")
    tags: list[str] | None = None
    document_link: str | None = Field(None, max_length=36, description="Optional vault document ID")


class JournalEntryUpdate(BaseModel):
    """Update a journal entry."""

    entry_type: str | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None
    occurred_at: str | None = None
    is_urgent: bool | None = None
    involved_party: str | None = Field(None, max_length=255)
    tags: list[str] | None = None
    document_link: str | None = Field(None, max_length=36)


class JournalEntryResponse(BaseModel):
    """Journal entry response."""

    id: str
    entry_type: str
    title: str
    content: str | None = None
    occurred_at: str
    is_urgent: bool
    involved_party: str | None = None
    tags: list[str] = Field(default_factory=list)
    document_link: str | None = None
    source: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class JournalListResponse(BaseModel):
    """List of journal entries."""

    entries: list[JournalEntryResponse]
    total: int


class JournalSummaryResponse(BaseModel):
    """Dashboard summary of journal entries."""

    total_entries: int
    urgent_entries: int
    recent_entries: list[JournalEntryResponse]


def _to_response(entry: UnifiedOverlay) -> JournalEntryResponse:
    """Convert a journal overlay to a response model."""
    p = entry.payload
    return JournalEntryResponse(
        id=entry.overlay_id,
        entry_type=p.get("entry_type") or "note",
        title=p.get("title") or "",
        content=p.get("content"),
        occurred_at=p.get("occurred_at") or "",
        is_urgent=bool(p.get("is_urgent")),
        involved_party=p.get("involved_party"),
        tags=_tags_from_str(p.get("tags")),
        document_link=p.get("document_link"),
        source=p.get("source") or "manual",
        created_at=entry.created_at.isoformat() if entry.created_at else "",
        updated_at=entry.updated_at.isoformat() if entry.updated_at else "",
    )


@router.post("/", response_model=JournalEntryResponse)
async def create_entry(
    body: JournalEntryCreate,
    user: UserContext = Depends(require_user),
):
    """Create a new journal entry."""
    await _validate_access(user, user.get_effective_user_id())

    entry_type = body.entry_type.lower().strip()
    if entry_type not in VALID_ENTRY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entry_type. Must be one of: {', '.join(sorted(VALID_ENTRY_TYPES))}",
        )

    occurred_at = _parse_iso(body.occurred_at) or utc_now()

    entry = await service.create_entry(
        user,
        entry_type=entry_type,
        title=body.title.strip(),
        content=body.content,
        occurred_at=occurred_at,
        is_urgent=body.is_urgent,
        involved_party=body.involved_party,
        tags=_tags_to_str(body.tags),
        document_link=body.document_link,
        source="manual",
    )

    event_bus.publish_sync(
        EventType.JOURNAL_ENTRY_CREATED,
        {
            "user_id": user.get_effective_user_id(),
            "entry_id": entry.overlay_id,
            "entry_type": entry_type,
            "is_urgent": body.is_urgent,
            "narrator": {
                "module": "app.modules.journal",
                "slot": 1 if body.is_urgent else 0,
            },
        },
    )

    return _to_response(entry)


@router.get("/", response_model=JournalListResponse)
async def list_entries(
    entry_type: str | None = None,
    is_urgent: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: UserContext = Depends(require_user),
):
    """List journal entries for the current user, newest first."""
    await _validate_access(user, user.get_effective_user_id())
    entries, total = await service.list_entries(
        user,
        entry_type=entry_type.lower().strip() if entry_type else None,
        is_urgent=is_urgent,
        skip=skip,
        limit=limit,
    )
    return JournalListResponse(entries=[_to_response(e) for e in entries], total=total)


@router.get("/summary", response_model=JournalSummaryResponse)
async def get_summary(
    user: UserContext = Depends(require_user),
):
    """Return a brief dashboard summary of journal entries."""
    await _validate_access(user, user.get_effective_user_id())
    entries, total = await service.list_entries(user, limit=200)

    return JournalSummaryResponse(
        total_entries=total,
        urgent_entries=sum(1 for e in entries if e.payload.get("is_urgent")),
        recent_entries=[_to_response(e) for e in entries[:5]],
    )


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_entry(
    entry_id: str,
    user: UserContext = Depends(require_user),
):
    """Get a single journal entry by ID."""
    await _validate_access(user, user.get_effective_user_id())
    entry = await service.get_entry(user, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    return _to_response(entry)


@router.put("/{entry_id}", response_model=JournalEntryResponse)
async def update_entry(
    entry_id: str,
    body: JournalEntryUpdate,
    user: UserContext = Depends(require_user),
):
    """Update a journal entry."""
    await _validate_access(user, user.get_effective_user_id())

    fields: dict = {}
    if body.entry_type is not None:
        entry_type = body.entry_type.lower().strip()
        if entry_type not in VALID_ENTRY_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entry_type. Must be one of: {', '.join(sorted(VALID_ENTRY_TYPES))}",
            )
        fields["entry_type"] = entry_type
    if body.title is not None:
        fields["title"] = body.title.strip()
    if body.content is not None:
        fields["content"] = body.content
    if body.occurred_at is not None:
        parsed = _parse_iso(body.occurred_at)
        if parsed:
            fields["occurred_at"] = parsed.isoformat()
    if body.is_urgent is not None:
        fields["is_urgent"] = body.is_urgent
    if body.involved_party is not None:
        fields["involved_party"] = body.involved_party
    if body.tags is not None:
        fields["tags"] = _tags_to_str(body.tags)
    if body.document_link is not None:
        fields["document_link"] = body.document_link

    entry = await service.update_entry(user, entry_id, fields)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    return _to_response(entry)


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: str,
    user: UserContext = Depends(require_user),
):
    """Delete a journal entry."""
    await _validate_access(user, user.get_effective_user_id())
    deleted = await service.delete_entry(user, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    return {"success": True, "deleted": entry_id}
