"""
✍️ Handwriting Recognition & Forgery Detection
===============================================
Advanced handwriting analysis for document verification.

Features:
- Signature extraction and comparison
- Handwriting style analysis
- Forgery detection patterns
- Consistency scoring across documents
- Pressure/stroke analysis simulation
- Date manipulation detection
"""

import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import math


class SignatureStatus(str, Enum):
    """Status of signature verification."""
    VERIFIED = "verified"
    SUSPICIOUS = "suspicious"
    LIKELY_FORGED = "likely_forged"
    MISSING = "missing"
    ILLEGIBLE = "illegible"
    MACHINE_GENERATED = "machine_generated"
    COPY_DETECTED = "copy_detected"


class HandwritingType(str, Enum):
    """Types of handwritten content."""
    SIGNATURE = "signature"
    INITIALS = "initials"
    DATE = "date"
    AMOUNT = "amount"
    ANNOTATION = "annotation"
    FULL_TEXT = "full_text"
    CHECKMARK = "checkmark"
    CORRECTION = "correction"


class ForgeryType(str, Enum):
    """Types of forgery indicators."""
    SIGNATURE_MISMATCH = "signature_mismatch"
    DATE_ALTERATION = "date_alteration"
    AMOUNT_MODIFICATION = "amount_modification"
    TEXT_INSERTION = "text_insertion"
    WHITEOUT_DETECTED = "whiteout_detected"
    INK_INCONSISTENCY = "ink_inconsistency"
    PRESSURE_ANOMALY = "pressure_anomaly"
    TRACING_DETECTED = "tracing_detected"
    DIGITAL_MANIPULATION = "digital_manipulation"
    COPY_PASTE_SIGNATURE = "copy_paste_signature"
    TIMESTAMP_MISMATCH = "timestamp_mismatch"


class RiskLevel(str, Enum):
    """Risk level for forgery detection."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SignatureProfile:
    """Profile of a signature for comparison."""
    id: str
    signer_name: str
    signature_text: str  # Extracted signature text/representation
    location_in_doc: str  # Where in document (e.g., "bottom", "witness line")
    
    # Characteristics (simulated from text analysis)
    estimated_slant: float = 0.0  # -1 to 1 (left to right)
    estimated_size: str = "medium"  # small, medium, large
    estimated_complexity: float = 0.5  # 0 to 1
    has_flourish: bool = False
    is_legible: bool = True
    
    # Metadata
    page_number: int = 1
    confidence: float = 0.8
    extraction_method: str = "pattern_match"
    
    # Hash for comparison
    signature_hash: str = ""
    
    def __post_init__(self):
        if not self.signature_hash:
            self.signature_hash = hashlib.md5(
                f"{self.signer_name}:{self.signature_text}".encode()
            ).hexdigest()[:12]
    
    def similarity_to(self, other: "SignatureProfile") -> float:
        """Calculate similarity score to another signature."""
        if not other:
            return 0.0
        
        score = 0.0
        factors = 0
        
        # Name similarity
        if self.signer_name.lower() == other.signer_name.lower():
            score += 1.0
            factors += 1
        elif self._name_similarity(self.signer_name, other.signer_name) > 0.7:
            score += 0.7
            factors += 1
        
        # Size similarity
        if self.estimated_size == other.estimated_size:
            score += 1.0
        else:
            score += 0.5
        factors += 1
        
        # Complexity similarity
        complexity_diff = abs(self.estimated_complexity - other.estimated_complexity)
        score += max(0, 1.0 - complexity_diff * 2)
        factors += 1
        
        # Flourish match
        if self.has_flourish == other.has_flourish:
            score += 1.0
        factors += 1
        
        # Slant similarity
        slant_diff = abs(self.estimated_slant - other.estimated_slant)
        score += max(0, 1.0 - slant_diff)
        factors += 1
        
        return score / factors if factors > 0 else 0.0
    
    def _name_similarity(self, name1: str, name2: str) -> float:
        """Simple name similarity check."""
        n1 = name1.lower().replace(" ", "")
        n2 = name2.lower().replace(" ", "")
        
        if n1 == n2:
            return 1.0
        
        # Check if one contains the other
        if n1 in n2 or n2 in n1:
            return 0.8
        
        # Check initials match
        initials1 = "".join(w[0] for w in name1.split() if w)
        initials2 = "".join(w[0] for w in name2.split() if w)
        if initials1.lower() == initials2.lower():
            return 0.6
        
        return 0.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "signer_name": self.signer_name,
            "signature_text": self.signature_text,
            "location": self.location_in_doc,
            "characteristics": {
                "slant": self.estimated_slant,
                "size": self.estimated_size,
                "complexity": self.estimated_complexity,
                "has_flourish": self.has_flourish,
                "legible": self.is_legible,
            },
            "confidence": self.confidence,
            "hash": self.signature_hash,
        }


@dataclass
class HandwrittenElement:
    """A handwritten element detected in document."""
    id: str
    element_type: HandwritingType
    content: str
    location: str
    page_number: int = 1
    
    # Analysis
    confidence: float = 0.8
    is_authentic: bool = True
    forgery_indicators: List[str] = field(default_factory=list)
    
    # Context
    near_text: str = ""
    field_label: str = ""  # e.g., "Signature:", "Date:"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.element_type.value,
            "content": self.content,
            "location": self.location,
            "page": self.page_number,
            "confidence": self.confidence,
            "authentic": self.is_authentic,
            "forgery_indicators": self.forgery_indicators,
            "field_label": self.field_label,
        }


@dataclass
class ForgeryIndicator:
    """An indicator of potential forgery."""
    id: str
    forgery_type: ForgeryType
    description: str
    location: str
    
    risk_level: RiskLevel = RiskLevel.MEDIUM
    confidence: float = 0.7
    evidence: List[str] = field(default_factory=list)
    
    # Legal implications
    legal_significance: str = ""
    recommended_action: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.forgery_type.value,
            "description": self.description,
            "location": self.location,
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "legal_significance": self.legal_significance,
            "recommended_action": self.recommended_action,
        }


@dataclass
class SignatureComparison:
    """Result of comparing two signatures."""
    signature1_id: str
    signature2_id: str
    similarity_score: float
    
    match_status: SignatureStatus = SignatureStatus.VERIFIED
    discrepancies: List[str] = field(default_factory=list)
    
    # Detailed comparison
    name_match: bool = True
    style_match: bool = True
    size_match: bool = True
    
    def to_dict(self) -> dict:
        return {
            "signature1": self.signature1_id,
            "signature2": self.signature2_id,
            "similarity": self.similarity_score,
            "status": self.match_status.value,
            "discrepancies": self.discrepancies,
            "matches": {
                "name": self.name_match,
                "style": self.style_match,
                "size": self.size_match,
            },
        }


@dataclass
class HandwritingAnalysisResult:
    """Complete handwriting analysis result."""
    analysis_id: str
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    # Extracted elements
    signatures: List[SignatureProfile] = field(default_factory=list)
    handwritten_elements: List[HandwrittenElement] = field(default_factory=list)
    
    # Forgery detection
    forgery_indicators: List[ForgeryIndicator] = field(default_factory=list)
    overall_risk_level: RiskLevel = RiskLevel.NONE
    forgery_risk_score: float = 0.0
    
    # Signature verification
    signature_comparisons: List[SignatureComparison] = field(default_factory=list)
    all_signatures_verified: bool = True
    
    # Summary
    total_signatures: int = 0
    total_handwritten: int = 0
    suspicious_elements: int = 0
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    requires_expert_review: bool = False
    
    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id,
            "analyzed_at": self.analyzed_at.isoformat(),
            "signatures": [s.to_dict() for s in self.signatures],
            "handwritten_elements": [e.to_dict() for e in self.handwritten_elements],
            "forgery_detection": {
                "indicators": [i.to_dict() for i in self.forgery_indicators],
                "risk_level": self.overall_risk_level.value,
                "risk_score": self.forgery_risk_score,
            },
            "signature_verification": {
                "comparisons": [c.to_dict() for c in self.signature_comparisons],
                "all_verified": self.all_signatures_verified,
            },
            "summary": {
                "total_signatures": self.total_signatures,
                "total_handwritten": self.total_handwritten,
                "suspicious_elements": self.suspicious_elements,
            },
            "recommendations": self.recommendations,
            "requires_expert_review": self.requires_expert_review,
        }


class HandwritingAnalyzer:
    """
    Advanced handwriting analysis engine.
    
    Analyzes documents for:
    - Signature presence and validity
    - Handwritten dates, amounts, annotations
    - Forgery indicators
    - Document manipulation
    """
    
    def __init__(self):
        self._init_patterns()
        self._init_forgery_rules()
    
    def _init_patterns(self):
        """Initialize detection patterns."""
        
        # Signature detection patterns
        self.signature_patterns = [
            # Explicit signature lines
            (r"(?:Signature|Signed|Sign here)[:\s]*[_\-]{3,}", "signature_line"),
            (r"(?:/{2,}|_{3,})\s*(?:Signature|Tenant|Landlord|Owner)", "signature_field"),
            
            # Name after signature indicator
            (r"(?:Signed|Executed by)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", "signed_name"),
            (r"(?:By|Signature of)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", "by_name"),
            
            # Witness signatures
            (r"Witness(?:ed)?[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", "witness_sig"),
            
            # Notary signatures
            (r"Notary\s+Public[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", "notary_sig"),
            
            # Common signature patterns
            (r"/s/\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", "electronic_sig"),
            (r"\[signed\]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", "indicated_sig"),
        ]
        
        # Handwritten date patterns
        self.handwritten_date_patterns = [
            # Dates that look handwritten (informal formats)
            (r"(?:Date|Dated)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", "written_date"),
            (r"(?:this|the)\s+(\d{1,2}(?:st|nd|rd|th)?)\s+(?:day of\s+)?([A-Z][a-z]+)[,\s]+(\d{4})", "formal_date"),
            (r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s*(?:_+|/{2,})", "date_field"),
        ]
        
        # Handwritten amount patterns
        self.handwritten_amount_patterns = [
            (r"(?:Amount|Sum|Total)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", "amount_field"),
            (r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:dollars?)?", "dollar_amount"),
            (r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:dollars?|and\s+\d+/100)", "written_amount"),
        ]
        
        # Initials patterns
        self.initials_patterns = [
            (r"(?:Initial|Initials)[:\s]*([A-Z]{2,4})", "initials_field"),
            (r"(?:_{2,}|/{2,})\s*(?:Initials)", "initials_line"),
            (r"\[([A-Z]{2,3})\]", "bracketed_initials"),
        ]
        
        # Annotation patterns
        self.annotation_patterns = [
            (r"(?:Note|N\.B\.|NB)[:\s]*(.+?)(?:\n|$)", "note"),
            (r"(?:See|Refer to)[:\s]*(.+?)(?:\n|$)", "reference"),
            (r"\*\s*(.+?)(?:\n|$)", "asterisk_note"),
        ]
    
    def _init_forgery_rules(self):
        """Initialize forgery detection rules."""
        
        self.forgery_rules = {
            # Date manipulation indicators
            "date_future": {
                "type": ForgeryType.DATE_ALTERATION,
                "description": "Document dated in the future",
                "risk": RiskLevel.HIGH,
            },
            "date_inconsistent": {
                "type": ForgeryType.DATE_ALTERATION,
                "description": "Multiple inconsistent dates in document",
                "risk": RiskLevel.MEDIUM,
            },
            "date_weekend": {
                "type": ForgeryType.DATE_ALTERATION,
                "description": "Legal document dated on weekend/holiday",
                "risk": RiskLevel.LOW,
            },
            
            # Signature issues
            "signature_missing": {
                "type": ForgeryType.SIGNATURE_MISMATCH,
                "description": "Required signature is missing",
                "risk": RiskLevel.HIGH,
            },
            "signature_copy": {
                "type": ForgeryType.COPY_PASTE_SIGNATURE,
                "description": "Signature appears to be copied/pasted",
                "risk": RiskLevel.CRITICAL,
            },
            "signature_mismatch": {
                "type": ForgeryType.SIGNATURE_MISMATCH,
                "description": "Signature doesn't match name",
                "risk": RiskLevel.HIGH,
            },
            
            # Amount manipulation
            "amount_altered": {
                "type": ForgeryType.AMOUNT_MODIFICATION,
                "description": "Amount appears to have been altered",
                "risk": RiskLevel.CRITICAL,
            },
            "amount_inconsistent": {
                "type": ForgeryType.AMOUNT_MODIFICATION,
                "description": "Amounts don't add up correctly",
                "risk": RiskLevel.HIGH,
            },
            
            # Document tampering
            "whiteout": {
                "type": ForgeryType.WHITEOUT_DETECTED,
                "description": "Evidence of whiteout/correction fluid",
                "risk": RiskLevel.HIGH,
            },
            "text_insertion": {
                "type": ForgeryType.TEXT_INSERTION,
                "description": "Text appears to be inserted after signing",
                "risk": RiskLevel.CRITICAL,
            },
            "ink_variation": {
                "type": ForgeryType.INK_INCONSISTENCY,
                "description": "Multiple ink colors/types detected",
                "risk": RiskLevel.MEDIUM,
            },
        }
        
        # Minnesota-specific rules for tenant documents
        self.mn_forgery_rules = {
            "backdated_notice": {
                "type": ForgeryType.DATE_ALTERATION,
                "description": "Eviction notice appears backdated to meet statutory timeline",
                "risk": RiskLevel.CRITICAL,
                "legal": "Violation of MN Stat. 504B.321 - Proper notice requirements",
            },
            "forged_tenant_signature": {
                "type": ForgeryType.SIGNATURE_MISMATCH,
                "description": "Tenant signature appears forged on lease modification",
                "risk": RiskLevel.CRITICAL,
                "legal": "Potential fraud - void agreement under MN contract law",
            },
            "altered_rent_amount": {
                "type": ForgeryType.AMOUNT_MODIFICATION,
                "description": "Rent amount appears altered from original",
                "risk": RiskLevel.CRITICAL,
                "legal": "Material alteration voids original terms",
            },
        }
    
    async def analyze(
        self,
        text: str,
        document_type: Optional[str] = None,
        reference_signatures: Optional[List[SignatureProfile]] = None,
    ) -> HandwritingAnalysisResult:
        """
        Perform complete handwriting analysis.
        
        Args:
            text: Document text to analyze
            document_type: Type of document for context
            reference_signatures: Known signatures for comparison
        
        Returns:
            Complete handwriting analysis result
        """
        from uuid import uuid4
        
        result = HandwritingAnalysisResult(
            analysis_id=str(uuid4())[:8],
        )
        
        # Extract signatures
        result.signatures = self._extract_signatures(text)
        result.total_signatures = len(result.signatures)
        
        # Extract other handwritten elements
        result.handwritten_elements = self._extract_handwritten_elements(text)
        result.total_handwritten = len(result.handwritten_elements)
        
        # Detect forgery indicators
        result.forgery_indicators = self._detect_forgery_indicators(
            text, result.signatures, result.handwritten_elements, document_type
        )
        
        # Compare signatures if references provided
        if reference_signatures:
            result.signature_comparisons = self._compare_signatures(
                result.signatures, reference_signatures
            )
            result.all_signatures_verified = all(
                c.match_status == SignatureStatus.VERIFIED
                for c in result.signature_comparisons
            )
        
        # Calculate overall risk
        result.forgery_risk_score = self._calculate_risk_score(result.forgery_indicators)
        result.overall_risk_level = self._determine_risk_level(result.forgery_risk_score)
        
        # Count suspicious elements
        result.suspicious_elements = len([
            e for e in result.handwritten_elements
            if not e.is_authentic
        ]) + len([
            s for s in result.signatures
            if s.confidence < 0.6
        ])
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)
        result.requires_expert_review = (
            result.overall_risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            or result.suspicious_elements > 2
        )
        
        return result
    
    def _extract_signatures(self, text: str) -> List[SignatureProfile]:
        """Extract all signatures from document."""
        from uuid import uuid4
        
        signatures = []
        text_lower = text.lower()
        
        for pattern, pattern_type in self.signature_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                # Determine signer name
                if match.groups():
                    signer_name = match.group(1).strip()
                else:
                    # Try to find name near signature line
                    signer_name = self._find_name_near_position(text, match.start())
                
                if not signer_name or len(signer_name) < 2:
                    signer_name = "Unknown Signer"
                
                # Determine location
                location = self._determine_signature_location(text, match.start())
                
                # Analyze signature characteristics
                sig = SignatureProfile(
                    id=str(uuid4())[:8],
                    signer_name=signer_name,
                    signature_text=match.group(0)[:100],
                    location_in_doc=location,
                    estimated_slant=self._estimate_slant(signer_name),
                    estimated_size=self._estimate_size(match.group(0)),
                    estimated_complexity=self._estimate_complexity(signer_name),
                    has_flourish=self._detect_flourish(signer_name),
                    is_legible=len(signer_name) > 2 and signer_name != "Unknown Signer",
                    page_number=self._estimate_page(text, match.start()),
                    confidence=0.8 if pattern_type in ["signed_name", "by_name"] else 0.6,
                    extraction_method=pattern_type,
                )
                
                # Avoid duplicates
                if not any(s.signer_name == sig.signer_name and s.location_in_doc == sig.location_in_doc for s in signatures):
                    signatures.append(sig)
        
        # Check for electronic signatures
        electronic_sigs = self._detect_electronic_signatures(text)
        for e_sig in electronic_sigs:
            if not any(s.signer_name == e_sig.signer_name for s in signatures):
                signatures.append(e_sig)
        
        return signatures
    
    def _extract_handwritten_elements(self, text: str) -> List[HandwrittenElement]:
        """Extract handwritten dates, amounts, initials, annotations."""
        from uuid import uuid4
        
        elements = []
        
        # Extract dates
        for pattern, pattern_type in self.handwritten_date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                elements.append(HandwrittenElement(
                    id=str(uuid4())[:8],
                    element_type=HandwritingType.DATE,
                    content=match.group(0),
                    location=self._determine_location(text, match.start()),
                    page_number=self._estimate_page(text, match.start()),
                    confidence=0.85,
                    field_label=self._find_field_label(text, match.start()),
                ))
        
        # Extract amounts
        for pattern, pattern_type in self.handwritten_amount_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                elements.append(HandwrittenElement(
                    id=str(uuid4())[:8],
                    element_type=HandwritingType.AMOUNT,
                    content=match.group(0),
                    location=self._determine_location(text, match.start()),
                    page_number=self._estimate_page(text, match.start()),
                    confidence=0.85,
                    field_label=self._find_field_label(text, match.start()),
                ))
        
        # Extract initials
        for pattern, pattern_type in self.initials_patterns:
            for match in re.finditer(pattern, text):
                elements.append(HandwrittenElement(
                    id=str(uuid4())[:8],
                    element_type=HandwritingType.INITIALS,
                    content=match.group(0),
                    location=self._determine_location(text, match.start()),
                    page_number=self._estimate_page(text, match.start()),
                    confidence=0.75,
                ))
        
        # Extract annotations
        for pattern, pattern_type in self.annotation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                elements.append(HandwrittenElement(
                    id=str(uuid4())[:8],
                    element_type=HandwritingType.ANNOTATION,
                    content=match.group(0)[:200],
                    location=self._determine_location(text, match.start()),
                    page_number=self._estimate_page(text, match.start()),
                    confidence=0.7,
                ))
        
        return elements
    
    def _detect_forgery_indicators(
        self,
        text: str,
        signatures: List[SignatureProfile],
        elements: List[HandwrittenElement],
        document_type: Optional[str],
    ) -> List[ForgeryIndicator]:
        """Detect potential forgery indicators."""
        from uuid import uuid4
        
        indicators = []
        
        # Check for missing signatures on legal documents
        if self._requires_signature(document_type) and not signatures:
            indicators.append(ForgeryIndicator(
                id=str(uuid4())[:8],
                forgery_type=ForgeryType.SIGNATURE_MISMATCH,
                description="Required signature is missing from document",
                location="document",
                risk_level=RiskLevel.HIGH,
                confidence=0.9,
                evidence=["No signature detected in legal document"],
                legal_significance="Document may not be legally binding without proper signatures",
                recommended_action="Request properly signed original document",
            ))
        
        # Check for date issues
        date_indicators = self._check_date_issues(text, elements)
        indicators.extend(date_indicators)
        
        # Check for amount inconsistencies
        amount_indicators = self._check_amount_issues(text, elements)
        indicators.extend(amount_indicators)
        
        # Check for duplicate/copied signatures
        sig_copy_indicators = self._check_signature_copying(signatures)
        indicators.extend(sig_copy_indicators)
        
        # Check for text alterations
        alteration_indicators = self._check_text_alterations(text)
        indicators.extend(alteration_indicators)
        
        # Minnesota-specific checks
        if document_type and "notice" in document_type.lower():
            mn_indicators = self._check_mn_notice_issues(text, elements)
            indicators.extend(mn_indicators)
        
        return indicators
    
    def _check_date_issues(self, text: str, elements: List[HandwrittenElement]) -> List[ForgeryIndicator]:
        """Check for date-related forgery indicators."""
        from uuid import uuid4
        
        indicators = []
        dates = [e for e in elements if e.element_type == HandwritingType.DATE]
        
        # Check for future dates
        today = date.today()
        for date_elem in dates:
            parsed_date = self._parse_date(date_elem.content)
            if parsed_date and parsed_date > today:
                indicators.append(ForgeryIndicator(
                    id=str(uuid4())[:8],
                    forgery_type=ForgeryType.DATE_ALTERATION,
                    description=f"Document contains future date: {date_elem.content}",
                    location=date_elem.location,
                    risk_level=RiskLevel.HIGH,
                    confidence=0.95,
                    evidence=[f"Date '{date_elem.content}' is after today's date"],
                    legal_significance="Future-dated documents may indicate fraud or manipulation",
                    recommended_action="Verify actual document creation date",
                ))
        
        # Check for inconsistent dates
        if len(dates) > 1:
            parsed_dates = [self._parse_date(d.content) for d in dates]
            parsed_dates = [d for d in parsed_dates if d]
            
            if parsed_dates:
                date_range = (max(parsed_dates) - min(parsed_dates)).days
                if date_range > 30:  # Dates more than 30 days apart
                    indicators.append(ForgeryIndicator(
                        id=str(uuid4())[:8],
                        forgery_type=ForgeryType.DATE_ALTERATION,
                        description=f"Document contains dates {date_range} days apart",
                        location="multiple",
                        risk_level=RiskLevel.MEDIUM,
                        confidence=0.7,
                        evidence=[f"Date range spans {date_range} days"],
                        legal_significance="May indicate document was modified over time",
                        recommended_action="Verify all dates are accurate and intentional",
                    ))
        
        return indicators
    
    def _check_amount_issues(self, text: str, elements: List[HandwrittenElement]) -> List[ForgeryIndicator]:
        """Check for amount-related forgery indicators."""
        from uuid import uuid4
        
        indicators = []
        amounts = [e for e in elements if e.element_type == HandwritingType.AMOUNT]
        
        # Extract all dollar amounts from text
        all_amounts = re.findall(r'\$\s*([\d,]+(?:\.\d{2})?)', text)
        parsed_amounts = []
        for amt in all_amounts:
            try:
                parsed_amounts.append(float(amt.replace(',', '')))
            except ValueError:
                pass
        
        # Check for amounts that don't add up
        if len(parsed_amounts) >= 3:
            # Look for a "total" pattern
            total_match = re.search(
                r'(?:total|sum|amount due|balance)[:\s]*\$?\s*([\d,]+(?:\.\d{2})?)',
                text, re.IGNORECASE
            )
            if total_match:
                try:
                    stated_total = float(total_match.group(1).replace(',', ''))
                    # Sum all other amounts
                    other_amounts = [a for a in parsed_amounts if a != stated_total]
                    if other_amounts:
                        calculated_sum = sum(other_amounts)
                        # Allow for small rounding differences
                        if abs(calculated_sum - stated_total) > 1.0 and stated_total > 0:
                            indicators.append(ForgeryIndicator(
                                id=str(uuid4())[:8],
                                forgery_type=ForgeryType.AMOUNT_MODIFICATION,
                                description=f"Amounts don't add up: stated ${stated_total:.2f}, calculated ${calculated_sum:.2f}",
                                location="financial section",
                                risk_level=RiskLevel.HIGH,
                                confidence=0.85,
                                evidence=[
                                    f"Stated total: ${stated_total:.2f}",
                                    f"Sum of items: ${calculated_sum:.2f}",
                                    f"Discrepancy: ${abs(stated_total - calculated_sum):.2f}",
                                ],
                                legal_significance="Amount discrepancies may indicate manipulation",
                                recommended_action="Request itemized breakdown and verify calculations",
                            ))
                except ValueError:
                    pass
        
        return indicators
    
    def _check_signature_copying(self, signatures: List[SignatureProfile]) -> List[ForgeryIndicator]:
        """Check for copied/pasted signatures."""
        from uuid import uuid4
        
        indicators = []
        
        # Check for identical signature hashes (exact copies)
        seen_hashes = {}
        for sig in signatures:
            if sig.signature_hash in seen_hashes:
                indicators.append(ForgeryIndicator(
                    id=str(uuid4())[:8],
                    forgery_type=ForgeryType.COPY_PASTE_SIGNATURE,
                    description=f"Identical signature detected in multiple locations",
                    location=f"{seen_hashes[sig.signature_hash]} and {sig.location_in_doc}",
                    risk_level=RiskLevel.CRITICAL,
                    confidence=0.9,
                    evidence=[
                        f"Signature hash {sig.signature_hash} appears multiple times",
                        "Digital copies produce identical patterns",
                    ],
                    legal_significance="Copy-pasted signatures are typically not legally valid",
                    recommended_action="Request original wet signatures or verified e-signatures",
                ))
            else:
                seen_hashes[sig.signature_hash] = sig.location_in_doc
        
        return indicators
    
    def _check_text_alterations(self, text: str) -> List[ForgeryIndicator]:
        """Check for signs of text alteration."""
        from uuid import uuid4
        
        indicators = []
        
        # Check for common alteration indicators
        alteration_patterns = [
            (r'\b(\d)\s+(\d)\b', "Spaced digits may indicate inserted numbers"),
            (r'(?:^|\s)([A-Z])\s+([a-z])', "Unusual spacing may indicate text insertion"),
            (r'\[\s*(?:sic|?)\s*\]', "Editorial marks may indicate known issues"),
        ]
        
        # Check for strikethrough/correction indicators
        correction_patterns = [
            (r'(?:strikethrough|crossed out|deleted)', "Document mentions deletions"),
            (r'(?:correction|corrected|amended)', "Document mentions corrections"),
            (r'(?:white.?out|liquid paper|correction fluid)', "Document mentions correction fluid"),
        ]
        
        for pattern, description in correction_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                indicators.append(ForgeryIndicator(
                    id=str(uuid4())[:8],
                    forgery_type=ForgeryType.WHITEOUT_DETECTED,
                    description=description,
                    location="document body",
                    risk_level=RiskLevel.MEDIUM,
                    confidence=0.7,
                    evidence=[f"Text pattern: {pattern}"],
                    legal_significance="Corrections should be initialed and dated",
                    recommended_action="Verify all corrections were made by authorized parties",
                ))
        
        return indicators
    
    def _check_mn_notice_issues(self, text: str, elements: List[HandwrittenElement]) -> List[ForgeryIndicator]:
        """Check Minnesota-specific notice issues."""
        from uuid import uuid4
        
        indicators = []
        
        # Check if notice date allows proper notice period
        dates = [e for e in elements if e.element_type == HandwritingType.DATE]
        
        # Look for eviction-related terms
        is_eviction = bool(re.search(
            r'evict|vacate|quit|terminate|14.?day|30.?day', text, re.IGNORECASE
        ))
        
        if is_eviction and dates:
            for date_elem in dates:
                parsed_date = self._parse_date(date_elem.content)
                if parsed_date:
                    days_from_now = (parsed_date - date.today()).days
                    
                    # Check if date is suspiciously close to current requirements
                    if -2 <= days_from_now <= 0:
                        indicators.append(ForgeryIndicator(
                            id=str(uuid4())[:8],
                            forgery_type=ForgeryType.DATE_ALTERATION,
                            description="Notice date appears to be backdated to meet statutory requirements",
                            location=date_elem.location,
                            risk_level=RiskLevel.CRITICAL,
                            confidence=0.75,
                            evidence=[
                                f"Notice dated {date_elem.content}",
                                "Date suspiciously close to statutory deadline",
                            ],
                            legal_significance="Backdating notices violates MN Stat. 504B - improper notice is a defense to eviction",
                            recommended_action="Challenge notice validity; request proof of service date",
                        ))
        
        return indicators
    
    def _compare_signatures(
        self,
        document_signatures: List[SignatureProfile],
        reference_signatures: List[SignatureProfile],
    ) -> List[SignatureComparison]:
        """Compare document signatures against reference signatures."""
        comparisons = []
        
        for doc_sig in document_signatures:
            # Find best matching reference
            best_match = None
            best_score = 0.0
            
            for ref_sig in reference_signatures:
                score = doc_sig.similarity_to(ref_sig)
                if score > best_score:
                    best_score = score
                    best_match = ref_sig
            
            if best_match:
                # Determine status based on score
                if best_score >= 0.85:
                    status = SignatureStatus.VERIFIED
                elif best_score >= 0.6:
                    status = SignatureStatus.SUSPICIOUS
                else:
                    status = SignatureStatus.LIKELY_FORGED
                
                discrepancies = []
                if doc_sig.signer_name.lower() != best_match.signer_name.lower():
                    discrepancies.append(f"Name mismatch: {doc_sig.signer_name} vs {best_match.signer_name}")
                if doc_sig.estimated_size != best_match.estimated_size:
                    discrepancies.append(f"Size difference: {doc_sig.estimated_size} vs {best_match.estimated_size}")
                if abs(doc_sig.estimated_slant - best_match.estimated_slant) > 0.3:
                    discrepancies.append("Significant slant difference")
                
                comparisons.append(SignatureComparison(
                    signature1_id=doc_sig.id,
                    signature2_id=best_match.id,
                    similarity_score=best_score,
                    match_status=status,
                    discrepancies=discrepancies,
                    name_match=doc_sig.signer_name.lower() == best_match.signer_name.lower(),
                    style_match=best_score >= 0.7,
                    size_match=doc_sig.estimated_size == best_match.estimated_size,
                ))
        
        return comparisons
    
    def _calculate_risk_score(self, indicators: List[ForgeryIndicator]) -> float:
        """Calculate overall forgery risk score (0-100)."""
        if not indicators:
            return 0.0
        
        # Weight by risk level
        weights = {
            RiskLevel.NONE: 0,
            RiskLevel.LOW: 10,
            RiskLevel.MEDIUM: 25,
            RiskLevel.HIGH: 50,
            RiskLevel.CRITICAL: 80,
        }
        
        total_weight = sum(weights[i.risk_level] * i.confidence for i in indicators)
        
        # Cap at 100
        return min(100.0, total_weight)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine overall risk level from score."""
        if score >= 70:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 25:
            return RiskLevel.MEDIUM
        elif score >= 10:
            return RiskLevel.LOW
        return RiskLevel.NONE
    
    def _generate_recommendations(self, result: HandwritingAnalysisResult) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if result.overall_risk_level == RiskLevel.CRITICAL:
            recommendations.append("⚠️ CRITICAL: This document shows strong indicators of forgery or manipulation")
            recommendations.append("Do NOT sign or act on this document until verified")
            recommendations.append("Consider consulting a forensic document examiner")
            recommendations.append("Preserve the original for potential legal action")
        
        elif result.overall_risk_level == RiskLevel.HIGH:
            recommendations.append("⚠️ HIGH RISK: Document shows concerning indicators")
            recommendations.append("Request the original document for examination")
            recommendations.append("Verify all dates and amounts independently")
            recommendations.append("Document your concerns in writing")
        
        elif result.overall_risk_level == RiskLevel.MEDIUM:
            recommendations.append("⚡ MODERATE CONCERN: Some irregularities detected")
            recommendations.append("Verify key information before acting")
            recommendations.append("Keep records of any discrepancies noted")
        
        # Specific recommendations
        for indicator in result.forgery_indicators:
            if indicator.recommended_action and indicator.recommended_action not in recommendations:
                recommendations.append(indicator.recommended_action)
        
        if not result.signatures and result.total_handwritten == 0:
            recommendations.append("No signatures detected - verify document is complete")
        
        if not result.all_signatures_verified and result.signature_comparisons:
            recommendations.append("One or more signatures could not be verified")
        
        return recommendations[:10]  # Limit to top 10
    
    # Helper methods
    
    def _find_name_near_position(self, text: str, position: int) -> str:
        """Find a name near the given position."""
        # Look in surrounding text
        start = max(0, position - 100)
        end = min(len(text), position + 100)
        surrounding = text[start:end]
        
        # Look for name patterns
        name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', surrounding)
        if name_match:
            return name_match.group(1)
        
        return ""
    
    def _determine_signature_location(self, text: str, position: int) -> str:
        """Determine where in document the signature is."""
        total_len = len(text)
        relative_pos = position / total_len if total_len > 0 else 0
        
        if relative_pos < 0.2:
            return "header"
        elif relative_pos > 0.8:
            return "bottom"
        else:
            return "body"
    
    def _determine_location(self, text: str, position: int) -> str:
        """Determine general location in document."""
        return self._determine_signature_location(text, position)
    
    def _estimate_page(self, text: str, position: int) -> int:
        """Estimate page number based on position."""
        # Rough estimate: ~3000 chars per page
        return (position // 3000) + 1
    
    def _estimate_slant(self, name: str) -> float:
        """Estimate signature slant (-1 left, 0 straight, 1 right)."""
        # Heuristic based on name characteristics
        if not name:
            return 0.0
        
        # Names with more descenders tend to slant right
        descenders = sum(1 for c in name.lower() if c in 'gjpqy')
        ascenders = sum(1 for c in name.lower() if c in 'bdfhklt')
        
        slant = (descenders - ascenders) * 0.1
        return max(-1.0, min(1.0, slant + 0.2))  # Slight right bias
    
    def _estimate_size(self, text: str) -> str:
        """Estimate signature size."""
        if len(text) > 50:
            return "large"
        elif len(text) < 20:
            return "small"
        return "medium"
    
    def _estimate_complexity(self, name: str) -> float:
        """Estimate signature complexity (0-1)."""
        if not name:
            return 0.5
        
        # Longer names = more complex
        length_factor = min(1.0, len(name) / 20)
        
        # More unique letters = more complex
        unique_factor = len(set(name.lower())) / 26
        
        return (length_factor + unique_factor) / 2
    
    def _detect_flourish(self, name: str) -> bool:
        """Detect if signature likely has flourishes."""
        # Names ending in certain letters often have flourishes
        if name and name[-1].lower() in 'sygnr':
            return True
        return False
    
    def _detect_electronic_signatures(self, text: str) -> List[SignatureProfile]:
        """Detect electronic/digital signatures."""
        from uuid import uuid4
        
        signatures = []
        
        # Common e-signature patterns
        e_sig_patterns = [
            r'Electronically signed by[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'DocuSign[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'Adobe Sign[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'e-?signed[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]
        
        for pattern in e_sig_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                signatures.append(SignatureProfile(
                    id=str(uuid4())[:8],
                    signer_name=match.group(1).strip(),
                    signature_text=match.group(0),
                    location_in_doc="electronic",
                    estimated_size="medium",
                    estimated_complexity=0.3,  # E-sigs are standardized
                    is_legible=True,
                    confidence=0.9,  # E-sigs are reliable
                    extraction_method="electronic_signature",
                ))
        
        return signatures
    
    def _find_field_label(self, text: str, position: int) -> str:
        """Find the field label near a position."""
        start = max(0, position - 50)
        preceding = text[start:position]
        
        # Look for label patterns
        label_match = re.search(r'([A-Za-z\s]+)[:\s]*$', preceding)
        if label_match:
            return label_match.group(1).strip()
        
        return ""
    
    def _requires_signature(self, document_type: Optional[str]) -> bool:
        """Check if document type requires signature."""
        if not document_type:
            return False
        
        doc_lower = document_type.lower()
        signature_required = [
            'lease', 'agreement', 'contract', 'notice', 'affidavit',
            'motion', 'complaint', 'summons', 'order', 'deed',
        ]
        
        return any(req in doc_lower for req in signature_required)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string."""
        import re
        from datetime import datetime
        
        # Clean the string
        date_str = re.sub(r'[^\d/\-\w\s]', '', date_str).strip()
        
        # Try common formats
        formats = [
            '%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y',
            '%Y-%m-%d', '%Y/%m/%d',
            '%B %d, %Y', '%b %d, %Y',
            '%d %B %Y', '%d %b %Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None


# Convenience function
async def analyze_handwriting(
    text: str,
    document_type: Optional[str] = None,
    reference_signatures: Optional[List[SignatureProfile]] = None,
) -> HandwritingAnalysisResult:
    """
    Analyze document for handwriting and forgery.
    
    Args:
        text: Document text
        document_type: Optional document type for context
        reference_signatures: Optional known signatures for comparison
    
    Returns:
        Complete handwriting analysis result
    """
    analyzer = HandwritingAnalyzer()
    return await analyzer.analyze(text, document_type, reference_signatures)
