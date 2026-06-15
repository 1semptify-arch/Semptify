"""
Semptify Data Freshness Manager
Version: 1.0.0
Purpose: Keep data fresh and prevent staleness across the system
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import asyncio
import json
from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class FreshnessType(str, Enum):
    """Types of data freshness management."""
    LEGAL_CONTENT = "legal_content"
    COURT_DATA = "court_data"
    FORMS = "forms"
    STATE_LAWS = "state_laws"
    DEADLINES = "deadlines"
    USER_DATA = "user_data"
    CACHE = "cache"
    INDEX = "index"


class FreshnessStatus(str, Enum):
    """Freshness status levels."""
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


@dataclass
class FreshnessRule:
    """Rule for data freshness."""
    rule_id: str
    data_type: FreshnessType
    max_age_hours: int
    refresh_enabled: bool
    refresh_function: Optional[str]
    priority: int  # 1=highest, 10=lowest
    last_check: Optional[datetime] = None
    last_refresh: Optional[datetime] = None
    status: FreshnessStatus = FreshnessStatus.UNKNOWN
    error_count: int = 0
    metadata: Dict[str, Any] = None


@dataclass
class FreshnessAlert:
    """Alert for data freshness issues."""
    alert_id: str
    rule_id: str
    data_type: FreshnessType
    severity: str  # info, warning, error, critical
    message: str
    created_at: datetime
    acknowledged: bool = False
    resolved_at: Optional[datetime] = None


class DataFreshnessManager:
    """Manages data freshness across the entire system."""
    
    def __init__(self):
        self.rules: Dict[str, FreshnessRule] = {}
        self.alerts: List[FreshnessAlert] = []
        self.refresh_functions: Dict[str, Callable] = {}
        self.running = False
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default freshness rules."""
        default_rules = {
            "legal_content_001": FreshnessRule(
                rule_id="legal_content_001",
                data_type=FreshnessType.LEGAL_CONTENT,
                max_age_hours=168,  # 1 week
                refresh_enabled=True,
                refresh_function="refresh_legal_content",
                priority=2,
                metadata={"sources": ["state_statutes", "case_law"]}
            ),
            "court_data_001": FreshnessRule(
                rule_id="court_data_001",
                data_type=FreshnessType.COURT_DATA,
                max_age_hours=24,  # 1 day
                refresh_enabled=True,
                refresh_function="refresh_court_data",
                priority=3,
                metadata={"jurisdictions": ["all"]}
            ),
            "forms_001": FreshnessRule(
                rule_id="forms_001",
                data_type=FreshnessType.FORMS,
                max_age_hours=720,  # 30 days
                refresh_enabled=True,
                refresh_function="refresh_forms",
                priority=4,
                metadata={"types": ["court", "notice", "complaint"]}
            ),
            "state_laws_001": FreshnessRule(
                rule_id="state_laws_001",
                data_type=FreshnessType.STATE_LAWS,
                max_age_hours=168,  # 1 week
                refresh_enabled=True,
                refresh_function="refresh_state_laws",
                priority=2,
                metadata={"scope": "tenant_rights"}
            ),
            "deadlines_001": FreshnessRule(
                rule_id="deadlines_001",
                data_type=FreshnessType.DEADLINES,
                max_age_hours=1,  # 1 hour
                refresh_enabled=True,
                refresh_function="refresh_deadlines",
                priority=1,
                metadata={"critical": True}
            ),
            "cache_001": FreshnessRule(
                rule_id="cache_001",
                data_type=FreshnessType.CACHE,
                max_age_hours=6,  # 6 hours
                refresh_enabled=True,
                refresh_function="refresh_cache",
                priority=5,
                metadata={"types": ["legal", "forms", "search"]}
            ),
            "index_001": FreshnessRule(
                rule_id="index_001",
                data_type=FreshnessType.INDEX,
                max_age_hours=12,  # 12 hours
                refresh_enabled=True,
                refresh_function="refresh_search_index",
                priority=3,
                metadata={"engines": ["vault", "legal", "timeline"]}
            ),
        }
        
        self.rules = default_rules
    
    def register_refresh_function(self, name: str, function: Callable):
        """Register a refresh function."""
        self.refresh_functions[name] = function
        logger.info(f"Registered refresh function: {name}")
    
    def check_freshness(self, rule_id: str) -> FreshnessStatus:
        """Check freshness of a specific data type."""
        rule = self.rules.get(rule_id)
        if not rule:
            return FreshnessStatus.UNKNOWN
        
        now = utc_now()
        
        # If we've never checked, assume stale
        if not rule.last_check:
            rule.status = FreshnessStatus.STALE
            return FreshnessStatus.STALE
        
        # Check if data is expired
        if rule.last_refresh:
            age = now - rule.last_refresh
            max_age = timedelta(hours=rule.max_age_hours)
            
            if age > max_age:
                rule.status = FreshnessStatus.EXPIRED
                return FreshnessStatus.EXPIRED
            elif age > max_age * 0.8:  # 80% of max age
                rule.status = FreshnessStatus.STALE
                return FreshnessStatus.STALE
        
        rule.status = FreshnessStatus.FRESH
        return FreshnessStatus.FRESH
    
    async def refresh_data(self, rule_id: str) -> bool:
        """Refresh data for a specific rule."""
        rule = self.rules.get(rule_id)
        if not rule or not rule.refresh_enabled:
            return False
        
        try:
            refresh_func = self.refresh_functions.get(rule.refresh_function)
            if not refresh_func:
                logger.warning(f"No refresh function found for {rule_id}")
                return False
            
            logger.info(f"Refreshing data for {rule_id}")
            await refresh_func(rule.metadata)
            
            rule.last_refresh = utc_now()
            rule.error_count = 0
            rule.status = FreshnessStatus.FRESH
            
            logger.info(f"Successfully refreshed {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh {rule_id}: {str(e)}")
            rule.error_count += 1
            
            # Create alert if too many errors
            if rule.error_count >= 3:
                self.create_alert(
                    rule_id=rule_id,
                    data_type=rule.data_type,
                    severity="error",
                    message=f"Failed to refresh {rule_id} after {rule.error_count} attempts: {str(e)}"
                )
            
            return False
    
    async def check_all_freshness(self) -> Dict[str, FreshnessStatus]:
        """Check freshness of all data types."""
        results = {}
        
        for rule_id in self.rules:
            results[rule_id] = self.check_freshness(rule_id)
        
        return results
    
    async def refresh_stale_data(self, priority_cutoff: int = 5) -> Dict[str, bool]:
        """Refresh all stale data up to priority cutoff."""
        results = {}
        
        # Sort by priority (lower number = higher priority)
        sorted_rules = sorted(
            self.rules.values(),
            key=lambda r: r.priority
        )
        
        for rule in sorted_rules:
            if rule.priority > priority_cutoff:
                break
            
            status = self.check_freshness(rule.rule_id)
            if status in [FreshnessStatus.STALE, FreshnessStatus.EXPIRED]:
                results[rule.rule_id] = await self.refresh_data(rule.rule_id)
        
        return results
    
    def create_alert(self, rule_id: str, data_type: FreshnessType, 
                    severity: str, message: str):
        """Create a freshness alert."""
        alert = FreshnessAlert(
            alert_id=f"{rule_id}_{utc_now().timestamp()}",
            rule_id=rule_id,
            data_type=data_type,
            severity=severity,
            message=message,
            created_at=utc_now()
        )
        
        self.alerts.append(alert)
        logger.warning(f"Freshness alert created: {message}")
    
    def get_alerts(self, severity: Optional[str] = None, 
                   acknowledged: Optional[bool] = None) -> List[FreshnessAlert]:
        """Get freshness alerts with optional filters."""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                logger.info(f"Alert {alert_id} acknowledged")
                return True
        return False
    
    def get_freshness_report(self) -> Dict[str, Any]:
        """Generate comprehensive freshness report."""
        now = utc_now()
        report = {
            "generated_at": now.isoformat(),
            "summary": {
                "total_rules": len(self.rules),
                "fresh": 0,
                "stale": 0,
                "expired": 0,
                "unknown": 0,
                "active_alerts": 0
            },
            "rules": {},
            "alerts": [],
            "recommendations": []
        }
        
        # Check all rules
        for rule_id, rule in self.rules.items():
            status = self.check_freshness(rule_id)
            report["summary"][status.value] += 1
            
            rule_info = {
                "data_type": rule.data_type.value,
                "status": status.value,
                "priority": rule.priority,
                "max_age_hours": rule.max_age_hours,
                "last_refresh": rule.last_refresh.isoformat() if rule.last_refresh else None,
                "error_count": rule.error_count
            }
            
            report["rules"][rule_id] = rule_info
        
        # Add recent alerts
        recent_alerts = self.get_alerts(acknowledged=False)
        report["summary"]["active_alerts"] = len(recent_alerts)
        report["alerts"] = [
            {
                "alert_id": a.alert_id,
                "rule_id": a.rule_id,
                "severity": a.severity,
                "message": a.message,
                "created_at": a.created_at.isoformat()
            }
            for a in recent_alerts[:10]  # Last 10 alerts
        ]
        
        # Generate recommendations
        if report["summary"]["expired"] > 0:
            report["recommendations"].append("Immediate refresh required for expired data")
        
        if report["summary"]["active_alerts"] > 5:
            report["recommendations"].append("High number of active alerts - investigate system health")
        
        if any(rule.error_count > 0 for rule in self.rules.values()):
            report["recommendations"].append("Some refresh functions are failing - check error logs")
        
        return report
    
    async def start_background_scheduler(self):
        """Start the background freshness scheduler."""
        if self.running:
            logger.warning("Freshness scheduler already running")
            return
        
        self.running = True
        logger.info("Starting background freshness scheduler")
        
        while self.running:
            try:
                # Check all freshness
                await self.check_all_freshness()
                
                # Refresh stale data (priority 1-3)
                await self.refresh_stale_data(priority_cutoff=3)
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in freshness scheduler: {str(e)}")
                await asyncio.sleep(300)  # 5 minutes on error
    
    def stop_background_scheduler(self):
        """Stop the background freshness scheduler."""
        self.running = False
        logger.info("Stopping background freshness scheduler")


# Global instance
data_freshness_manager = DataFreshnessManager()


# Default refresh functions (to be implemented)
async def refresh_legal_content(metadata: Dict[str, Any]):
    """Refresh legal content from various sources."""
    logger.info("Refreshing legal content")
    # Implementation would fetch latest statutes, case law, etc.
    pass

async def refresh_court_data(metadata: Dict[str, Any]):
    """Refresh court data and procedures."""
    logger.info("Refreshing court data")
    # Implementation would fetch latest court procedures, forms, etc.
    pass

async def refresh_forms(metadata: Dict[str, Any]):
    """Refresh form templates and requirements."""
    logger.info("Refreshing forms")
    # Implementation would fetch latest court forms, notices, etc.
    pass

async def refresh_state_laws(metadata: Dict[str, Any]):
    """Refresh state-specific housing laws."""
    logger.info("Refreshing state laws")
    # Implementation would fetch latest state statutes and regulations
    pass

async def refresh_deadlines(metadata: Dict[str, Any]):
    """Refresh deadline calculations and requirements."""
    logger.info("Refreshing deadlines")
    # Implementation would update deadline logic based on current laws
    pass

async def refresh_cache(metadata: Dict[str, Any]):
    """Refresh system caches."""
    logger.info("Refreshing cache")
    # Implementation would clear and rebuild caches
    pass

async def refresh_search_index(metadata: Dict[str, Any]):
    """Refresh search indexes."""
    logger.info("Refreshing search index")
    # Implementation would rebuild search indexes
    pass


# Register default functions
data_freshness_manager.register_refresh_function("refresh_legal_content", refresh_legal_content)
data_freshness_manager.register_refresh_function("refresh_court_data", refresh_court_data)
data_freshness_manager.register_refresh_function("refresh_forms", refresh_forms)
data_freshness_manager.register_refresh_function("refresh_state_laws", refresh_state_laws)
data_freshness_manager.register_refresh_function("refresh_deadlines", refresh_deadlines)
data_freshness_manager.register_refresh_function("refresh_cache", refresh_cache)
data_freshness_manager.register_refresh_function("refresh_search_index", refresh_search_index)
