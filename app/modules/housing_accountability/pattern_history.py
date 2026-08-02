"""
Pattern History API - Optional endpoints for pattern persistence and trend analysis

These endpoints provide historical tracking of housing accountability patterns
when ENABLE_PATTERN_PERSISTENCE=true is set in the environment.
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

# Import pattern record model and functions
try:
    from app.models.pattern_record import (
        PatternRecord,
        get_pattern_history,
        get_pattern_trends,
        is_pattern_persistence_enabled,
    )

    PATTERN_PERSISTENCE_AVAILABLE = True
except ImportError:
    PATTERN_PERSISTENCE_AVAILABLE = False
    PatternRecord = None

# Initialize router
pattern_history_router = APIRouter(prefix="/api/housing-accountability/patterns", tags=["Pattern History"])


@pattern_history_router.get("/history")
async def get_pattern_history_endpoint(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    days: int | None = Query(None, ge=1, le=365, description="Filter to last N days"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
        records = get_pattern_history(db, current_user.id, limit)

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
    db: AsyncSession = Depends(get_db),
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
        trends = get_pattern_trends(db, current_user.id, days)

        return JSONResponse(
            content={"success": True, "trends": trends, "persistence_enabled": True, "analysis_period_days": days}
        )

    except Exception as e:
        logger.error(f"Failed to get pattern trends: {e}")
        logger.exception("Failed to analyze pattern trends")
        raise HTTPException(status_code=500, detail="Failed to analyze pattern trends")


@pattern_history_router.get("/record/{record_id}")
async def get_pattern_record_detail(
    record_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific pattern record.

    Requires ENABLE_PATTERN_PERSISTENCE=true to be enabled.
    """
    if not PATTERN_PERSISTENCE_AVAILABLE or not is_pattern_persistence_enabled():
        raise HTTPException(status_code=404, detail="Pattern persistence is disabled")

    try:
        result = await db.execute(
            select(PatternRecord).where(and_(PatternRecord.id == record_id, PatternRecord.user_id == current_user.id))
        )
        record = result.scalar_one_or_none()

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
    record_id: int, notes: str | None = None, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Mark a pattern record as human-reviewed and add notes.

    Requires ENABLE_PATTERN_PERSISTENCE=true to be enabled.
    """
    if not PATTERN_PERSISTENCE_AVAILABLE or not is_pattern_persistence_enabled():
        raise HTTPException(status_code=404, detail="Pattern persistence is disabled")

    try:
        result = await db.execute(
            select(PatternRecord).where(and_(PatternRecord.id == record_id, PatternRecord.user_id == current_user.id))
        )
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(status_code=404, detail="Pattern record not found")

        # Update record
        record.reviewed = True
        if notes:
            record.notes = notes

        await db.commit()

        return JSONResponse(
            content={"success": True, "message": "Pattern record marked as reviewed", "record": record.to_dict()}
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to mark pattern record {record_id} as reviewed: {e}")
        logger.exception("Failed to update pattern record")
        raise HTTPException(status_code=500, detail="Failed to update pattern record")


@pattern_history_router.get("/stats")
async def get_pattern_statistics(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
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
        # Get total count
        total_result = await db.execute(select(PatternRecord.id).where(PatternRecord.user_id == current_user.id))
        total_count = len(total_result.scalars().all())

        if total_count == 0:
            return JSONResponse(
                content={
                    "success": True,
                    "stats": {
                        "total_analyses": 0,
                        "average_risk_score": 0,
                        "most_common_risk_level": "none",
                        "pattern_types": [],
                        "recent_analyses": [],
                    },
                    "persistence_enabled": True,
                }
            )

        # Get risk level distribution
        risk_result = await db.execute(select(PatternRecord.risk_level).where(PatternRecord.user_id == current_user.id))
        risk_levels = [row[0] for row in risk_result.all()]

        # Get average risk score
        avg_result = await db.execute(select(PatternRecord.risk_score).where(PatternRecord.user_id == current_user.id))
        risk_scores = [row[0] for row in avg_result.all()]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0

        # Get recent analyses
        recent_records = get_pattern_history(db, current_user.id, 5)
        recent_data = [record.to_dict() for record in recent_records]

        # Calculate most common risk level
        risk_counts = {}
        for level in risk_levels:
            risk_counts[level] = risk_counts.get(level, 0) + 1
        most_common = max(risk_counts.items(), key=lambda x: x[1])[0] if risk_counts else "none"

        return JSONResponse(
            content={
                "success": True,
                "stats": {
                    "total_analyses": total_count,
                    "average_risk_score": round(avg_risk, 2),
                    "most_common_risk_level": most_common,
                    "risk_level_distribution": risk_counts,
                    "recent_analyses": recent_data,
                },
                "persistence_enabled": True,
            }
        )

    except Exception as e:
        logger.error(f"Failed to get pattern statistics: {e}")
        logger.exception("Failed to retrieve pattern statistics")
        raise HTTPException(status_code=500, detail="Failed to retrieve pattern statistics")
