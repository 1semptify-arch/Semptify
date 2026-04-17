"""
Scheduler & Watchdog - Automated Monitoring for LIS
============================================

Automated monitoring and scheduling for Litigation Intelligence System.
Handles periodic tasks, watchdog alerts, and background processing.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import asyncio
import json

logger = logging.getLogger(__name__)

@dataclass
class ScheduledTask:
    """Scheduled task configuration."""
    task_id: str
    task_name: str
    schedule_type: str  # cron, interval, once
    schedule_expression: str
    handler: str
    parameters: Dict[str, Any]
    enabled: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime

@dataclass
class WatchdogAlert:
    """Watchdog alert for system monitoring."""
    alert_id: str
    alert_type: str
    severity: str
    message: str
    source: str
    data: Dict[str, Any]
    created_at: datetime
    acknowledged: bool = False

class LitigationScheduler:
    """Main scheduler and watchdog for LIS."""
    
    def __init__(self):
        self.scheduled_tasks = {}
        self.active_tasks = {}
        self.watchdog_alerts = []
        self.event_handlers = {}
        self.running = False
        
    async def start(self):
        """Start the scheduler and watchdog."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting Litigation Intelligence Scheduler and Watchdog")
        
        # Start background monitoring
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._scheduled_task_loop())
        
        logger.info("Scheduler and watchdog started successfully")
    
    async def stop(self):
        """Stop the scheduler and watchdog."""
        self.running = False
        logger.info("Stopping Litigation Intelligence Scheduler and Watchdog")
        
        # Cancel all active tasks
        for task_id, task in self.active_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled task: {task_id}")
        
        self.active_tasks.clear()
        logger.info("Scheduler and watchdog stopped")
    
    def add_scheduled_task(self, task: ScheduledTask) -> str:
        """Add a scheduled task."""
        self.scheduled_tasks[task.task_id] = task
        
        # Calculate next run time
        if task.schedule_type == "cron":
            task.next_run = self._calculate_next_cron_run(task.schedule_expression)
        elif task.schedule_type == "interval":
            task.next_run = datetime.now(timezone.utc) + self._parse_interval(task.schedule_expression)
        elif task.schedule_type == "once":
            task.next_run = datetime.now(timezone.utc) + self._parse_interval(task.schedule_expression)
        
        logger.info(f"Added scheduled task: {task.task_name} ({task.task_id})")
        return task.task_id
    
    def remove_scheduled_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            logger.info(f"Removed scheduled task: {task_id}")
            return True
        return False
    
    def add_watchdog_alert(self, alert: WatchdogAlert) -> str:
        """Add a watchdog alert."""
        self.watchdog_alerts.append(alert)
        logger.info(f"Added watchdog alert: {alert.alert_type}")
        return alert.alert_id
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler."""
        self.event_handlers[event_type] = handler
        logger.info(f"Registered event handler for: {event_type}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for watchdog alerts."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check for overdue tasks
                await self._check_overdue_tasks()
                
                # Check for system health
                await self._check_system_health()
                
                # Process watchdog alerts
                await self._process_alerts()
                
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _scheduled_task_loop(self):
        """Main loop for scheduled task execution."""
        while self.running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Check for tasks ready to run
                ready_tasks = self._get_ready_tasks()
                
                for task in ready_tasks:
                    await self._execute_task(task)
                
            except asyncio.CancelledError:
                logger.info("Scheduled task loop cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduled task loop error: {e}")
                await asyncio.sleep(300)
    
    def _get_ready_tasks(self) -> List[ScheduledTask]:
        """Get tasks that are ready to run."""
        ready_tasks = []
        current_time = datetime.now(timezone.utc)
        
        for task in self.scheduled_tasks.values():
            if not task.enabled:
                continue
            
            if task.next_run and task.next_run <= current_time:
                ready_tasks.append(task)
        
        return ready_tasks
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        logger.info(f"Executing scheduled task: {task.task_name}")
        
        try:
            # Update last run time
            task.last_run = datetime.now(timezone.utc)
            
            # Calculate next run time
            if task.schedule_type == "interval":
                task.next_run = task.last_run + self._parse_interval(task.schedule_expression)
            elif task.schedule_type == "cron":
                task.next_run = self._calculate_next_cron_run(task.schedule_expression)
            
            # Execute the task
            if task.handler in self.event_handlers:
                handler = self.event_handlers[task.handler]
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(task.parameters)
                else:
                    result = handler(task.parameters)
                
                logger.info(f"Task {task.task_name} completed successfully")
                
                # Trigger completion event
                await self._trigger_event("task_completed", {
                    "task_id": task.task_id,
                    "task_name": task.task_name,
                    "result": result,
                    "executed_at": task.last_run.isoformat()
                })
            else:
                logger.warning(f"No handler found for task: {task.handler}")
        
        except Exception as e:
            logger.error(f"Task {task.task_name} failed: {e}")
            
            # Trigger failure event
            await self._trigger_event("task_failed", {
                "task_id": task.task_id,
                "task_name": task.task_name,
                "error": str(e),
                "failed_at": datetime.now(timezone.utc).isoformat()
            })
    
    async def _check_overdue_tasks(self):
        """Check for overdue tasks and create alerts."""
        current_time = datetime.now(timezone.utc)
        
        for task in self.scheduled_tasks.values():
            if not task.enabled:
                continue
            
            if task.next_run and task.next_run < current_time:
                # Task is overdue
                alert = WatchdogAlert(
                    alert_id=f"overdue_task_{task.task_id}",
                    alert_type="task_overdue",
                    severity="warning",
                    message=f"Scheduled task '{task.task_name}' is overdue",
                    source="scheduler",
                    data={
                        "task_id": task.task_id,
                        "task_name": task.task_name,
                        "scheduled_time": task.next_run.isoformat(),
                        "overdue_by": (current_time - task.next_run).total_seconds()
                    },
                    created_at=current_time
                )
                
                self.add_watchdog_alert(alert)
                logger.warning(f"Task overdue: {task.task_name}")
    
    async def _check_system_health(self):
        """Check system health and create alerts if needed."""
        try:
            # Check storage layer health
            # This would integrate with storage layer
            storage_health = "healthy"  # Placeholder
            
            # Check external service health
            # This would check court systems availability
            external_health = "healthy"  # Placeholder
            
            if storage_health != "healthy" or external_health != "healthy":
                alert = WatchdogAlert(
                    alert_id=f"system_health_{datetime.now().timestamp()}",
                    alert_type="system_health",
                    severity="critical",
                    message="System health check failed",
                    source="watchdog",
                    data={
                        "storage_health": storage_health,
                        "external_health": external_health,
                        "checked_at": datetime.now(timezone.utc).isoformat()
                    },
                    created_at=datetime.now(timezone.utc)
                )
                
                self.add_watchdog_alert(alert)
                logger.error("System health check failed")
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _process_alerts(self):
        """Process pending watchdog alerts."""
        if not self.watchdog_alerts:
            return
        
        processed_alerts = []
        
        for alert in self.watchdog_alerts:
            if not alert.acknowledged:
                # Trigger alert event
                await self._trigger_event("watchdog_alert", {
                    "alert_id": alert.alert_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "data": alert.data
                })
                
                # Mark as processed (but not acknowledged)
                alert.acknowledged = True
                processed_alerts.append(alert)
        
        # Remove processed alerts
        self.watchdog_alerts = [a for a in self.watchdog_alerts if not a.acknowledged]
        
        if processed_alerts:
            logger.info(f"Processed {len(processed_alerts)} watchdog alerts")
    
    async def _trigger_event(self, event_type: str, data: Dict[str, Any]):
        """Trigger an event to registered handlers."""
        if event_type in self.event_handlers:
            handler = self.event_handlers[event_type]
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
        else:
            logger.debug(f"No handler for event type: {event_type}")
    
    def _parse_interval(self, interval_str: str) -> timedelta:
        """Parse interval string to timedelta."""
        # Support formats: "1h", "30m", "7d", "1w"
        if interval_str.endswith('h'):
            hours = int(interval_str[:-1])
            return timedelta(hours=hours)
        elif interval_str.endswith('m'):
            minutes = int(interval_str[:-1])
            return timedelta(minutes=minutes)
        elif interval_str.endswith('d'):
            days = int(interval_str[:-1])
            return timedelta(days=days)
        elif interval_str.endswith('w'):
            weeks = int(interval_str[:-1])
            return timedelta(weeks=weeks)
        else:
            # Default to 1 hour
            return timedelta(hours=1)
    
    def _calculate_next_cron_run(self, cron_expression: str) -> datetime:
        """Calculate next run time for cron expression."""
        # Simplified cron parsing - would use a full cron library
        # For now, assume daily at midnight
        current_time = datetime.now(timezone.utc)
        next_run = current_time.replace(hour=0, minute=0, second=0)
        
        # If next run is in the past, add a day
        if next_run <= current_time:
            next_run = next_run + timedelta(days=1)
        
        return next_run
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a scheduled task."""
        if task_id not in self.scheduled_tasks:
            return None
        
        task = self.scheduled_tasks[task_id]
        return {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "schedule_type": task.schedule_type,
            "schedule_expression": task.schedule_expression,
            "enabled": task.enabled,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "created_at": task.created_at.isoformat()
        }
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks."""
        return [self.get_task_status(task_id) for task_id in self.scheduled_tasks.keys()]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active watchdog alerts."""
        return [
            {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "source": alert.source,
                "data": alert.data,
                "created_at": alert.created_at.isoformat(),
                "acknowledged": alert.acknowledged
            }
            for alert in self.watchdog_alerts
        ]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a watchdog alert."""
        for alert in self.watchdog_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                logger.info(f"Acknowledged alert: {alert_id}")
                return True
        return False

# Factory function
def create_litigation_scheduler() -> LitigationScheduler:
    """Create litigation scheduler instance."""
    return LitigationScheduler()

# Example usage
async def example_usage():
    """Example usage of litigation scheduler."""
    scheduler = create_litigation_scheduler()
    
    # Register event handlers
    def on_task_completed(data):
        print(f"Task completed: {data['task_name']}")
    
    def on_watchdog_alert(data):
        print(f"Watchdog alert: {data['message']}")
    
    scheduler.register_event_handler("task_completed", on_task_completed)
    scheduler.register_event_handler("watchdog_alert", on_watchdog_alert)
    
    # Add scheduled tasks
    task1 = ScheduledTask(
        task_id="daily_case_scan",
        task_name="Daily Case Scan",
        schedule_type="cron",
        schedule_expression="0 2 * * *",  # Daily at 2 AM
        handler="case_scanner",
        parameters={"scan_type": "new_cases"},
        enabled=True,
        created_at=datetime.now(timezone.utc)
    )
    
    task2 = ScheduledTask(
        task_id="weekly_pattern_analysis",
        task_name="Weekly Pattern Analysis",
        schedule_type="interval",
        schedule_expression="7d",  # Every 7 days
        handler="pattern_analyzer",
        parameters={"analysis_type": "trends"},
        enabled=True,
        created_at=datetime.now(timezone.utc)
    )
    
    scheduler.add_scheduled_task(task1)
    scheduler.add_scheduled_task(task2)
    
    # Start scheduler
    await scheduler.start()
    
    print("Scheduler started with 2 tasks")
    print(f"Tasks: {scheduler.get_all_tasks()}")
    
    # Run for a bit
    await asyncio.sleep(10)
    
    # Stop scheduler
    await scheduler.stop()
    print("Scheduler stopped")

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
