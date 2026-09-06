"""
System Health & Updates Router
==============================

Admin-only API for the System Health & Updates hub tile.

Routes:
- GET /api/admin/system/health        — lightweight liveness/status
- GET /api/admin/system/registry      — registry summary (counts by status)
- POST /api/admin/system/verify       — trigger async registry sync+verify

This module intentionally does NOT expose PII. All responses are system-level
metadata (version, module counts, verification status).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.module_registry_loader import load_registry
from app.core.product_manifest import MANIFEST
from app.core.security import require_admin
from app.core.utc import utc_now

router = APIRouter(
    tags=["System Health"],
    dependencies=[Depends(require_admin)],
)


@router.get("/health")
async def system_health() -> dict[str, Any]:
    """Lightweight liveness check for the system-health tile."""
    manifest_summary = MANIFEST.summary()
    return {
        "status": "ok",
        "service": "system_health",
        "timestamp": utc_now().isoformat(),
        "manifest": {
            "total_modules": manifest_summary.get("total", 0),
            "by_tier": manifest_summary.get("by_tier", {}),
        },
    }


@router.get("/registry")
async def registry_summary() -> dict[str, Any]:
    """Return a non-PII summary of the module registry."""
    entries = await asyncio.to_thread(load_registry)
    counts: dict[str, int] = {}
    for e in entries:
        status = e.get("status") or "unverified"
        counts[status] = counts.get(status, 0) + 1

    return {
        "total": len(entries),
        "by_status": counts,
        "last_verified_any": _latest_verified(entries),
    }


def _latest_verified(entries: list[dict[str, Any]]) -> str | None:
    latest: datetime | None = None
    for e in entries:
        ts = e.get("last_verified")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            continue
        if latest is None or dt > latest:
            latest = dt
    return latest.isoformat() if latest else None


@router.post("/verify")
async def trigger_verify() -> dict[str, Any]:
    """Trigger async registry sync+verify and return a handle.

    The real verification is async and can take > 60s; this endpoint just
    enqueues it and returns the expected completion path. Admin-only.
    """
    raise HTTPException(status_code=501, detail="Async verify trigger not yet implemented")
