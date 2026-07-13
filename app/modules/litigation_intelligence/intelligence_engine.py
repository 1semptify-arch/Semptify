"""
Litigation Intelligence Engine - Case Analysis & Pattern Detection
=========================================================

Turns raw case data into actionable intelligence for housing rights cases.
Detects patterns, scores risks, and provides strategic insights.
"""

import logging
from app.core.utc import utc_now
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
import re
from enum import Enum

logger = logging.getLogger(__name__)

class PatternType(Enum):
    """Types of legal patterns detected."""
    REPEAT_OFFENDER = "repeat_offender"
    SERIAL_FILER = "serial_filer"
    FRIVOLOUS_CLAIM = "frivolous_claim"
    PROFESSIONAL_LANDLORD = "professional_landlord"
    RETALIATION_PATTERN = "retaliation_pattern"
    HABITABILITY_ISSUE = "habitability_issue"
    DISCRIMINATION_PATTERN = "discrimination_pattern"
    CIVIL_RIGHTS_VIOLATION = "civil_rights_violation"

class RiskLevel(Enum):
    """Risk assessment levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"

@dataclass
class PatternMatch:
    """Detected legal pattern."""
    pattern_type: PatternType
    confidence: float
    description: str
    affected_parties: List[str]
    legal_basis: Optional[str]
    precedent_cases: List[str]
    recommended_actions: List[str]

@dataclass
class RiskAssessment:
    """Risk assessment for a case."""
    risk_level: RiskLevel
    risk_score: float
    risk_factors: List[str]
    mitigation_strategies: List[str]
    escalation_triggers: List[str]
    estimated_outcomes: Dict[str, float]

@dataclass
class IntelligenceReport:
    """Complete intelligence report for a case."""
    case_id: str
    analysis_date: datetime
    patterns_detected: List[PatternMatch]
    risk_assessment: RiskAssessment
    timeline_predictions: List[Dict[str, Any]]
    strategic_recommendations: List[str]
    evidence_gaps: List[str]
    success_probability: float

class LitigationIntelligenceEngine:
    """Main intelligence engine for housing rights cases."""
    
    def __init__(self):
        self.pattern_detectors = self._initialize_pattern_detectors()
        self.risk_calculator = RiskCalculator()
        self.timeline_predictor = TimelinePredictor()
        self.case_database = {}
        
    def _initialize_pattern_detectors(self) -> Dict[str, Any]:
        """Initialize pattern detection algorithms."""
        return {
            "repeat_offender": RepeatOffenderDetector(),
            "serial_filer": SerialFilerDetector(),
            "frivolous_claim": FrivolousClaimDetector(),
            "retaliation_pattern": RetaliationPatternDetector(),
            "habitability": HabitabilityIssueDetector(),
            "discrimination": DiscriminationPatternDetector(),
            "professional_landlord": ProfessionalLandlordDetector()
        }
    
    async def analyze_case(self, case_data: Dict[str, Any]) -> IntelligenceReport:
        """
        Analyze a case and generate comprehensive intelligence report.
        
        Args:
            case_data: Raw case data from court scraper
            
        Returns:
            IntelligenceReport: Complete analysis and recommendations
        """
        case_id = case_data.get("case_number", "unknown")
        
        logger.info(f"Analyzing case {case_id} for intelligence patterns")
        
        # Initialize report
        report = IntelligenceReport(
            case_id=case_id,
            analysis_date=utc_now(),
            patterns_detected=[],
            risk_assessment=RiskAssessment(
                risk_level=RiskLevel.LOW,
                risk_score=0.0,
                risk_factors=[],
                mitigation_strategies=[],
                escalation_triggers=[],
                estimated_outcomes={}
            ),
            timeline_predictions=[],
            strategic_recommendations=[],
            evidence_gaps=[],
            success_probability=0.5
        )
        
        # Detect patterns
        for pattern_name, detector in self.pattern_detectors.items():
            try:
                pattern_match = await detector.detect_pattern(case_data)
                if pattern_match and pattern_match.confidence > 0.6:
                    report.patterns_detected.append(pattern_match)
                    logger.info(f"Detected {pattern_name} pattern with confidence {pattern_match.confidence}")
            except Exception as e:
                logger.error(f"Pattern detection failed for {pattern_name}: {e}")
        
        # Calculate risk assessment
        report.risk_assessment = self.risk_calculator.calculate_risk(
            case_data, report.patterns_detected
        )
        
        # Generate timeline predictions
        report.timeline_predictions = self.timeline_predictor.predict_timeline(
            case_data, report.patterns_detected
        )
        
        # Generate strategic recommendations
        report.strategic_recommendations = self._generate_recommendations(
            case_data, report.patterns_detected, report.risk_assessment
        )
        
        # Identify evidence gaps
        report.evidence_gaps = self._identify_evidence_gaps(
            case_data, report.patterns_detected
        )
        
        # Calculate success probability
        report.success_probability = self._calculate_success_probability(
            case_data, report.patterns_detected, report.risk_assessment
        )
        
        # Store in database
        self.case_database[case_id] = asdict(report)
        
        logger.info(f"Intelligence analysis complete for case {case_id}")
        return report
    
    def _generate_recommendations(self, case_data: Dict[str, Any],
                                patterns: List[PatternMatch],
                                risk_assessment: RiskAssessment) -> List[str]:
        """Generate strategic recommendations based on analysis."""
        recommendations = []
        
        # Pattern-based recommendations
        for pattern in patterns:
            if pattern.pattern_type == PatternType.REPEAT_OFFENDER:
                recommendations.extend([
                    "Document pattern of repeat offenses for enhanced damages",
                    "Request enhanced discovery procedures",
                    "Consider punitive damages claim"
                ])
            elif pattern.pattern_type == PatternType.HABITABILITY_ISSUE:
                recommendations.extend([
                    "Document all habitability violations with photos/videos",
                    "Request rent reduction or abatement",
                    "Consider constructive eviction claim"
                ])
            elif pattern.pattern_type == PatternType.RETALIATION_PATTERN:
                recommendations.extend([
                    "Document all retaliatory actions and communications",
                    "File complaint with housing authority",
                    "Request injunctive relief"
                ])
            elif pattern.pattern_type == PatternType.DISCRIMINATION_PATTERN:
                recommendations.extend([
                    "File discrimination complaint with HUD",
                    "Request protected class status",
                    "Consider fair housing lawsuit"
                ])
        
        # Risk-based recommendations
        if risk_assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.extend([
                "Expedite discovery and disclosure",
                    "Consider emergency injunction",
                    "Prepare for immediate court intervention"
            ])
        
        # Case-specific recommendations
        case_type = case_data.get("case_type", "general")
        if case_type == "eviction":
            recommendations.extend([
                "Verify proper notice procedures were followed",
                "Check for procedural defenses",
                "Document rent payment history"
            ])
        elif case_type == "security_deposit":
            recommendations.extend([
                    "Request itemized statement of deductions",
                    "Verify return timeline compliance",
                "Consider bad faith damages"
            ])
        
        return list(set(recommendations))  # Remove duplicates
    
    def _identify_evidence_gaps(self, case_data: Dict[str, Any],
                                patterns: List[PatternMatch]) -> List[str]:
        """Identify missing evidence based on patterns and case type."""
        gaps = []
        
        # Check for required documentation
        required_docs = self._get_required_documents(case_data)
        existing_docs = case_data.get("documents", [])
        
        for doc_type in required_docs:
            if not any(doc.get("type") == doc_type for doc in existing_docs):
                gaps.append(f"Missing {doc_type} documentation")
        
        # Pattern-specific gaps
        for pattern in patterns:
            if pattern.pattern_type == PatternType.HABITABILITY_ISSUE:
                gaps.extend([
                    "Lack of photo/video evidence of conditions",
                    "Missing maintenance request documentation",
                    "No expert inspection reports"
                ])
            elif pattern.pattern_type == PatternType.DISCRIMINATION_PATTERN:
                gaps.extend([
                    "No documentation of differential treatment",
                    "Missing communication records",
                    "No witness statements for discriminatory actions"
                ])
        
        return gaps
    
    def _get_required_documents(self, case_data: Dict[str, Any]) -> List[str]:
        """Get required documents based on case type."""
        case_type = case_data.get("case_type", "general")
        
        if case_type == "eviction":
            return [
                "lease_agreement",
                "payment_history",
                "notice_of_termination",
                "communication_records"
            ]
        elif case_type == "security_deposit":
            return [
                "lease_agreement",
                "move_in_checklist",
                "move_out_checklist",
                "deduction_itemization"
            ]
        elif case_type == "habitability":
            return [
                "maintenance_requests",
                "photos_videos",
                "expert_inspection",
                "communication_records"
            ]
        elif case_type == "discrimination":
            return [
                "communication_records",
                "witness_statements",
                "comparative_evidence",
                "protected_class_documentation"
            ]
        
        return ["general_documentation"]
    
    def _calculate_success_probability(self, case_data: Dict[str, Any],
                                   patterns: List[PatternMatch],
                                   risk_assessment: RiskAssessment) -> float:
        """Calculate probability of successful outcome."""
        base_probability = 0.5  # Base 50% success rate
        
        # Adjust based on patterns
        for pattern in patterns:
            if pattern.pattern_type == PatternType.REPEAT_OFFENDER:
                base_probability += 0.2  # Repeat offenders often lose
            elif pattern.pattern_type == PatternType.PROFESSIONAL_LANDLORD:
                base_probability -= 0.1  # Professional landlords harder to beat
            elif pattern.pattern_type == PatternType.HABITABILITY_ISSUE:
                base_probability += 0.15  # Habitability issues favor tenants
            elif pattern.pattern_type == PatternType.DISCRIMINATION_PATTERN:
                base_probability += 0.25  # Discrimination cases favor tenants
        
        # Adjust based on risk
        if risk_assessment.risk_level == RiskLevel.CRITICAL:
            base_probability -= 0.2
        elif risk_assessment.risk_level == RiskLevel.HIGH:
            base_probability -= 0.1
        elif risk_assessment.risk_level == RiskLevel.LOW:
            base_probability += 0.1
        
        # Ensure probability stays within bounds
        return max(0.1, min(0.9, base_probability))
    
    def get_case_intelligence(self, case_id: str) -> Optional[IntelligenceReport]:
        """Get stored intelligence report for a case."""
        return self.case_database.get(case_id)
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics on detected patterns."""
        pattern_counts = {}
        total_cases = len(self.case_database)
        
        for report in self.case_database.values():
            for pattern in report.patterns_detected:
                pattern_type = pattern.pattern_type.value
                pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
        
        return {
            "total_cases_analyzed": total_cases,
            "pattern_distribution": pattern_counts,
            "most_common_patterns": sorted(
                pattern_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]
        }

class RiskCalculator:
    """Calculates risk levels and factors for housing cases."""
    
    def calculate_risk(self, case_data: Dict[str, Any],
                    patterns: List[PatternMatch]) -> RiskAssessment:
        """Calculate comprehensive risk assessment."""
        risk_score = 0.0
        risk_factors = []
        
        # Base risk from case type
        case_type = case_data.get("case_type", "general")
        case_type_risks = {
            "eviction": 0.3,
            "security_deposit": 0.2,
            "habitability": 0.4,
            "discrimination": 0.5,
            "lease_violation": 0.3
        }
        
        risk_score += case_type_risks.get(case_type, 0.2)
        risk_factors.append(f"Case type: {case_type}")
        
        # Risk from patterns
        for pattern in patterns:
            if pattern.pattern_type == PatternType.REPEAT_OFFENDER:
                risk_score += 0.4
                risk_factors.append("Repeat offender landlord")
            elif pattern.pattern_type == PatternType.SERIAL_FILER:
                risk_score += 0.2
                risk_factors.append("Serial litigation history")
            elif pattern.pattern_type == PatternType.PROFESSIONAL_LANDLORD:
                risk_score += 0.3
                risk_factors.append("Professional landlord with legal team")
            elif pattern.pattern_type == PatternType.HABITABILITY_ISSUE:
                risk_score += 0.2
                risk_factors.append("Multiple habitability violations")
            elif pattern.pattern_type == PatternType.DISCRIMINATION_PATTERN:
                risk_score += 0.5
                risk_factors.append("Evidence of discriminatory practices")
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
            mitigation_strategies = [
                "Emergency injunction filing",
                "Expedited discovery process",
                "Media engagement strategy",
                "Community organizing support"
            ]
            escalation_triggers = [
                "Immediate court filing required",
                "Health and safety concerns",
                "Elderly or disabled tenant involved"
            ]
        elif risk_score >= 0.6:
            risk_level = RiskLevel.HIGH
            mitigation_strategies = [
                "Aggressive discovery timeline",
                "Expert witness preparation",
                "Settlement demand letter",
                "Regulatory agency complaint"
            ]
            escalation_triggers = [
                "Multiple code violations",
                "Retaliation evidence",
                "Pattern of escalating harassment"
            ]
        elif risk_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
            mitigation_strategies = [
                "Standard discovery process",
                "Document preservation strategy",
                "Negotiation preparation",
                "Legal research focus"
            ]
            escalation_triggers = [
                "Unresolved maintenance issues",
                "Communication breakdown",
                "Procedural violations"
            ]
        else:
            risk_level = RiskLevel.LOW
            mitigation_strategies = [
                "Standard case management",
                "Documentation organization",
                "Regular communication",
                "Legal research as needed"
            ]
            escalation_triggers = [
                "Case complexity increases",
                "New evidence emerges",
                "Deadline approaches"
            ]
        
        # Estimate outcomes
        estimated_outcomes = {
            "settlement_probability": max(0.1, 0.7 - risk_score),
            "trial_success_probability": max(0.2, 0.8 - risk_score),
            "injunctive_relief_probability": max(0.05, 0.3 - risk_score) if risk_level == RiskLevel.HIGH else 0.1
        }
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            mitigation_strategies=mitigation_strategies,
            escalation_triggers=escalation_triggers,
            estimated_outcomes=estimated_outcomes
        )

class TimelinePredictor:
    """Predicts case timeline and critical dates."""
    
    def predict_timeline(self, case_data: Dict[str, Any],
                      patterns: List[PatternMatch]) -> List[Dict[str, Any]]:
        """Predict timeline and critical dates."""
        predictions = []
        
        case_type = case_data.get("case_type", "general")
        filing_date = case_data.get("filing_date")
        
        if not filing_date:
            return predictions
        
        # Base timeline by case type
        base_timelines = {
            "eviction": {
                "notice_period": 14,
                "court_hearing": 21,
                "judgment": 35,
                "enforcement": 45
            },
            "security_deposit": {
                "return_deadline": 21,
                "dispute_resolution": 45,
                "small_claims_deadline": 60
            },
            "habitability": {
                "repair_deadline": 14,
                "inspection_deadline": 21,
                "compliance_deadline": 30
            }
        }
        
        timeline = base_timelines.get(case_type, {})
        
        # Adjust based on patterns
        for pattern in patterns:
            if pattern.pattern_type == PatternType.REPEAT_OFFENDER:
                # Expedited timeline for repeat offenders
                for key, days in timeline.items():
                    if isinstance(days, int):
                        timeline[key] = int(days * 0.7)  # 30% faster
            elif pattern.pattern_type == PatternType.PROFESSIONAL_LANDLORD:
                # Extended timeline for professional landlords
                for key, days in timeline.items():
                    if isinstance(days, int):
                        timeline[key] = int(days * 1.3)  # 30% longer
            elif pattern.pattern_type == PatternType.HABITABILITY_ISSUE:
                # Compressed timeline for habitability
                for key, days in timeline.items():
                    if isinstance(days, int):
                        timeline[key] = int(days * 0.8)  # 20% faster
        
        # Generate predictions
        base_date = filing_date
        for event, days in timeline.items():
            if isinstance(days, int):
                event_date = base_date + timedelta(days=days)
                predictions.append({
                    "event": event,
                    "predicted_date": event_date.isoformat(),
                    "days_from_filing": days,
                    "confidence": 0.8
                })
        
        return predictions

def _parties_from_case(case_data: Dict[str, Any]) -> Tuple[str, str]:
    """Extract tenant and landlord names from case data."""
    parties = case_data.get("parties") or {}
    tenant = parties.get("tenant") if isinstance(parties, dict) else None
    landlord = parties.get("landlord") if isinstance(parties, dict) else None
    return tenant or "tenant", landlord or "landlord"


# Pattern Detector Classes
class RepeatOffenderDetector:
    """Detects repeat offender patterns."""

    async def detect_pattern(self, case_data: Dict[str, Any]) -> Optional[PatternMatch]:
        """Detect if landlord is repeat offender."""
        prior_cases = case_data.get("landlord_prior_cases", [])
        if not isinstance(prior_cases, list):
            prior_cases = []

        if case_data.get("landlord_repeat_offender") or len(prior_cases) >= 3:
            count = len(prior_cases)
            confidence = min(0.95, 0.65 + count * 0.04)
            tenant, landlord = _parties_from_case(case_data)
            return PatternMatch(
                pattern_type=PatternType.REPEAT_OFFENDER,
                confidence=confidence,
                description=f"Landlord has {count} prior cases, indicating a repeat offender pattern",
                affected_parties=[tenant, landlord],
                legal_basis="Pattern of repeated landlord-tenant litigation",
                precedent_cases=[],
                recommended_actions=[
                    "Document pattern of repeat offenses for enhanced damages",
                    "Request enhanced discovery procedures",
                    "Consider punitive damages claim",
                ],
            )
        return None


class SerialFilerDetector:
    """Detects serial filing patterns."""

    async def detect_pattern(self, case_data: Dict[str, Any]) -> Optional[PatternMatch]:
        """Detect serial filing patterns."""
        filing_count = case_data.get("landlord_filing_count", 0)
        if isinstance(filing_count, list):
            filing_count = len(filing_count)
        try:
            filing_count = int(filing_count)
        except (TypeError, ValueError):
            filing_count = 0

        if filing_count >= 5:
            confidence = min(0.95, 0.65 + filing_count * 0.03)
            tenant, landlord = _parties_from_case(case_data)
            return PatternMatch(
                pattern_type=PatternType.SERIAL_FILER,
                confidence=confidence,
                description=f"Landlord has filed {filing_count} recent cases, indicating serial litigation",
                affected_parties=[tenant, landlord],
                legal_basis="Pattern of frequent filings against tenants",
                precedent_cases=[],
                recommended_actions=[
                    "Request filing history in discovery",
                    "Investigate other affected tenants",
                    "Consider bad faith litigation claim",
                ],
            )
        return None


class FrivolousClaimDetector:
    """Detects potentially frivolous claims."""

    async def detect_pattern(self, case_data: Dict[str, Any]) -> Optional[PatternMatch]:
        """Detect frivolous claim patterns."""
        indicators = case_data.get("frivolous_claim_indicators", [])
        procedural_defects = case_data.get("procedural_defects", [])
        if not isinstance(indicators, list):
            indicators = []
        if not isinstance(procedural_defects, list):
            procedural_defects = []

        total_indicators = len(indicators) + len(procedural_defects)
        if total_indicators >= 2 or case_data.get("frivolous_claim", False):
            confidence = min(0.9, 0.65 + total_indicators * 0.05)
            tenant, landlord = _parties_from_case(case_data)
            return PatternMatch(
                pattern_type=PatternType.FRIVOLOUS_CLAIM,
                confidence=confidence,
                description="Claim includes indicators of being meritless or procedurally defective",
                affected_parties=[tenant, landlord],
                legal_basis="Lack of good faith basis or procedural compliance",
                precedent_cases=[],
                recommended_actions=[
                    "Challenge pleadings for specificity and good faith",
                    "Document procedural defects",
                    "Request attorney fees if successful",
                ],
            )
        return None


class RetaliationPatternDetector:
    """Detects retaliation patterns."""

    async def detect_pattern(self, case_data: Dict[str, Any]) -> Optional[PatternMatch]:
        """Detect retaliation patterns."""
        retaliatory_actions = case_data.get("retaliatory_actions", [])
        if not isinstance(retaliatory_actions, list):
            retaliatory_actions = []

        if (
            case_data.get("retaliation_pattern", False)
            or case_data.get("complaint_then_adverse_action", False)
            or len(retaliatory_actions) >= 1
        ):
            count = len(retaliatory_actions)
            confidence = min(0.95, 0.75 + count * 0.05)
            tenant, landlord = _parties_from_case(case_data)
            return PatternMatch(
                pattern_type=PatternType.RETALIATION_PATTERN,
                confidence=confidence,
                description="Landlord action appears retaliatory after tenant complaint",
                affected_parties=[tenant, landlord],
                legal_basis="Retaliation protections under housing law",
                precedent_cases=[],
                recommended_actions=[
                    "Document all retaliatory actions and communications",
                    "File complaint with housing authority",
                    "Request injunctive relief",
                ],
            )
        return None


class HabitabilityIssueDetector:
    """Detects habitability violation patterns."""

    async def detect_pattern(self, case_data: Dict[str, Any]) -> Optional[PatternMatch]:
        """Detect habitability issues."""
        violations = case_data.get("habitability_violations", [])
        repair_requests = case_data.get("repair_requests", [])
        if not isinstance(violations, list):
            violations = []
        if not isinstance(repair_requests, list):
            repair_requests = []

        total = len(violations) + len(repair_requests)
        if total >= 2 or case_data.get("habitability_issue", False):
            confidence = min(0.95, 0.65 + total * 0.04)
            tenant, landlord = _parties_from_case(case_data)
            return PatternMatch(
                pattern_type=PatternType.HABITABILITY_ISSUE,
                confidence=confidence,
                description=f"{total} habitability violations or unresolved repair requests detected",
                affected_parties=[tenant, landlord],
                legal_basis="Warranty of habitability and housing code compliance",
                precedent_cases=[],
                recommended_actions=[
                    "Document all habitability violations with photos/videos",
                    "Request rent reduction or abatement",
                    "Consider constructive eviction claim",
                ],
            )
        return None


class DiscriminationPatternDetector:
    """Detects discrimination patterns."""

    async def detect_pattern(self, case_data: Dict[str, Any]) -> Optional[PatternMatch]:
        """Detect discrimination patterns."""
        protected_class = case_data.get("protected_class")
        differential_treatment = case_data.get("differential_treatment")
        discriminatory_statements = case_data.get("discriminatory_statements", [])
        if not isinstance(discriminatory_statements, list):
            discriminatory_statements = []

        if protected_class and (differential_treatment or len(discriminatory_statements) >= 1):
            confidence = min(0.95, 0.75 + len(discriminatory_statements) * 0.05)
            tenant, landlord = _parties_from_case(case_data)
            return PatternMatch(
                pattern_type=PatternType.DISCRIMINATION_PATTERN,
                confidence=confidence,
                description=f"Evidence suggests discrimination based on {protected_class}",
                affected_parties=[tenant, landlord],
                legal_basis="Fair housing and anti-discrimination protections",
                precedent_cases=[],
                recommended_actions=[
                    "File discrimination complaint with HUD",
                    "Request protected class status",
                    "Consider fair housing lawsuit",
                ],
            )
        return None


class ProfessionalLandlordDetector:
    """Detects professional landlord patterns."""

    async def detect_pattern(self, case_data: Dict[str, Any]) -> Optional[PatternMatch]:
        """Detect professional landlord patterns."""
        landlord = case_data.get("parties", {}).get("landlord", "") or case_data.get("landlord_name", "")
        landlord = str(landlord)
        entity_type = case_data.get("landlord_entity_type", "")
        portfolio_size = case_data.get("landlord_portfolio_size", 0)
        try:
            portfolio_size = int(portfolio_size)
        except (TypeError, ValueError):
            portfolio_size = 0

        is_professional = (
            entity_type in {"LLC", "CORPORATION", "PROPERTY_MANAGEMENT", "TRUST"}
            or portfolio_size >= 10
            or re.search(r"LLC|Properties|Property Management|Corp|Inc\.|Trust|Holdings", landlord, re.IGNORECASE)
        )

        if is_professional:
            confidence = min(0.95, 0.7 + min(portfolio_size, 20) * 0.01)
            tenant, _ = _parties_from_case(case_data)
            return PatternMatch(
                pattern_type=PatternType.PROFESSIONAL_LANDLORD,
                confidence=confidence,
                description="Landlord appears to be a professional or institutional entity",
                affected_parties=[tenant, landlord or "landlord"],
                legal_basis="Professional landlords have greater resources and repeat legal practices",
                precedent_cases=[],
                recommended_actions=[
                    "Expect aggressive procedural tactics",
                    "Request complete ownership and management disclosures",
                    "Investigate other properties owned by entity",
                ],
            )
        return None

# Factory function
def create_intelligence_engine() -> LitigationIntelligenceEngine:
    """Create intelligence engine instance."""
    return LitigationIntelligenceEngine()

# Example usage
async def example_usage():
    """Example usage of intelligence engine."""
    engine = create_intelligence_engine()
    
    # Sample case data
    case_data = {
        "case_number": "27-CV-21-12345",
        "case_title": "Eviction for non-payment of rent",
        "case_type": "eviction",
        "filing_date": utc_now() - timedelta(days=10),
        "parties": {
            "landlord": "Professional Properties LLC",
            "tenant": "John Doe"
        },
        "documents": [
            {"type": "lease_agreement", "date": "2023-01-01"},
            {"type": "payment_history", "entries": 12}
        ]
    }
    
    # Analyze case
    report = await engine.analyze_case(case_data)
    
    logger.info(f"Intelligence Report for Case {report.case_id}")
    logger.info("=" * 50)
    logger.info(f"Analysis Date: {report.analysis_date}")
    logger.info(f"Risk Level: {report.risk_assessment.risk_level.value}")
    logger.info(f"Risk Score: {report.risk_assessment.risk_score:.2f}")
    logger.info(f"Success Probability: {report.success_probability:.2f}")
    logger.info("Patterns Detected:")
    for pattern in report.patterns_detected:
        logger.info(f"  - {pattern.pattern_type.value}: {pattern.description}")
    logger.info("Strategic Recommendations:")
    for rec in report.strategic_recommendations:
        logger.info(f"  - {rec}")
    logger.info("Timeline Predictions:")
    for prediction in report.timeline_predictions:
        logger.info(f"  - {prediction['event']}: {prediction['predicted_date']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
