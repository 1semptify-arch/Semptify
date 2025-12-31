"""
Document Hub - Central Access Point for All Semptify Modules

This module provides a unified interface for ALL Semptify modules to access
processed document data. It integrates with the DocumentDistributor and provides
helper functions for common use cases.

USAGE:
    from app.core.document_hub import get_document_hub, DocumentHub
    
    hub = get_document_hub()
    
    # Get all data for a user
    case_data = await hub.get_case_data(user_id)
    
    # Get specific data types
    dates = hub.get_key_dates(user_id)
    parties = hub.get_parties(user_id)
    amounts = hub.get_amounts(user_id)
    
    # Auto-fill forms
    form_data = hub.get_form_autofill(user_id, "HOU301")
    
    # Get timeline events for display
    timeline = hub.get_timeline_events(user_id)
    
    # Get urgent action items
    actions = hub.get_action_items(user_id, urgent_only=True)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class DataCategory(str, Enum):
    """Categories of document data"""
    DATES = "dates"
    PARTIES = "parties"
    AMOUNTS = "amounts"
    CASE_NUMBERS = "case_numbers"
    TIMELINE = "timeline"
    ACTION_ITEMS = "action_items"
    LAW_REFERENCES = "law_references"
    DOCUMENTS = "documents"


@dataclass
class CaseData:
    """Aggregated case data from all documents"""
    user_id: str
    
    # Case identification
    case_numbers: List[str] = field(default_factory=list)
    primary_case_number: Optional[str] = None
    
    # Parties
    tenant_name: Optional[str] = None
    tenant_address: Optional[str] = None
    landlord_name: Optional[str] = None
    landlord_address: Optional[str] = None
    all_parties: List[Dict[str, Any]] = field(default_factory=list)
    
    # Key dates
    hearing_date: Optional[str] = None
    hearing_time: Optional[str] = None
    notice_date: Optional[str] = None
    answer_deadline: Optional[str] = None
    lease_start: Optional[str] = None
    lease_end: Optional[str] = None
    all_dates: List[Dict[str, Any]] = field(default_factory=list)
    
    # Amounts
    rent_amount: Optional[float] = None
    rent_claimed: Optional[float] = None
    deposit_amount: Optional[float] = None
    late_fees: Optional[float] = None
    damages_claimed: Optional[float] = None
    total_claimed: Optional[float] = None
    all_amounts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Property
    property_address: Optional[str] = None
    unit_number: Optional[str] = None
    
    # Legal references
    law_references: List[Dict[str, Any]] = field(default_factory=list)
    matched_statutes: List[str] = field(default_factory=list)
    
    # Timeline & Actions
    timeline_events: List[Dict[str, Any]] = field(default_factory=list)
    action_items: List[Dict[str, Any]] = field(default_factory=list)
    urgent_actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Documents summary
    document_count: int = 0
    documents_by_type: Dict[str, int] = field(default_factory=dict)
    urgency_level: Optional[str] = None
    
    # Metadata
    last_updated: Optional[datetime] = None
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "case_numbers": self.case_numbers,
            "primary_case_number": self.primary_case_number,
            "tenant": {
                "name": self.tenant_name,
                "address": self.tenant_address,
            },
            "landlord": {
                "name": self.landlord_name,
                "address": self.landlord_address,
            },
            "all_parties": self.all_parties,
            "key_dates": {
                "hearing_date": self.hearing_date,
                "hearing_time": self.hearing_time,
                "notice_date": self.notice_date,
                "answer_deadline": self.answer_deadline,
                "lease_start": self.lease_start,
                "lease_end": self.lease_end,
            },
            "all_dates": self.all_dates,
            "amounts": {
                "rent": self.rent_amount,
                "rent_claimed": self.rent_claimed,
                "deposit": self.deposit_amount,
                "late_fees": self.late_fees,
                "damages_claimed": self.damages_claimed,
                "total_claimed": self.total_claimed,
            },
            "all_amounts": self.all_amounts,
            "property": {
                "address": self.property_address,
                "unit": self.unit_number,
            },
            "law_references": self.law_references,
            "matched_statutes": self.matched_statutes,
            "timeline_events": self.timeline_events,
            "action_items": self.action_items,
            "urgent_actions": self.urgent_actions,
            "document_count": self.document_count,
            "documents_by_type": self.documents_by_type,
            "urgency_level": self.urgency_level,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "confidence_score": self.confidence_score,
        }


class DocumentHub:
    """
    Central hub for accessing document data across all Semptify modules.
    
    This provides a consistent interface that any module can use to get
    processed document data without needing to know about the underlying
    document pipeline, registry, or distributor services.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._cache: Dict[str, CaseData] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._initialized = True
        logger.info("DocumentHub initialized")
    
    def _get_distributor(self):
        """Lazy load the document distributor"""
        try:
            from app.services.document_distributor import get_document_distributor
            return get_document_distributor()
        except ImportError:
            logger.warning("DocumentDistributor not available")
            return None
    
    def _get_pipeline(self):
        """Lazy load the document pipeline"""
        try:
            from app.services.document_pipeline import get_document_pipeline
            return get_document_pipeline()
        except ImportError:
            return None
    
    def _get_registry(self):
        """Lazy load the document registry"""
        try:
            from app.services.document_registry import get_document_registry
            return get_document_registry()
        except ImportError:
            return None
    
    def get_case_data(self, user_id: str, force_refresh: bool = False) -> CaseData:
        """
        Get aggregated case data for a user from all their documents.
        
        This is the main entry point for modules that need document data.
        Returns a CaseData object with all extracted information.
        """
        # Check cache
        if not force_refresh and user_id in self._cache:
            cached = self._cache[user_id]
            if cached.last_updated and datetime.now(timezone.utc) - cached.last_updated < self._cache_ttl:
                return cached
        
        # Build case data from distributor
        case_data = CaseData(user_id=user_id)
        
        distributor = self._get_distributor()
        if distributor:
            try:
                docs = distributor.get_user_documents(user_id)
                extracted = distributor.get_extracted_case_info(user_id)
                
                # Aggregate data
                case_data.document_count = len(docs)
                case_data.all_dates = extracted.get("dates", [])
                case_data.all_parties = extracted.get("parties", [])
                case_data.all_amounts = extracted.get("amounts", [])
                case_data.case_numbers = extracted.get("case_numbers", [])
                case_data.action_items = extracted.get("action_items", [])
                case_data.timeline_events = extracted.get("timeline_events", [])
                
                # Extract primary case number
                if case_data.case_numbers:
                    case_data.primary_case_number = case_data.case_numbers[0]
                
                # Extract structured data from parties
                for party in case_data.all_parties:
                    party_type = party.get("type", "").lower()
                    if "tenant" in party_type or "defendant" in party_type:
                        if not case_data.tenant_name:
                            case_data.tenant_name = party.get("name")
                            case_data.tenant_address = party.get("address")
                    elif "landlord" in party_type or "plaintiff" in party_type:
                        if not case_data.landlord_name:
                            case_data.landlord_name = party.get("name")
                            case_data.landlord_address = party.get("address")
                
                # Extract key dates
                for date_info in case_data.all_dates:
                    date_type = date_info.get("type", "").lower()
                    date_value = date_info.get("date") or date_info.get("value")
                    
                    if "hearing" in date_type:
                        case_data.hearing_date = date_value
                        case_data.hearing_time = date_info.get("time")
                    elif "notice" in date_type:
                        case_data.notice_date = date_value
                    elif "answer" in date_type or "deadline" in date_type:
                        case_data.answer_deadline = date_value
                    elif "lease" in date_type:
                        if "start" in date_type or "begin" in date_type:
                            case_data.lease_start = date_value
                        elif "end" in date_type:
                            case_data.lease_end = date_value
                
                # Extract amounts
                for amount_info in case_data.all_amounts:
                    amount_type = amount_info.get("type", "").lower()
                    value = amount_info.get("amount") or amount_info.get("value")
                    
                    if value:
                        try:
                            value = float(str(value).replace("$", "").replace(",", ""))
                        except (ValueError, TypeError):
                            continue
                    
                        if "rent" in amount_type and "claim" in amount_type:
                            case_data.rent_claimed = value
                        elif "rent" in amount_type:
                            case_data.rent_amount = value
                        elif "deposit" in amount_type:
                            case_data.deposit_amount = value
                        elif "late" in amount_type or "fee" in amount_type:
                            case_data.late_fees = value
                        elif "damage" in amount_type:
                            case_data.damages_claimed = value
                        elif "total" in amount_type:
                            case_data.total_claimed = value
                
                # Get law references from documents
                for doc in docs:
                    law_refs = doc.law_references if hasattr(doc, 'law_references') else []
                    if law_refs:
                        case_data.law_references.extend(law_refs)
                    
                    statutes = doc.matched_statutes if hasattr(doc, 'matched_statutes') else []
                    case_data.matched_statutes.extend(statutes)
                    
                    # Track document types
                    doc_type = doc.doc_type if hasattr(doc, 'doc_type') else "unknown"
                    case_data.documents_by_type[doc_type] = case_data.documents_by_type.get(doc_type, 0) + 1
                
                # Get urgent documents
                urgent_docs = distributor.get_urgent_documents(user_id)
                if urgent_docs:
                    case_data.urgency_level = urgent_docs[0].urgency_level if hasattr(urgent_docs[0], 'urgency_level') else "high"
                
                # Filter urgent action items
                case_data.urgent_actions = [
                    a for a in case_data.action_items
                    if a.get("priority", 0) <= 2 or a.get("urgent")
                ]
                
                # Deduplicate
                case_data.matched_statutes = list(set(case_data.matched_statutes))
                
            except Exception as e:
                logger.warning(f"Error building case data from distributor: {e}")
        
        # Also try to get data from pipeline if available
        pipeline = self._get_pipeline()
        if pipeline:
            try:
                pipeline_docs = pipeline.get_user_documents(user_id)
                if pipeline_docs and not case_data.document_count:
                    case_data.document_count = len(pipeline_docs)
            except Exception as e:
                logger.debug(f"Pipeline data not available: {e}")
        
        case_data.last_updated = datetime.now(timezone.utc)
        self._cache[user_id] = case_data
        
        return case_data
    
    # =========================================================================
    # Convenience methods for specific data types
    # =========================================================================
    
    def get_key_dates(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all extracted dates for a user"""
        case_data = self.get_case_data(user_id)
        return case_data.all_dates
    
    def get_parties(self, user_id: str) -> Dict[str, Any]:
        """Get party information (tenant, landlord)"""
        case_data = self.get_case_data(user_id)
        return {
            "tenant": {
                "name": case_data.tenant_name,
                "address": case_data.tenant_address,
            },
            "landlord": {
                "name": case_data.landlord_name,
                "address": case_data.landlord_address,
            },
            "all_parties": case_data.all_parties,
        }
    
    def get_amounts(self, user_id: str) -> Dict[str, Any]:
        """Get all extracted monetary amounts"""
        case_data = self.get_case_data(user_id)
        return {
            "rent": case_data.rent_amount,
            "rent_claimed": case_data.rent_claimed,
            "deposit": case_data.deposit_amount,
            "late_fees": case_data.late_fees,
            "damages_claimed": case_data.damages_claimed,
            "total_claimed": case_data.total_claimed,
            "all_amounts": case_data.all_amounts,
        }
    
    def get_case_numbers(self, user_id: str) -> List[str]:
        """Get all case numbers found in documents"""
        case_data = self.get_case_data(user_id)
        return case_data.case_numbers
    
    def get_primary_case_number(self, user_id: str) -> Optional[str]:
        """Get the primary (first found) case number"""
        case_data = self.get_case_data(user_id)
        return case_data.primary_case_number
    
    def get_timeline_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all timeline events extracted from documents"""
        case_data = self.get_case_data(user_id)
        return sorted(case_data.timeline_events, key=lambda x: x.get("date", ""))
    
    def get_action_items(self, user_id: str, urgent_only: bool = False) -> List[Dict[str, Any]]:
        """Get action items from documents"""
        case_data = self.get_case_data(user_id)
        if urgent_only:
            return case_data.urgent_actions
        return case_data.action_items
    
    def get_law_references(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all law references matched to documents"""
        case_data = self.get_case_data(user_id)
        return case_data.law_references
    
    def get_matched_statutes(self, user_id: str) -> List[str]:
        """Get list of matched statute codes"""
        case_data = self.get_case_data(user_id)
        return case_data.matched_statutes
    
    def get_urgency_level(self, user_id: str) -> Optional[str]:
        """Get overall urgency level based on documents"""
        case_data = self.get_case_data(user_id)
        return case_data.urgency_level
    
    def get_hearing_info(self, user_id: str) -> Dict[str, Any]:
        """Get hearing date/time information"""
        case_data = self.get_case_data(user_id)
        return {
            "date": case_data.hearing_date,
            "time": case_data.hearing_time,
            "has_hearing": bool(case_data.hearing_date),
        }
    
    def get_deadline_info(self, user_id: str) -> Dict[str, Any]:
        """Get answer deadline information"""
        case_data = self.get_case_data(user_id)
        
        days_until = None
        is_past = False
        
        if case_data.answer_deadline:
            try:
                deadline = datetime.fromisoformat(case_data.answer_deadline.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                delta = deadline - now
                days_until = delta.days
                is_past = days_until < 0
            except (ValueError, TypeError):
                pass
        
        return {
            "answer_deadline": case_data.answer_deadline,
            "days_until": days_until,
            "is_past": is_past,
            "is_urgent": days_until is not None and 0 <= days_until <= 3,
        }
    
    # =========================================================================
    # Form auto-fill helpers
    # =========================================================================
    
    def get_form_autofill(self, user_id: str, form_id: str) -> Dict[str, Any]:
        """
        Get pre-filled form data based on extracted document data.
        
        Supported form_ids:
        - HOU301: Answer to Eviction Complaint
        - HOU302: Motion to Dismiss
        - HOU303: Motion for Continuance
        - HOU304: Counterclaim
        - GENERAL: Generic form fields
        """
        case_data = self.get_case_data(user_id)
        
        # Base fields for all forms
        base_fields = {
            "case_number": case_data.primary_case_number,
            "plaintiff_name": case_data.landlord_name,
            "plaintiff_address": case_data.landlord_address,
            "defendant_name": case_data.tenant_name,
            "defendant_address": case_data.tenant_address,
            "property_address": case_data.property_address,
            "hearing_date": case_data.hearing_date,
            "hearing_time": case_data.hearing_time,
        }
        
        if form_id == "HOU301":
            # Answer to Eviction Complaint
            return {
                **base_fields,
                "rent_amount": case_data.rent_amount,
                "rent_claimed": case_data.rent_claimed,
                "deposit_amount": case_data.deposit_amount,
                "notice_date": case_data.notice_date,
                "lease_start_date": case_data.lease_start,
                "lease_end_date": case_data.lease_end,
                "late_fees_claimed": case_data.late_fees,
                "total_claimed": case_data.total_claimed,
                "suggested_defenses": self._suggest_defenses(case_data),
            }
        
        elif form_id == "HOU302":
            # Motion to Dismiss
            return {
                **base_fields,
                "grounds": self._suggest_dismissal_grounds(case_data),
                "supporting_statutes": case_data.matched_statutes[:5],
            }
        
        elif form_id == "HOU303":
            # Motion for Continuance
            return {
                **base_fields,
                "current_hearing_date": case_data.hearing_date,
                "reason": "",  # User must provide
            }
        
        elif form_id == "HOU304":
            # Counterclaim
            return {
                **base_fields,
                "damages_claimed": case_data.damages_claimed,
                "suggested_claims": self._suggest_counterclaims(case_data),
            }
        
        return base_fields
    
    def _suggest_defenses(self, case_data: CaseData) -> List[str]:
        """Suggest defenses based on document data"""
        defenses = []
        
        # Check for improper notice
        if case_data.notice_date and case_data.hearing_date:
            defenses.append("IMPROPER_NOTICE")
        
        # Check for habitability issues (if repair documents found)
        if "repair_request" in case_data.documents_by_type or "inspection_report" in case_data.documents_by_type:
            defenses.append("HABITABILITY")
            defenses.append("RENT_ESCROW")
        
        # Check for retaliation (if complaints found)
        if case_data.documents_by_type.get("letter") or case_data.documents_by_type.get("email_communication"):
            defenses.append("RETALIATION")
        
        # Check for payment issues
        if case_data.documents_by_type.get("receipt") or case_data.documents_by_type.get("payment_record"):
            defenses.append("PAYMENT_MADE")
        
        return defenses
    
    def _suggest_dismissal_grounds(self, case_data: CaseData) -> List[str]:
        """Suggest grounds for dismissal"""
        grounds = []
        
        if not case_data.case_numbers:
            grounds.append("IMPROPER_SERVICE")
        
        if case_data.documents_by_type.get("receipt"):
            grounds.append("PAYMENT_RENDERED_MOOT")
        
        return grounds
    
    def _suggest_counterclaims(self, case_data: CaseData) -> List[str]:
        """Suggest counterclaims based on document data"""
        claims = []
        
        if case_data.deposit_amount:
            claims.append("SECURITY_DEPOSIT_VIOLATION")
        
        if "repair_request" in case_data.documents_by_type:
            claims.append("BREACH_OF_WARRANTY_HABITABILITY")
        
        if "photo_evidence" in case_data.documents_by_type:
            claims.append("PROPERTY_DAMAGE")
        
        return claims
    
    # =========================================================================
    # Calendar/Deadline helpers
    # =========================================================================
    
    def get_calendar_events(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get calendar events derived from documents.
        
        Returns events in a format suitable for calendar display.
        """
        case_data = self.get_case_data(user_id)
        events = []
        
        # Add hearing as event
        if case_data.hearing_date:
            events.append({
                "id": f"hearing_{user_id}",
                "title": "Court Hearing",
                "date": case_data.hearing_date,
                "time": case_data.hearing_time,
                "type": "hearing",
                "critical": True,
                "source": "document_extraction",
            })
        
        # Add answer deadline
        if case_data.answer_deadline:
            events.append({
                "id": f"deadline_{user_id}",
                "title": "Answer Deadline",
                "date": case_data.answer_deadline,
                "type": "deadline",
                "critical": True,
                "source": "document_extraction",
            })
        
        # Add action items with deadlines
        for i, action in enumerate(case_data.action_items):
            if action.get("deadline"):
                events.append({
                    "id": f"action_{user_id}_{i}",
                    "title": action.get("title", "Action Required"),
                    "date": action["deadline"],
                    "type": "action_item",
                    "critical": action.get("priority", 5) <= 2,
                    "source": "document_extraction",
                    "description": action.get("description"),
                })
        
        # Add timeline events that have future dates
        for i, event in enumerate(case_data.timeline_events):
            event_date = event.get("date")
            if event_date:
                try:
                    dt = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
                    if dt > datetime.now(timezone.utc):
                        events.append({
                            "id": f"timeline_{user_id}_{i}",
                            "title": event.get("title", "Event"),
                            "date": event_date,
                            "type": "timeline",
                            "critical": event.get("is_critical", False),
                            "source": "document_extraction",
                        })
                except (ValueError, TypeError):
                    pass
        
        # Sort by date
        events.sort(key=lambda x: x.get("date", "9999"))
        
        return events
    
    # =========================================================================
    # AI/Copilot context helpers
    # =========================================================================
    
    def get_ai_context(self, user_id: str) -> str:
        """
        Get a text summary of case data for AI context injection.
        
        This provides the AI copilot with relevant case information.
        """
        case_data = self.get_case_data(user_id)
        
        context_parts = []
        
        # Case identification
        if case_data.primary_case_number:
            context_parts.append(f"Case Number: {case_data.primary_case_number}")
        
        # Parties
        if case_data.tenant_name:
            context_parts.append(f"Tenant: {case_data.tenant_name}")
        if case_data.landlord_name:
            context_parts.append(f"Landlord: {case_data.landlord_name}")
        
        # Key dates
        if case_data.hearing_date:
            context_parts.append(f"Hearing Date: {case_data.hearing_date}")
        if case_data.answer_deadline:
            deadline_info = self.get_deadline_info(user_id)
            if deadline_info.get("days_until") is not None:
                context_parts.append(f"Answer Deadline: {case_data.answer_deadline} ({deadline_info['days_until']} days)")
        
        # Amounts
        if case_data.rent_claimed:
            context_parts.append(f"Rent Claimed: ${case_data.rent_claimed:,.2f}")
        if case_data.total_claimed:
            context_parts.append(f"Total Claimed: ${case_data.total_claimed:,.2f}")
        
        # Documents
        context_parts.append(f"Documents Analyzed: {case_data.document_count}")
        
        # Urgency
        if case_data.urgency_level:
            context_parts.append(f"Urgency Level: {case_data.urgency_level.upper()}")
        
        # Urgent actions
        if case_data.urgent_actions:
            context_parts.append(f"Urgent Actions: {len(case_data.urgent_actions)} pending")
        
        # Legal references
        if case_data.matched_statutes:
            context_parts.append(f"Applicable Statutes: {', '.join(case_data.matched_statutes[:3])}")
        
        return "\n".join(context_parts)
    
    def get_ai_context_dict(self, user_id: str) -> Dict[str, Any]:
        """Get case data as a dictionary for AI context"""
        return self.get_case_data(user_id).to_dict()
    
    # =========================================================================
    # Cache management
    # =========================================================================
    
    def invalidate_cache(self, user_id: str):
        """Invalidate cached data for a user"""
        if user_id in self._cache:
            del self._cache[user_id]
    
    def invalidate_all(self):
        """Invalidate all cached data"""
        self._cache.clear()


# =============================================================================
# Singleton accessor
# =============================================================================

_hub: Optional[DocumentHub] = None


def get_document_hub() -> DocumentHub:
    """Get or create the document hub singleton"""
    global _hub
    if _hub is None:
        _hub = DocumentHub()
    return _hub
