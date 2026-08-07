"""
Semptify Accountability Planner - Compliance & Audit Framework
Version: 1.0.0
Purpose: Track compliance, maintain audit trails, and ensure accountability
"""

import hashlib
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class ComplianceType(str, Enum):
    """Types of compliance requirements."""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    HOUSING_LAW = "housing_law"
    COURT_RULES = "court_rules"
    INTERNAL_POLICY = "internal_policy"


class AuditAction(str, Enum):
    """Types of audit actions."""
    DOCUMENT_ACCESS = "document_access"
    DOCUMENT_PROCESS = "document_process"
    DATA_EXPORT = "data_export"
    USER_LOGIN = "user_login"
    API_CALL = "api_call"
    SYSTEM_CHANGE = "system_change"
    ERROR_OCCURRED = "error_occurred"


class ComplianceStatus(str, Enum):
    """Compliance status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    EXEMPTION_GRANTED = "exemption_granted"


class AuditEvent(BaseModel):
    """Single audit event."""
    event_id: str
    timestamp: datetime
    user_id: str | None
    action: AuditAction
    resource: str
    details: dict[str, Any]
    ip_address: str | None
    user_agent: str | None
    success: bool
    error_message: str | None


class ComplianceCheck(BaseModel):
    """Compliance check result."""
    check_id: str
    compliance_type: ComplianceType
    status: ComplianceStatus
    description: str
    requirements: list[str]
    findings: list[str]
    recommendations: list[str]
    checked_at: datetime
    next_review: datetime


class AccountabilityMetrics(BaseModel):
    """Accountability metrics."""
    total_events: int
    successful_events: int
    failed_events: int
    compliance_score: float
    last_audit: datetime
    open_issues: int
    resolved_issues: int


class AccountabilityPlanner:
    """Main accountability and compliance planner."""

    def __init__(self):
        self.audit_trail: list[AuditEvent] = []
        self.compliance_checks: dict[ComplianceType, ComplianceCheck] = {}
        self.metrics = AccountabilityMetrics(
            total_events=0,
            successful_events=0,
            failed_events=0,
            compliance_score=0.0,
            last_audit=utc_now(),
            open_issues=0,
            resolved_issues=0
        )
        self._initialize_compliance_checks()

    def _initialize_compliance_checks(self):
        """Initialize default compliance checks."""
        checks = {
            ComplianceType.GDPR: ComplianceCheck(
                check_id="gdpr_001",
                compliance_type=ComplianceType.GDPR,
                status=ComplianceStatus.PENDING_REVIEW,
                description="EU General Data Protection Regulation compliance",
                requirements=[
                    "Lawful basis for processing",
                    "Data minimization",
                    "Right to be forgotten",
                    "Data portability",
                    "Breach notification within 72 hours"
                ],
                findings=[],
                recommendations=[],
                checked_at=utc_now(),
                next_review=utc_now().replace(year=utc_now().year + 1)
            ),
            ComplianceType.CCPA: ComplianceCheck(
                check_id="ccpa_001",
                compliance_type=ComplianceType.CCPA,
                status=ComplianceStatus.PENDING_REVIEW,
                description="California Consumer Privacy Act compliance",
                requirements=[
                    "Right to know",
                    "Right to delete",
                    "Right to opt-out",
                    "Non-discrimination"
                ],
                findings=[],
                recommendations=[],
                checked_at=utc_now(),
                next_review=utc_now().replace(year=utc_now().year + 1)
            ),
            ComplianceType.HOUSING_LAW: ComplianceCheck(
                check_id="housing_001",
                compliance_type=ComplianceType.HOUSING_LAW,
                status=ComplianceStatus.PENDING_REVIEW,
                description="Housing law compliance for tenant rights",
                requirements=[
                    "Fair housing practices",
                    "Proper notice periods",
                    "Legal form requirements",
                    "Privacy of tenant data"
                ],
                findings=[],
                recommendations=[],
                checked_at=utc_now(),
                next_review=utc_now() + timedelta(days=180)
            ),
        }

        self.compliance_checks = checks

    def log_audit_event(self, user_id: str | None, action: AuditAction,
                       resource: str, details: dict[str, Any],
                       success: bool = True, error_message: str | None = None,
                       ip_address: str | None = None,
                       user_agent: str | None = None) -> str:
        """Log an audit event."""
        event_id = hashlib.sha256(
            f"{utc_now().isoformat()}{user_id}{action}{resource}".encode()
        ).hexdigest()[:16]

        event = AuditEvent(
            event_id=event_id,
            timestamp=utc_now(),
            user_id=user_id,
            action=action,
            resource=resource,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )

        self.audit_trail.append(event)

        # Update metrics
        self.metrics.total_events += 1
        if success:
            self.metrics.successful_events += 1
        else:
            self.metrics.failed_events += 1

        logger.info(f"Audit event logged: {event_id} - {action} on {resource}")
        return event_id

    def get_audit_trail(self, user_id: str | None = None,
                       action: AuditAction | None = None,
                       start_date: datetime | None = None,
                       end_date: datetime | None = None,
                       limit: int = 100) -> list[AuditEvent]:
        """Get audit trail with optional filters."""
        filtered_trail = self.audit_trail

        if user_id:
            filtered_trail = [e for e in filtered_trail if e.user_id == user_id]

        if action:
            filtered_trail = [e for e in filtered_trail if e.action == action]

        if start_date:
            filtered_trail = [e for e in filtered_trail if e.timestamp >= start_date]

        if end_date:
            filtered_trail = [e for e in filtered_trail if e.timestamp <= end_date]

        # Sort by timestamp descending and limit
        filtered_trail.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_trail[:limit]

    def run_compliance_check(self, compliance_type: ComplianceType) -> ComplianceCheck:
        """Run a compliance check for the specified type."""
        check = self.compliance_checks.get(compliance_type)
        if not check:
            raise ValueError(f"Compliance check not found: {compliance_type}")

        findings = []
        recommendations = []

        # Run specific compliance checks
        if compliance_type == ComplianceType.GDPR:
            findings, recommendations = self._check_gdpr_compliance()
        elif compliance_type == ComplianceType.CCPA:
            findings, recommendations = self._check_ccpa_compliance()
        elif compliance_type == ComplianceType.HOUSING_LAW:
            findings, recommendations = self._check_housing_law_compliance()

        # Update check
        check.findings = findings
        check.recommendations = recommendations
        check.checked_at = utc_now()
        check.status = ComplianceStatus.COMPLIANT if not findings else ComplianceStatus.NON_COMPLIANT

        self.compliance_checks[compliance_type] = check

        # Update metrics
        self.metrics.last_audit = utc_now()
        self.metrics.open_issues = len(findings)

        return check

    def _check_gdpr_compliance(self) -> tuple[list[str], list[str]]:
        """Check GDPR compliance."""
        findings = []
        recommendations = []

        # Check for data minimization
        recent_events = self.get_audit_trail(limit=1000)
        if len(recent_events) > 100:
            findings.append("Large amount of data processed - review data minimization")
            recommendations.append("Implement data retention policies")

        # Check for proper consent
        user_events = [e for e in recent_events if e.action == AuditAction.DOCUMENT_ACCESS]
        if user_events:
            findings.append("Document access logged - ensure proper consent")
            recommendations.append("Review consent management system")

        return findings, recommendations

    def _check_ccpa_compliance(self) -> tuple[list[str], list[str]]:
        """Check CCPA compliance."""
        findings = []
        recommendations = []

        # Check for data export functionality
        export_events = [e for e in self.audit_trail if e.action == AuditAction.DATA_EXPORT]
        if not export_events:
            findings.append("No data export functionality detected")
            recommendations.append("Implement data export feature for CCPA compliance")

        return findings, recommendations

    def _check_housing_law_compliance(self) -> tuple[list[str], list[str]]:
        """Check housing law compliance."""
        findings = []
        recommendations = []

        # Check for proper legal form usage
        doc_events = [e for e in self.audit_trail if e.action == AuditAction.DOCUMENT_PROCESS]
        if doc_events:
            findings.append("Document processing detected - ensure legal compliance")
            recommendations.append("Review document processing against local housing laws")

        return findings, recommendations

    def get_compliance_report(self) -> dict[str, Any]:
        """Generate comprehensive compliance report."""
        report = {
            "generated_at": utc_now().isoformat(),
            "metrics": self.metrics.dict(),
            "compliance_checks": {},
            "recent_events": self.get_audit_trail(limit=50),
            "summary": {
                "total_checks": len(self.compliance_checks),
                "compliant_checks": sum(1 for c in self.compliance_checks.values() if c.status == ComplianceStatus.COMPLIANT),
                "non_compliant_checks": sum(1 for c in self.compliance_checks.values() if c.status == ComplianceStatus.NON_COMPLIANT),
                "pending_checks": sum(1 for c in self.compliance_checks.values() if c.status == ComplianceStatus.PENDING_REVIEW),
            }
        }

        for compliance_type, check in self.compliance_checks.items():
            report["compliance_checks"][compliance_type.value] = check.dict()

        # Calculate compliance score
        if report["summary"]["total_checks"] > 0:
            report["metrics"]["compliance_score"] = (
                report["summary"]["compliant_checks"] / report["summary"]["total_checks"]
            ) * 100

        return report

    def export_audit_data(self, user_id: str, format: str = "json") -> dict[str, Any]:
        """Export audit data for a user (GDPR/CCPA compliance)."""
        user_events = self.get_audit_trail(user_id=user_id)

        export_data = {
            "user_id": user_id,
            "export_date": utc_now().isoformat(),
            "total_events": len(user_events),
            "events": [event.dict() for event in user_events]
        }

        # Log the export
        self.log_audit_event(
            user_id=user_id,
            action=AuditAction.DATA_EXPORT,
            resource="audit_data",
            details={"format": format, "event_count": len(user_events)},
            success=True
        )

        return export_data


# Global instance
accountability_planner = AccountabilityPlanner()


# Decorator for automatic audit logging
def audit_action(action: AuditAction, resource: str = ""):
    """Decorator to automatically audit function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract user_id from kwargs or context
            user_id = kwargs.get('user_id') or getattr(args[0], 'user_id', None) if args else None

            try:
                result = func(*args, **kwargs)
                accountability_planner.log_audit_event(
                    user_id=user_id,
                    action=action,
                    resource=resource or func.__name__,
                    details={"args": str(args), "kwargs": str(kwargs)},
                    success=True
                )
                return result
            except Exception as e:
                accountability_planner.log_audit_event(
                    user_id=user_id,
                    action=action,
                    resource=resource or func.__name__,
                    details={"args": str(args), "kwargs": str(kwargs)},
                    success=False,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator
