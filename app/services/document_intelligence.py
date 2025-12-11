"""
Semptify 5.0 - World-Class Document Intelligence Service
=========================================================

The unified brain for document processing - integrating:
- Multi-layered recognition engine (5 analysis layers)
- Entity extraction with contextual understanding
- Legal reasoning with Minnesota tenant law
- Automatic timeline event generation
- Deadline detection and urgency scoring
- Law cross-referencing with explanations

This service orchestrates ALL document intelligence components
to provide comprehensive, actionable insights.

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│                    Document Intelligence                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   OCR/Text   │──▶│  Recognition │──▶│   Entity     │        │
│  │  Extraction  │  │    Engine    │  │  Extraction  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                 │                 │                  │
│         ▼                 ▼                 ▼                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    Legal     │  │   Timeline   │  │   Urgency    │         │
│  │  Reasoning   │  │  Generation  │  │   Scoring    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                            │                                   │
│                            ▼                                   │
│              ┌──────────────────────────┐                     │
│              │   Intelligence Result    │                     │
│              │  (Actionable Insights)   │                     │
│              └──────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from app.services.document_recognition import (
    DocumentCategory,
    DocumentType,
    RecognitionResult,
    ExtractedEntity,
    recognize_document,
)

logger = logging.getLogger(__name__)


# =============================================================================
# URGENCY LEVELS WITH CLEAR CRITERIA
# =============================================================================

class UrgencyLevel(str, Enum):
    """Document urgency classification with clear criteria."""
    CRITICAL = "critical"  # Must act within 24-48 hours
    HIGH = "high"          # Must act within 3-7 days
    MEDIUM = "medium"      # Should act within 7-14 days
    NORMAL = "normal"      # Standard document, no rush
    LOW = "low"            # Informational, no action required


# =============================================================================
# ACTION ITEMS - What the user should do
# =============================================================================

@dataclass
class ActionItem:
    """A specific action the user should take."""
    id: str
    priority: int  # 1 = highest
    title: str
    description: str
    deadline: Optional[datetime] = None
    deadline_type: str = "recommended"  # "legal", "recommended", "optional"
    legal_basis: Optional[str] = None
    completed: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "deadline_type": self.deadline_type,
            "legal_basis": self.legal_basis,
            "completed": self.completed,
        }


# =============================================================================
# LEGAL INSIGHT - Law cross-references with explanations
# =============================================================================

@dataclass
class LegalInsight:
    """A legal insight related to the document."""
    statute: str  # e.g., "Minn. Stat. § 504B.291"
    title: str
    relevance: str  # Why this applies
    protection_level: str  # "strong", "moderate", "weak", "none"
    key_points: list[str] = field(default_factory=list)
    tenant_rights: list[str] = field(default_factory=list)
    landlord_obligations: list[str] = field(default_factory=list)
    deadlines_imposed: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "statute": self.statute,
            "title": self.title,
            "relevance": self.relevance,
            "protection_level": self.protection_level,
            "key_points": self.key_points,
            "tenant_rights": self.tenant_rights,
            "landlord_obligations": self.landlord_obligations,
            "deadlines_imposed": self.deadlines_imposed,
        }


# =============================================================================
# TIMELINE EVENT - Auto-generated from document
# =============================================================================

@dataclass
class TimelineEvent:
    """A timeline event extracted from the document."""
    id: str
    event_type: str  # "deadline", "hearing", "notice", "payment", "filing"
    title: str
    description: str
    date: datetime
    source: str  # What text this came from
    is_critical: bool = False
    days_until: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "date": self.date.isoformat(),
            "source": self.source,
            "is_critical": self.is_critical,
            "days_until": self.days_until,
        }


# =============================================================================
# INTELLIGENCE RESULT - The complete analysis
# =============================================================================

@dataclass
class IntelligenceResult:
    """Complete document intelligence result."""
    # Core identification
    document_id: str
    filename: str
    
    # Classification with confidence
    category: DocumentCategory
    document_type: DocumentType
    confidence: float
    
    # Human-readable understanding
    title: str
    summary: str
    plain_english_explanation: str
    
    # Urgency assessment
    urgency: UrgencyLevel
    urgency_reason: str
    
    # Extracted intelligence
    key_dates: list[dict] = field(default_factory=list)
    key_parties: list[dict] = field(default_factory=list)
    key_amounts: list[dict] = field(default_factory=list)
    key_terms: list[str] = field(default_factory=list)
    case_numbers: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    
    # Actionable insights
    action_items: list[ActionItem] = field(default_factory=list)
    legal_insights: list[LegalInsight] = field(default_factory=list)
    timeline_events: list[TimelineEvent] = field(default_factory=list)
    
    # Reasoning chain (for transparency)
    reasoning_chain: list[str] = field(default_factory=list)
    
    # Metadata
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    analysis_version: str = "5.0"
    
    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "classification": {
                "category": self.category.value,
                "document_type": self.document_type.value,
                "confidence": self.confidence,
            },
            "understanding": {
                "title": self.title,
                "summary": self.summary,
                "plain_english": self.plain_english_explanation,
            },
            "urgency": {
                "level": self.urgency.value,
                "reason": self.urgency_reason,
            },
            "extracted_data": {
                "dates": self.key_dates,
                "parties": self.key_parties,
                "amounts": self.key_amounts,
                "terms": self.key_terms,
                "case_numbers": self.case_numbers,
                "addresses": self.addresses,
            },
            "insights": {
                "action_items": [a.to_dict() for a in self.action_items],
                "legal_insights": [l.to_dict() for l in self.legal_insights],
                "timeline_events": [t.to_dict() for t in self.timeline_events],
            },
            "reasoning": self.reasoning_chain,
            "metadata": {
                "analyzed_at": self.analyzed_at.isoformat(),
                "version": self.analysis_version,
            }
        }


# =============================================================================
# MINNESOTA TENANT LAW KNOWLEDGE BASE
# =============================================================================

MN_TENANT_LAWS = {
    "504B.135": {
        "title": "Security Deposit Requirements",
        "summary": "Landlord must return security deposit within 21 days after tenant moves out",
        "tenant_rights": [
            "Receive itemized statement of deductions",
            "Get full deposit back if no legitimate deductions",
            "Sue for bad faith retention (up to $500 penalty)",
        ],
        "landlord_obligations": [
            "Return deposit within 21 days",
            "Provide written itemization of any deductions",
            "Keep deposits in separate account",
        ],
        "deadlines": ["21 days to return deposit after move-out"],
        "applies_to": [DocumentType.DEPOSIT_STATEMENT, DocumentType.LEASE, DocumentType.INSPECTION],
    },
    "504B.178": {
        "title": "Landlord's Right of Entry",
        "summary": "Landlord must give reasonable notice before entering (24 hours typical)",
        "tenant_rights": [
            "Receive reasonable advance notice",
            "Refuse entry without proper notice (except emergencies)",
            "Privacy in your home",
        ],
        "landlord_obligations": [
            "Give reasonable notice (24 hours is standard)",
            "Enter only for legitimate purposes",
            "Enter only at reasonable times",
        ],
        "deadlines": ["24 hours advance notice for non-emergency entry"],
        "applies_to": [DocumentType.ENTRY_NOTICE],
    },
    "504B.285": {
        "title": "Eviction Notice Requirements",
        "summary": "Landlord must follow specific notice procedures before eviction",
        "tenant_rights": [
            "Receive proper written notice",
            "Time to cure violations (if applicable)",
            "Challenge improper evictions",
        ],
        "landlord_obligations": [
            "Give 14-day notice for non-payment (month-to-month)",
            "Give 30-day notice for other terminations (month-to-month)",
            "Follow proper service procedures",
        ],
        "deadlines": ["14 days (non-payment)", "30 days (other terminations)"],
        "applies_to": [DocumentType.EVICTION_NOTICE, DocumentType.NOTICE_TO_QUIT],
    },
    "504B.291": {
        "title": "Eviction Actions (Unlawful Detainer)",
        "summary": "Court process for eviction - tenant has right to respond",
        "tenant_rights": [
            "Respond to summons/complaint",
            "Appear at hearing",
            "Present defenses",
            "Request continuance in hardship",
        ],
        "landlord_obligations": [
            "Properly serve tenant",
            "File with correct court",
            "Prove case at hearing",
        ],
        "deadlines": ["7-14 days to respond to summons"],
        "applies_to": [DocumentType.SUMMONS, DocumentType.COMPLAINT, DocumentType.EVICTION_FILING],
    },
    "504B.321": {
        "title": "Writ of Restitution",
        "summary": "Court order allowing sheriff to physically remove tenant",
        "tenant_rights": [
            "24 hours notice before sheriff execution",
            "Remove personal property",
            "Request stay in some cases",
        ],
        "landlord_obligations": [
            "Follow legal eviction process",
            "Cannot self-help evict",
            "Must use sheriff for removal",
        ],
        "deadlines": ["24 hours notice before execution"],
        "applies_to": [DocumentType.WRIT, DocumentType.COURT_ORDER, DocumentType.JUDGMENT],
    },
    "504B.161": {
        "title": "Landlord Duty to Maintain",
        "summary": "Landlord must maintain habitable conditions",
        "tenant_rights": [
            "Safe and habitable living conditions",
            "Working utilities and systems",
            "Repairs within reasonable time",
            "Rent escrow if repairs not made",
        ],
        "landlord_obligations": [
            "Make repairs within 14 days of notice",
            "Maintain building code compliance",
            "Provide working utilities",
        ],
        "deadlines": ["14 days to make repairs after written notice"],
        "applies_to": [DocumentType.REPAIR_REQUEST, DocumentType.INSPECTION],
    },
}


# =============================================================================
# DOCUMENT INTELLIGENCE SERVICE
# =============================================================================

class DocumentIntelligenceService:
    """
    World-class document intelligence service.
    
    Orchestrates all document analysis components to provide
    comprehensive, actionable insights for tenants.
    """
    
    def __init__(self):
        self.analysis_count = 0
        self.law_database = MN_TENANT_LAWS
        
    async def analyze(
        self,
        text: str,
        filename: str = "",
        document_id: Optional[str] = None,
    ) -> IntelligenceResult:
        """
        Perform complete document intelligence analysis.
        
        This is the main entry point - it orchestrates:
        1. Document recognition with 5-layer analysis
        2. Entity extraction with contextual understanding
        3. Legal reasoning with MN tenant law
        4. Timeline event generation
        5. Action item creation
        6. Urgency assessment
        
        Args:
            text: The document text
            filename: Original filename (helps with classification)
            document_id: Optional ID (generates one if not provided)
            
        Returns:
            IntelligenceResult with comprehensive analysis
        """
        self.analysis_count += 1
        doc_id = document_id or str(uuid4())
        
        # Step 1: Run recognition engine
        recognition = recognize_document(text, filename)
        
        # Step 2: Enhanced entity extraction with better labels
        key_dates = self._enhance_dates(recognition)
        key_parties = self._enhance_parties(recognition)
        key_amounts = self._enhance_amounts(recognition)
        case_numbers = [e.value for e in recognition.case_numbers]
        addresses = [e.value for e in recognition.addresses]
        
        # Step 3: Generate timeline events from dates
        timeline_events = self._generate_timeline_events(recognition)
        
        # Step 4: Get applicable laws
        legal_insights = self._get_legal_insights(recognition)
        
        # Step 5: Generate action items
        action_items = self._generate_action_items(recognition, legal_insights)
        
        # Step 6: Assess urgency
        urgency, urgency_reason = self._assess_urgency(recognition, action_items)
        
        # Step 7: Generate plain English explanation
        plain_english = self._generate_explanation(recognition, urgency, action_items)
        
        return IntelligenceResult(
            document_id=doc_id,
            filename=filename,
            category=recognition.category,
            document_type=recognition.doc_type,
            confidence=recognition.confidence,
            title=recognition.title,
            summary=recognition.summary,
            plain_english_explanation=plain_english,
            urgency=urgency,
            urgency_reason=urgency_reason,
            key_dates=key_dates,
            key_parties=key_parties,
            key_amounts=key_amounts,
            key_terms=recognition.key_terms,
            case_numbers=case_numbers,
            addresses=addresses,
            action_items=action_items,
            legal_insights=legal_insights,
            timeline_events=timeline_events,
            reasoning_chain=recognition.reasoning_chain,
        )
    
    def _enhance_dates(self, recognition: RecognitionResult) -> list[dict]:
        """Enhance extracted dates with better labels and days-until."""
        now = datetime.now(timezone.utc)
        enhanced = []
        
        for entity in recognition.dates:
            try:
                # Parse the date
                date_str = entity.normalized or entity.value
                if 'T' in date_str:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                
                days_until = (date_obj.date() - now.date()).days
                
                enhanced.append({
                    "date": date_str,
                    "description": entity.context_label or "Date mentioned",
                    "days_until": days_until,
                    "is_past": days_until < 0,
                    "is_urgent": 0 <= days_until <= 7,
                    "confidence": entity.confidence,
                })
            except (ValueError, TypeError):
                enhanced.append({
                    "date": entity.value,
                    "description": entity.context_label or "Date mentioned",
                    "confidence": entity.confidence,
                })
        
        return enhanced
    
    def _enhance_parties(self, recognition: RecognitionResult) -> list[dict]:
        """Enhance extracted parties with role descriptions."""
        enhanced = []
        
        role_descriptions = {
            "plaintiff": "The party who filed the lawsuit",
            "defendant": "The party being sued",
            "landlord": "Property owner/manager",
            "tenant": "Current or former renter",
            "petitioner": "Party requesting court action",
            "respondent": "Party responding to petition",
            "attorney": "Legal representative",
            "judge": "Court official presiding",
            "clerk": "Court administrative staff",
        }
        
        for entity in recognition.parties:
            role = entity.context_label.lower()
            enhanced.append({
                "name": entity.value,
                "role": entity.context_label,
                "role_description": role_descriptions.get(role, "Party involved in matter"),
                "confidence": entity.confidence,
            })
        
        return enhanced
    
    def _enhance_amounts(self, recognition: RecognitionResult) -> list[dict]:
        """Enhance extracted amounts with context."""
        enhanced = []
        
        for entity in recognition.amounts:
            enhanced.append({
                "amount": entity.value,
                "description": entity.context_label or "Amount",
                "confidence": entity.confidence,
            })
        
        return enhanced
    
    def _generate_timeline_events(self, recognition: RecognitionResult) -> list[TimelineEvent]:
        """Generate timeline events from extracted dates."""
        events = []
        now = datetime.now(timezone.utc)
        
        for entity in recognition.dates:
            try:
                # Parse date
                date_str = entity.normalized or entity.value
                if 'T' in date_str:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                
                days_until = (date_obj.date() - now.date()).days
                
                # Determine event type from label
                label_lower = entity.context_label.lower()
                if any(w in label_lower for w in ["deadline", "respond", "due", "must"]):
                    event_type = "deadline"
                elif any(w in label_lower for w in ["hearing", "court", "appear"]):
                    event_type = "hearing"
                elif any(w in label_lower for w in ["notice", "served"]):
                    event_type = "notice"
                elif any(w in label_lower for w in ["payment", "rent", "paid"]):
                    event_type = "payment"
                elif any(w in label_lower for w in ["file", "filed", "filing"]):
                    event_type = "filing"
                else:
                    event_type = "date"
                
                is_critical = event_type in ["deadline", "hearing"] and 0 <= days_until <= 7
                
                events.append(TimelineEvent(
                    id=str(uuid4()),
                    event_type=event_type,
                    title=entity.context_label or "Date",
                    description=f"From document: {entity.source_text[:100]}..." if len(entity.source_text) > 100 else f"From document: {entity.source_text}",
                    date=date_obj,
                    source=entity.source_text,
                    is_critical=is_critical,
                    days_until=days_until,
                ))
            except (ValueError, TypeError):
                continue
        
        # Sort by date
        events.sort(key=lambda e: e.date)
        return events
    
    def _get_legal_insights(self, recognition: RecognitionResult) -> list[LegalInsight]:
        """Get applicable Minnesota tenant laws."""
        insights = []
        
        for statute, law_info in self.law_database.items():
            # Check if this law applies to this document type
            if recognition.doc_type in law_info.get("applies_to", []):
                insights.append(LegalInsight(
                    statute=f"Minn. Stat. § {statute}",
                    title=law_info["title"],
                    relevance=f"This law applies to {recognition.doc_type.value} documents",
                    protection_level="strong" if recognition.category == DocumentCategory.COURT else "moderate",
                    key_points=[law_info["summary"]],
                    tenant_rights=law_info.get("tenant_rights", []),
                    landlord_obligations=law_info.get("landlord_obligations", []),
                    deadlines_imposed=law_info.get("deadlines", []),
                ))
        
        # Add general insights based on document category
        if recognition.category == DocumentCategory.COURT and not insights:
            insights.append(LegalInsight(
                statute="Minn. Stat. § 504B.291",
                title="Eviction Actions - General",
                relevance="Court documents require timely response",
                protection_level="strong",
                key_points=["You have a right to respond to any court filing"],
                tenant_rights=[
                    "Right to appear and be heard",
                    "Right to present defenses",
                    "Right to legal representation",
                ],
                landlord_obligations=["Must follow proper court procedures"],
                deadlines_imposed=["Typically 7-14 days to respond"],
            ))
        
        return insights
    
    def _generate_action_items(
        self,
        recognition: RecognitionResult,
        legal_insights: list[LegalInsight]
    ) -> list[ActionItem]:
        """Generate specific action items based on document type."""
        actions = []
        now = datetime.now(timezone.utc)
        priority = 1
        
        # Critical court documents
        if recognition.category == DocumentCategory.COURT:
            if recognition.doc_type == DocumentType.SUMMONS:
                actions.append(ActionItem(
                    id=str(uuid4()),
                    priority=priority,
                    title="Respond to Summons",
                    description="You must file a written Answer with the court within the time specified (usually 7-14 days).",
                    deadline=now + timedelta(days=7),
                    deadline_type="legal",
                    legal_basis="Failure to respond may result in default judgment against you.",
                ))
                priority += 1
                
            if recognition.doc_type == DocumentType.WRIT:
                actions.append(ActionItem(
                    id=str(uuid4()),
                    priority=1,  # Always highest for writ
                    title="CRITICAL: Writ of Restitution",
                    description="The sheriff may remove you from the property. Gather belongings immediately and contact legal aid.",
                    deadline=now + timedelta(days=1),
                    deadline_type="legal",
                    legal_basis="Minn. Stat. § 504B.321",
                ))
                
            if recognition.doc_type in [DocumentType.COMPLAINT, DocumentType.EVICTION_FILING]:
                actions.append(ActionItem(
                    id=str(uuid4()),
                    priority=priority,
                    title="Review Complaint Allegations",
                    description="Read each allegation carefully. You will need to admit, deny, or state you lack information for each one.",
                    deadline=now + timedelta(days=3),
                    deadline_type="recommended",
                ))
                priority += 1
        
        # Notices from landlord
        if recognition.category == DocumentCategory.LANDLORD:
            if recognition.doc_type == DocumentType.EVICTION_NOTICE:
                actions.append(ActionItem(
                    id=str(uuid4()),
                    priority=priority,
                    title="Review Eviction Notice",
                    description="Check if the notice is proper: correct days, proper service, valid reason.",
                    deadline=now + timedelta(days=3),
                    deadline_type="recommended",
                    legal_basis="Minn. Stat. § 504B.285",
                ))
                priority += 1
                
            if recognition.doc_type == DocumentType.RENT_INCREASE:
                actions.append(ActionItem(
                    id=str(uuid4()),
                    priority=priority,
                    title="Review Rent Increase",
                    description="Verify proper notice period given. Month-to-month requires 30 days. Fixed-term requires notice before renewal.",
                    deadline=now + timedelta(days=7),
                    deadline_type="recommended",
                ))
                priority += 1
        
        # Add legal consultation recommendation for serious documents
        if recognition.category == DocumentCategory.COURT or recognition.urgency_level in ["critical", "high"]:
            actions.append(ActionItem(
                id=str(uuid4()),
                priority=priority,
                title="Seek Legal Help",
                description="Contact Legal Aid, Volunteer Lawyers Network, or a tenant rights organization for assistance.",
                deadline=now + timedelta(days=2),
                deadline_type="recommended",
            ))
        
        return actions
    
    def _assess_urgency(
        self,
        recognition: RecognitionResult,
        action_items: list[ActionItem]
    ) -> tuple[UrgencyLevel, str]:
        """Assess document urgency."""
        # Writs are always critical
        if recognition.doc_type == DocumentType.WRIT:
            return UrgencyLevel.CRITICAL, "Writ of Restitution - Sheriff may execute within 24 hours"
        
        # Court summons are critical
        if recognition.doc_type == DocumentType.SUMMONS:
            return UrgencyLevel.CRITICAL, "Court Summons - Must respond within legal deadline"
        
        # Check for imminent deadlines
        if recognition.has_deadline and recognition.days_to_respond is not None:
            if recognition.days_to_respond < 0:
                return UrgencyLevel.CRITICAL, f"Deadline has PASSED by {abs(recognition.days_to_respond)} days!"
            elif recognition.days_to_respond <= 3:
                return UrgencyLevel.CRITICAL, f"Only {recognition.days_to_respond} days to respond"
            elif recognition.days_to_respond <= 7:
                return UrgencyLevel.HIGH, f"{recognition.days_to_respond} days until deadline"
            elif recognition.days_to_respond <= 14:
                return UrgencyLevel.MEDIUM, f"{recognition.days_to_respond} days until deadline"
        
        # Court documents are generally high urgency
        if recognition.category == DocumentCategory.COURT:
            return UrgencyLevel.HIGH, "Court document - requires timely response"
        
        # Eviction notices
        if recognition.doc_type in [DocumentType.EVICTION_NOTICE, DocumentType.NOTICE_TO_QUIT]:
            return UrgencyLevel.HIGH, "Eviction notice - time-sensitive"
        
        # Financial documents
        if recognition.category == DocumentCategory.FINANCIAL:
            return UrgencyLevel.MEDIUM, "Financial document - review for accuracy"
        
        return UrgencyLevel.NORMAL, "Standard document"
    
    def _generate_explanation(
        self,
        recognition: RecognitionResult,
        urgency: UrgencyLevel,
        action_items: list[ActionItem]
    ) -> str:
        """Generate a plain English explanation of what this document means."""
        explanations = {
            DocumentType.SUMMONS: (
                "This is a Court Summons - a formal legal document telling you that someone "
                "(usually your landlord) is suing you. This is SERIOUS. You MUST respond by "
                "the deadline shown, or the court may rule against you automatically (default judgment)."
            ),
            DocumentType.COMPLAINT: (
                "This is a legal Complaint - it lists the specific claims being made against you. "
                "Each numbered paragraph needs to be answered (admit, deny, or 'lack information'). "
                "Read it carefully to understand exactly what you're being accused of."
            ),
            DocumentType.WRIT: (
                "⚠️ CRITICAL: This is a Writ of Restitution - this means the court has already "
                "ruled that you must leave, and the sheriff can physically remove you. "
                "You typically have only 24 hours notice. Contact Legal Aid IMMEDIATELY."
            ),
            DocumentType.EVICTION_NOTICE: (
                "This is an eviction notice from your landlord. It's the START of the eviction "
                "process, not the end. You still have rights and time to respond. Check if the "
                "notice is proper (correct number of days, properly served, valid reason)."
            ),
            DocumentType.LEASE: (
                "This is your Lease Agreement - the contract between you and your landlord. "
                "It defines your rights and responsibilities as a tenant. Review it carefully, "
                "especially sections about rent, deposits, and lease violations."
            ),
            DocumentType.RECEIPT: (
                "This is a payment receipt - proof that you made a payment. KEEP THIS! "
                "Payment records are crucial evidence if there's ever a dispute about rent."
            ),
            DocumentType.DEPOSIT_STATEMENT: (
                "This is a security deposit statement. In Minnesota, landlords must return your "
                "deposit within 21 days of move-out and provide itemized deductions. "
                "Review each deduction carefully - you can challenge unfair charges."
            ),
        }
        
        base = explanations.get(
            recognition.doc_type,
            f"This appears to be a {recognition.doc_type.value.replace('_', ' ')} document."
        )
        
        # Add urgency context
        if urgency == UrgencyLevel.CRITICAL:
            base = f"⚠️ URGENT ACTION REQUIRED ⚠️\n\n{base}"
        elif urgency == UrgencyLevel.HIGH:
            base = f"⏰ TIME-SENSITIVE\n\n{base}"
        
        # Add action summary
        if action_items:
            top_action = min(action_items, key=lambda a: a.priority)
            base += f"\n\n👉 Most Important Action: {top_action.title}"
        
        return base


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

_service: Optional[DocumentIntelligenceService] = None


def get_document_intelligence() -> DocumentIntelligenceService:
    """Get the document intelligence service singleton."""
    global _service
    if _service is None:
        _service = DocumentIntelligenceService()
    return _service


async def analyze_document(
    text: str,
    filename: str = "",
    document_id: Optional[str] = None,
) -> IntelligenceResult:
    """
    Convenience function for document analysis.
    
    Args:
        text: Document text
        filename: Original filename
        document_id: Optional ID
        
    Returns:
        IntelligenceResult with full analysis
    """
    service = get_document_intelligence()
    return await service.analyze(text, filename, document_id)
