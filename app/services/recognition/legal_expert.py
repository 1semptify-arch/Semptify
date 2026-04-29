"""
Minnesota Tenant Law Expert
===========================

Domain-specific knowledge engine for Minnesota tenant law.
Provides legal analysis, issue detection, and compliance checking.

Key Minnesota Statutes Covered:
- Minn. Stat. § 504B.135 - Residential lease terms
- Minn. Stat. § 504B.145 - Unlawful exclusion from premises
- Minn. Stat. § 504B.171 - Tenants' notice to quit
- Minn. Stat. § 504B.175 - Security deposits
- Minn. Stat. § 504B.178 - Landlord's right to enter
- Minn. Stat. § 504B.211 - Action for recovery of premises
- Minn. Stat. § 504B.285 - Eviction actions
- Minn. Stat. § 504B.321 - Remedies for tenant
- Minn. Stat. § 504B.345 - Retaliation prohibited
- Minn. Stat. § 504B.375 - Emergency tenant remedies
- Minn. Stat. § 504B.385 - Rent escrow
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum

from .models import (
    LegalIssue, IssueSeverity, DocumentType, DocumentCategory,
    ExtractedEntity, EntityType, PartyRole,
    ReasoningChain, ReasoningStep, ReasoningType,
    TimelineEntry,
)


class IssueType(Enum):
    """Types of legal issues that can be detected"""
    IMPROPER_NOTICE_PERIOD = "improper_notice_period"
    NOTICE_NOT_SERVED_PROPERLY = "notice_not_served_properly"
    ILLEGAL_LATE_FEE = "illegal_late_fee"
    ILLEGAL_LOCKOUT = "illegal_lockout"
    RETALIATION = "retaliation"
    HABITABILITY = "habitability"
    SECURITY_DEPOSIT_VIOLATION = "security_deposit_violation"
    ILLEGAL_ENTRY = "illegal_entry"
    DISCRIMINATION = "discrimination"
    RENT_ESCROW_ELIGIBLE = "rent_escrow_eligible"
    COURT_DEADLINE = "court_deadline"
    PROCEDURAL_DEFECT = "procedural_defect"
    MISSING_REQUIRED_INFO = "missing_required_info"
    STATUTE_OF_LIMITATIONS = "statute_of_limitations"


@dataclass
class MinnesotaStatute:
    """Minnesota statute reference"""
    section: str
    title: str
    summary: str
    key_provisions: List[str] = field(default_factory=list)
    tenant_protections: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    penalties: List[str] = field(default_factory=list)


@dataclass
class NoticeRequirement:
    """Notice period requirements by situation"""
    notice_type: str
    days_required: int
    statute: str
    exceptions: List[str] = field(default_factory=list)
    service_requirements: List[str] = field(default_factory=list)


class MinnesotaTenantLawExpert:
    """
    Expert system for Minnesota tenant law.
    
    Provides:
    - Legal issue detection specific to MN law
    - Notice period compliance checking
    - Security deposit rule validation
    - Eviction defense identification
    - Court deadline calculation
    """
    
    def __init__(self):
        self.statutes = self._load_statutes()
        self.notice_requirements = self._load_notice_requirements()
        self.issue_patterns = self._build_issue_patterns()
        self.defense_patterns = self._build_defense_patterns()
        
    def _load_statutes(self) -> Dict[str, MinnesotaStatute]:
        """Load Minnesota tenant law statutes"""
        return {
            "504B.135": MinnesotaStatute(
                section="504B.135",
                title="Terms of residential lease",
                summary="Governs automatic renewal and required lease terms",
                key_provisions=[
                    "Written lease required for terms over 1 year",
                    "Automatic renewal provisions must be conspicuous",
                    "30-day minimum notice for non-renewal on month-to-month",
                ],
                tenant_protections=[
                    "Lease cannot waive statutory tenant rights",
                    "Unconscionable terms unenforceable",
                ],
            ),
            "504B.145": MinnesotaStatute(
                section="504B.145",
                title="Unlawful exclusion from premises",
                summary="Prohibits landlord self-help eviction (lockouts)",
                key_provisions=[
                    "Cannot remove tenant's belongings without court order",
                    "Cannot change locks to exclude tenant",
                    "Cannot interrupt utilities",
                ],
                tenant_protections=[
                    "Tenant may sue for actual damages",
                    "May recover up to $500 statutory damages",
                    "May recover attorney fees",
                ],
                violations=[
                    "Changing locks without court order",
                    "Removing tenant's property",
                    "Shutting off utilities",
                    "Threats of illegal lockout",
                ],
                penalties=[
                    "Actual damages",
                    "Up to $500 statutory damages",
                    "Attorney fees",
                    "Criminal misdemeanor possible",
                ],
            ),
            "504B.171": MinnesotaStatute(
                section="504B.171",
                title="Notice to quit",
                summary="Tenant's ability to terminate lease with notice",
                key_provisions=[
                    "Month-to-month requires one full rental period notice",
                    "Notice must be in writing",
                ],
            ),
            "504B.175": MinnesotaStatute(
                section="504B.175",
                title="Security deposits",
                summary="Rules for security deposit handling",
                key_provisions=[
                    "Return within 21 days after termination",
                    "Must provide itemized list of deductions",
                    "Interest required on deposits held over 12 months (Minneapolis/St. Paul)",
                    "Cannot exceed amount equal to one month's rent",
                ],
                tenant_protections=[
                    "Bad faith retention = penalty of up to $500 plus deposit",
                    "Failure to itemize within 21 days = forfeit right to withhold",
                ],
                violations=[
                    "Failing to return within 21 days",
                    "No itemization of deductions",
                    "Excessive security deposit",
                    "Using deposit for normal wear and tear",
                ],
            ),
            "504B.178": MinnesotaStatute(
                section="504B.178",
                title="Landlord right to enter",
                summary="Limits on landlord entry to rental unit",
                key_provisions=[
                    "Reasonable notice required (typically 24 hours)",
                    "Entry only at reasonable times",
                    "Limited purposes: repairs, inspections, showings",
                ],
                tenant_protections=[
                    "Can refuse entry without proper notice",
                    "May sue for harassment",
                ],
                violations=[
                    "Entering without notice",
                    "Entering at unreasonable hours",
                    "Frequent unnecessary entries",
                ],
            ),
            "504B.211": MinnesotaStatute(
                section="504B.211",
                title="Action for recovery of premises",
                summary="Eviction procedure requirements",
                key_provisions=[
                    "Must give proper written notice before filing",
                    "14-day notice for nonpayment of rent",
                    "Notice must state amount owed",
                    "Tenant can cure by paying before notice expires",
                ],
                tenant_protections=[
                    "Right to cure nonpayment within 14 days",
                    "Proper service of notice required",
                ],
            ),
            "504B.285": MinnesotaStatute(
                section="504B.285",
                title="Eviction actions",
                summary="Court procedures for eviction",
                key_provisions=[
                    "Summons must be served at least 7 days before hearing",
                    "Tenant has right to request jury trial",
                    "Court can stay eviction for up to 7 days in hardship cases",
                ],
                tenant_protections=[
                    "Right to appear and contest",
                    "Right to jury trial on request",
                    "Hardship stay available",
                ],
            ),
            "504B.321": MinnesotaStatute(
                section="504B.321",
                title="Tenant remedies for housing violations",
                summary="Tenant rights when landlord fails to maintain",
                key_provisions=[
                    "Must give landlord reasonable time to repair",
                    "Can deduct repair costs from rent if landlord fails",
                    "Can terminate lease for material violations",
                ],
                tenant_protections=[
                    "Right to habitable premises",
                    "Right to deduct repairs from rent",
                    "Right to terminate for habitability issues",
                ],
            ),
            "504B.345": MinnesotaStatute(
                section="504B.345",
                title="Retaliation prohibited",
                summary="Landlord cannot retaliate against tenant for exercising rights",
                key_provisions=[
                    "Cannot evict for complaints to government",
                    "Cannot raise rent in retaliation",
                    "Cannot decrease services in retaliation",
                    "Presumption of retaliation within 90 days of protected activity",
                ],
                tenant_protections=[
                    "90-day presumption period for retaliation claims",
                    "Can use as defense to eviction",
                    "Can sue for damages",
                ],
                violations=[
                    "Eviction within 90 days of complaint",
                    "Rent increase after repair request",
                    "Threats after exercising rights",
                ],
            ),
            "504B.375": MinnesotaStatute(
                section="504B.375",
                title="Emergency tenant remedies",
                summary="Immediate remedies for serious violations",
                key_provisions=[
                    "Available for loss of essential services",
                    "Heat, running water, hot water, electricity, sanitation",
                    "Tenant can get emergency relief from court",
                ],
                tenant_protections=[
                    "Quick court action available",
                    "May recover costs and damages",
                ],
            ),
            "504B.385": MinnesotaStatute(
                section="504B.385",
                title="Rent escrow",
                summary="Tenant can pay rent to court instead of landlord",
                key_provisions=[
                    "Available when landlord fails to maintain",
                    "Must document violations",
                    "Rent held by court until issues resolved",
                ],
                tenant_protections=[
                    "Protection from eviction while escrowing",
                    "Pressure on landlord to make repairs",
                ],
            ),
        }
    
    def _load_notice_requirements(self) -> Dict[str, NoticeRequirement]:
        """Load notice period requirements"""
        return {
            "nonpayment_cure": NoticeRequirement(
                notice_type="Nonpayment of Rent",
                days_required=14,
                statute="504B.291",
                exceptions=["Emergency holds for subsidized housing"],
                service_requirements=[
                    "In writing",
                    "Delivered personally or by mail",
                    "Must state amount owed",
                    "Must state cure deadline",
                ],
            ),
            "lease_violation_cure": NoticeRequirement(
                notice_type="Lease Violation",
                days_required=14,
                statute="504B.285",
                service_requirements=[
                    "In writing",
                    "Describe violation specifically",
                    "State deadline to cure",
                ],
            ),
            "month_to_month_termination": NoticeRequirement(
                notice_type="Month-to-Month Termination",
                days_required=30,
                statute="504B.135",
                exceptions=["Local ordinances may require longer"],
                service_requirements=[
                    "One full rental period notice",
                    "In writing",
                    "Effective at end of rental period",
                ],
            ),
            "holdover": NoticeRequirement(
                notice_type="Holdover After Lease End",
                days_required=0,
                statute="504B.291",
                service_requirements=[
                    "No notice required if lease properly terminated",
                ],
            ),
            "material_breach": NoticeRequirement(
                notice_type="Material Lease Breach",
                days_required=0,
                statute="504B.285",
                exceptions=[
                    "Immediate for conduct endangering safety",
                    "Immediate for drug-related criminal activity",
                ],
            ),
            "subsidized_housing": NoticeRequirement(
                notice_type="Subsidized Housing Termination",
                days_required=30,
                statute="504B.285 / Federal law",
                exceptions=["Shorter for serious violations"],
                service_requirements=[
                    "Must comply with federal requirements",
                    "Must state reason for termination",
                    "Must inform of right to contest",
                ],
            ),
        }
    
    def _build_issue_patterns(self) -> Dict[IssueType, List[Dict[str, Any]]]:
        """Build patterns for detecting legal issues"""
        return {
            IssueType.IMPROPER_NOTICE_PERIOD: [
                {
                    "pattern": r"(?i)(?:3|three|5|five|7|seven|10|ten)[\s-]?days?\s+(?:notice|to\s+(?:vacate|quit))",
                    "description": "Notice period may be too short",
                    "severity": IssueSeverity.HIGH,
                    "statute": "504B.291",
                },
                {
                    "pattern": r"(?i)immediate(?:ly)?.*(?:vacate|leave|quit)",
                    "description": "Immediate eviction without court order is illegal",
                    "severity": IssueSeverity.CRITICAL,
                    "statute": "504B.145",
                },
            ],
            IssueType.ILLEGAL_LOCKOUT: [
                {
                    "pattern": r"(?i)(?:change|changed|changing)\s+(?:the\s+)?locks?",
                    "description": "Changing locks without court order is illegal lockout",
                    "severity": IssueSeverity.CRITICAL,
                    "statute": "504B.145",
                },
                {
                    "pattern": r"(?i)(?:remove|removing|disposed?\s+of)\s+(?:your\s+)?(?:belongings|property|possessions)",
                    "description": "Removing tenant property without court order is illegal",
                    "severity": IssueSeverity.CRITICAL,
                    "statute": "504B.145",
                },
                {
                    "pattern": r"(?i)(?:shut|turn|cutting)\s+(?:off|down)\s+(?:utilities|power|electricity|water|heat|gas)",
                    "description": "Shutting off utilities to force tenant out is illegal",
                    "severity": IssueSeverity.CRITICAL,
                    "statute": "504B.145",
                },
            ],
            IssueType.ILLEGAL_LATE_FEE: [
                {
                    "pattern": r"\$\s*(?:[2-9]\d{2}|\d{4,})\s*(?:late|fee)",
                    "description": "Late fee appears excessive",
                    "severity": IssueSeverity.MEDIUM,
                    "statute": "504B.177",
                },
                {
                    "pattern": r"(?i)(?:8|9|10)\s*%.*(?:late|fee|charge)",
                    "description": "Percentage-based late fee may be excessive",
                    "severity": IssueSeverity.MEDIUM,
                    "statute": "504B.177",
                },
            ],
            IssueType.RETALIATION: [
                {
                    "pattern": r"(?i)(?:because|after|since)\s+(?:you|tenant)\s+(?:complained|reported|called|contacted)",
                    "description": "Possible retaliation for exercising tenant rights",
                    "severity": IssueSeverity.HIGH,
                    "statute": "504B.345",
                },
                {
                    "pattern": r"(?i)(?:inspection|inspector|code\s+enforcement).*(?:evict|terminate|notice)",
                    "description": "Possible retaliation for code enforcement complaints",
                    "severity": IssueSeverity.HIGH,
                    "statute": "504B.345",
                },
            ],
            IssueType.HABITABILITY: [
                {
                    "pattern": r"(?i)(?:no|broken|not\s+working|out\s+of)\s+(?:heat|hot\s+water|running\s+water|electricity)",
                    "description": "Essential service issue - habitability violation",
                    "severity": IssueSeverity.HIGH,
                    "statute": "504B.161",
                },
                {
                    "pattern": r"(?i)(?:mold|rodent|mice|rat|cockroach|bed\s*bug|pest|infestation)",
                    "description": "Health hazard - habitability issue",
                    "severity": IssueSeverity.HIGH,
                    "statute": "504B.161",
                },
                {
                    "pattern": r"(?i)(?:leak|leaking|water\s+damage|flooding)",
                    "description": "Water damage - habitability concern",
                    "severity": IssueSeverity.MEDIUM,
                    "statute": "504B.161",
                },
            ],
            IssueType.SECURITY_DEPOSIT_VIOLATION: [
                {
                    "pattern": r"(?i)deposit.*(?:will\s+not|won't|cannot|refused?\s+to)\s+(?:be\s+)?return",
                    "description": "Deposit retention may be improper",
                    "severity": IssueSeverity.MEDIUM,
                    "statute": "504B.178",
                },
                {
                    "pattern": r"(?i)normal\s+wear.*(?:deduct|charge|withhold)",
                    "description": "Cannot deduct for normal wear and tear",
                    "severity": IssueSeverity.MEDIUM,
                    "statute": "504B.178",
                },
            ],
            IssueType.ILLEGAL_ENTRY: [
                {
                    "pattern": r"(?i)(?:entered|entering|came\s+in|went\s+into).*(?:without|no)\s+(?:permission|notice|consent)",
                    "description": "Landlord may have entered illegally",
                    "severity": IssueSeverity.MEDIUM,
                    "statute": "504B.211",
                },
            ],
            IssueType.PROCEDURAL_DEFECT: [
                {
                    "pattern": r"(?i)(?:oral|verbal|verbally)\s+(?:notice|told|informed)",
                    "description": "Notice must be in writing",
                    "severity": IssueSeverity.HIGH,
                    "statute": "504B.321",
                },
            ],
            IssueType.MISSING_REQUIRED_INFO: [
                {
                    "pattern": r"(?i)evict.*(?:without|no)\s+(?:reason|cause|explanation)",
                    "description": "Notice may lack required information",
                    "severity": IssueSeverity.MEDIUM,
                    "statute": "504B.285",
                },
            ],
        }
    
    def _build_defense_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build patterns for identifying potential defenses"""
        return {
            "retaliation_defense": {
                "triggers": [
                    r"(?i)(?:repair|maintenance)\s+request.*(?:\d{1,2}|one|two|three)\s*(?:weeks?|months?)\s*(?:ago|before|prior)",
                    r"(?i)(?:complained|reported).*(?:code|inspector|health|safety)",
                ],
                "timeframe_days": 90,
                "statute": "504B.345",
                "description": "Retaliation defense - eviction within 90 days of protected activity",
            },
            "habitability_defense": {
                "triggers": [
                    r"(?i)(?:no|broken|lack\s+of)\s+(?:heat|hot\s+water|water|electricity)",
                    r"(?i)(?:mold|infestation|unsafe|hazardous)",
                ],
                "statute": "504B.161",
                "description": "Habitability defense - landlord failed to maintain habitable conditions",
            },
            "improper_notice_defense": {
                "triggers": [
                    r"(?i)(?:7|5|3|seven|five|three)\s*[-\s]?days?\s*notice",
                    r"(?i)(?:never\s+received|didn't\s+get|no)\s+(?:written\s+)?notice",
                ],
                "statute": "504B.321",
                "description": "Improper notice defense - notice requirements not met",
            },
            "payment_cure_defense": {
                "triggers": [
                    r"(?i)(?:paid|payment|paid\s+off).*(?:before|within|prior)",
                    r"(?i)(?:offered|tried)\s+to\s+pay",
                ],
                "statute": "504B.291",
                "description": "Payment cure defense - tenant cured default within notice period",
            },
            "waiver_defense": {
                "triggers": [
                    r"(?i)(?:accepted|took|received)\s+(?:partial\s+)?(?:rent|payment)",
                ],
                "statute": "504B.291",
                "description": "Waiver defense - landlord accepted rent after notice period",
            },
        }
    
    async def analyze(self, text: str, entities: List[ExtractedEntity],
                      document_type: DocumentType,
                      timeline: List[TimelineEntry]) -> Tuple[
        List[LegalIssue], 
        List[str],  # applicable statutes
        List[str],  # defense options
        ReasoningChain
    ]:
        """
        Perform legal analysis on document.
        
        Returns:
            Tuple of (issues, applicable_statutes, defense_options, reasoning_chain)
        """
        reasoning = ReasoningChain(pass_number=1)
        reasoning.add_step(
            ReasoningType.LEGAL_RULE,
            "Beginning Minnesota tenant law analysis",
            {"document_type": document_type.value},
            {}
        )
        
        issues = []
        applicable_statutes = set()
        defense_options = []
        
        # Step 1: Detect legal issues
        detected_issues = await self._detect_issues(text, entities, document_type, reasoning)
        issues.extend(detected_issues)
        
        # Step 2: Check notice compliance if applicable
        if document_type in [DocumentType.EVICTION_NOTICE, DocumentType.NOTICE_TO_QUIT,
                            DocumentType.NOTICE_TO_VACATE, DocumentType.FOURTEEN_DAY_NOTICE,
                            DocumentType.THIRTY_DAY_NOTICE]:
            notice_issues, notice_statutes = await self._check_notice_compliance(
                text, entities, document_type, timeline, reasoning
            )
            issues.extend(notice_issues)
            applicable_statutes.update(notice_statutes)
        
        # Step 3: Check for defenses
        defenses = await self._identify_defenses(text, entities, document_type, reasoning)
        defense_options.extend(defenses)
        
        # Step 4: Add applicable statutes from issues
        for issue in issues:
            if issue.mn_statute:
                applicable_statutes.add(issue.mn_statute)
            applicable_statutes.update(issue.legal_basis)
        
        # Step 5: Calculate urgency and deadlines
        await self._calculate_urgency(issues, timeline, reasoning)
        
        reasoning.completed_at = datetime.now()
        reasoning.conclusion = f"Found {len(issues)} legal issues, {len(defense_options)} potential defenses"
        reasoning.new_findings = [issue.title for issue in issues[:5]]
        
        return issues, list(applicable_statutes), defense_options, reasoning
    
    async def _detect_issues(self, text: str, entities: List[ExtractedEntity],
                             document_type: DocumentType,
                             reasoning: ReasoningChain) -> List[LegalIssue]:
        """Detect legal issues using patterns"""
        issues = []
        
        for issue_type, patterns in self.issue_patterns.items():
            for pattern_def in patterns:
                matches = re.finditer(pattern_def["pattern"], text)
                
                for match in matches:
                    # Get surrounding context
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]
                    
                    issue = LegalIssue(
                        issue_type=issue_type.value,
                        title=pattern_def["description"],
                        description=f"Found in text: '{match.group()}'",
                        severity=pattern_def["severity"],
                        mn_statute=pattern_def.get("statute"),
                        legal_basis=[f"Minn. Stat. § {pattern_def.get('statute')}"] if pattern_def.get("statute") else [],
                        supporting_text=context,
                        text_location=(match.start(), match.end()),
                        confidence=0.85,
                        reasoning=f"Matched pattern for {issue_type.value}",
                    )
                    
                    # Add recommended actions based on issue type
                    issue.recommended_actions = self._get_actions_for_issue(issue_type)
                    
                    # Add defense strategies
                    issue.defense_available = self._has_defense(issue_type)
                    if issue.defense_available:
                        issue.defense_strategies = self._get_defense_strategies(issue_type)
                    
                    issues.append(issue)
        
        reasoning.add_step(
            ReasoningType.LEGAL_RULE,
            f"Detected {len(issues)} potential legal issues",
            {},
            {"issue_types": list(set(i.issue_type for i in issues))},
            confidence_impact=len(issues) * 2
        )
        
        return issues
    
    async def _check_notice_compliance(self, text: str, entities: List[ExtractedEntity],
                                       document_type: DocumentType,
                                       timeline: List[TimelineEntry],
                                       reasoning: ReasoningChain) -> Tuple[List[LegalIssue], Set[str]]:
        """Check if notice complies with Minnesota requirements"""
        issues = []
        statutes = set()
        
        # Determine notice type
        notice_req = None
        text_lower = text.lower()
        
        if "nonpayment" in text_lower or "rent" in text_lower:
            notice_req = self.notice_requirements.get("nonpayment_cure")
        elif "violation" in text_lower or "breach" in text_lower:
            notice_req = self.notice_requirements.get("lease_violation_cure")
        elif "month-to-month" in text_lower or "month to month" in text_lower:
            notice_req = self.notice_requirements.get("month_to_month_termination")
        elif document_type == DocumentType.FOURTEEN_DAY_NOTICE:
            notice_req = self.notice_requirements.get("nonpayment_cure")
        elif document_type == DocumentType.THIRTY_DAY_NOTICE:
            notice_req = self.notice_requirements.get("month_to_month_termination")
        
        if notice_req:
            statutes.add(notice_req.statute)
            
            # Check notice period mentioned in document
            period_match = re.search(r"(\d+)\s*[-\s]?days?", text, re.IGNORECASE)
            if period_match:
                stated_days = int(period_match.group(1))
                required_days = notice_req.days_required
                
                if stated_days < required_days:
                    issue = LegalIssue(
                        issue_type=IssueType.IMPROPER_NOTICE_PERIOD.value,
                        title="Notice period too short",
                        description=f"Notice states {stated_days} days, but Minnesota law requires {required_days} days for {notice_req.notice_type}",
                        severity=IssueSeverity.HIGH,
                        mn_statute=notice_req.statute,
                        legal_basis=[f"Minn. Stat. § {notice_req.statute}"],
                        confidence=0.9,
                        reasoning=f"Stated {stated_days} days vs required {required_days} days",
                        defense_available=True,
                        defense_strategies=["Challenge notice as insufficient", 
                                           "Request dismissal for improper notice"],
                        recommended_actions=[
                            f"Note that proper notice should be {required_days} days",
                            "Consider challenging the notice in court",
                            "Consult with legal aid about notice defenses",
                        ],
                    )
                    issues.append(issue)
            
            # Check for required content
            for requirement in notice_req.service_requirements:
                if "amount" in requirement.lower():
                    # Check if amount is stated
                    money_entities = [e for e in entities if e.entity_type == EntityType.MONEY]
                    if not money_entities:
                        issue = LegalIssue(
                            issue_type=IssueType.MISSING_REQUIRED_INFO.value,
                            title="Notice missing required information",
                            description="Notice should state the specific amount owed",
                            severity=IssueSeverity.MEDIUM,
                            mn_statute=notice_req.statute,
                            legal_basis=[f"Minn. Stat. § {notice_req.statute}"],
                            confidence=0.7,
                            reasoning="No money amount found in notice",
                            recommended_actions=["Request specific amount from landlord"],
                        )
                        issues.append(issue)
        
        reasoning.add_step(
            ReasoningType.LEGAL_RULE,
            f"Checked notice compliance: {len(issues)} issues found",
            {"notice_type": notice_req.notice_type if notice_req else "unknown"},
            {"issues_found": len(issues)},
        )
        
        return issues, statutes
    
    async def _identify_defenses(self, text: str, entities: List[ExtractedEntity],
                                 document_type: DocumentType,
                                 reasoning: ReasoningChain) -> List[str]:
        """Identify potential legal defenses"""
        defenses = []
        
        for defense_name, defense_def in self.defense_patterns.items():
            for trigger in defense_def["triggers"]:
                if re.search(trigger, text, re.IGNORECASE):
                    defenses.append(defense_def["description"])
                    break
        
        # Add document-type specific defenses
        if document_type in [DocumentType.EVICTION_NOTICE, DocumentType.SUMMONS]:
            # Check for common eviction defenses
            text_lower = text.lower()
            
            if "rent" in text_lower and any(e.entity_type == EntityType.MONEY for e in entities):
                defenses.append("Consider whether rent was actually owed - verify amounts")
            
            if "lease" not in text_lower:
                defenses.append("Request copy of lease to verify terms")
        
        reasoning.add_step(
            ReasoningType.LEGAL_RULE,
            f"Identified {len(defenses)} potential defenses",
            {},
            {"defenses": defenses},
            confidence_impact=len(defenses) * 3
        )
        
        return list(set(defenses))
    
    async def _calculate_urgency(self, issues: List[LegalIssue], 
                                 timeline: List[TimelineEntry],
                                 reasoning: ReasoningChain):
        """Calculate urgency based on deadlines and issue severity"""
        today = date.today()
        
        # Find nearest deadline
        deadlines = [t for t in timeline if t.is_deadline and t.event_date]
        if deadlines:
            nearest = min(deadlines, key=lambda t: t.event_date)
            days_until = (nearest.event_date - today).days
            
            for issue in issues:
                if issue.is_deadline or issue.issue_type == IssueType.COURT_DEADLINE.value:
                    issue.deadline = nearest.event_date
                    issue.days_to_act = days_until
        
        # Check for court dates
        court_dates = [t for t in timeline if t.is_court_date and t.event_date]
        if court_dates:
            nearest_court = min(court_dates, key=lambda t: t.event_date)
            days_until_court = (nearest_court.event_date - today).days
            
            if days_until_court <= 7:
                # Add critical court deadline issue
                court_issue = LegalIssue(
                    issue_type=IssueType.COURT_DEADLINE.value,
                    title="Court date approaching",
                    description=f"Court date in {days_until_court} days",
                    severity=IssueSeverity.CRITICAL,
                    deadline=nearest_court.event_date,
                    days_to_act=days_until_court,
                    confidence=0.95,
                    recommended_actions=[
                        "Prepare for court appearance",
                        "Gather evidence and documentation",
                        "Contact legal aid if not represented",
                    ],
                )
                issues.append(court_issue)
    
    def _get_actions_for_issue(self, issue_type: IssueType) -> List[str]:
        """Get recommended actions for an issue type"""
        actions = {
            IssueType.IMPROPER_NOTICE_PERIOD: [
                "Do not vacate until proper notice is given",
                "Document the improper notice",
                "Consult with legal aid about challenging the notice",
            ],
            IssueType.ILLEGAL_LOCKOUT: [
                "Call police - lockouts are illegal in Minnesota",
                "Document everything (photos, videos, witnesses)",
                "File emergency motion with court if needed",
                "Contact legal aid immediately",
            ],
            IssueType.ILLEGAL_LATE_FEE: [
                "Request itemization of all fees",
                "Challenge excessive fees in court",
                "Document all payments made",
            ],
            IssueType.RETALIATION: [
                "Document timeline of events",
                "Gather evidence of protected activity",
                "Consult legal aid about retaliation defense",
            ],
            IssueType.HABITABILITY: [
                "Document all conditions (photos, videos)",
                "Request repairs in writing",
                "Contact housing inspections if no response",
                "Consider rent escrow if serious",
            ],
            IssueType.SECURITY_DEPOSIT_VIOLATION: [
                "Request itemized list of deductions",
                "Document condition at move-out (photos)",
                "Send demand letter if deposit not returned in 21 days",
            ],
        }
        return actions.get(issue_type, ["Consult with legal aid"])
    
    def _has_defense(self, issue_type: IssueType) -> bool:
        """Check if issue type has associated defense"""
        return issue_type in [
            IssueType.IMPROPER_NOTICE_PERIOD,
            IssueType.ILLEGAL_LOCKOUT,
            IssueType.RETALIATION,
            IssueType.HABITABILITY,
            IssueType.PROCEDURAL_DEFECT,
        ]
    
    def _get_defense_strategies(self, issue_type: IssueType) -> List[str]:
        """Get defense strategies for an issue type"""
        strategies = {
            IssueType.IMPROPER_NOTICE_PERIOD: [
                "Motion to dismiss for defective notice",
                "Challenge notice compliance at hearing",
            ],
            IssueType.ILLEGAL_LOCKOUT: [
                "Emergency motion to restore possession",
                "Counterclaim for damages",
                "Demand statutory penalty",
            ],
            IssueType.RETALIATION: [
                "Assert retaliation as affirmative defense",
                "Document protected activity timeline",
                "90-day presumption under § 504B.345",
            ],
            IssueType.HABITABILITY: [
                "Rent escrow action",
                "Counterclaim for repairs",
                "Defense to nonpayment action",
            ],
            IssueType.PROCEDURAL_DEFECT: [
                "Motion to dismiss for improper service",
                "Challenge jurisdiction",
            ],
        }
        return strategies.get(issue_type, [])
    
    def get_statute_info(self, section: str) -> Optional[MinnesotaStatute]:
        """Get information about a Minnesota statute"""
        return self.statutes.get(section)
    
    def get_notice_requirement(self, notice_type: str) -> Optional[NoticeRequirement]:
        """Get notice requirement by type"""
        return self.notice_requirements.get(notice_type)
    
    def calculate_deadline(self, notice_date: date, notice_type: str) -> Optional[date]:
        """Calculate compliance deadline from notice date"""
        req = self.notice_requirements.get(notice_type)
        if req:
            return notice_date + timedelta(days=req.days_required)
        return None
    
    def get_all_applicable_statutes(self, document_type: DocumentType) -> List[str]:
        """Get all potentially applicable statutes for a document type"""
        statute_map = {
            DocumentType.EVICTION_NOTICE: ["504B.291", "504B.321", "504B.345"],
            DocumentType.NOTICE_TO_QUIT: ["504B.291", "504B.321"],
            DocumentType.SUMMONS: ["504B.285", "504B.291", "504B.321", "504B.345"],
            DocumentType.LEASE: ["504B.135", "504B.161", "504B.175", "504B.178"],
            DocumentType.SECURITY_DEPOSIT_ITEMIZATION: ["504B.175", "504B.178"],
            DocumentType.REPAIR_REQUEST: ["504B.161", "504B.321", "504B.375", "504B.385"],
        }
        return statute_map.get(document_type, ["504B.001"])
