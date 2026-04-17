"""
Performance Monitor - System Performance Tracking and Optimization
==============================================================

Tracks application performance, bottlenecks, and optimization opportunities.
"""

import logging
import time
import psutil
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json
import threading

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data point."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags or {}
        }

@dataclass
class RequestMetrics:
    """HTTP request performance metrics."""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: datetime
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "ip_address": self.ip_address
        }

@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_connections: int
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_usage_percent": self.disk_usage_percent,
            "active_connections": self.active_connections,
            "timestamp": self.timestamp.isoformat()
        }

class PerformanceMonitor:
    """Monitors and tracks application performance."""
    
    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.request_metrics: deque = deque(maxlen=10000)
        self.system_metrics: deque = deque(maxlen=1000)
        self.slow_queries: deque = deque(maxlen=1000)
        self.error_rates: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Performance thresholds
        self.slow_request_threshold = 1000  # ms
        self.high_cpu_threshold = 80.0  # percent
        self.high_memory_threshold = 85.0  # percent
        self.high_error_rate_threshold = 5.0  # percent
        
        # Background monitoring
        self.monitoring_active = False
        self.monitoring_thread = None
        
    def start_monitoring(self):
        """Start background performance monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background performance monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Check for performance issues
                self._check_performance_issues()
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)
    
    def _collect_system_metrics(self):
        """Collect system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            # Network connections
            connections = len(psutil.net_connections())
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                active_connections=connections,
                timestamp=datetime.now(timezone.utc)
            )
            
            self.system_metrics.append(metrics)
            
            # Store individual metrics for time series
            self._store_metric("system.cpu_percent", cpu_percent, "percent")
            self._store_metric("system.memory_percent", memory_percent, "percent")
            self._store_metric("system.disk_usage_percent", disk_usage_percent, "percent")
            self._store_metric("system.active_connections", connections, "count")
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _check_performance_issues(self):
        """Check for performance issues and alert."""
        if not self.system_metrics:
            return
        
        latest = self.system_metrics[-1]
        
        # Check CPU usage
        if latest.cpu_percent > self.high_cpu_threshold:
            self._alert_performance_issue(
                "high_cpu_usage",
                f"CPU usage at {latest.cpu_percent:.1f}%",
                {"cpu_percent": latest.cpu_percent, "threshold": self.high_cpu_threshold}
            )
        
        # Check memory usage
        if latest.memory_percent > self.high_memory_threshold:
            self._alert_performance_issue(
                "high_memory_usage",
                f"Memory usage at {latest.memory_percent:.1f}%",
                {"memory_percent": latest.memory_percent, "threshold": self.high_memory_threshold}
            )
        
        # Check error rates
        self._check_error_rates()
    
    def _check_error_rates(self):
        """Check for high error rates."""
        for endpoint, errors in self.error_rates.items():
            if len(errors) >= 10:  # Need at least 10 requests
                recent_errors = list(errors)[-10:]
                error_rate = sum(recent_errors) / len(recent_errors) * 100
                
                if error_rate > self.high_error_rate_threshold:
                    self._alert_performance_issue(
                        "high_error_rate",
                        f"Error rate for {endpoint} at {error_rate:.1f}%",
                        {"endpoint": endpoint, "error_rate": error_rate, "threshold": self.high_error_rate_threshold}
                    )
    
    def _alert_performance_issue(self, issue_type: str, message: str, details: Dict[str, Any]):
        """Alert on performance issue."""
        logger.warning(f"Performance issue: {issue_type} - {message}")
        
        # Store alert metric
        self._store_metric(f"performance.{issue_type}", 1, "count", details)
    
    def _store_metric(self, name: str, value: float, unit: str, tags: Dict[str, str] = None):
        """Store a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(timezone.utc),
            tags=tags
        )
        self.metrics[name].append(metric)
    
    def record_request(self, endpoint: str, method: str, status_code: int, 
                      duration_ms: float, user_id: str = None, ip_address: str = None):
        """Record HTTP request performance."""
        request_metric = RequestMetrics(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            ip_address=ip_address
        )
        
        self.request_metrics.append(request_metric)
        
        # Store request duration metric
        self._store_metric(f"request.duration.{endpoint}", duration_ms, "ms", {
            "method": method,
            "status_code": str(status_code)
        })
        
        # Track slow requests
        if duration_ms > self.slow_request_threshold:
            self.slow_queries.append(request_metric)
            self._store_metric("slow_requests.count", 1, "count", {
                "endpoint": endpoint,
                "method": method,
                "duration_ms": duration_ms
            })
        
        # Track error rates
        is_error = status_code >= 400
        self.error_rates[endpoint].append(1 if is_error else 0)
        
        # Store error rate metric
        if is_error:
            self._store_metric("request.errors", 1, "count", {
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code)
            })
    
    def record_database_query(self, query: str, duration_ms: float, 
                            rows_affected: int = None):
        """Record database query performance."""
        self._store_metric("database.query_duration", duration_ms, "ms", {
            "query_type": self._classify_query(query)
        })
        
        if rows_affected is not None:
            self._store_metric("database.rows_affected", rows_affected, "count")
        
        # Track slow queries
        if duration_ms > 500:  # 500ms threshold for slow queries
            self.slow_queries.append({
                "type": "database",
                "query": query[:100],  # First 100 chars
                "duration_ms": duration_ms,
                "timestamp": datetime.now(timezone.utc)
            })
    
    def record_storage_operation(self, operation: str, duration_ms: float, 
                              file_size: int = None):
        """Record storage operation performance."""
        self._store_metric(f"storage.{operation}_duration", duration_ms, "ms")
        
        if file_size:
            self._store_metric(f"storage.{operation}_size", file_size, "bytes")
    
    def _classify_query(self, query: str) -> str:
        """Classify database query type."""
        query_lower = query.lower().strip()
        
        if query_lower.startswith('select'):
            return 'select'
        elif query_lower.startswith('insert'):
            return 'insert'
        elif query_lower.startswith('update'):
            return 'update'
        elif query_lower.startswith('delete'):
            return 'delete'
        elif query_lower.startswith('create'):
            return 'create'
        elif query_lower.startswith('drop'):
            return 'drop'
        elif query_lower.startswith('alter'):
            return 'alter'
        else:
            return 'other'
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        
        # Request metrics
        recent_requests = [
            req for req in self.request_metrics 
            if req.timestamp >= one_hour_ago
        ]
        
        if recent_requests:
            avg_response_time = sum(req.duration_ms for req in recent_requests) / len(recent_requests)
            requests_per_minute = len(recent_requests) / 60
            error_rate = len([req for req in recent_requests if req.status_code >= 400]) / len(recent_requests) * 100
        else:
            avg_response_time = 0
            requests_per_minute = 0
            error_rate = 0
        
        # System metrics
        if self.system_metrics:
            latest_system = self.system_metrics[-1]
            system_stats = {
                "cpu_percent": latest_system.cpu_percent,
                "memory_percent": latest_system.memory_percent,
                "disk_usage_percent": latest_system.disk_usage_percent,
                "active_connections": latest_system.active_connections
            }
        else:
            system_stats = {}
        
        # Slow requests
        slow_requests_count = len([
            req for req in recent_requests 
            if req.duration_ms > self.slow_request_threshold
        ])
        
        return {
            "timestamp": now.isoformat(),
            "requests": {
                "total_last_hour": len(recent_requests),
                "requests_per_minute": round(requests_per_minute, 2),
                "average_response_time_ms": round(avg_response_time, 2),
                "error_rate_percent": round(error_rate, 2),
                "slow_requests_count": slow_requests_count
            },
            "system": system_stats,
            "slow_queries": {
                "total_count": len(self.slow_queries),
                "database_queries": len([sq for sq in self.slow_queries if isinstance(sq, dict) and sq.get('type') == 'database']),
                "http_requests": len([sq for sq in self.slow_queries if isinstance(sq, RequestMetrics)])
            }
        }
    
    def get_endpoint_performance(self, endpoint: str) -> Dict[str, Any]:
        """Get performance statistics for a specific endpoint."""
        endpoint_requests = [
            req for req in self.request_metrics 
            if req.endpoint == endpoint
        ]
        
        if not endpoint_requests:
            return {"error": "No data found for endpoint"}
        
        # Calculate statistics
        durations = [req.duration_ms for req in endpoint_requests]
        status_codes = [req.status_code for req in endpoint_requests]
        
        return {
            "endpoint": endpoint,
            "total_requests": len(endpoint_requests),
            "average_response_time_ms": sum(durations) / len(durations),
            "min_response_time_ms": min(durations),
            "max_response_time_ms": max(durations),
            "p50_response_time_ms": self._percentile(durations, 50),
            "p95_response_time_ms": self._percentile(durations, 95),
            "p99_response_time_ms": self._percentile(durations, 99),
            "error_rate_percent": len([sc for sc in status_codes if sc >= 400]) / len(status_codes) * 100,
            "status_code_distribution": self._count_status_codes(status_codes)
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _count_status_codes(self, status_codes: List[int]) -> Dict[str, int]:
        """Count distribution of status codes."""
        distribution = defaultdict(int)
        for code in status_codes:
            distribution[str(code)] += 1
        return dict(distribution)
    
    def get_slow_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get slow queries and requests."""
        slow_items = list(self.slow_queries)[-limit:]
        
        result = []
        for item in slow_items:
            if isinstance(item, RequestMetrics):
                result.append({
                    "type": "http_request",
                    "endpoint": item.endpoint,
                    "method": item.method,
                    "duration_ms": item.duration_ms,
                    "timestamp": item.timestamp.isoformat(),
                    "user_id": item.user_id
                })
            elif isinstance(item, dict):
                result.append({
                    "type": item.get("type", "unknown"),
                    "query": item.get("query", ""),
                    "duration_ms": item.get("duration_ms", 0),
                    "timestamp": item.get("timestamp", datetime.now(timezone.utc)).isoformat()
                })
        
        return result
    
    def get_metrics_history(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        if metric_name not in self.metrics:
            return []
        
        historical_metrics = [
            metric for metric in self.metrics[metric_name]
            if metric.timestamp >= cutoff_time
        ]
        
        return [metric.to_dict() for metric in historical_metrics]
    
    def export_performance_data(self, hours: int = 24) -> Dict[str, Any]:
        """Export all performance data for analysis."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Filter recent data
        recent_requests = [
            req.to_dict() for req in self.request_metrics
            if req.timestamp >= cutoff_time
        ]
        
        recent_system = [
            sys.to_dict() for sys in self.system_metrics
            if sys.timestamp >= cutoff_time
        ]
        
        recent_slow = []
        for item in self.slow_queries:
            if isinstance(item, RequestMetrics):
                if item.timestamp >= cutoff_time:
                    recent_slow.append(item.to_dict())
            elif isinstance(item, dict):
                timestamp = item.get("timestamp")
                if isinstance(timestamp, datetime) and timestamp >= cutoff_time:
                    recent_slow.append(item)
        
        return {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "time_range_hours": hours,
            "requests": recent_requests,
            "system_metrics": recent_system,
            "slow_operations": recent_slow,
            "summary": self.get_performance_summary()
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return performance_monitor

# Decorator for monitoring function performance
def monitor_performance(metric_name: str = None):
    """Decorator to monitor function performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Record performance
                name = metric_name or f"function.{func.__name__}"
                performance_monitor._store_metric(name, duration_ms, "ms")
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Record error
                name = metric_name or f"function.{func.__name__}"
                performance_monitor._store_metric(f"{name}.errors", 1, "count")
                
                raise
        
        return wrapper
    return decorator

# Helper functions
def record_request_performance(endpoint: str, method: str, status_code: int, 
                            duration_ms: float, user_id: str = None, ip_address: str = None):
    """Record HTTP request performance."""
    performance_monitor.record_request(endpoint, method, status_code, duration_ms, user_id, ip_address)

def get_performance_dashboard_data() -> Dict[str, Any]:
    """Get data for performance dashboard."""
    return performance_monitor.get_performance_summary()
