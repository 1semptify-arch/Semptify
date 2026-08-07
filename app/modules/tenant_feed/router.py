"""Tenant Feed Aggregator router.

Endpoint:
    GET /api/tenant/feed — aggregated feed (timeline + documents + journal + deadlines + letters)

Query params:
    type — filter by type (document, timeline_event, journal, deadline, letter)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.modules.tenant_feed.service import FEED_TYPES, aggregate_feed_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tenant", tags=["Tenant Feed"])


def _get_user_id_sync(request) -> str:
    """Extract user_id from signed cookie on the request."""
    try:
        from app.core.cookie_auth import verify_user_id

        user_id_cookie = request.cookies.get("semptify_uid", "")
        if not user_id_cookie:
            return ""
        return verify_user_id(user_id_cookie) or ""
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.debug("Feed: no user_id on request: %s", e)
        return ""


@router.get("/feed")
async def get_tenant_feed(
    request: Request,
    type: str | None = Query(
        default=None,
        description=f"Filter by type. Valid: {sorted(FEED_TYPES)}",
    ),
):
    """Return the aggregated tenant feed.

    Merges timeline events + documents + journal + deadlines + letters,
    sorted chronologically (newest first). Filterable by type.
    """
    if type and type not in FEED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown feed type: {type}. Valid: {sorted(FEED_TYPES)}",
        )

    user_id = _get_user_id_sync(request)
    if not user_id:
        # Unauthenticated — return empty feed rather than 401.
        # The UI Composer renders an empty state for this case.
        return {"items": [], "total_count": 0, "filtered": type is not None}

    try:
        items = await aggregate_feed_async(user_id, type_filter=type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "items": items,
        "total_count": len(items),
        "filtered": type is not None,
    }
