"""
Analytics API - Usage and Performance Analytics
================================================

Provides comprehensive analytics endpoints for:
- API usage tracking
- User behavior analysis
- Performance metrics
- Document processing statistics
- Data export
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.security import require_user, StorageUser, require_admin
from app.core.analytics_engine import (
    get_analytics_engine,
    AnalyticsEventType,
    TimePeriod,
    track_api_request,
    track_user_action,
    track_document_event
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class EventTrackRequest(BaseModel):
    """Track a custom analytics event."""
    event_type: str = Field(..., description="Event type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Event metadata")


class EventTrackResponse(BaseModel):
    """Event tracking response."""
    success: bool
    event_id: str
    message: str


class MetricsQueryRequest(BaseModel):
    """Metrics aggregation query."""
    period: str = Field("day", description="Time period: hour, day, week, month")
    start_time: Optional[datetime] = Field(None, description="Start time (ISO format)")
    end_time: Optional[datetime] = Field(None, description="End time (ISO format)")


class MetricsResponse(BaseModel):
    """Aggregated metrics response."""
    period: str
    start_time: str
    end_time: str
    total_requests: int
    unique_users: int
    avg_response_time_ms: float
    error_count: int
    error_rate: float
    top_endpoints: List[Dict[str, Any]]
    feature_usage: Dict[str, int]
    document_metrics: Dict[str, int]


class EventsListResponse(BaseModel):
    """List of analytics events."""
    events: List[Dict[str, Any]]
    total: int
    limit: int


class ExportResponse(BaseModel):
    """Export response."""
    success: bool
    format: str
    record_count: int
    data: str


# =============================================================================
# Event Tracking Endpoints
# =============================================================================

@router.post("/track", response_model=EventTrackResponse)
async def track_event(
    request: EventTrackRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Track a custom analytics event.
    
    Use this endpoint to record user actions, feature usage, or custom events.
    """
    try:
        # Map string event type to enum
        try:
            event_type = AnalyticsEventType(request.event_type)
        except ValueError:
            # Allow custom event types
            event_type = AnalyticsEventType.USER_ACTION
        
        event_id = track_user_action(
            action=request.event_type,
            user_id=user.user_id,
            metadata=request.metadata or {}
        )
        
        return EventTrackResponse(
            success=True,
            event_id=event_id,
            message="Event tracked successfully"
        )
        
    except Exception as e:
        logger.error(f"Event tracking error: {e}")
        raise HTTPException(status_code=500, detail="Failed to track event")


@router.post("/track/document-upload")
async def track_document_upload(
    document_id: str,
    doc_type: Optional[str] = None,
    user: StorageUser = Depends(require_user)
):
    """Track a document upload event."""
    try:
        event_id = track_document_event(
            event_type=AnalyticsEventType.DOCUMENT_UPLOAD,
            user_id=user.user_id,
            document_id=document_id,
            doc_type=doc_type
        )
        
        return {"success": True, "event_id": event_id}
        
    except Exception as e:
        logger.error(f"Document tracking error: {e}")
        raise HTTPException(status_code=500, detail="Failed to track document event")


# =============================================================================
# Metrics & Aggregation Endpoints
# =============================================================================

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    period: str = Query("day", description="Time period: hour, day, week, month"),
    hours: int = Query(24, ge=1, le=720, description="Hours to look back (alternative to period)"),
    user: StorageUser = Depends(require_admin)
):
    """
    Get aggregated analytics metrics.
    
    Returns usage statistics, performance metrics, and feature adoption data.
    Requires admin access.
    """
    try:
        engine = get_analytics_engine()
        
        # Map period string to TimePeriod enum
        period_map = {
            "hour": TimePeriod.HOUR,
            "day": TimePeriod.DAY,
            "week": TimePeriod.WEEK,
            "month": TimePeriod.MONTH
        }
        time_period = period_map.get(period.lower(), TimePeriod.DAY)
        
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Aggregate metrics
        metrics = await engine.aggregate_metrics(
            period=time_period,
            start_time=start_time,
            end_time=end_time
        )
        
        return MetricsResponse(**metrics.to_dict())
        
    except Exception as e:
        logger.error(f"Metrics aggregation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to aggregate metrics")


@router.get("/metrics/realtime")
async def get_realtime_metrics(
    user: StorageUser = Depends(require_admin)
):
    """
    Get real-time system metrics (last 5 minutes).
    
    Quick overview of current system activity.
    """
    try:
        engine = get_analytics_engine()
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=5)
        
        metrics = await engine.aggregate_metrics(
            period=TimePeriod.HOUR,
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            "time_window": "last_5_minutes",
            "requests_per_minute": metrics.total_requests / 5,
            "active_users": metrics.unique_users,
            "avg_response_time_ms": metrics.avg_response_time,
            "error_rate": metrics.error_rate,
            "top_endpoints": metrics.top_endpoints[:5]
        }
        
    except Exception as e:
        logger.error(f"Realtime metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get realtime metrics")


@router.get("/metrics/user/{user_id}")
async def get_user_metrics(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="Days to look back"),
    admin: StorageUser = Depends(require_admin)
):
    """
    Get analytics for a specific user.
    
    Requires admin access for privacy compliance.
    """
    try:
        engine = get_analytics_engine()
        
        # Get user's recent events
        events = engine.get_recent_events(user_id=user_id, limit=1000)
        
        # Calculate user-specific metrics
        document_uploads = len([e for e in events if e.event_type == AnalyticsEventType.DOCUMENT_UPLOAD])
        api_requests = len([e for e in events if e.event_type == AnalyticsEventType.API_REQUEST])
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_events": len(events),
            "document_uploads": document_uploads,
            "api_requests": api_requests,
            "last_activity": events[0].timestamp.isoformat() if events else None
        }
        
    except Exception as e:
        logger.error(f"User metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user metrics")


# =============================================================================
# Events Query Endpoints
# =============================================================================

@router.get("/events/recent")
async def get_recent_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    user: StorageUser = Depends(require_admin)
):
    """
    Get recent analytics events.
    
    Query raw event data with optional filtering.
    Requires admin access.
    """
    try:
        engine = get_analytics_engine()
        
        # Map event type if provided
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = AnalyticsEventType(event_type)
            except ValueError:
                pass
        
        events = engine.get_recent_events(
            event_type=event_type_enum,
            limit=limit
        )
        
        return EventsListResponse(
            events=[e.to_dict() for e in events],
            total=len(events),
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Events query error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get events")


# =============================================================================
# Export Endpoints
# =============================================================================

@router.get("/export/json")
async def export_json(
    days: int = Query(30, ge=1, le=365, description="Days of data to export"),
    user: StorageUser = Depends(require_admin)
):
    """
    Export analytics data as JSON.
    
    Download complete analytics dataset for external analysis.
    """
    try:
        engine = get_analytics_engine()
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        json_data = engine.export_to_json(start_time=start_time, end_time=end_time)
        
        return Response(
            content=json_data,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=analytics_export_{datetime.now().strftime('%Y%m%d')}.json",
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        logger.error(f"JSON export error: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")


@router.get("/export/csv")
async def export_csv(
    days: int = Query(30, ge=1, le=365, description="Days of data to export"),
    user: StorageUser = Depends(require_admin)
):
    """
    Export analytics data as CSV.
    
    Download analytics data in spreadsheet format.
    """
    try:
        engine = get_analytics_engine()
        
        csv_data = engine.export_to_csv()
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=analytics_export_{datetime.now().strftime('%Y%m%d')}.csv",
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/statistics")
async def get_statistics(
    user: StorageUser = Depends(require_admin)
):
    """
    Get analytics engine statistics.
    
    Overview of storage usage and data availability.
    """
    try:
        engine = get_analytics_engine()
        stats = engine.get_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get("/dashboard")
async def get_dashboard_summary(
    user: StorageUser = Depends(require_admin)
):
    """
    Get analytics dashboard summary.
    
    Combined metrics for dashboard display.
    """
    try:
        engine = get_analytics_engine()
        
        # Get metrics for different time periods
        now = datetime.now(timezone.utc)
        
        today = await engine.aggregate_metrics(
            period=TimePeriod.DAY,
            start_time=now - timedelta(days=1),
            end_time=now
        )
        
        this_week = await engine.aggregate_metrics(
            period=TimePeriod.WEEK,
            start_time=now - timedelta(weeks=1),
            end_time=now
        )
        
        this_month = await engine.aggregate_metrics(
            period=TimePeriod.MONTH,
            start_time=now - timedelta(days=30),
            end_time=now
        )
        
        return {
            "today": {
                "requests": today.total_requests,
                "unique_users": today.unique_users,
                "avg_response_time_ms": today.avg_response_time,
                "error_rate": today.error_rate
            },
            "this_week": {
                "requests": this_week.total_requests,
                "unique_users": this_week.unique_users,
                "avg_response_time_ms": this_week.avg_response_time,
                "error_rate": this_week.error_rate
            },
            "this_month": {
                "requests": this_month.total_requests,
                "unique_users": this_month.unique_users,
                "avg_response_time_ms": this_month.avg_response_time,
                "error_rate": this_month.error_rate
            },
            "top_features": today.feature_usage,
            "document_types": today.document_metrics
        }
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")
