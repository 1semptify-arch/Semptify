"""Eviction Timeline router — list + add event page and API.

T2 tenant-facing module. `subject_id` is a placeholder with no FK.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.database import get_db
from app.core.id_gen import make_id
from app.core.navigation import navigation
from app.core.security import UserContext, require_tier
from app.core.ssot_guard import ssot_redirect
from app.core.utc import utc_now
from app.models.models import EvictionTimelineEvent

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(
    tags=["Eviction Timeline"],
)


def _user_id(user: UserContext | None) -> str | None:
    return user.user_id if user else None


@router.get("/health", dependencies=[Depends(require_tier("T2"))])
async def eviction_timeline_health() -> dict[str, Any]:
    """Module health check."""
    return {"status": "ok", "module": "eviction_timeline"}


@router.get("/", response_class=HTMLResponse)
async def eviction_timeline_page(
    request: Request,
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Render the eviction timeline page (add event + list)."""
    from app.main import templates

    result = await db.execute(
        select(EvictionTimelineEvent)
        .where(EvictionTimelineEvent.user_id == _user_id(user))
        .order_by(EvictionTimelineEvent.event_date.desc())
    )
    events = result.scalars().all()

    return templates.TemplateResponse(
        "pages/eviction_timeline.html",
        {
            "request": request,
            "events": events,
            "user": user,
        },
    )


@router.post("/events")
async def create_eviction_event(
    request: Request,
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
    subject_id: str = Form(""),
    event_type: str = Form(...),
    event_date: str = Form(...),
    source: str = Form("manual"),
    jurisdiction: str = Form("MN"),
) -> Any:
    """Create a new eviction timeline event and redirect back to the page."""
    parsed_date = None
    if event_date:
        try:
            parsed_date = datetime.fromisoformat(event_date).replace(tzinfo=UTC)
        except ValueError:
            parsed_date = None

    if parsed_date is None:
        parsed_date = utc_now()

    event = EvictionTimelineEvent(
        id=make_id("ete"),
        user_id=_user_id(user),
        subject_id=subject_id or None,
        event_type=event_type,
        event_date=parsed_date,
        source=source,
        jurisdiction=jurisdiction,
        created_at=utc_now().replace(tzinfo=None),
        updated_at=utc_now().replace(tzinfo=None),
    )
    db.add(event)
    await db.commit()
    return ssot_redirect(navigation.get_stage("eviction_timeline_home").path, context="create eviction timeline event")
