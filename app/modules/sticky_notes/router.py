"""
Sticky Notes Router
===================
API surface for the tenant scratch-pad:
  - POST   /api/sticky-notes         create a note
  - GET    /api/sticky-notes         list notes
  - PATCH  /api/sticky-notes/{id}    update a note
  - DELETE /api/sticky-notes/{id}    delete a note

Also serves the notepad page at /record/notes.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.core.capabilities import require_capability
from app.core.security import yellow_access
from app.core.user_context import UserContext
from app.modules.sticky_notes import service as sticky_notes_service

logger = logging.getLogger(__name__)


capability_key = "app.modules.sticky_notes.router"

router = APIRouter(
    dependencies=[Depends(require_capability(capability_key))],
)


# =============================================================================
# Schemas
# =============================================================================


class StickyNoteCreate(BaseModel):
    """Create a sticky note."""

    text: str = Field(..., min_length=1, description="Note body text")
    source: str | None = Field(default=None, description="Optional source reference")


class StickyNoteUpdate(BaseModel):
    """Update a sticky note."""

    text: str = Field(..., min_length=1, description="Updated note body text")


class StickyNoteResponse(BaseModel):
    """Sticky note JSON response."""

    id: str
    text: str
    source: str | None
    created_at: str
    updated_at: str


def _overlay_to_response(overlay) -> StickyNoteResponse:
    """Convert a UnifiedOverlay to a clean API response."""
    return StickyNoteResponse(
        id=overlay.overlay_id,
        text=overlay.payload.get("text", ""),
        source=overlay.payload.get("source") or overlay.metadata.get("source") or None,
        created_at=overlay.created_at.isoformat() if overlay.created_at else "",
        updated_at=overlay.updated_at.isoformat() if overlay.updated_at else "",
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.post(
    "/api/sticky-notes",
    response_model=StickyNoteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Sticky Notes"],
)
async def create_note(
    request: StickyNoteCreate,
    user: UserContext = Depends(yellow_access),
):
    """Create a new sticky note in the user's scratch-pad."""
    overlay = await sticky_notes_service.create_sticky_note(
        user=user,
        text=request.text,
        source=request.source,
    )
    return _overlay_to_response(overlay)


@router.get(
    "/api/sticky-notes",
    response_model=list[StickyNoteResponse],
    tags=["Sticky Notes"],
)
async def list_notes(
    user: UserContext = Depends(yellow_access),
):
    """Return the user's sticky notes, newest first."""
    overlays = await sticky_notes_service.list_sticky_notes(user)
    return [_overlay_to_response(o) for o in overlays]


@router.patch(
    "/api/sticky-notes/{note_id}",
    response_model=StickyNoteResponse,
    tags=["Sticky Notes"],
)
async def update_note(
    note_id: str,
    request: StickyNoteUpdate,
    user: UserContext = Depends(yellow_access),
):
    """Update a sticky note's text."""
    overlay = await sticky_notes_service.update_sticky_note(
        user=user,
        overlay_id=note_id,
        text=request.text,
    )
    if not overlay:
        raise HTTPException(status_code=404, detail="Sticky note not found")
    refreshed = await sticky_notes_service.list_sticky_notes(user)
    for o in refreshed:
        if o.overlay_id == note_id:
            return _overlay_to_response(o)
    raise HTTPException(status_code=500, detail="Note updated but could not be re-read")


@router.delete(
    "/api/sticky-notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Sticky Notes"],
)
async def delete_note(
    note_id: str,
    user: UserContext = Depends(yellow_access),
):
    """Delete a sticky note."""
    success = await sticky_notes_service.delete_sticky_note(user, note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sticky note not found")
    return None


# =============================================================================
# Page
# =============================================================================


@router.get(
    "/record/notes",
    response_class=HTMLResponse,
    tags=["Sticky Notes"],
)
async def notes_page(
    request: Request,
    user: UserContext = Depends(yellow_access),
):
    """Render the notepad page in the Record area."""
    from app.main import templates

    overlays = await sticky_notes_service.list_sticky_notes(user)
    notes = [_overlay_to_response(o) for o in overlays]
    return templates.TemplateResponse(
        request,
        "pages/sticky_notes.html",
        {
            "request": request,
            "user": user,
            "notes": notes,
        },
    )
