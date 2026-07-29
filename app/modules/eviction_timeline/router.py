"""Eviction Timeline router — scaffold only.

T2 tenant-facing module. Full routes (list, add event) wired in later
commits. `subject_id` is a placeholder with no FK.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.security import get_current_user

router = APIRouter(
    prefix="/api/eviction-timeline",
    tags=["Eviction Timeline"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/health")
async def eviction_timeline_health() -> dict[str, Any]:
    """Module health check."""
    return {"status": "ok", "module": "eviction_timeline"}
