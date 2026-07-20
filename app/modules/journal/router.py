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
from sqlalchemy import select

from app.core.database import get_db_session
from app.core.id_gen import make_id
from app.core.security import can_access, require_user
from app.core.user_context import UserContext
from app.core.utc import utc_now
from app.models.models import JournalEntry as JournalEntryModel


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


def _to_response(entry: JournalEntryModel) -> JournalEntryResponse:
    """Convert a JournalEntry model row to a response model."""
    return JournalEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type,
        title=entry.title,
        content=entry.content,
        occurred_at=entry.occurred_at.isoformat() if entry.occurred_at else "",
        is_urgent=entry.is_urgent or False,
        involved_party=entry.involved_party,
        tags=_tags_from_str(entry.tags),
        document_link=entry.document_link,
        source=entry.source or "manual",
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

    entry = JournalEntryModel(
        id=make_id("jrn"),
        user_id=user.get_effective_user_id(),
        entry_type=entry_type,
        title=body.title.strip(),
        content=body.content,
        occurred_at=occurred_at,
        is_urgent=body.is_urgent,
        involved_party=body.involved_party,
        tags=_tags_to_str(body.tags),
        document_link=body.document_link,
        source="manual",
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    async with get_db_session() as db:
        db.add(entry)
        await db.commit()

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
    async with get_db_session() as db:
        query = select(JournalEntryModel).where(
            JournalEntryModel.user_id == user.get_effective_user_id()
        )
        if entry_type:
            query = query.where(JournalEntryModel.entry_type == entry_type.lower().strip())
        if is_urgent is not None:
            query = query.where(JournalEntryModel.is_urgent == is_urgent)
        query = query.order_by(JournalEntryModel.occurred_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        entries = list(result.scalars().all())

        total_result = await db.execute(
            select(JournalEntryModel).where(JournalEntryModel.user_id == user.get_effective_user_id())
        )
        total = len(list(total_result.scalars().all()))

    return JournalListResponse(entries=[_to_response(e) for e in entries], total=total)


@router.get("/summary", response_model=JournalSummaryResponse)
async def get_summary(
    user: UserContext = Depends(require_user),
):
    """Return a brief dashboard summary of journal entries."""
    await _validate_access(user, user.get_effective_user_id())
    async with get_db_session() as db:
        result = await db.execute(
            select(JournalEntryModel)
            .where(JournalEntryModel.user_id == user.get_effective_user_id())
            .order_by(JournalEntryModel.occurred_at.desc())
        )
        entries = list(result.scalars().all())

    return JournalSummaryResponse(
        total_entries=len(entries),
        urgent_entries=sum(1 for e in entries if e.is_urgent),
        recent_entries=[_to_response(e) for e in entries[:5]],
    )


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_entry(
    entry_id: str,
    user: UserContext = Depends(require_user),
):
    """Get a single journal entry by ID."""
    await _validate_access(user, user.get_effective_user_id())
    async with get_db_session() as db:
        result = await db.execute(
            select(JournalEntryModel).where(
                JournalEntryModel.id == entry_id,
                JournalEntryModel.user_id == user.get_effective_user_id(),
            )
        )
        entry = result.scalar_one_or_none()

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
    async with get_db_session() as db:
        result = await db.execute(
            select(JournalEntryModel).where(
                JournalEntryModel.id == entry_id,
                JournalEntryModel.user_id == user.get_effective_user_id(),
            )
        )
        entry = result.scalar_one_or_none()

        if not entry:
            raise HTTPException(status_code=404, detail="Journal entry not found")

        if body.entry_type is not None:
            entry_type = body.entry_type.lower().strip()
            if entry_type not in VALID_ENTRY_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid entry_type. Must be one of: {', '.join(sorted(VALID_ENTRY_TYPES))}",
                )
            entry.entry_type = entry_type
        if body.title is not None:
            entry.title = body.title.strip()
        if body.content is not None:
            entry.content = body.content
        if body.occurred_at is not None:
            entry.occurred_at = _parse_iso(body.occurred_at) or entry.occurred_at
        if body.is_urgent is not None:
            entry.is_urgent = body.is_urgent
        if body.involved_party is not None:
            entry.involved_party = body.involved_party
        if body.tags is not None:
            entry.tags = _tags_to_str(body.tags)
        if body.document_link is not None:
            entry.document_link = body.document_link
        entry.updated_at = utc_now()

        await db.commit()

    return _to_response(entry)


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: str,
    user: UserContext = Depends(require_user),
):
    """Delete a journal entry."""
    await _validate_access(user, user.get_effective_user_id())
    async with get_db_session() as db:
        result = await db.execute(
            select(JournalEntryModel).where(
                JournalEntryModel.id == entry_id,
                JournalEntryModel.user_id == user.get_effective_user_id(),
            )
        )
        entry = result.scalar_one_or_none()

        if not entry:
            raise HTTPException(status_code=404, detail="Journal entry not found")

        await db.delete(entry)
        await db.commit()

    return {"success": True, "deleted": entry_id}
