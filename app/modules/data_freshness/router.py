"""
Data Freshness Router
Version: 1.0.0
Purpose: API endpoints for data freshness management
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.accountability_planner import AuditAction, accountability_planner
from app.core.data_freshness_manager import FreshnessStatus, data_freshness_manager
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-freshness", tags=["data-freshness"])


@router.get("/status")
async def get_freshness_status():
    """Get overall freshness status of all data types."""
    try:
        status = await data_freshness_manager.check_all_freshness()

        return {
            "timestamp": utc_now().isoformat(),
            "status": status,
            "summary": {
                "total": len(status),
                "fresh": sum(1 for s in status.values() if s == FreshnessStatus.FRESH),
                "stale": sum(1 for s in status.values() if s == FreshnessStatus.STALE),
                "expired": sum(1 for s in status.values() if s == FreshnessStatus.EXPIRED),
                "unknown": sum(1 for s in status.values() if s == FreshnessStatus.UNKNOWN),
            },
        }
    except Exception as e:
        logger.error(f"Error getting freshness status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get freshness status")


@router.get("/report")
async def get_freshness_report():
    """Get comprehensive freshness report."""
    try:
        report = data_freshness_manager.get_freshness_report()
        return report
    except Exception as e:
        logger.error(f"Error generating freshness report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.post("/refresh/{rule_id}")
async def refresh_data(rule_id: str, background_tasks: BackgroundTasks):
    """Manually trigger refresh for specific data type."""
    try:
        # Log the refresh request
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource=f"data_freshness:{rule_id}",
            details={"manual_refresh": True},
            success=True,
        )

        # Queue background refresh
        background_tasks.add_task(data_freshness_manager.refresh_data, rule_id)

        return {"message": f"Refresh queued for {rule_id}", "rule_id": rule_id, "timestamp": utc_now().isoformat()}
    except Exception as e:
        logger.error(f"Error queuing refresh for {rule_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to queue refresh")


@router.post("/refresh-stale")
async def refresh_stale_data(background_tasks: BackgroundTasks, priority: int = 5):
    """Refresh all stale data up to specified priority."""
    try:
        # Log the bulk refresh
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource="data_freshness:bulk_refresh",
            details={"priority": priority},
            success=True,
        )

        # Queue background refresh
        background_tasks.add_task(data_freshness_manager.refresh_stale_data, priority)

        return {
            "message": f"Bulk refresh queued for priority <= {priority}",
            "priority": priority,
            "timestamp": utc_now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error queuing bulk refresh: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to queue bulk refresh")


@router.get("/alerts")
async def get_freshness_alerts(severity: str | None = None, acknowledged: bool | None = None):
    """Get freshness alerts."""
    try:
        alerts = data_freshness_manager.get_alerts(severity=severity, acknowledged=acknowledged)

        return {
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "rule_id": a.rule_id,
                    "data_type": a.data_type.value,
                    "severity": a.severity,
                    "message": a.message,
                    "created_at": a.created_at.isoformat(),
                    "acknowledged": a.acknowledged,
                    "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                }
                for a in alerts
            ]
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge a freshness alert."""
    try:
        success = data_freshness_manager.acknowledge_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {"message": f"Alert {alert_id} acknowledged"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/rules")
async def get_freshness_rules():
    """Get all freshness rules."""
    try:
        rules = {}
        for rule_id, rule in data_freshness_manager.rules.items():
            rules[rule_id] = {
                "rule_id": rule.rule_id,
                "data_type": rule.data_type.value,
                "max_age_hours": rule.max_age_hours,
                "refresh_enabled": rule.refresh_enabled,
                "priority": rule.priority,
                "last_check": rule.last_check.isoformat() if rule.last_check else None,
                "last_refresh": rule.last_refresh.isoformat() if rule.last_refresh else None,
                "status": rule.status.value,
                "error_count": rule.error_count,
                "metadata": rule.metadata,
            }

        return {"rules": rules}
    except Exception as e:
        logger.error(f"Error getting rules: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get rules")


# Cron job endpoint for Render
@router.post("/cron/daily-refresh")
async def daily_refresh_cron():
    """Daily cron job for data freshness (Render compatible)."""
    try:
        logger.info("Starting daily refresh cron job")

        # Log the cron run
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource="data_freshness:cron_daily",
            details={"cron_job": "daily_refresh"},
            success=True,
        )

        # Refresh high-priority data (1-3)
        results = await data_freshness_manager.refresh_stale_data(priority_cutoff=3)

        # Generate summary
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        logger.info(f"Daily refresh completed: {success_count}/{total_count} successful")

        return {
            "message": "Daily refresh completed",
            "timestamp": utc_now().isoformat(),
            "results": {
                "total": total_count,
                "successful": success_count,
                "failed": total_count - success_count,
                "details": results,
            },
        }
    except Exception as e:
        logger.error(f"Error in daily refresh cron: {str(e)}")

        # Log the failure
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource="data_freshness:cron_daily",
            details={"cron_job": "daily_refresh", "error": str(e)},
            success=False,
        )

        raise HTTPException(status_code=500, detail="Daily refresh failed")


@router.post("/cron/hourly-deadlines")
async def hourly_deadlines_cron():
    """Hourly cron job for deadline updates (Render compatible)."""
    try:
        logger.info("Starting hourly deadlines cron job")

        # Log the cron run
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource="data_freshness:cron_hourly",
            details={"cron_job": "hourly_deadlines"},
            success=True,
        )

        # Refresh deadlines (highest priority)
        success = await data_freshness_manager.refresh_data("deadlines_001")

        logger.info(f"Hourly deadlines refresh completed: {'success' if success else 'failed'}")

        return {"message": "Hourly deadlines refresh completed", "timestamp": utc_now().isoformat(), "success": success}
    except Exception as e:
        logger.error(f"Error in hourly deadlines cron: {str(e)}")

        # Log the failure
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource="data_freshness:cron_hourly",
            details={"cron_job": "hourly_deadlines", "error": str(e)},
            success=False,
        )

        raise HTTPException(status_code=500, detail="Hourly deadlines refresh failed")


@router.get("/health")
async def health_check():
    """Health check for data freshness system."""
    try:
        status = await data_freshness_manager.check_all_freshness()
        alerts = data_freshness_manager.get_alerts(acknowledged=False)

        # Determine health status
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        expired_count = sum(1 for s in status.values() if s == FreshnessStatus.EXPIRED)

        if critical_alerts or expired_count > 0:
            health_status = "unhealthy"
        elif any(s == FreshnessStatus.STALE for s in status.values()):
            health_status = "degraded"
        else:
            health_status = "healthy"

        return {
            "status": health_status,
            "timestamp": utc_now().isoformat(),
            "metrics": {
                "total_rules": len(status),
                "expired": expired_count,
                "stale": sum(1 for s in status.values() if s == FreshnessStatus.STALE),
                "fresh": sum(1 for s in status.values() if s == FreshnessStatus.FRESH),
                "active_alerts": len(alerts),
                "critical_alerts": len(critical_alerts),
            },
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return {"status": "error", "timestamp": utc_now().isoformat(), "error": str(e)}
