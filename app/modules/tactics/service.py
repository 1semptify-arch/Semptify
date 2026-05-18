"""
Proactive Tactics Engine
Implements automated defense strategies from proactive_tactics.md

Features:
- Auto-flag rent escrow when 3+ habitability tags within 30 days
- Suggest retaliation counterclaim if eviction filed <30 days after complaint
- Provide expungement prompt when case dismissed
- Generate decision tree recommendations
- Track evidence preparation checklist
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TacticType(str, Enum):
    """Types of proactive tactics."""
    MOTION_DISMISS = "motion_dismiss"
    RENT_ESCROW = "rent_escrow"
    RETALIATION = "retaliation"
    CONTINUANCE = "continuance"
    EXPUNGEMENT = "expungement"


class UrgencyLevel(str, Enum):
    """Urgency levels for tactics."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConditionSeverity(str, Enum):
    """Severity levels for habitability conditions."""
    CRITICAL = "critical"      # No heat, sewage, mold - immediate escrow
    MAJOR = "major"            # Persistent leaks, broken locks - escrow after notice
    MODERATE = "moderate"      # Peeling paint, minor appliances - track & escalate
    PATTERN = "pattern"        # Multiple unresolved moderate issues - aggregate


@dataclass
class TacticRecommendation:
    """A recommended tactic with supporting context."""
    tactic_type: TacticType
    title: str
    urgency: UrgencyLevel
    reason: str
    action_items: List[str]
    deadline: Optional[datetime] = None
    evidence_needed: List[str] = field(default_factory=list)
    motion_template: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "tactic_type": self.tactic_type.value,
            "title": self.title,
            "urgency": self.urgency.value,
            "reason": self.reason,
            "action_items": self.action_items,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "evidence_needed": self.evidence_needed,
            "motion_template": self.motion_template,
        }


@dataclass
class EvidenceItem:
    """An item in the evidence preparation checklist."""
    name: str
    action: str
    category: str
    stored: bool = False
    document_id: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class RetaliationFlag:
    """A potential retaliation event."""
    protected_activity: str
    protected_date: datetime
    landlord_response: str
    response_date: datetime
    days_between: int
    flagged: bool  # True if <30 days


class ProactiveTacticsEngine:
    """
    Engine for generating proactive defense tactics.
    Analyzes case data and suggests appropriate motions/strategies.
    """
    
    # Service period thresholds (Minnesota)
    MIN_SERVICE_DAYS = 7
    
    # Retaliation proximity threshold
    RETALIATION_THRESHOLD_DAYS = 30
    
    # Habitability tag threshold for rent escrow
    HABITABILITY_TAG_THRESHOLD = 3
    HABITABILITY_WINDOW_DAYS = 30
    
    def __init__(self):
        self.evidence_checklist = self._build_evidence_checklist()
    
    def _build_evidence_checklist(self) -> List[EvidenceItem]:
        """Build the standard evidence preparation checklist."""
        return [
            EvidenceItem("Lease (all pages)", "Upload & hash certify", "core"),
            EvidenceItem("Rent ledger (tenant version)", "Build chronology, highlight payments", "financial"),
            EvidenceItem("Payment proofs (receipts, bank)", "Attach to ledger entries", "financial"),
            EvidenceItem("Repair request emails/texts", "Tag as habitability", "habitability"),
            EvidenceItem("Photos/videos of conditions", "Timestamp in vault", "habitability"),
            EvidenceItem("City inspection reports", "Upload PDF", "habitability"),
            EvidenceItem("Utility disruption logs", "Note dates & duration", "habitability"),
            EvidenceItem("Medical impact letters", "Collect if health affected", "hardship"),
            EvidenceItem("Hardship statements", "Prepare narrative", "hardship"),
        ]
    
    def analyze_service_timeline(
        self,
        service_date: datetime,
        hearing_date: datetime,
    ) -> Optional[TacticRecommendation]:
        """
        Check if service was less than 7 days before hearing.
        If so, recommend Motion to Dismiss.
        """
        days_between = (hearing_date - service_date).days
        
        if days_between < self.MIN_SERVICE_DAYS:
            return TacticRecommendation(
                tactic_type=TacticType.MOTION_DISMISS,
                title="Motion to Dismiss - Insufficient Service Time",
                urgency=UrgencyLevel.CRITICAL,
                reason=f"Service was only {days_between} days before hearing. Minnesota requires at least {self.MIN_SERVICE_DAYS} days.",
                action_items=[
                    "Draft Motion to Dismiss citing Minn. Stat. § 504B.321",
                    "Include proof of service date",
                    "File before or at hearing",
                ],
                deadline=hearing_date,
                evidence_needed=["Proof of service with date", "Summons showing hearing date"],
                motion_template="motion_dismiss_service",
            )
        return None
    
    def analyze_habitability_issues(
        self,
        timeline_events: List[Dict],
        tags: Optional[List[str]] = None,
    ) -> Optional[TacticRecommendation]:
        """
        Auto-flag rent escrow when 3+ habitability tags within 30 days.
        """
        cutoff = datetime.now() - timedelta(days=self.HABITABILITY_WINDOW_DAYS)
        
        # Count habitability-related events in window
        habitability_events = []
        for event in timeline_events:
            event_date = event.get("date") or event.get("event_date")
            if isinstance(event_date, str):
                try:
                    event_date = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
                except ValueError:
                    continue
            
            if event_date and event_date >= cutoff:
                event_tags = event.get("tags", [])
                event_type = event.get("event_type", "").lower()
                
                if "habitability" in event_tags or event_type in [
                    "repair_request", "condition_report", "inspection", "complaint"
                ]:
                    habitability_events.append(event)
        
        if len(habitability_events) >= self.HABITABILITY_TAG_THRESHOLD:
            # Determine severity
            severity = self._assess_condition_severity(habitability_events)
            
            return TacticRecommendation(
                tactic_type=TacticType.RENT_ESCROW,
                title="Rent Escrow Motion - Multiple Habitability Issues",
                urgency=UrgencyLevel.HIGH if severity in [ConditionSeverity.CRITICAL, ConditionSeverity.MAJOR] else UrgencyLevel.MEDIUM,
                reason=f"Found {len(habitability_events)} habitability issues in the past {self.HABITABILITY_WINDOW_DAYS} days. This supports a rent escrow motion.",
                action_items=[
                    "Document all habitability issues with photos/videos",
                    "Compile repair request history",
                    "Draft Rent Escrow Motion citing Minn. Stat. § 504B.385",
                    "File motion and pay rent into court escrow",
                ],
                evidence_needed=[
                    "Photos/videos of conditions",
                    "Written repair requests with dates",
                    "City inspection reports (if available)",
                    "Medical documentation (if health affected)",
                ],
                motion_template="motion_rent_escrow",
            )
        return None
    
    def _assess_condition_severity(self, events: List[Dict]) -> ConditionSeverity:
        """Assess the severity of habitability conditions."""
        critical_keywords = ["heat", "sewage", "mold", "no water", "gas leak", "fire"]
        major_keywords = ["leak", "lock", "plumbing", "electrical", "roof", "pest"]
        
        for event in events:
            description = (event.get("description", "") + " " + event.get("title", "")).lower()
            
            if any(kw in description for kw in critical_keywords):
                return ConditionSeverity.CRITICAL
        
        for event in events:
            description = (event.get("description", "") + " " + event.get("title", "")).lower()
            
            if any(kw in description for kw in major_keywords):
                return ConditionSeverity.MAJOR
        
        if len(events) >= 5:
            return ConditionSeverity.PATTERN
        
        return ConditionSeverity.MODERATE
    
    def analyze_retaliation(
        self,
        protected_activities: List[Dict],
        eviction_filed_date: datetime,
    ) -> Optional[TacticRecommendation]:
        """
        Suggest retaliation counterclaim if eviction filed <30 days after protected activity.
        
        Protected activities include:
        - Complaints to city/housing authority
        - Repair requests
        - Rent withholding (documented)
        - Organizing with other tenants
        """
        flags = []
        
        for activity in protected_activities:
            activity_date = activity.get("date")
            if isinstance(activity_date, str):
                try:
                    activity_date = datetime.fromisoformat(activity_date.replace("Z", "+00:00"))
                except ValueError:
                    continue
            
            if activity_date:
                days_until_filing = (eviction_filed_date - activity_date).days
                
                if 0 < days_until_filing <= self.RETALIATION_THRESHOLD_DAYS:
                    flags.append(RetaliationFlag(
                        protected_activity=activity.get("type", "Protected activity"),
                        protected_date=activity_date,
                        landlord_response="Eviction filing",
                        response_date=eviction_filed_date,
                        days_between=days_until_filing,
                        flagged=True,
                    ))
        
        if flags:
            closest = min(flags, key=lambda f: f.days_between)
            
            return TacticRecommendation(
                tactic_type=TacticType.RETALIATION,
                title="Retaliation Counterclaim",
                urgency=UrgencyLevel.HIGH,
                reason=f"Eviction filed only {closest.days_between} days after {closest.protected_activity}. This proximity suggests retaliation under Minn. Stat. § 504B.441.",
                action_items=[
                    "Document the timeline of protected activity → eviction",
                    "Gather evidence of the protected activity (emails, reports)",
                    "Draft Retaliation Counterclaim",
                    "Request treble damages if proven",
                ],
                evidence_needed=[
                    "Proof of protected activity with date",
                    "Eviction filing date",
                    "Any communications from landlord",
                ],
                motion_template="counterclaim_retaliation",
            )
        return None
    
    def analyze_continuance_triggers(
        self,
        hearing_date: datetime,
        pending_inspection: Optional[datetime] = None,
        rental_assistance_pending: bool = False,
        recent_medical_event: bool = False,
        new_evidence_discovered: bool = False,
    ) -> Optional[TacticRecommendation]:
        """
        Check if continuance should be requested.
        """
        reasons = []
        evidence = []
        
        if pending_inspection and pending_inspection > datetime.now():
            days_until = (pending_inspection - datetime.now()).days
            if days_until <= 7:
                reasons.append(f"Inspection scheduled in {days_until} days - need objective report")
                evidence.append("Scheduled inspection confirmation")
        
        if rental_assistance_pending:
            reasons.append("Awaiting rental assistance decision - funds may cure the issue")
            evidence.append("Rental assistance application receipt")
        
        if recent_medical_event:
            reasons.append("Recent medical event - hardship and fairness concerns")
            evidence.append("Medical documentation (brief note sufficient)")
        
        if new_evidence_discovered:
            reasons.append("Newly discovered evidence requires additional preparation")
            evidence.append("Description of new evidence")
        
        if reasons:
            return TacticRecommendation(
                tactic_type=TacticType.CONTINUANCE,
                title="Motion for Continuance",
                urgency=UrgencyLevel.MEDIUM,
                reason="; ".join(reasons),
                action_items=[
                    "Draft Motion for Continuance",
                    "Attach supporting documentation",
                    "File as soon as possible (before hearing if possible)",
                    "Propose a specific new date",
                ],
                deadline=hearing_date - timedelta(days=1),
                evidence_needed=evidence,
                motion_template="motion_continuance",
            )
        return None
    
    def analyze_expungement_eligibility(
        self,
        case_outcome: str,
        was_dismissed: bool = False,
        settlement_favorable: bool = False,
        hardship_documented: bool = False,
        procedural_defects: bool = False,
    ) -> Optional[TacticRecommendation]:
        """
        Provide expungement prompt when case outcome is favorable.
        """
        if was_dismissed or settlement_favorable:
            factors = []
            if was_dismissed:
                factors.append("Case was dismissed")
            if settlement_favorable:
                factors.append("Settlement was favorable to tenant")
            if hardship_documented:
                factors.append("Hardship has been documented")
            if procedural_defects:
                factors.append("Procedural defects were identified")
            
            return TacticRecommendation(
                tactic_type=TacticType.EXPUNGEMENT,
                title="Expungement Motion",
                urgency=UrgencyLevel.LOW,
                reason=f"Case outcome supports expungement: {', '.join(factors)}",
                action_items=[
                    "Wait for case to fully close",
                    "Gather supporting documentation",
                    "Draft Expungement Motion citing Minn. Stat. § 484.014",
                    "Include public interest argument",
                    "File motion with court",
                ],
                evidence_needed=[
                    "Dismissal order or settlement agreement",
                    "Employment/housing impact letters (if applicable)",
                    "Documentation of procedural defects",
                ],
                motion_template="motion_expungement",
            )
        return None
    
    def run_decision_tree(
        self,
        service_date: Optional[datetime] = None,
        hearing_date: Optional[datetime] = None,
        timeline_events: Optional[List[Dict]] = None,
        protected_activities: Optional[List[Dict]] = None,
        eviction_filed_date: Optional[datetime] = None,
        case_dismissed: bool = False,
        case_settled: bool = False,
        pending_inspection: Optional[datetime] = None,
        rental_assistance_pending: bool = False,
    ) -> List[TacticRecommendation]:
        """
        Run the full decision tree and return all applicable tactics.
        
        Decision Tree:
        1. Was service <7 days? → Motion to Dismiss
        2. ≥3 serious habitability issues? → Rent Escrow Motion
        3. Recent protected complaint (<30 days)? → Retaliation Counterclaim
        4. Pending objective evidence? → Continuance Motion
        5. Case dismissed or settled? → Expungement Motion
        """
        recommendations = []
        
        # 1. Check service timeline
        if service_date and hearing_date:
            rec = self.analyze_service_timeline(service_date, hearing_date)
            if rec:
                recommendations.append(rec)
        
        # 2. Check habitability issues
        if timeline_events:
            rec = self.analyze_habitability_issues(timeline_events)
            if rec:
                recommendations.append(rec)
        
        # 3. Check retaliation
        if protected_activities and eviction_filed_date:
            rec = self.analyze_retaliation(protected_activities, eviction_filed_date)
            if rec:
                recommendations.append(rec)
        
        # 4. Check continuance triggers
        if hearing_date:
            rec = self.analyze_continuance_triggers(
                hearing_date,
                pending_inspection=pending_inspection,
                rental_assistance_pending=rental_assistance_pending,
            )
            if rec:
                recommendations.append(rec)
        
        # 5. Check expungement eligibility
        if case_dismissed or case_settled:
            rec = self.analyze_expungement_eligibility(
                case_outcome="dismissed" if case_dismissed else "settled",
                was_dismissed=case_dismissed,
                settlement_favorable=case_settled,
            )
            if rec:
                recommendations.append(rec)
        
        # Sort by urgency
        urgency_order = {
            UrgencyLevel.CRITICAL: 0,
            UrgencyLevel.HIGH: 1,
            UrgencyLevel.MEDIUM: 2,
            UrgencyLevel.LOW: 3,
        }
        recommendations.sort(key=lambda r: urgency_order.get(r.urgency, 99))
        
        return recommendations
    
    def get_evidence_checklist(
        self,
        stored_documents: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Get the evidence preparation checklist with storage status.
        """
        checklist = []
        stored_types = set()
        
        if stored_documents:
            for doc in stored_documents:
                doc_type = doc.get("doc_type", "").lower()
                stored_types.add(doc_type)
        
        type_mapping = {
            "lease": "Lease (all pages)",
            "payment": "Payment proofs (receipts, bank)",
            "repair_request": "Repair request emails/texts",
            "photo": "Photos/videos of conditions",
            "inspection": "City inspection reports",
            "medical": "Medical impact letters",
        }
        
        for item in self.evidence_checklist:
            stored = any(
                item.name.lower() in doc_type or doc_type in item.name.lower()
                for doc_type in stored_types
            )
            checklist.append({
                "name": item.name,
                "action": item.action,
                "category": item.category,
                "stored": stored,
            })
        
        return checklist
    
    def get_pre_hearing_timeline(
        self,
        hearing_date: datetime,
    ) -> List[Dict]:
        """
        Generate pre-hearing tactical timeline.
        """
        now = datetime.now()
        days_until = (hearing_date - now).days
        
        actions = [
            {
                "timing": "Immediately after service",
                "action": "Reconstruct service timeline",
                "purpose": "Identify dismissal motion opportunity",
                "due": now,
                "completed": False,
            },
            {
                "timing": "Within 24 hours",
                "action": "Log all existing habitability issues",
                "purpose": "Support escrow/counterclaims",
                "due": now + timedelta(days=1),
                "completed": False,
            },
            {
                "timing": "3-5 days before hearing",
                "action": "Request inspection (if needed)",
                "purpose": "Creates pending evidence for continuance",
                "due": hearing_date - timedelta(days=4),
                "completed": False,
            },
            {
                "timing": "2-3 days before hearing",
                "action": "Draft motions (dismiss, continue, escrow)",
                "purpose": "Ready to deploy",
                "due": hearing_date - timedelta(days=2),
                "completed": False,
            },
            {
                "timing": "1-2 days before hearing",
                "action": "Organize exhibits folder (PDFs)",
                "purpose": "Efficient remote presentation",
                "due": hearing_date - timedelta(days=1),
                "completed": False,
            },
            {
                "timing": "Day before hearing",
                "action": "Tech check (camera/mic/bandwidth)",
                "purpose": "Prevent default via tech issues",
                "due": hearing_date - timedelta(days=1),
                "completed": False,
            },
        ]
        
        # Mark past items
        for action in actions:
            if action["due"] < now:
                action["overdue"] = True
            action["due"] = action["due"].isoformat()
        
        return actions


# Singleton instance
_tactics_engine: Optional[ProactiveTacticsEngine] = None


def get_tactics_engine() -> ProactiveTacticsEngine:
    """Get the singleton ProactiveTacticsEngine instance."""
    global _tactics_engine
    if _tactics_engine is None:
        _tactics_engine = ProactiveTacticsEngine()
    return _tactics_engine
