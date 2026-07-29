"""Dispute Tracker router — scaffold only.

T2 tenant-facing module. Full routes (list, add, compare) will be wired
in subsequent commits.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.security import get_current_user

router = APIRouter(
    prefix="/api/dispute-tracker",
    tags=["Dispute Tracker"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/health")
async def dispute_tracker_health() -> dict[str, Any]:
    """Module health check."""
    return {"status": "ok", "module": "dispute_tracker"}
