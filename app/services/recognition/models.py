"""
Recognition Engine Data Models
==============================

Comprehensive data structures for document recognition, supporting:
- Multi-level confidence scoring
- Reasoning chain tracking
- Legal domain entities
- Relationship mapping
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any, Set, Tuple
from uuid import uuid4


# ============================================================================
# ENUMERATIONS
# ============================================================================

class DocumentCategory(Enum):
    """High-level document categorization"""
    NOTICE = "notice"
    COURT_FILING = "court_filing"
    LEASE_AGREEMENT = "lease_agreement"
    CORRESPONDENCE = "correspondence"
    FINANCIAL = "financial"
    EVIDENCE = "evidence"
    GOVERNMENT_FORM = "government_form"
    UNKNOWN = "unknown"


class DocumentType(Enum):
    """Specific document types for Minnesota tenant law"""
    # Eviction Related
    EVICTION_NOTICE = "eviction_notice"
    NOTICE_TO_QUIT = "notice_to_quit"
    NOTICE_TO_VACATE = "notice_to_vacate"
    FOURTEEN_DAY_NOTICE = "14_day_notice"
    THIRTY_DAY_NOTICE = "30_day_notice"
    IMMEDIATE_NOTICE = "immediate_notice"
    
    # Court Documents
    SUMMONS = "summons"
    COMPLAINT = "complaint"
    WRIT_OF_RECOVERY = "writ_of_recovery"
    ORDER_FOR_JUDGMENT = "order_for_judgment"
    STIPULATION = "stipulation"
    MOTION = "motion"
    AFFIDAVIT = "affidavit"
    SUBPOENA = "subpoena"
    COURT_ORDER = "court_order"
    JUDGMENT = "judgment"
    
    # Lease Documents
    LEASE = "lease"
    LEASE_AMENDMENT = "lease_amendment"
    LEASE_RENEWAL = "lease_renewal"
    LEASE_TERMINATION = "lease_termination"
    
    # Financial Documents
    RENT_RECEIPT = "rent_receipt"
    RENT_LEDGER = "rent_ledger"
    RENT_INCREASE_NOTICE = "rent_increase_notice"
    SECURITY_DEPOSIT_RECEIPT = "security_deposit_receipt"
    SECURITY_DEPOSIT_ITEMIZATION = "security_deposit_itemization"
    LATE_FEE_NOTICE = "late_fee_notice"
    
    # Maintenance/Habitability
    REPAIR_REQUEST = "repair_request"
    MAINTENANCE_LOG = "maintenance_log"
    INSPECTION_REPORT = "inspection_report"
    CODE_VIOLATION = "code_violation"
    
    # Correspondence
    LANDLORD_LETTER = "landlord_letter"
    TENANT_LETTER = "tenant_letter"
    PROPERTY_MANAGER_LETTER = "property_manager_letter"
    ATTORNEY_LETTER = "attorney_letter"
    
    # Evidence
    PHOTOGRAPH = "photograph"
    TEXT_MESSAGES = "text_messages"
    EMAIL = "email"
    BANK_STATEMENT = "bank_statement"
    
    # Government
    HUD_FORM = "hud_form"
    HOUSING_ASSISTANCE_NOTICE = "housing_assistance_notice"
    SECTION_8_DOCUMENT = "section_8_document"
    
    UNKNOWN = "unknown"


class IssueSeverity(Enum):
    """Legal issue severity levels"""
    CRITICAL = "critical"      # Immediate action required
    HIGH = "high"              # Serious issue, action needed soon
    MEDIUM = "medium"          # Notable issue, should address
    LOW = "low"                # Minor issue, FYI
    INFORMATIONAL = "informational"  # Not an issue, just noting


class ConfidenceLevel(Enum):
    """Confidence classification"""
    CERTAIN = "certain"        # 95%+ confidence
    HIGH = "high"              # 80-95% confidence
    MEDIUM = "medium"          # 60-80% confidence
    LOW = "low"                # 40-60% confidence
    UNCERTAIN = "uncertain"    # Below 40%


class EntityType(Enum):
    """Types of extracted entities"""
    PERSON = "person"
    ORGANIZATION = "organization"
    ADDRESS = "address"
    DATE = "date"
    MONEY = "money"
    COURT_CASE = "court_case"
    STATUTE = "statute"
    DEADLINE = "deadline"
    PHONE = "phone"
    EMAIL = "email"
    UNIT_NUMBER = "unit_number"


class PartyRole(Enum):
    """Roles parties can play in tenant law"""
    TENANT = "tenant"
    LANDLORD = "landlord"
    PROPERTY_MANAGER = "property_manager"
    MANAGEMENT_COMPANY = "management_company"
    OWNER = "owner"
    ATTORNEY = "attorney"
    JUDGE = "judge"
    PROCESS_SERVER = "process_server"
    WITNESS = "witness"
    GUARANTOR = "guarantor"
    HOUSING_AUTHORITY = "housing_authority"
    UNKNOWN = "unknown"


class ReasoningType(Enum):
    """Types of reasoning applied"""
    PATTERN_MATCH = "pattern_match"
    SEMANTIC_ANALYSIS = "semantic_analysis"
    LEGAL_RULE = "legal_rule"
    CROSS_REFERENCE = "cross_reference"
    TEMPORAL_LOGIC = "temporal_logic"
    ENTITY_RELATIONSHIP = "entity_relationship"
    STRUCTURAL_ANALYSIS = "structural_analysis"
    STATISTICAL = "statistical"


# ============================================================================
# CORE DATA CLASSES
# ============================================================================

@dataclass
class ConfidenceMetrics:
    """
    Multi-dimensional confidence scoring.
    Tracks confidence across different aspects of analysis.
    """
    overall_score: float = 0.0  # 0-100 aggregate confidence
    level: ConfidenceLevel = ConfidenceLevel.UNCERTAIN
    
    # Component scores (0-100)
    document_type_confidence: float = 0.0
    text_quality_confidence: float = 0.0
    entity_extraction_confidence: float = 0.0
    legal_analysis_confidence: float = 0.0
    relationship_confidence: float = 0.0
    temporal_confidence: float = 0.0
    
    # Uncertainty factors
    ambiguous_elements: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    conflicting_signals: List[str] = field(default_factory=list)
    
    # Quality indicators
    text_completeness: float = 0.0  # How complete is the extracted text
    structural_clarity: float = 0.0  # How clear is document structure
    reasoning_agreement: float = 0.0  # How well do multiple passes agree
    
    def classify(self) -> ConfidenceLevel:
        """Classify overall confidence into level"""
        if self.overall_score >= 95:
            return ConfidenceLevel.CERTAIN
        elif self.overall_score >= 80:
            return ConfidenceLevel.HIGH
        elif self.overall_score >= 60:
            return ConfidenceLevel.MEDIUM
        elif self.overall_score >= 40:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNCERTAIN
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "level": self.level.value,
            "components": {
                "document_type": self.document_type_confidence,
                "text_quality": self.text_quality_confidence,
                "entity_extraction": self.entity_extraction_confidence,
                "legal_analysis": self.legal_analysis_confidence,
                "relationships": self.relationship_confidence,
                "temporal": self.temporal_confidence,
            },
            "uncertainty": {
                "ambiguous": self.ambiguous_elements,
                "missing": self.missing_information,
                "conflicting": self.conflicting_signals,
            },
            "quality": {
                "text_completeness": self.text_completeness,
                "structural_clarity": self.structural_clarity,
                "reasoning_agreement": self.reasoning_agreement,
            }
        }


@dataclass
class ExtractedEntity:
    """
    An entity extracted from the document.
    """
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    entity_type: EntityType = EntityType.PERSON
    value: str = ""
    normalized_value: Optional[str] = None  # Standardized form
    
    # Position in document
    start_position: int = 0
    end_position: int = 0
    page_number: int = 1
    section: Optional[str] = None
    
    # Confidence and reasoning
    confidence: float = 0.0
    extraction_method: str = ""
    reasoning: str = ""
    
    # Additional attributes based on type
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    # For relationships
    related_entities: List[str] = field(default_factory=list)  # Entity IDs
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.entity_type.value,
            "value": self.value,
            "normalized_value": self.normalized_value,
            "position": {
                "start": self.start_position,
                "end": self.end_position,
                "page": self.page_number,
                "section": self.section,
            },
            "confidence": self.confidence,
            "method": self.extraction_method,
            "reasoning": self.reasoning,
            "attributes": self.attributes,
            "related_entities": self.related_entities,
        }


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain"""
    step_number: int = 0
    reasoning_type: ReasoningType = ReasoningType.PATTERN_MATCH
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    confidence_impact: float = 0.0  # How much this step affected confidence
    duration_ms: float = 0.0


@dataclass
class ReasoningChain:
    """
    Complete chain of reasoning for an analysis.
    Enables transparency and debugging.
    """
    chain_id: str = field(default_factory=lambda: str(uuid4())[:8])
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    steps: List[ReasoningStep] = field(default_factory=list)
    
    # Multi-pass tracking
    pass_number: int = 1
    previous_pass_id: Optional[str] = None
    
    # Consensus tracking
    findings_confirmed: List[str] = field(default_factory=list)
    findings_revised: List[str] = field(default_factory=list)
    new_findings: List[str] = field(default_factory=list)
    
    # Final determination
    conclusion: str = ""
    confidence_delta: float = 0.0  # Change in confidence from this pass
    
    def add_step(self, reasoning_type: ReasoningType, description: str,
                 input_data: Dict = None, output_data: Dict = None,
                 confidence_impact: float = 0.0) -> ReasoningStep:
        step = ReasoningStep(
            step_number=len(self.steps) + 1,
            reasoning_type=reasoning_type,
            description=description,
            input_data=input_data or {},
            output_data=output_data or {},
            confidence_impact=confidence_impact
        )
        self.steps.append(step)
        return step
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "pass_number": self.pass_number,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [
                {
                    "step": s.step_number,
                    "type": s.reasoning_type.value,
                    "description": s.description,
                    "confidence_impact": s.confidence_impact,
                }
                for s in self.steps
            ],
            "findings": {
                "confirmed": self.findings_confirmed,
                "revised": self.findings_revised,
                "new": self.new_findings,
            },
            "conclusion": self.conclusion,
            "confidence_delta": self.confidence_delta,
        }


@dataclass
class DocumentSection:
    """A recognized section within a document"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    section_type: str = ""  # header, body, footer, signature, etc.
    title: Optional[str] = None
    content: str = ""
    
    start_position: int = 0
    end_position: int = 0
    page_number: int = 1
    
    # Hierarchy
    parent_section_id: Optional[str] = None
    child_section_ids: List[str] = field(default_factory=list)
    
    # Analysis
    importance_score: float = 0.0  # How important is this section
    entities_in_section: List[str] = field(default_factory=list)


@dataclass
class DocumentContext:
    """
    Rich context about the document structure and content.
    """
    # Document identification
    filename: Optional[str] = None
    file_type: str = ""  # pdf, jpg, docx, etc.
    file_size: int = 0
    page_count: int = 1
    
    # Quality assessment
    is_scanned: bool = False
    ocr_quality: float = 0.0  # 0-100
    has_handwriting: bool = False
    has_signatures: bool = False
    has_stamps: bool = False
    language: str = "en"
    
    # Structure analysis
    sections: List[DocumentSection] = field(default_factory=list)
    has_header: bool = False
    has_footer: bool = False
    has_letterhead: bool = False
    is_form: bool = False
    is_multi_document: bool = False
    
    # Content overview
    total_characters: int = 0
    total_words: int = 0
    total_sentences: int = 0
    
    # Key structural elements found
    has_date_line: bool = False
    has_address_block: bool = False
    has_salutation: bool = False
    has_signature_block: bool = False
    has_notary_block: bool = False
    has_case_caption: bool = False
    
    # Document flow
    document_flow_type: str = ""  # letter, form, legal_filing, etc.
    reading_order: List[str] = field(default_factory=list)  # Section IDs in order
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": {
                "name": self.filename,
                "type": self.file_type,
                "size": self.file_size,
                "pages": self.page_count,
            },
            "quality": {
                "is_scanned": self.is_scanned,
                "ocr_quality": self.ocr_quality,
                "has_handwriting": self.has_handwriting,
                "language": self.language,
            },
            "structure": {
                "sections": len(self.sections),
                "has_letterhead": self.has_letterhead,
                "is_form": self.is_form,
                "document_flow": self.document_flow_type,
            },
            "content": {
                "characters": self.total_characters,
                "words": self.total_words,
                "sentences": self.total_sentences,
            },
            "elements": {
                "date_line": self.has_date_line,
                "address_block": self.has_address_block,
                "case_caption": self.has_case_caption,
                "signature_block": self.has_signature_block,
                "notary_block": self.has_notary_block,
            }
        }


@dataclass
class LegalIssue:
    """
    A legal issue detected in the document.
    """
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    
    # Issue details
    issue_type: str = ""
    title: str = ""
    description: str = ""
    severity: IssueSeverity = IssueSeverity.MEDIUM
    
    # Legal basis
    legal_basis: List[str] = field(default_factory=list)  # Statutes, case law
    mn_statute: Optional[str] = None  # Specific MN statute if applicable
    
    # Evidence in document
    supporting_text: str = ""
    text_location: Tuple[int, int] = (0, 0)  # Start, end positions
    page_number: int = 1
    
    # Analysis
    confidence: float = 0.0
    reasoning: str = ""
    
    # Action items
    recommended_actions: List[str] = field(default_factory=list)
    deadline: Optional[date] = None
    days_to_act: Optional[int] = None
    
    # Defense potential
    defense_available: bool = False
    defense_strategies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.issue_type,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "legal_basis": self.legal_basis,
            "mn_statute": self.mn_statute,
            "evidence": {
                "text": self.supporting_text[:200] + "..." if len(self.supporting_text) > 200 else self.supporting_text,
                "location": self.text_location,
                "page": self.page_number,
            },
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "actions": {
                "recommended": self.recommended_actions,
                "deadline": self.deadline.isoformat() if self.deadline else None,
                "days_to_act": self.days_to_act,
            },
            "defense": {
                "available": self.defense_available,
                "strategies": self.defense_strategies,
            }
        }


@dataclass
class TimelineEntry:
    """An event extracted for timeline"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    
    event_date: Optional[date] = None
    event_date_end: Optional[date] = None  # For ranges
    date_text: str = ""  # Original text
    is_approximate: bool = False
    
    event_type: str = ""
    title: str = ""
    description: str = ""
    
    # Importance
    is_deadline: bool = False
    is_court_date: bool = False
    is_milestone: bool = False
    
    # Source
    source_text: str = ""
    page_number: int = 1
    confidence: float = 0.0
    
    # Related entities
    related_party_ids: List[str] = field(default_factory=list)
    related_amount_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": self.event_date.isoformat() if self.event_date else None,
            "date_end": self.event_date_end.isoformat() if self.event_date_end else None,
            "date_text": self.date_text,
            "is_approximate": self.is_approximate,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "flags": {
                "is_deadline": self.is_deadline,
                "is_court_date": self.is_court_date,
                "is_milestone": self.is_milestone,
            },
            "confidence": self.confidence,
            "page": self.page_number,
        }


@dataclass 
class PartyRelationship:
    """Relationship between parties"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    
    party_a_id: str = ""
    party_a_role: PartyRole = PartyRole.UNKNOWN
    party_a_name: str = ""
    
    party_b_id: str = ""
    party_b_role: PartyRole = PartyRole.UNKNOWN
    party_b_name: str = ""
    
    relationship_type: str = ""  # landlord_tenant, attorney_client, etc.
    
    # Details
    property_address: Optional[str] = None
    unit_number: Optional[str] = None
    
    # Evidence
    supporting_text: str = ""
    confidence: float = 0.0


@dataclass
class AmountRelationship:
    """Financial amount with context"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    
    amount: float = 0.0
    currency: str = "USD"
    amount_text: str = ""  # Original text
    
    # Classification
    amount_type: str = ""  # rent, deposit, fee, damages, etc.
    period: Optional[str] = None  # monthly, one-time, etc.
    
    # Related entities
    owed_by_id: Optional[str] = None
    owed_to_id: Optional[str] = None
    
    # Dates
    due_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    
    # Analysis
    is_disputed: bool = False
    dispute_reason: Optional[str] = None
    may_be_illegal: bool = False
    illegality_reason: Optional[str] = None
    
    confidence: float = 0.0


@dataclass
class RelationshipMap:
    """
    Complete map of relationships in the document.
    """
    # Parties
    parties: List[ExtractedEntity] = field(default_factory=list)
    party_relationships: List[PartyRelationship] = field(default_factory=list)
    
    # Financial
    amounts: List[ExtractedEntity] = field(default_factory=list)
    amount_relationships: List[AmountRelationship] = field(default_factory=list)
    
    # Temporal
    dates: List[ExtractedEntity] = field(default_factory=list)
    timeline: List[TimelineEntry] = field(default_factory=list)
    
    # Property
    addresses: List[ExtractedEntity] = field(default_factory=list)
    primary_property: Optional[str] = None
    
    # Legal
    statutes_cited: List[ExtractedEntity] = field(default_factory=list)
    case_numbers: List[ExtractedEntity] = field(default_factory=list)
    
    def get_tenant(self) -> Optional[ExtractedEntity]:
        """Get primary tenant from parties"""
        for party in self.parties:
            if party.attributes.get("role") == PartyRole.TENANT.value:
                return party
        return None
    
    def get_landlord(self) -> Optional[ExtractedEntity]:
        """Get primary landlord from parties"""
        for party in self.parties:
            role = party.attributes.get("role")
            if role in [PartyRole.LANDLORD.value, PartyRole.PROPERTY_MANAGER.value]:
                return party
        return None
    
    def get_total_claimed(self) -> float:
        """Get total amount claimed"""
        total = 0.0
        for rel in self.amount_relationships:
            if rel.amount_type in ["rent_owed", "damages", "fees", "total_owed"]:
                total += rel.amount
        return total
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "parties": [p.to_dict() for p in self.parties],
            "party_relationships": [
                {
                    "from": pr.party_a_name,
                    "from_role": pr.party_a_role.value,
                    "to": pr.party_b_name,
                    "to_role": pr.party_b_role.value,
                    "relationship": pr.relationship_type,
                    "property": pr.property_address,
                }
                for pr in self.party_relationships
            ],
            "amounts": [a.to_dict() for a in self.amounts],
            "amount_details": [
                {
                    "amount": ar.amount,
                    "type": ar.amount_type,
                    "due_date": ar.due_date.isoformat() if ar.due_date else None,
                    "disputed": ar.is_disputed,
                    "may_be_illegal": ar.may_be_illegal,
                }
                for ar in self.amount_relationships
            ],
            "dates": [d.to_dict() for d in self.dates],
            "timeline": [t.to_dict() for t in self.timeline],
            "primary_property": self.primary_property,
            "statutes": [s.value for s in self.statutes_cited],
            "case_numbers": [c.value for c in self.case_numbers],
            "summary": {
                "tenant": self.get_tenant().value if self.get_tenant() else None,
                "landlord": self.get_landlord().value if self.get_landlord() else None,
                "total_claimed": self.get_total_claimed(),
            }
        }


@dataclass
class LegalAnalysis:
    """
    Complete legal analysis of the document.
    """
    # Document classification
    document_category: DocumentCategory = DocumentCategory.UNKNOWN
    document_type: DocumentType = DocumentType.UNKNOWN
    document_type_reasoning: str = ""
    
    # Issues found
    issues: List[LegalIssue] = field(default_factory=list)
    critical_issues: List[LegalIssue] = field(default_factory=list)
    
    # Minnesota law specific
    applicable_mn_statutes: List[str] = field(default_factory=list)
    statute_references: List[Dict[str, Any]] = field(default_factory=list)  # Enhanced statute info
    procedural_requirements: List[str] = field(default_factory=list)
    procedural_violations: List[str] = field(default_factory=list)
    
    # Notice analysis (if applicable)
    notice_type: Optional[str] = None
    notice_period_days: Optional[int] = None
    notice_period_compliant: Optional[bool] = None
    notice_served_date: Optional[date] = None
    notice_effective_date: Optional[date] = None
    
    # Court case analysis (if applicable)
    court_name: Optional[str] = None
    case_number: Optional[str] = None
    judge_name: Optional[str] = None
    next_court_date: Optional[date] = None
    
    # Recommended actions
    immediate_actions: List[str] = field(default_factory=list)
    upcoming_deadlines: List[TimelineEntry] = field(default_factory=list)
    defense_options: List[str] = field(default_factory=list)
    
    # Risk assessment
    urgency_level: str = "normal"  # critical, high, normal, low
    risk_score: float = 0.0  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "classification": {
                "category": self.document_category.value,
                "type": self.document_type.value,
                "reasoning": self.document_type_reasoning,
            },
            "issues": {
                "all": [i.to_dict() for i in self.issues],
                "critical": [i.to_dict() for i in self.critical_issues],
                "count": len(self.issues),
                "critical_count": len(self.critical_issues),
            },
            "minnesota_law": {
                "applicable_statutes": self.applicable_mn_statutes,
                "procedural_requirements": self.procedural_requirements,
                "procedural_violations": self.procedural_violations,
            },
            "notice_analysis": {
                "type": self.notice_type,
                "period_days": self.notice_period_days,
                "compliant": self.notice_period_compliant,
                "served": self.notice_served_date.isoformat() if self.notice_served_date else None,
                "effective": self.notice_effective_date.isoformat() if self.notice_effective_date else None,
            } if self.notice_type else None,
            "court_case": {
                "court": self.court_name,
                "case_number": self.case_number,
                "judge": self.judge_name,
                "next_date": self.next_court_date.isoformat() if self.next_court_date else None,
            } if self.case_number else None,
            "actions": {
                "immediate": self.immediate_actions,
                "deadlines": [d.to_dict() for d in self.upcoming_deadlines],
                "defense_options": self.defense_options,
            },
            "risk": {
                "urgency": self.urgency_level,
                "score": self.risk_score,
            }
        }


@dataclass
class RecognitionResult:
    """
    Complete result from the document recognition engine.
    This is the primary output of the analysis.
    """
    # Identification
    analysis_id: str = field(default_factory=lambda: str(uuid4()))
    analyzed_at: datetime = field(default_factory=datetime.now)
    engine_version: str = "1.0.0"
    
    # Raw content
    original_text: str = ""
    cleaned_text: str = ""
    
    # Context and structure
    context: DocumentContext = field(default_factory=DocumentContext)
    
    # Extracted data
    entities: List[ExtractedEntity] = field(default_factory=list)
    relationships: RelationshipMap = field(default_factory=RelationshipMap)
    
    # Legal analysis
    document_type: DocumentType = DocumentType.UNKNOWN
    document_category: DocumentCategory = DocumentCategory.UNKNOWN
    legal_analysis: LegalAnalysis = field(default_factory=LegalAnalysis)
    
    # Tone and direction analysis
    tone_analysis: Any = None  # ToneAnalysisResult (avoid circular import)
    
    # Confidence and reasoning
    confidence: ConfidenceMetrics = field(default_factory=ConfidenceMetrics)
    reasoning_chains: List[ReasoningChain] = field(default_factory=list)
    
    # Processing stats
    processing_time_ms: float = 0.0
    passes_completed: int = 0
    
    # Warnings and notes
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    def get_critical_issues(self) -> List[LegalIssue]:
        """Get all critical severity issues"""
        return [i for i in self.legal_analysis.issues 
                if i.severity == IssueSeverity.CRITICAL]
    
    def get_deadlines(self, within_days: int = 30) -> List[TimelineEntry]:
        """Get upcoming deadlines within specified days"""
        today = date.today()
        deadlines = []
        for entry in self.relationships.timeline:
            if entry.is_deadline and entry.event_date:
                days_until = (entry.event_date - today).days
                if 0 <= days_until <= within_days:
                    deadlines.append(entry)
        return sorted(deadlines, key=lambda x: x.event_date or date.max)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a concise summary of the analysis"""
        return {
            "document_type": self.document_type.value,
            "confidence": self.confidence.overall_score,
            "confidence_level": self.confidence.level.value,
            "critical_issues": len(self.get_critical_issues()),
            "total_issues": len(self.legal_analysis.issues),
            "upcoming_deadlines": len(self.get_deadlines(within_days=14)),
            "urgency": self.legal_analysis.urgency_level,
            "risk_score": self.legal_analysis.risk_score,
            "tenant": self.relationships.get_tenant().value if self.relationships.get_tenant() else None,
            "landlord": self.relationships.get_landlord().value if self.relationships.get_landlord() else None,
            "total_claimed": self.relationships.get_total_claimed(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to full dictionary representation"""
        return {
            "analysis_id": self.analysis_id,
            "analyzed_at": self.analyzed_at.isoformat(),
            "engine_version": self.engine_version,
            "summary": self.get_summary(),
            "context": self.context.to_dict(),
            "entities": [e.to_dict() for e in self.entities],
            "relationships": self.relationships.to_dict(),
            "document_type": self.document_type.value,
            "document_category": self.document_category.value,
            "legal_analysis": self.legal_analysis.to_dict(),
            "confidence": self.confidence.to_dict(),
            "reasoning": [r.to_dict() for r in self.reasoning_chains],
            "processing": {
                "time_ms": self.processing_time_ms,
                "passes": self.passes_completed,
            },
            "warnings": self.warnings,
            "notes": self.notes,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=2, default=str)
