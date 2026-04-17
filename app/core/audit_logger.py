"""
Audit Logger - Document Access and Security Logging
===============================================

Tracks all document access, modifications, and security events.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import os

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of audit events."""
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DOWNLOAD = "document_download"
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_SHARE = "document_share"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    SECURITY_VIOLATION = "security_violation"
    FILE_VALIDATION_FAILURE = "file_validation_failure"
    TOKEN_REFRESH = "token_refresh"
    STORAGE_ACCESS = "storage_access"
    SYSTEM_ERROR = "system_error"

class AuditSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Audit event record."""
    event_type: AuditEventType
    user_id: Optional[str]
    timestamp: datetime
    severity: AuditSeverity
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_id: Optional[str]
    resource_type: Optional[str]
    action: str
    details: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "action": self.action,
            "details": self.details,
            "success": self.success,
            "error_message": self.error_message
        }

class AuditLogger:
    """Centralized audit logging system."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file or "logs/audit.log"
        self.events: List[AuditEvent] = []
        self.max_events = 10000  # Keep last 10k events in memory
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Setup audit logger
        self.logger = logging.getLogger("semptify.audit")
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        handler = logging.FileHandler(self.log_file)
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
    
    def log_event(self, event: AuditEvent):
        """Log an audit event."""
        # Add to memory
        self.events.append(event)
        
        # Trim memory if needed
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Log to file
        log_message = json.dumps(event.to_dict())
        
        if event.severity == AuditSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif event.severity == AuditSeverity.HIGH:
            self.logger.error(log_message)
        elif event.severity == AuditSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def document_uploaded(self, user_id: str, document_id: str, filename: str, 
                         file_size: int, file_type: str, ip_address: str, 
                         user_agent: str, success: bool = True, error: str = None):
        """Log document upload event."""
        event = AuditEvent(
            event_type=AuditEventType.DOCUMENT_UPLOAD,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=AuditSeverity.MEDIUM,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=document_id,
            resource_type="document",
            action="upload",
            details={
                "filename": filename,
                "file_size": file_size,
                "file_type": file_type
            },
            success=success,
            error_message=error
        )
        self.log_event(event)
    
    def document_downloaded(self, user_id: str, document_id: str, filename: str,
                           ip_address: str, user_agent: str, success: bool = True, error: str = None):
        """Log document download event."""
        event = AuditEvent(
            event_type=AuditEventType.DOCUMENT_DOWNLOAD,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=AuditSeverity.MEDIUM,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=document_id,
            resource_type="document",
            action="download",
            details={
                "filename": filename
            },
            success=success,
            error_message=error
        )
        self.log_event(event)
    
    def document_viewed(self, user_id: str, document_id: str, filename: str,
                       ip_address: str, user_agent: str):
        """Log document view event."""
        event = AuditEvent(
            event_type=AuditEventType.DOCUMENT_VIEW,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=AuditSeverity.LOW,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=document_id,
            resource_type="document",
            action="view",
            details={
                "filename": filename
            },
            success=True
        )
        self.log_event(event)
    
    def document_deleted(self, user_id: str, document_id: str, filename: str,
                        ip_address: str, user_agent: str, success: bool = True, error: str = None):
        """Log document deletion event."""
        event = AuditEvent(
            event_type=AuditEventType.DOCUMENT_DELETE,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=AuditSeverity.HIGH,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=document_id,
            resource_type="document",
            action="delete",
            details={
                "filename": filename
            },
            success=success,
            error_message=error
        )
        self.log_event(event)
    
    def file_validation_failed(self, user_id: str, filename: str, error_message: str,
                               security_risk: str, ip_address: str, user_agent: str):
        """Log file validation failure."""
        event = AuditEvent(
            event_type=AuditEventType.FILE_VALIDATION_FAILURE,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=AuditSeverity.HIGH,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=None,
            resource_type="file",
            action="validation_failed",
            details={
                "filename": filename,
                "security_risk": security_risk,
                "validation_error": error_message
            },
            success=False,
            error_message=error_message
        )
        self.log_event(event)
    
    def security_violation(self, user_id: str, violation_type: str, details: Dict[str, Any],
                          ip_address: str, user_agent: str, severity: AuditSeverity = AuditSeverity.HIGH):
        """Log security violation."""
        event = AuditEvent(
            event_type=AuditEventType.SECURITY_VIOLATION,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=None,
            resource_type="security",
            action="violation",
            details={
                "violation_type": violation_type,
                **details
            },
            success=False
        )
        self.log_event(event)
    
    def user_login(self, user_id: str, provider: str, ip_address: str, user_agent: str,
                   success: bool = True, error: str = None):
        """Log user login event."""
        event = AuditEvent(
            event_type=AuditEventType.USER_LOGIN,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=AuditSeverity.MEDIUM,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=None,
            resource_type="user",
            action="login",
            details={
                "provider": provider
            },
            success=success,
            error_message=error
        )
        self.log_event(event)
    
    def user_logout(self, user_id: str, ip_address: str, user_agent: str):
        """Log user logout event."""
        event = AuditEvent(
            event_type=AuditEventType.USER_LOGOUT,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=AuditSeverity.LOW,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=None,
            resource_type="user",
            action="logout",
            details={},
            success=True
        )
        self.log_event(event)
    
    def token_refreshed(self, user_id: str, provider: str, success: bool = True, error: str = None):
        """Log token refresh event."""
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_REFRESH,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=AuditSeverity.MEDIUM,
            ip_address=None,
            user_agent=None,
            resource_id=None,
            resource_type="token",
            action="refresh",
            details={
                "provider": provider
            },
            success=success,
            error_message=error
        )
        self.log_event(event)
    
    def system_error(self, error_message: str, context: Dict[str, Any], user_id: str = None):
        """Log system error."""
        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_ERROR,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            severity=AuditSeverity.HIGH,
            ip_address=None,
            user_agent=None,
            resource_id=None,
            resource_type="system",
            action="error",
            details={
                "error_message": error_message,
                **context
            },
            success=False,
            error_message=error_message
        )
        self.log_event(event)
    
    def get_user_events(self, user_id: str, limit: int = 100) -> List[AuditEvent]:
        """Get events for a specific user."""
        user_events = [event for event in self.events if event.user_id == user_id]
        return user_events[-limit:]
    
    def get_document_events(self, document_id: str, limit: int = 100) -> List[AuditEvent]:
        """Get events for a specific document."""
        doc_events = [event for event in self.events if event.resource_id == document_id]
        return doc_events[-limit:]
    
    def get_security_events(self, severity: Optional[AuditSeverity] = None, 
                           limit: int = 100) -> List[AuditEvent]:
        """Get security events."""
        security_events = [event for event in self.events 
                          if event.event_type == AuditEventType.SECURITY_VIOLATION]
        
        if severity:
            security_events = [event for event in security_events 
                              if event.severity == severity]
        
        return security_events[-limit:]
    
    def get_events_by_type(self, event_type: AuditEventType, limit: int = 100) -> List[AuditEvent]:
        """Get events by type."""
        typed_events = [event for event in self.events if event.event_type == event_type]
        return typed_events[-limit:]
    
    def export_events(self, start_time: Optional[datetime] = None, 
                     end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Export events for compliance reporting."""
        events = self.events
        
        # Filter by time range
        if start_time:
            events = [event for event in events if event.timestamp >= start_time]
        if end_time:
            events = [event for event in events if event.timestamp <= end_time]
        
        return [event.to_dict() for event in events]
    
    def get_audit_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get audit summary statistics."""
        events = self.events
        
        if user_id:
            events = [event for event in events if event.user_id == user_id]
        
        # Count by event type
        event_counts = {}
        for event in events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for event in events:
            severity = event.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Success rate
        total_events = len(events)
        successful_events = len([event for event in events if event.success])
        success_rate = (successful_events / total_events * 100) if total_events > 0 else 0
        
        return {
            "total_events": total_events,
            "event_counts": event_counts,
            "severity_counts": severity_counts,
            "success_rate": success_rate,
            "time_range": {
                "earliest": min([event.timestamp for event in events]).isoformat() if events else None,
                "latest": max([event.timestamp for event in events]).isoformat() if events else None
            }
        }

# Global audit logger instance
audit_logger = AuditLogger()

def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    return audit_logger

# Helper functions for common audit operations
def log_document_upload(user_id: str, document_id: str, filename: str, 
                      file_size: int, file_type: str, ip_address: str, 
                      user_agent: str, success: bool = True, error: str = None):
    """Log document upload."""
    audit_logger.document_uploaded(user_id, document_id, filename, file_size, 
                                 file_type, ip_address, user_agent, success, error)

def log_document_access(user_id: str, document_id: str, filename: str, 
                       action: str, ip_address: str, user_agent: str):
    """Log document access (view/download)."""
    if action == "download":
        audit_logger.document_downloaded(user_id, document_id, filename, 
                                        ip_address, user_agent)
    else:
        audit_logger.document_viewed(user_id, document_id, filename, 
                                   ip_address, user_agent)

def log_security_event(user_id: str, event_type: str, details: Dict[str, Any],
                      ip_address: str, user_agent: str, severity: str = "high"):
    """Log security event."""
    severity_enum = AuditSeverity[severity.upper()]
    audit_logger.security_violation(user_id, event_type, details, 
                                   ip_address, user_agent, severity_enum)
