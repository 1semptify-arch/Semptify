"""
Pattern History API - Optional endpoints for pattern persistence and trend analysis

These endpoints provide historical tracking of housing accountability patterns
when ENABLE_PATTERN_PERSISTENCE=true is set in the environment.

Pattern records live in the tenant's own cloud vault (PATTERN_RECORD overlays
under Vault/derived/) — not the server database.
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.security import get_current_user
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

# Import pattern store (vault-backed)
try:
    from app.services.pattern_store import (
        get_pattern_history,
        get_pattern_record,
        get_pattern_stats,
        get_pattern_trends,
        is_pattern_persistence_enabled,
        mark_pattern_reviewed,
    )

    PATTERN_PERSISTENCE_AVAILABLE = True
except ImportError:
    PATTERN_PERSISTENCE_AVAILABLE = False

# Initialize router
pattern_history_router = APIRouter(prefix="/api/housing-accountability/patterns", tags=["Pattern History"])


@pattern_history_router.get("/history")
async def get_pattern_history_endpoint(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    days: int | None = Query(None, ge=1, le=365, description="Filter to last N days"),
    current_user=Depends(get_current_user),
):
    """
    Get pattern detection history for the current user.

    Requires ENABLE_PATTERN_PERSISTENCE=true to be enabled.
    Returns empty list if persistence is disabled.
    """
    if not PATTERN_PERSISTENCE_AVAILABLE or not is_pattern_persistence_enabled():
        return JSONResponse(
            content={
                "success": True,
                "message": "Pattern persistence is disabled",
                "records": [],
                "persistence_enabled": False,
            }
        )

    try:
        # Get base history
        records = await get_pattern_history(current_user, limit)

        # Filter by days if specified
        if days and records:
            cutoff_date = utc_now() - timedelta(days=days)
            records = [r for r in records if r.created_at >= cutoff_date]

        # Convert to dict format
        history_data = [record.to_dict() for record in records]

        return JSONResponse(
            content={
                "success": True,
                "records": history_data,
                "persistence_enabled": True,
                "total_count": len(history_data),
                "filter_days": days,
            }
        )

    except Exception as e:
        logger.error(f"Failed to get pattern history: {e}")
        logger.exception("Failed to retrieve pattern history")
        raise HTTPException(status_code=500, detail="Failed to retrieve pattern history")


@pattern_history_router.get("/trends")
async def get_pattern_trends_endpoint(
    days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    current_user=Depends(get_current_user),
):
    """
    Get pattern trend analysis over time.

    Requires ENABLE_PATTERN_PERSISTENCE=true to be enabled.
    Returns empty trends if persistence is disabled or insufficient data.
    """
    if not PATTERN_PERSISTENCE_AVAILABLE or not is_pattern_persistence_enabled():
        return JSONResponse(
            content={
                "success": True,
                "message": "Pattern persistence is disabled",
                "trends": {},
                "persistence_enabled": False,
            }
        )

    try:
        trends = await get_pattern_trends(current_user, days)

        return JSONResponse(
            content={"success": True, "trends": trends, "persistence_enabled": True, "analysis_period_days": days}
        )

    except Exception as e:
        logger.error(f"Failed to get pattern trends: {e}")
        logger.exception("Failed to analyze pattern trends")
        raise HTTPException(status_code=500, detail="Failed to analyze pattern trends")


@pattern_history_router.get("/record/{record_id}")
async def get_pattern_record_detail(record_id: int, current_user=Depends(get_current_user)):
    """
    Get detailed information about a specific pattern record.

    Requires ENABLE_PATTERN_PERSISTENCE=true to be enabled.
    """
    if not PATTERN_PERSISTENCE_AVAILABLE or not is_pattern_persistence_enabled():
        raise HTTPException(status_code=404, detail="Pattern persistence is disabled")

    try:
        record = await get_pattern_record(current_user, record_id)

        if not record:
            raise HTTPException(status_code=404, detail="Pattern record not found")

        return JSONResponse(content={"success": True, "record": record.to_dict()})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pattern record {record_id}: {e}")
        logger.exception("Failed to retrieve pattern record")
        raise HTTPException(status_code=500, detail="Failed to retrieve pattern record")


@pattern_history_router.post("/record/{record_id}/review")
async def mark_pattern_record_reviewed(
    record_id: int, notes: str | None = None, current_user=Depends(get_current_user)
):
    """
    Mark a pattern record as human-reviewed and add notes.

    Requires ENABLE_PATTERN_PERSISTENCE=true to be enabled.
    """
    if not PATTERN_PERSISTENCE_AVAILABLE or not is_pattern_persistence_enabled():
        raise HTTPException(status_code=404, detail="Pattern persistence is disabled")

    try:
        record = await mark_pattern_reviewed(current_user, record_id, notes)

        if not record:
            raise HTTPException(status_code=404, detail="Pattern record not found")

        return JSONResponse(
            content={"success": True, "message": "Pattern record marked as reviewed", "record": record.to_dict()}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark pattern record {record_id} as reviewed: {e}")
        logger.exception("Failed to update pattern record")
        raise HTTPException(status_code=500, detail="Failed to update pattern record")


@pattern_history_router.get("/stats")
async def get_pattern_statistics(current_user=Depends(get_current_user)):
    """
    Get pattern detection statistics for the current user.

    Requires ENABLE_PATTERN_PERSISTENCE=true to be enabled.
    """
    if not PATTERN_PERSISTENCE_AVAILABLE or not is_pattern_persistence_enabled():
        return JSONResponse(
            content={
                "success": True,
                "message": "Pattern persistence is disabled",
                "stats": {},
                "persistence_enabled": False,
            }
        )

    try:
        stats = await get_pattern_stats(current_user)

        return JSONResponse(
            content={
                "success": True,
                "stats": stats,
                "persistence_enabled": True,
            }
        )

    except Exception as e:
        logger.error(f"Failed to get pattern statistics: {e}")
        logger.exception("Failed to retrieve pattern statistics")
        raise HTTPException(status_code=500, detail="Failed to retrieve pattern statistics")
