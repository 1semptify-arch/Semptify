"""
Legal Analysis Engine

Evaluates documents, timelines, and information in legal context for:
- Cross-referencing and corroboration
- Consistency and contradiction detection
- Legal merit evaluation
- Fact vs hearsay classification
- Binding vs non-binding document analysis
- Chain of evidence validation
- Statute of limitations checking
- Notice requirement compliance

Integrated with 🧠 Positronic Brain for real-time event communication.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Tuple, Set
from enum import Enum
import re
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS - Legal Classifications
# =============================================================================

class EvidenceType(str, Enum):
    """Classification of evidence types"""
    DIRECT = "direct"           # First-hand evidence (documents, photos)
    CIRCUMSTANTIAL = "circumstantial"  # Indirect evidence
    DOCUMENTARY = "documentary"  # Written documents
    TESTIMONIAL = "testimonial"  # Witness statements
    PHYSICAL = "physical"       # Physical evidence (photos, videos)
    HEARSAY = "hearsay"         # Second-hand information
    EXPERT = "expert"           # Expert opinion


class DocumentLegalStatus(str, Enum):
    """Legal standing of a document"""
    LEGALLY_BINDING = "legally_binding"
    POTENTIALLY_BINDING = "potentially_binding"
    INFORMATIONAL = "informational"
    HEARSAY = "hearsay"
    INADMISSIBLE = "inadmissible"
    NEEDS_AUTHENTICATION = "needs_authentication"


class CredibilityLevel(str, Enum):
    """Credibility assessment"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"
    DISPUTED = "disputed"


class ConsistencyStatus(str, Enum):
    """Consistency check results"""
    CONSISTENT = "consistent"
    MINOR_DISCREPANCY = "minor_discrepancy"
    MAJOR_CONTRADICTION = "major_contradiction"
    UNVERIFIED = "unverified"


class LegalMeritLevel(str, Enum):
    """Assessment of legal merit"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class NoticeComplianceStatus(str, Enum):
    """Notice requirement compliance"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    DEFECTIVE = "defective"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNKNOWN = "unknown"


# =============================================================================
# DATA CLASSES - Analysis Results
# =============================================================================

@dataclass
class EvidenceClassification:
    """Classification of a piece of evidence"""
    evidence_type: EvidenceType
    legal_status: DocumentLegalStatus
    credibility: CredibilityLevel
    weight: float  # 0.0 to 1.0
    admissibility_issues: List[str] = field(default_factory=list)
    authentication_required: bool = False
    supporting_elements: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type": self.evidence_type.value,
            "legal_status": self.legal_status.value,
            "credibility": self.credibility.value,
            "weight": self.weight,
            "admissibility_issues": self.admissibility_issues,
            "authentication_required": self.authentication_required,
            "supporting_elements": self.supporting_elements,
            "weaknesses": self.weaknesses,
        }


@dataclass
class ConsistencyCheck:
    """Result of consistency analysis between items"""
    item1_id: str
    item1_type: str
    item2_id: str
    item2_type: str
    status: ConsistencyStatus
    field_checked: str
    item1_value: str
    item2_value: str
    significance: str  # How important is this discrepancy?
    explanation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item1_id": self.item1_id,
            "item1_type": self.item1_type,
            "item2_id": self.item2_id,
            "item2_type": self.item2_type,
            "status": self.status.value,
            "field_checked": self.field_checked,
            "item1_value": self.item1_value,
            "item2_value": self.item2_value,
            "significance": self.significance,
            "explanation": self.explanation,
        }


@dataclass
class CorroborationAnalysis:
    """Analysis of how evidence corroborates claims"""
    claim: str
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    contradicting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    corroboration_strength: float = 0.0  # 0.0 to 1.0
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "corroboration_strength": self.corroboration_strength,
            "gaps": self.gaps,
            "recommendations": self.recommendations,
        }


@dataclass
class TimelineAnalysis:
    """Analysis of timeline for legal compliance"""
    events: List[Dict[str, Any]]
    total_span_days: int
    critical_deadlines: List[Dict[str, Any]]
    missed_deadlines: List[Dict[str, Any]]
    gaps: List[Dict[str, Any]]
    sequence_issues: List[str]
    notice_compliance: NoticeComplianceStatus
    statute_issues: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": self.events,
            "total_span_days": self.total_span_days,
            "critical_deadlines": self.critical_deadlines,
            "missed_deadlines": self.missed_deadlines,
            "gaps": self.gaps,
            "sequence_issues": self.sequence_issues,
            "notice_compliance": self.notice_compliance.value,
            "statute_issues": self.statute_issues,
        }


@dataclass
class LegalMeritAssessment:
    """Overall assessment of legal merit"""
    overall_merit: LegalMeritLevel
    score: float  # 0.0 to 100.0
    strengths: List[str]
    weaknesses: List[str]
    critical_issues: List[str]
    evidence_summary: Dict[str, Any]
    consistency_summary: Dict[str, Any]
    timeline_summary: Dict[str, Any]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_merit": self.overall_merit.value,
            "score": self.score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "critical_issues": self.critical_issues,
            "evidence_summary": self.evidence_summary,
            "consistency_summary": self.consistency_summary,
            "timeline_summary": self.timeline_summary,
            "recommendations": self.recommendations,
        }


# =============================================================================
# MINNESOTA LEGAL REQUIREMENTS
# =============================================================================

MN_EVICTION_REQUIREMENTS = {
    "non_payment": {
        "notice_type": "14-day notice",
        "notice_days": 14,
        "cure_allowed": True,
        "statute": "Minn. Stat. § 504B.135",
        "requirements": [
            "Written notice required",
            "Must specify amount owed",
            "Must allow 14 days to cure",
            "Must be properly served (personal, substitute, or posting)",
        ]
    },
    "lease_violation": {
        "notice_type": "Conditional notice",
        "notice_days": 14,  # Typically, but can vary
        "cure_allowed": True,  # For curable violations
        "statute": "Minn. Stat. § 504B.285",
        "requirements": [
            "Written notice required",
            "Must specify the violation",
            "Must give reasonable time to cure if curable",
        ]
    },
    "holdover": {
        "notice_type": "None required if lease expired",
        "notice_days": 0,
        "cure_allowed": False,
        "statute": "Minn. Stat. § 504B.135",
        "requirements": [
            "Lease must have expired",
            "No notice required if lease specified termination date",
        ]
    },
    "criminal_activity": {
        "notice_type": "Immediate",
        "notice_days": 0,
        "cure_allowed": False,
        "statute": "Minn. Stat. § 504B.171",
        "requirements": [
            "Must involve criminal activity on premises",
            "No cure period required",
        ]
    }
}

MN_SERVICE_REQUIREMENTS = {
    "personal": {
        "description": "Delivered directly to tenant",
        "valid": True,
        "proof_needed": "Affidavit of service"
    },
    "substitute": {
        "description": "Delivered to person of suitable age at residence",
        "valid": True,
        "proof_needed": "Affidavit of service with description of recipient"
    },
    "posting": {
        "description": "Posted on door (only if personal/substitute failed)",
        "valid": True,
        "conditions": "Only valid if personal and substitute service attempted first",
        "proof_needed": "Affidavit showing failed attempts"
    },
    "mail": {
        "description": "Sent via certified mail",
        "valid": True,
        "proof_needed": "Certified mail receipt"
    }
}

BINDING_DOCUMENT_TYPES = {
    "lease": {
        "binding": True,
        "requirements": ["Signatures of all parties", "Property identified", "Terms stated"],
        "exceptions": ["Unconscionable terms", "Illegal provisions"]
    },
    "notice": {
        "binding": True,
        "requirements": ["Proper service", "Correct time periods", "Required content"],
        "exceptions": ["Defective service", "Incorrect time", "Missing required elements"]
    },
    "court_order": {
        "binding": True,
        "requirements": ["Signed by judge", "Properly filed"],
        "exceptions": ["Stayed", "Appealed", "Expired"]
    },
    "summons": {
        "binding": True,
        "requirements": ["Proper service", "Court jurisdiction"],
        "exceptions": ["Improper service", "Wrong jurisdiction"]
    },
    "email": {
        "binding": False,
        "requirements": [],
        "exceptions": [],
        "notes": "Generally informational, but may be evidence of communications"
    },
    "text_message": {
        "binding": False,
        "requirements": [],
        "exceptions": [],
        "notes": "Generally informational, but may be evidence of communications"
    },
    "photo": {
        "binding": False,
        "requirements": ["Timestamp", "Location (if relevant)", "Context"],
        "exceptions": [],
        "notes": "Documentary evidence, needs authentication"
    }
}


# =============================================================================
# LEGAL ANALYSIS ENGINE
# =============================================================================

class LegalAnalysisEngine:
    """
    Engine for analyzing legal merit, consistency, and evidentiary value
    of tenancy case information.
    """
    
    def __init__(self):
        self.mn_requirements = MN_EVICTION_REQUIREMENTS
        self.service_requirements = MN_SERVICE_REQUIREMENTS
        self.binding_types = BINDING_DOCUMENT_TYPES
    
    # -------------------------------------------------------------------------
    # Document Analysis
    # -------------------------------------------------------------------------
    
    def classify_evidence(self, document: Dict[str, Any]) -> EvidenceClassification:
        """
        Classify a document/evidence item for legal purposes.
        """
        doc_type = document.get("category", "").lower()
        content = document.get("full_text", "") or document.get("description", "")
        
        # Determine evidence type
        evidence_type = self._determine_evidence_type(doc_type, content)
        
        # Determine legal status
        legal_status = self._determine_legal_status(doc_type, document)
        
        # Calculate credibility
        credibility, cred_factors = self._assess_credibility(document)
        
        # Calculate weight
        weight = self._calculate_evidence_weight(evidence_type, legal_status, credibility)
        
        # Check admissibility issues
        admissibility_issues = self._check_admissibility(doc_type, document)
        
        # Check if authentication needed
        auth_required = doc_type in ["photo_evidence", "video_evidence", "email", "text_message"]
        
        return EvidenceClassification(
            evidence_type=evidence_type,
            legal_status=legal_status,
            credibility=credibility,
            weight=weight,
            admissibility_issues=admissibility_issues,
            authentication_required=auth_required,
            supporting_elements=cred_factors.get("supporting", []),
            weaknesses=cred_factors.get("weaknesses", []),
        )
    
    def _determine_evidence_type(self, doc_type: str, content: str) -> EvidenceType:
        """Determine the type of evidence."""
        content_lower = content.lower()
        
        # Check for hearsay first - expanded phrases
        hearsay_phrases = [
            "told me", "said that", "heard that", "according to",
            "i was told", "someone said", "they say", "allegedly",
            "he said she said", "my neighbor told", "i heard from",
            "second hand", "secondhand", "word is", "rumor",
            "they told me", "i heard", "she told me", "he told me",
            "informed me that", "mentioned that", "claims that",
            "supposedly", "reported to me", "passed along",
        ]
        if any(phrase in content_lower for phrase in hearsay_phrases):
            return EvidenceType.HEARSAY
            
        if doc_type in ["lease", "notice", "court_filing", "legal_form", "amendment"]:
            return EvidenceType.DOCUMENTARY
        elif doc_type in ["photo_evidence", "video_evidence", "photo", "photos", "video", "videos"]:
            return EvidenceType.PHYSICAL
        elif doc_type in ["witness_statement", "testimony", "declaration", "affidavit"]:
            return EvidenceType.TESTIMONIAL
        elif "inspection" in doc_type or "professional" in content_lower:
            return EvidenceType.EXPERT
        else:
            return EvidenceType.DOCUMENTARY
    
    def _determine_legal_status(self, doc_type: str, document: Dict[str, Any]) -> DocumentLegalStatus:
        """Determine the legal status of a document."""
        if doc_type in self.binding_types:
            binding_info = self.binding_types[doc_type]
            if binding_info.get("binding"):
                # Check if requirements are met
                # This is simplified - would need more document analysis
                return DocumentLegalStatus.LEGALLY_BINDING
            else:
                return DocumentLegalStatus.INFORMATIONAL
        
        # Court documents are always binding
        if doc_type in ["court_filing", "summons", "eviction"]:
            return DocumentLegalStatus.LEGALLY_BINDING
        
        # Photos/videos need authentication
        if doc_type in ["photo_evidence", "video_evidence"]:
            return DocumentLegalStatus.NEEDS_AUTHENTICATION
        
        return DocumentLegalStatus.INFORMATIONAL
    
    def _assess_credibility(self, document: Dict[str, Any]) -> Tuple[CredibilityLevel, Dict[str, List[str]]]:
        """Assess credibility of evidence."""
        supporting = []
        weaknesses = []
        score = 50  # Start at medium
        
        # Check for timestamp
        if document.get("document_date") or document.get("created_at"):
            supporting.append("Document is dated/timestamped")
            score += 10
        else:
            weaknesses.append("No date/timestamp on document")
            score -= 10
        
        # Check for official source
        doc_type = document.get("category", "").lower()
        if doc_type in ["court_filing", "inspection_report", "legal_form"]:
            supporting.append("Official/institutional source")
            score += 20
        
        # Check for signatures (simplified)
        content = str(document.get("full_text", "")).lower()
        if "signed" in content or "signature" in content:
            supporting.append("Document appears to be signed")
            score += 10
        
        # Check for notarization
        if "notary" in content or "notarized" in content:
            supporting.append("Document is notarized")
            score += 15
        
        # Check for certification
        if "certified" in content or "certification" in content:
            supporting.append("Document is certified")
            score += 10
        
        # Check for hearsay indicators
        hearsay_phrases = ["someone said", "i heard", "they told", "rumor", "gossip"]
        if any(phrase in content for phrase in hearsay_phrases):
            weaknesses.append("Contains hearsay statements")
            score -= 20
        
        # Determine level
        if score >= 70:
            level = CredibilityLevel.HIGH
        elif score >= 40:
            level = CredibilityLevel.MEDIUM
        else:
            level = CredibilityLevel.LOW
        
        return level, {"supporting": supporting, "weaknesses": weaknesses}
    
    def _calculate_evidence_weight(
        self,
        evidence_type: EvidenceType,
        legal_status: DocumentLegalStatus,
        credibility: CredibilityLevel
    ) -> float:
        """Calculate overall weight of evidence (0.0 to 1.0)."""
        base_weight = 0.5
        
        # Adjust for evidence type
        type_adjustments = {
            EvidenceType.DOCUMENTARY: 0.2,
            EvidenceType.PHYSICAL: 0.15,
            EvidenceType.DIRECT: 0.2,
            EvidenceType.EXPERT: 0.15,
            EvidenceType.TESTIMONIAL: 0.05,
            EvidenceType.CIRCUMSTANTIAL: 0.0,
            EvidenceType.HEARSAY: -0.3,
        }
        base_weight += type_adjustments.get(evidence_type, 0)
        
        # Adjust for legal status
        status_adjustments = {
            DocumentLegalStatus.LEGALLY_BINDING: 0.2,
            DocumentLegalStatus.POTENTIALLY_BINDING: 0.1,
            DocumentLegalStatus.INFORMATIONAL: 0.0,
            DocumentLegalStatus.HEARSAY: -0.2,
            DocumentLegalStatus.INADMISSIBLE: -0.4,
            DocumentLegalStatus.NEEDS_AUTHENTICATION: -0.1,
        }
        base_weight += status_adjustments.get(legal_status, 0)
        
        # Adjust for credibility
        cred_adjustments = {
            CredibilityLevel.HIGH: 0.15,
            CredibilityLevel.MEDIUM: 0.0,
            CredibilityLevel.LOW: -0.15,
            CredibilityLevel.UNKNOWN: -0.1,
            CredibilityLevel.DISPUTED: -0.2,
        }
        base_weight += cred_adjustments.get(credibility, 0)
        
        return max(0.0, min(1.0, base_weight))
    
    def _check_admissibility(self, doc_type: str, document: Dict[str, Any]) -> List[str]:
        """Check for potential admissibility issues."""
        issues = []
        
        # Check for hearsay
        content = str(document.get("full_text", "")).lower()
        if any(phrase in content for phrase in ["someone said", "i heard", "they told me"]):
            issues.append("May contain inadmissible hearsay")
        
        # Check for authentication needs
        if doc_type in ["photo_evidence", "video_evidence"]:
            issues.append("Requires authentication (who took it, when, where)")
        
        # Check for relevance indicators
        if not document.get("description") and not document.get("summary"):
            issues.append("Relevance may need to be established")
        
        # Check for chain of custody for physical evidence
        if doc_type in ["photo_evidence", "video_evidence", "physical"]:
            if not document.get("created_at"):
                issues.append("Chain of custody should be documented")
        
        return issues
    
    # -------------------------------------------------------------------------
    # Consistency Analysis
    # -------------------------------------------------------------------------
    
    def check_consistency(
        self,
        items: List[Dict[str, Any]],
        fields_to_check: Optional[List[str]] = None
    ) -> List[ConsistencyCheck]:
        """
        Check consistency across multiple items (documents, events, statements).
        """
        if fields_to_check is None:
            fields_to_check = [
                "tenant_name", "landlord_name", "property_address",
                "rent_amount", "lease_start", "lease_end",
                "case_number", "amount_claimed"
            ]
        
        results = []
        
        # Compare each pair of items
        for i, item1 in enumerate(items):
            for item2 in items[i+1:]:
                for field in fields_to_check:
                    value1 = self._extract_field_value(item1, field)
                    value2 = self._extract_field_value(item2, field)
                    
                    if value1 and value2:
                        status, explanation, significance = self._compare_values(
                            field, value1, value2
                        )
                        
                        if status != ConsistencyStatus.CONSISTENT:
                            results.append(ConsistencyCheck(
                                item1_id=item1.get("id", "unknown"),
                                item1_type=item1.get("category", item1.get("event_type", "unknown")),
                                item2_id=item2.get("id", "unknown"),
                                item2_type=item2.get("category", item2.get("event_type", "unknown")),
                                status=status,
                                field_checked=field,
                                item1_value=str(value1),
                                item2_value=str(value2),
                                significance=significance,
                                explanation=explanation,
                            ))
        
        return results
    
    def _extract_field_value(self, item: Dict[str, Any], field: str) -> Any:
        """Extract a field value from an item, checking multiple possible locations."""
        # Direct field
        if field in item:
            return item[field]
        
        # Check in extracted_data
        extracted = item.get("extracted_data", {})
        if field in extracted:
            return extracted[field]
        
        # Check in nested structures
        for key in ["tenant", "landlord", "property", "lease"]:
            nested = item.get(key, {})
            if isinstance(nested, dict) and field in nested:
                return nested[field]
        
        # Try to extract from full_text
        content = item.get("full_text", "")
        if content and field in ["rent_amount", "amount_claimed"]:
            amounts = re.findall(r'\$[\d,]+\.?\d*', content)
            if amounts:
                return amounts[0]
        
        return None
    
    def _compare_values(
        self,
        field: str,
        value1: Any,
        value2: Any
    ) -> Tuple[ConsistencyStatus, str, str]:
        """Compare two values and determine consistency."""
        # Normalize values
        v1 = str(value1).strip().lower()
        v2 = str(value2).strip().lower()
        
        # Exact match
        if v1 == v2:
            return ConsistencyStatus.CONSISTENT, "Values match", "n/a"
        
        # Check for numerical fields
        if field in ["rent_amount", "amount_claimed", "security_deposit"]:
            try:
                n1 = float(re.sub(r'[^\d.]', '', v1))
                n2 = float(re.sub(r'[^\d.]', '', v2))
                diff = abs(n1 - n2)
                if diff == 0:
                    return ConsistencyStatus.CONSISTENT, "Amounts match", "n/a"
                elif diff < 10:
                    return ConsistencyStatus.MINOR_DISCREPANCY, f"Small difference: ${diff:.2f}", "low"
                else:
                    return ConsistencyStatus.MAJOR_CONTRADICTION, f"Significant difference: ${diff:.2f}", "high"
            except:
                pass
        
        # Check for date fields
        if field in ["lease_start", "lease_end", "event_date", "document_date"]:
            # Simple date comparison
            if v1 != v2:
                return ConsistencyStatus.MAJOR_CONTRADICTION, f"Dates differ: {value1} vs {value2}", "high"
        
        # Check for name fields
        if field in ["tenant_name", "landlord_name"]:
            # Check if one contains the other (partial match)
            if v1 in v2 or v2 in v1:
                return ConsistencyStatus.MINOR_DISCREPANCY, "Names partially match", "low"
            else:
                return ConsistencyStatus.MAJOR_CONTRADICTION, "Names don't match", "critical"
        
        # Check for address fields
        if field in ["property_address"]:
            # Normalize addresses
            v1_norm = re.sub(r'[.,#]', '', v1)
            v2_norm = re.sub(r'[.,#]', '', v2)
            if v1_norm == v2_norm:
                return ConsistencyStatus.CONSISTENT, "Addresses match (formatting difference)", "n/a"
            elif self._addresses_similar(v1_norm, v2_norm):
                return ConsistencyStatus.MINOR_DISCREPANCY, "Addresses similar", "medium"
            else:
                return ConsistencyStatus.MAJOR_CONTRADICTION, "Addresses differ", "critical"
        
        # Default comparison
        return ConsistencyStatus.MINOR_DISCREPANCY, f"Values differ: {value1} vs {value2}", "medium"
    
    def _addresses_similar(self, addr1: str, addr2: str) -> bool:
        """Check if two addresses are similar (same street number and name)."""
        # Extract street numbers
        num1 = re.search(r'(\d+)', addr1)
        num2 = re.search(r'(\d+)', addr2)
        
        if num1 and num2 and num1.group(1) == num2.group(1):
            # Same street number, check for common street name
            words1 = set(addr1.split())
            words2 = set(addr2.split())
            common = words1 & words2
            return len(common) >= 2
        
        return False
    
    # -------------------------------------------------------------------------
    # Corroboration Analysis
    # -------------------------------------------------------------------------
    
    def analyze_corroboration(
        self,
        claim: str,
        evidence_items: List[Dict[str, Any]]
    ) -> CorroborationAnalysis:
        """
        Analyze how well evidence supports a specific claim.
        """
        supporting = []
        contradicting = []
        gaps = []
        recommendations = []
        
        claim_lower = claim.lower()
        
        for item in evidence_items:
            content = str(item.get("full_text", "")).lower()
            content += " " + str(item.get("description", "")).lower()
            content += " " + str(item.get("title", "")).lower()
            
            # Classify the evidence
            classification = self.classify_evidence(item)
            
            # Simple keyword matching (would be more sophisticated in production)
            relevance_score = self._calculate_relevance(claim_lower, content)
            
            if relevance_score > 0.3:
                # Check if supporting or contradicting
                if self._supports_claim(claim_lower, content):
                    supporting.append({
                        "id": item.get("id"),
                        "type": item.get("category", item.get("event_type")),
                        "title": item.get("title", item.get("filename")),
                        "relevance": relevance_score,
                        "weight": classification.weight,
                        "summary": f"Supports claim with {classification.evidence_type.value} evidence"
                    })
                elif self._contradicts_claim(claim_lower, content):
                    contradicting.append({
                        "id": item.get("id"),
                        "type": item.get("category", item.get("event_type")),
                        "title": item.get("title", item.get("filename")),
                        "relevance": relevance_score,
                        "issue": "Contains contradicting information"
                    })
        
        # Calculate corroboration strength
        if not supporting and not contradicting:
            strength = 0.0
            gaps.append("No evidence found directly related to this claim")
            recommendations.append("Gather additional evidence to support this claim")
        else:
            total_support_weight = sum(s["weight"] for s in supporting)
            total_contra_weight = len(contradicting) * 0.5
            
            if total_support_weight + total_contra_weight > 0:
                strength = total_support_weight / (total_support_weight + total_contra_weight)
            else:
                strength = 0.0
        
        # Identify gaps
        if not any(s.get("type") == "documentary" for s in supporting):
            gaps.append("No documentary evidence supporting claim")
            recommendations.append("Obtain written documentation")
        
        if not any(s.get("type") in ["photo_evidence", "video_evidence"] for s in supporting):
            if "condition" in claim_lower or "damage" in claim_lower:
                gaps.append("No photographic evidence of conditions")
                recommendations.append("Take photos to document conditions")
        
        return CorroborationAnalysis(
            claim=claim,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            corroboration_strength=strength,
            gaps=gaps,
            recommendations=recommendations,
        )
    
    def _calculate_relevance(self, claim: str, content: str) -> float:
        """Calculate how relevant content is to a claim."""
        claim_words = set(claim.split())
        content_words = set(content.split())
        
        # Remove common words
        common_words = {"the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "and", "in", "that", "it"}
        claim_words -= common_words
        
        if not claim_words:
            return 0.0
        
        overlap = claim_words & content_words
        return len(overlap) / len(claim_words)
    
    def _supports_claim(self, claim: str, content: str) -> bool:
        """Check if content supports a claim."""
        # Simplified - would use NLP in production
        negative_words = ["not", "never", "no", "didn't", "don't", "wasn't", "weren't"]
        
        # If claim has negatives and content doesn't (or vice versa), might contradict
        claim_has_negative = any(word in claim for word in negative_words)
        content_has_negative = any(word in content for word in negative_words)
        
        return claim_has_negative == content_has_negative
    
    def _contradicts_claim(self, claim: str, content: str) -> bool:
        """Check if content contradicts a claim."""
        return not self._supports_claim(claim, content)
    
    # -------------------------------------------------------------------------
    # Timeline Analysis
    # -------------------------------------------------------------------------
    
    def analyze_timeline(
        self,
        events: List[Dict[str, Any]],
        eviction_type: str = "non_payment"
    ) -> TimelineAnalysis:
        """
        Analyze timeline for legal compliance and issues.
        """
        # Sort events by date
        sorted_events = sorted(
            events,
            key=lambda e: e.get("event_date", e.get("date", "9999-99-99"))
        )
        
        # Calculate total span
        if len(sorted_events) >= 2:
            first_date = self._parse_date(sorted_events[0].get("event_date", ""))
            last_date = self._parse_date(sorted_events[-1].get("event_date", ""))
            if first_date and last_date:
                total_span = (last_date - first_date).days
            else:
                total_span = 0
        else:
            total_span = 0
        
        # Find critical deadlines
        critical_deadlines = []
        missed_deadlines = []
        today = date.today()
        
        for event in sorted_events:
            if event.get("is_deadline"):
                deadline_date = self._parse_date(event.get("deadline_date", event.get("event_date", "")))
                is_completed = event.get("deadline_completed", False)
                
                deadline_info = {
                    "id": event.get("id"),
                    "title": event.get("title"),
                    "date": event.get("deadline_date", event.get("event_date")),
                    "completed": is_completed,
                }
                
                critical_deadlines.append(deadline_info)
                
                if deadline_date and deadline_date < today and not is_completed:
                    missed_deadlines.append(deadline_info)
        
        # Check for gaps in timeline
        gaps = self._find_timeline_gaps(sorted_events)
        
        # Check sequence issues
        sequence_issues = self._check_sequence_issues(sorted_events, eviction_type)
        
        # Check notice compliance
        notice_compliance = self._check_notice_compliance(sorted_events, eviction_type)
        
        # Check statute issues
        statute_issues = self._check_statute_issues(sorted_events, eviction_type)
        
        return TimelineAnalysis(
            events=[{
                "id": e.get("id"),
                "date": e.get("event_date"),
                "type": e.get("event_type"),
                "title": e.get("title"),
            } for e in sorted_events],
            total_span_days=total_span,
            critical_deadlines=critical_deadlines,
            missed_deadlines=missed_deadlines,
            gaps=gaps,
            sequence_issues=sequence_issues,
            notice_compliance=notice_compliance,
            statute_issues=statute_issues,
        )
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except:
            return None
    
    def _find_timeline_gaps(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find significant gaps in the timeline."""
        gaps = []
        
        for i in range(len(events) - 1):
            date1 = self._parse_date(events[i].get("event_date", ""))
            date2 = self._parse_date(events[i+1].get("event_date", ""))
            
            if date1 and date2:
                gap_days = (date2 - date1).days
                if gap_days > 30:  # Gap of more than 30 days
                    gaps.append({
                        "start_date": events[i].get("event_date"),
                        "end_date": events[i+1].get("event_date"),
                        "days": gap_days,
                        "note": f"No documented activity for {gap_days} days"
                    })
        
        return gaps
    
    def _check_sequence_issues(
        self,
        events: List[Dict[str, Any]],
        eviction_type: str
    ) -> List[str]:
        """Check for issues with event sequence."""
        issues = []
        event_types = [e.get("event_type", "") for e in events]
        
        # Check for notice before summons
        if "summons_served" in event_types:
            summons_idx = event_types.index("summons_served")
            notice_types = ["notice_sent", "notice_posted", "notice_received"]
            
            has_prior_notice = any(
                et in notice_types and i < summons_idx
                for i, et in enumerate(event_types)
            )
            
            if not has_prior_notice and eviction_type != "holdover":
                issues.append("Summons appears to have been served without proper notice")
        
        # Check for answer filed before hearing
        if "hearing_held" in event_types and "answer_filed" in event_types:
            hearing_idx = event_types.index("hearing_held")
            answer_idx = event_types.index("answer_filed")
            
            if answer_idx > hearing_idx:
                issues.append("Answer filed after hearing (may be late)")
        
        return issues
    
    def _check_notice_compliance(
        self,
        events: List[Dict[str, Any]],
        eviction_type: str
    ) -> NoticeComplianceStatus:
        """Check if notice requirements were met."""
        requirements = self.mn_requirements.get(eviction_type, {})
        required_days = requirements.get("notice_days", 0)
        
        # Find notice and filing dates
        notice_date = None
        filing_date = None
        
        for event in events:
            event_type = event.get("event_type", "")
            if event_type in ["notice_sent", "notice_posted", "notice_received"]:
                notice_date = self._parse_date(event.get("event_date", ""))
            elif event_type in ["complaint_filed", "summons_served"]:
                filing_date = self._parse_date(event.get("event_date", ""))
        
        if not notice_date:
            if required_days > 0:
                return NoticeComplianceStatus.NON_COMPLIANT
            else:
                return NoticeComplianceStatus.COMPLIANT  # No notice required
        
        if not filing_date:
            return NoticeComplianceStatus.UNKNOWN
        
        days_between = (filing_date - notice_date).days
        
        if days_between >= required_days:
            return NoticeComplianceStatus.COMPLIANT
        elif days_between > 0:
            return NoticeComplianceStatus.PARTIALLY_COMPLIANT
        else:
            return NoticeComplianceStatus.NON_COMPLIANT
    
    def _check_statute_issues(
        self,
        events: List[Dict[str, Any]],
        eviction_type: str
    ) -> List[str]:
        """Check for statute of limitations and other legal timing issues."""
        issues = []
        requirements = self.mn_requirements.get(eviction_type, {})
        
        # Add relevant statute reference
        statute = requirements.get("statute", "")
        if statute:
            # Note: This would be more sophisticated in production
            pass
        
        return issues
    
    # -------------------------------------------------------------------------
    # Overall Legal Merit Assessment
    # -------------------------------------------------------------------------
    
    def assess_legal_merit(
        self,
        case_data: Dict[str, Any],
        perspective: str = "defendant"  # "defendant" (tenant) or "plaintiff" (landlord)
    ) -> LegalMeritAssessment:
        """
        Comprehensive assessment of legal merit for a case.
        """
        strengths = []
        weaknesses = []
        critical_issues = []
        recommendations = []
        
        # Analyze all documents
        documents = case_data.get("documents", {})
        doc_classifications = []
        total_doc_weight = 0
        
        for doc_id, doc in documents.items():
            classification = self.classify_evidence(doc)
            doc_classifications.append(classification)
            total_doc_weight += classification.weight
            
            if classification.weight > 0.7:
                strengths.append(f"Strong evidence: {doc.get('title', doc.get('filename'))}")
            elif classification.weight < 0.3:
                weaknesses.append(f"Weak evidence: {doc.get('title', doc.get('filename'))}")
            
            for issue in classification.admissibility_issues:
                weaknesses.append(f"Document '{doc.get('title')}': {issue}")
        
        # Evidence summary
        evidence_summary = {
            "total_documents": len(documents),
            "average_weight": total_doc_weight / len(documents) if documents else 0,
            "binding_documents": sum(1 for c in doc_classifications if c.legal_status == DocumentLegalStatus.LEGALLY_BINDING),
            "hearsay_documents": sum(1 for c in doc_classifications if c.evidence_type == EvidenceType.HEARSAY),
        }
        
        # Analyze timeline
        events = list(case_data.get("events", {}).values())
        eviction_type = self._determine_eviction_type(case_data)
        timeline_analysis = self.analyze_timeline(events, eviction_type)
        
        # Timeline issues
        if timeline_analysis.missed_deadlines:
            if perspective == "defendant":
                critical_issues.append(f"{len(timeline_analysis.missed_deadlines)} missed deadline(s) - may affect case")
            else:
                strengths.append("Defendant missed deadlines")
        
        if timeline_analysis.notice_compliance == NoticeComplianceStatus.NON_COMPLIANT:
            if perspective == "defendant":
                strengths.append("Notice requirements not met by landlord - potential defense")
            else:
                critical_issues.append("Notice requirements not met - case may be dismissed")
        
        for issue in timeline_analysis.sequence_issues:
            if perspective == "defendant":
                strengths.append(f"Procedural issue: {issue}")
            else:
                weaknesses.append(f"Procedural issue: {issue}")
        
        # Timeline summary
        timeline_summary = {
            "total_events": len(events),
            "span_days": timeline_analysis.total_span_days,
            "missed_deadlines": len(timeline_analysis.missed_deadlines),
            "notice_compliance": timeline_analysis.notice_compliance.value,
            "sequence_issues": len(timeline_analysis.sequence_issues),
        }
        
        # Check consistency
        all_items = list(documents.values()) + events
        consistency_checks = self.check_consistency(all_items)
        
        contradictions = [c for c in consistency_checks if c.status == ConsistencyStatus.MAJOR_CONTRADICTION]
        if contradictions:
            for c in contradictions:
                if c.significance == "critical":
                    critical_issues.append(f"Critical inconsistency in {c.field_checked}: {c.explanation}")
                else:
                    weaknesses.append(f"Inconsistency in {c.field_checked}: {c.explanation}")
        
        # Consistency summary
        consistency_summary = {
            "total_checks": len(consistency_checks),
            "consistent": sum(1 for c in consistency_checks if c.status == ConsistencyStatus.CONSISTENT),
            "minor_discrepancies": sum(1 for c in consistency_checks if c.status == ConsistencyStatus.MINOR_DISCREPANCY),
            "major_contradictions": len(contradictions),
        }
        
        # Check issues for habitability defense
        issues = list(case_data.get("issues", {}).values())
        habitability_issues = [i for i in issues if i.get("is_habitability_issue")]
        if habitability_issues and perspective == "defendant":
            strengths.append(f"{len(habitability_issues)} documented habitability issue(s) - potential defense")
        
        # Calculate overall score
        score = 50.0  # Start at neutral
        
        # Adjust for evidence strength
        score += (evidence_summary["average_weight"] - 0.5) * 30
        
        # Adjust for consistency
        if consistency_summary["major_contradictions"] > 0:
            score -= consistency_summary["major_contradictions"] * 10
        
        # Adjust for timeline compliance
        if timeline_analysis.notice_compliance == NoticeComplianceStatus.COMPLIANT:
            if perspective == "plaintiff":
                score += 10
            else:
                score -= 5
        elif timeline_analysis.notice_compliance == NoticeComplianceStatus.NON_COMPLIANT:
            if perspective == "defendant":
                score += 15
            else:
                score -= 20
        
        # Adjust for critical issues
        score -= len(critical_issues) * 10
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        # Determine merit level
        if score >= 70:
            merit = LegalMeritLevel.STRONG
        elif score >= 50:
            merit = LegalMeritLevel.MODERATE
        elif score >= 30:
            merit = LegalMeritLevel.WEAK
        else:
            merit = LegalMeritLevel.INSUFFICIENT
        
        # Generate recommendations
        if evidence_summary["total_documents"] < 3:
            recommendations.append("Gather additional documentary evidence")
        if evidence_summary["hearsay_documents"] > 0:
            recommendations.append("Obtain direct evidence to replace hearsay")
        if timeline_analysis.gaps:
            recommendations.append("Document activities during timeline gaps")
        if not habitability_issues and perspective == "defendant":
            recommendations.append("Document any habitability issues if present")
        
        return LegalMeritAssessment(
            overall_merit=merit,
            score=score,
            strengths=strengths,
            weaknesses=weaknesses,
            critical_issues=critical_issues,
            evidence_summary=evidence_summary,
            consistency_summary=consistency_summary,
            timeline_summary=timeline_summary,
            recommendations=recommendations,
        )
    
    def _determine_eviction_type(self, case_data: Dict[str, Any]) -> str:
        """Determine the type of eviction from case data."""
        legal_cases = case_data.get("legal_cases", {})
        
        for case in legal_cases.values():
            claims = case.get("claims", [])
            for claim in claims:
                claim_lower = claim.lower()
                if "nonpayment" in claim_lower or "rent" in claim_lower:
                    return "non_payment"
                elif "lease violation" in claim_lower:
                    return "lease_violation"
                elif "holdover" in claim_lower:
                    return "holdover"
        
        return "non_payment"  # Default


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_legal_analysis_engine: Optional[LegalAnalysisEngine] = None


def get_legal_analysis_engine() -> LegalAnalysisEngine:
    """Get the singleton LegalAnalysisEngine instance."""
    global _legal_analysis_engine
    if _legal_analysis_engine is None:
        _legal_analysis_engine = LegalAnalysisEngine()
    return _legal_analysis_engine
