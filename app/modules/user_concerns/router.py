"""
User Concerns Router
====================

Admin-only module for the User Concerns hub tile (support queue and flagged issues).

This first wiring pass is PII-free:
- `GET /concerns` returns an empty placeholder list.
- `GET /summary` returns only status counts (no user details).
- `POST /flag` and `POST /resolve` return 501.

When the T2 data model is designed, the real implementation will expose
admin-only tenant-submitted concerns with audit logging and retention rules.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_admin

router = APIRouter(
    prefix="/api/admin/user-concerns",
    tags=["User Concerns"],
    dependencies=[Depends(require_admin)],
)


@router.get("/health")
async def user_concerns_health() -> dict[str, Any]:
    """Admin health check for the user_concerns module."""
    return {
        "status": "ok",
        "service": "user_concerns",
        "pii_exposure": "none",
        "pending_decision": "T2 data model and retention policy",
    }


@router.get("/concerns")
async def list_concerns() -> dict[str, Any]:
    """Placeholder for the support-queue concern list.

    When implemented, this will return admin-only tenant-submitted concerns
    with T2 handling. For now it returns an empty list so no PII is exposed
    while the wiring is validated.
    """
    return {
        "concerns": [],
        "count": 0,
        "note": "support queue is a placeholder; T2 data model pending",
    }


@router.get("/summary")
async def concerns_summary() -> dict[str, Any]:
    """Placeholder summary — status buckets only, no PII."""
    return {
        "status_counts": {
            "open": 0,
            "in_progress": 0,
            "resolved": 0,
            "escalated": 0,
        },
        "note": "summary is a placeholder; T2 data model pending",
    }


@router.post("/flag")
async def flag_concern() -> dict[str, Any]:
    """Placeholder for flagging a concern.

    The real implementation will require a T2 data model and admin audit log.
    """
    raise HTTPException(status_code=501, detail="Flag concern not yet implemented")


@router.post("/resolve")
async def resolve_concern() -> dict[str, Any]:
    """Placeholder for resolving a concern.

    The real implementation will require a T2 data model and admin audit log.
    """
    raise HTTPException(status_code=501, detail="Resolve concern not yet implemented")
