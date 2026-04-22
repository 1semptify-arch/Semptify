"""
Analytics Engine - Usage and Performance Analytics
=================================================

Comprehensive analytics system for tracking:
- API endpoint usage
- User behavior and feature adoption
- Document processing metrics
- Performance trends
- Error tracking

Provides aggregation, reporting, and export capabilities.
"""

import logging
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum
import hashlib
from app.core.id_gen import make_id

logger = logging.getLogger(__name__)


class AnalyticsEventType(Enum):
    """Types of analytics events."""
    # API Events
    API_REQUEST = "api_request"
    API_ERROR = "api_error"
    API_SLOW = "api_slow"
    
    # User Events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_ACTION = "user_action"
    PAGE_VIEW = "page_view"
    
    # Document Events
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_PROCESS = "document_process"
    DOCUMENT_ANALYZE = "document_analyze"
    DOCUMENT_DOWNLOAD = "document_download"
    
    # Feature Events
    FEATURE_USED = "feature_used"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    
    # System Events
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_METRIC = "performance_metric"


class TimePeriod(Enum):
    """Time periods for aggregation."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class AnalyticsEvent:
    """Analytics event data."""
    event_id: str
    event_type: AnalyticsEventType
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    endpoint: Optional[str]
    method: Optional[str]
    status_code: Optional[int]
    duration_ms: Optional[float]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }


@dataclass
class AggregatedMetrics:
    """Aggregated analytics metrics."""
    period: str
    start_time: datetime
    end_time: datetime
    total_requests: int
    unique_users: int
    avg_response_time: float
    error_count: int
    error_rate: float
    top_endpoints: List[Dict[str, Any]]
    feature_usage: Dict[str, int]
    document_metrics: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_requests": self.total_requests,
            "unique_users": self.unique_users,
            "avg_response_time_ms": self.avg_response_time,
            "error_count": self.error_count,
            "error_rate": self.error_rate,
            "top_endpoints": self.top_endpoints,
            "feature_usage": self.feature_usage,
            "document_metrics": self.document_metrics
        }


class AnalyticsEngine:
    """Main analytics engine for tracking and aggregating metrics."""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events: List[AnalyticsEvent] = []
        self.event_buffer: List[AnalyticsEvent] = []
        self.aggregated_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        
    def track_event(
        self,
        event_type: AnalyticsEventType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Track a new analytics event."""
        event_id = make_id("anl")
        
        event = AnalyticsEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            session_id=session_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        # Add to buffer
        self.event_buffer.append(event)
        
        # Flush buffer if full
        if len(self.event_buffer) >= 100:
            asyncio.create_task(self._flush_buffer())
        
        return event_id
    
    async def _flush_buffer(self):
        """Flush event buffer to main storage."""
        async with self._lock:
            if not self.event_buffer:
                return
            
            # Move buffer to main storage
            self.events.extend(self.event_buffer)
            self.event_buffer.clear()
            
            # Trim old events if exceeding max
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
    
    def track_api_request(
        self,
        endpoint: str,
        method: str,
        user_id: Optional[str] = None,
        status_code: int = 200,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Track an API request."""
        return self.track_event(
            event_type=AnalyticsEventType.API_REQUEST,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            metadata=metadata
        )
    
    def track_user_action(
        self,
        action: str,
        user_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Track a user action."""
        return self.track_event(
            event_type=AnalyticsEventType.USER_ACTION,
            user_id=user_id,
            session_id=session_id,
            metadata={"action": action, **(metadata or {})}
        )
    
    def track_document_event(
        self,
        event_type: AnalyticsEventType,
        user_id: str,
        document_id: Optional[str] = None,
        doc_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Track a document-related event."""
        return self.track_event(
            event_type=event_type,
            user_id=user_id,
            metadata={
                "document_id": document_id,
                "doc_type": doc_type,
                **(metadata or {})
            }
        )
    
    async def aggregate_metrics(
        self,
        period: TimePeriod,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> AggregatedMetrics:
        """Aggregate metrics for a time period."""
        # Ensure buffer is flushed
        await self._flush_buffer()
        
        # Default time range
        end_time = end_time or datetime.now(timezone.utc)
        if period == TimePeriod.HOUR:
            start_time = start_time or (end_time - timedelta(hours=1))
        elif period == TimePeriod.DAY:
            start_time = start_time or (end_time - timedelta(days=1))
        elif period == TimePeriod.WEEK:
            start_time = start_time or (end_time - timedelta(weeks=1))
        elif period == TimePeriod.MONTH:
            start_time = start_time or (end_time - timedelta(days=30))
        
        # Filter events in time range
        filtered_events = [
            e for e in self.events
            if start_time <= e.timestamp <= end_time
        ]
        
        # Calculate metrics
        total_requests = len([e for e in filtered_events if e.event_type == AnalyticsEventType.API_REQUEST])
        unique_users = len(set(e.user_id for e in filtered_events if e.user_id))
        
        # Response times
        response_times = [e.duration_ms for e in filtered_events if e.duration_ms is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        # Errors
        error_events = [e for e in filtered_events if e.status_code and e.status_code >= 400]
        error_count = len(error_events)
        error_rate = error_count / total_requests if total_requests > 0 else 0.0
        
        # Top endpoints
        endpoint_counts = defaultdict(int)
        for e in filtered_events:
            if e.endpoint:
                endpoint_counts[e.endpoint] += 1
        top_endpoints = [
            {"endpoint": ep, "count": cnt}
            for ep, cnt in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Feature usage
        feature_usage = defaultdict(int)
        for e in filtered_events:
            if e.event_type == AnalyticsEventType.FEATURE_USED:
                feature = e.metadata.get("feature", "unknown")
                feature_usage[feature] += 1
        
        # Document metrics
        document_metrics = defaultdict(int)
        for e in filtered_events:
            if e.event_type in [AnalyticsEventType.DOCUMENT_UPLOAD, AnalyticsEventType.DOCUMENT_PROCESS]:
                doc_type = e.metadata.get("doc_type", "unknown")
                document_metrics[doc_type] += 1
        
        return AggregatedMetrics(
            period=period.value,
            start_time=start_time,
            end_time=end_time,
            total_requests=total_requests,
            unique_users=unique_users,
            avg_response_time=avg_response_time,
            error_count=error_count,
            error_rate=error_rate,
            top_endpoints=top_endpoints,
            feature_usage=dict(feature_usage),
            document_metrics=dict(document_metrics)
        )
    
    def get_recent_events(
        self,
        event_type: Optional[AnalyticsEventType] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AnalyticsEvent]:
        """Get recent events with optional filtering."""
        events = self.events + self.event_buffer
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def export_to_json(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> str:
        """Export analytics data to JSON string."""
        events = self.events + self.event_buffer
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_events": len(events),
            "events": [e.to_dict() for e in events]
        }
        
        return json.dumps(data, indent=2, default=str)
    
    def export_to_csv(self) -> str:
        """Export analytics data to CSV string."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "event_id", "event_type", "timestamp", "user_id", "session_id",
            "endpoint", "method", "status_code", "duration_ms", "metadata"
        ])
        
        # Data
        for event in self.events + self.event_buffer:
            writer.writerow([
                event.event_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.user_id or "",
                event.session_id or "",
                event.endpoint or "",
                event.method or "",
                event.status_code or "",
                event.duration_ms or "",
                json.dumps(event.metadata)
            ])
        
        return output.getvalue()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analytics engine statistics."""
        all_events = self.events + self.event_buffer
        
        return {
            "total_events_stored": len(self.events),
            "buffered_events": len(self.event_buffer),
            "max_capacity": self.max_events,
            "unique_users_all_time": len(set(e.user_id for e in all_events if e.user_id)),
            "oldest_event": min((e.timestamp for e in all_events), default=None),
            "newest_event": max((e.timestamp for e in all_events), default=None),
            "event_types": {
                et.value: len([e for e in all_events if e.event_type == et])
                for et in AnalyticsEventType
            }
        }


# Global analytics engine instance
_analytics_engine: Optional[AnalyticsEngine] = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get or create the global analytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AnalyticsEngine()
    return _analytics_engine


# Convenience functions for tracking
def track_api_request(*args, **kwargs) -> str:
    """Track an API request."""
    return get_analytics_engine().track_api_request(*args, **kwargs)


def track_user_action(*args, **kwargs) -> str:
    """Track a user action."""
    return get_analytics_engine().track_user_action(*args, **kwargs)


def track_document_event(*args, **kwargs) -> str:
    """Track a document event."""
    return get_analytics_engine().track_document_event(*args, **kwargs)
