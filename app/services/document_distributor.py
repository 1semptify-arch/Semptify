"""
Document Distributor Service
Automatically distributes processed documents to all Semptify modules:
- Briefcase (folder organization)
- Form Data (case information extraction)
- Court Packet (evidence organization)

This service subscribes to document events and pushes data to all consumers.
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum

from app.core.event_bus import event_bus, EventType

logger = logging.getLogger(__name__)


class DocumentCategory(str, Enum):
    """Document categories for briefcase organization"""
    EVIDENCE = "evidence"
    COURT = "court"
    CORRESPONDENCE = "correspondence"
    FINANCIAL = "financial"
    LEASE = "lease"
    OTHER = "other"


@dataclass
class DistributedDocument:
    """A document ready for distribution to all modules"""
    # Core identifiers
    document_id: str
    registry_id: Optional[str] = None
    user_id: str = ""
    
    # File info
    filename: str = ""
    mime_type: str = ""
    file_size: int = 0
    storage_path: Optional[str] = None
    content_hash: Optional[str] = None
    
    # Classification
    doc_type: Optional[str] = None
    category: DocumentCategory = DocumentCategory.OTHER
    confidence: float = 0.0
    
    # Extracted data
    title: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    
    # Key data points
    key_dates: List[Dict[str, Any]] = None
    key_parties: List[Dict[str, Any]] = None
    key_amounts: List[Dict[str, Any]] = None
    key_terms: List[str] = None
    case_numbers: List[str] = None
    
    # Legal references
    law_references: List[Dict[str, Any]] = None
    matched_statutes: List[str] = None
    
    # Intelligence
    urgency_level: Optional[str] = None
    action_items: List[Dict[str, Any]] = None
    timeline_events: List[Dict[str, Any]] = None
    
    # Registry status
    is_duplicate: bool = False
    integrity_verified: bool = False
    forgery_score: float = 0.0
    requires_review: bool = False
    
    # Timestamps
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.key_dates is None:
            self.key_dates = []
        if self.key_parties is None:
            self.key_parties = []
        if self.key_amounts is None:
            self.key_amounts = []
        if self.key_terms is None:
            self.key_terms = []
        if self.case_numbers is None:
            self.case_numbers = []
        if self.law_references is None:
            self.law_references = []
        if self.matched_statutes is None:
            self.matched_statutes = []
        if self.action_items is None:
            self.action_items = []
        if self.timeline_events is None:
            self.timeline_events = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "registry_id": self.registry_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "storage_path": self.storage_path,
            "content_hash": self.content_hash,
            "doc_type": self.doc_type,
            "category": self.category.value if isinstance(self.category, DocumentCategory) else self.category,
            "confidence": self.confidence,
            "title": self.title,
            "summary": self.summary,
            "key_dates": self.key_dates,
            "key_parties": self.key_parties,
            "key_amounts": self.key_amounts,
            "key_terms": self.key_terms,
            "case_numbers": self.case_numbers,
            "law_references": self.law_references,
            "matched_statutes": self.matched_statutes,
            "urgency_level": self.urgency_level,
            "action_items": self.action_items,
            "timeline_events": self.timeline_events,
            "is_duplicate": self.is_duplicate,
            "integrity_verified": self.integrity_verified,
            "forgery_score": self.forgery_score,
            "requires_review": self.requires_review,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }
    
    def to_briefcase_format(self) -> Dict[str, Any]:
        """Convert to briefcase document format"""
        return {
            "id": self.document_id,
            "registry_id": self.registry_id,
            "name": self.filename,
            "type": self._get_file_type(),
            "size": self.file_size,
            "mime_type": self.mime_type,
            "folder_id": self._get_briefcase_folder(),
            "category": self.category.value,
            "doc_type": self.doc_type,
            "title": self.title,
            "summary": self.summary,
            "tags": self._generate_tags(),
            "starred": self.urgency_level in ["critical", "high"],
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "metadata": {
                "key_dates_count": len(self.key_dates),
                "key_parties_count": len(self.key_parties),
                "key_amounts_count": len(self.key_amounts),
                "law_refs_count": len(self.law_references),
                "urgency_level": self.urgency_level,
                "requires_review": self.requires_review,
            }
        }
    
    def to_form_data_format(self) -> Dict[str, Any]:
        """Convert to form data format for case info extraction"""
        return {
            "id": self.document_id,
            "filename": self.filename,
            "type": self.doc_type,
            "uploaded": self.uploaded_at.isoformat() if self.uploaded_at else "",
            "description": self.summary or "",
            "extracted_dates": self.key_dates,
            "extracted_parties": self.key_parties,
            "extracted_amounts": self.key_amounts,
            "case_numbers": self.case_numbers,
            "key_terms": self.key_terms,
            "urgency_level": self.urgency_level,
            "action_items": self.action_items,
        }
    
    def to_court_packet_format(self) -> Dict[str, Any]:
        """Convert to court packet evidence format"""
        return {
            "id": self.document_id,
            "registry_id": self.registry_id,
            "name": self.filename,
            "type": self._get_file_type(),
            "category": self._get_court_category(),
            "doc_type": self.doc_type,
            "title": self.title,
            "summary": self.summary,
            "is_evidence": self.category == DocumentCategory.EVIDENCE,
            "starred": self.urgency_level in ["critical", "high"],
            "integrity_verified": self.integrity_verified,
            "content_hash": self.content_hash,
            "key_dates": self.key_dates,
            "key_parties": self.key_parties,
            "key_amounts": self.key_amounts,
            "law_references": self.law_references,
            "timeline_events": self.timeline_events,
        }
    
    def _get_file_type(self) -> str:
        """Get file type from mime type"""
        type_map = {
            "application/pdf": "pdf",
            "image/jpeg": "image",
            "image/png": "image",
            "image/gif": "image",
            "application/msword": "word",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "word",
            "text/plain": "text",
        }
        return type_map.get(self.mime_type, "other")
    
    def _get_briefcase_folder(self) -> str:
        """Determine appropriate briefcase folder"""
        if self.doc_type in ["court_summons", "court_complaint", "court_filing", "court_order", "motion", "affidavit"]:
            return "court"
        elif self.doc_type in ["photo_evidence", "video_evidence"]:
            return "evidence"
        elif self.doc_type in ["email_communication", "text_message", "letter"]:
            return "correspondence"
        elif self.doc_type in ["receipt", "payment_record", "bank_statement", "utility_bill"]:
            return "financial"
        elif self.doc_type in ["eviction_notice", "notice_to_quit", "rent_increase_notice", "late_fee_notice"]:
            return "court"  # Notices are court-related
        return "root"
    
    def _get_court_category(self) -> str:
        """Determine court packet category"""
        if self.doc_type in ["photo_evidence", "video_evidence"]:
            return "evidence_photos"
        elif self.doc_type in ["court_summons", "court_complaint", "court_filing", "court_order", "eviction_notice", "notice_to_quit"]:
            return "legal_documents"
        elif self.doc_type in ["email_communication", "text_message", "letter"]:
            return "communications"
        elif self.doc_type in ["receipt", "payment_record", "bank_statement"]:
            return "financial"
        return "other"
    
    def _generate_tags(self) -> List[str]:
        """Generate tags based on document content"""
        tags = []
        
        if self.doc_type:
            tags.append(self.doc_type.replace("_", " ").title())
        
        if self.urgency_level == "critical":
            tags.append("Urgent")
        
        if self.category == DocumentCategory.EVIDENCE:
            tags.append("Evidence")
        
        if self.category == DocumentCategory.COURT:
            tags.append("Court")
        
        if len(self.key_amounts) > 0:
            tags.append("Financial")
        
        if self.requires_review:
            tags.append("Review Needed")
        
        return tags[:5]  # Limit to 5 tags


class DocumentDistributor:
    """
    Central service for distributing processed documents to all Semptify modules.
    
    When a document is uploaded and processed via unified upload, this service:
    1. Receives the processed document data
    2. Formats it for each consuming module
    3. Pushes to Briefcase, Form Data, and Court Packet
    4. Emits events for real-time UI updates
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
        
        # In-memory stores (in production, use database)
        self._distributed_docs: Dict[str, DistributedDocument] = {}
        self._user_docs: Dict[str, List[str]] = {}  # user_id -> [doc_ids]
        
        # Subscribe to document events
        self._setup_event_listeners()
        
        self._initialized = True
        logger.info("DocumentDistributor initialized")
    
    def _setup_event_listeners(self):
        """Set up event bus listeners"""
        try:
            event_bus.subscribe(EventType.DOCUMENT_FULLY_PROCESSED, self._on_document_processed)
            logger.info("DocumentDistributor subscribed to events")
        except Exception as e:
            logger.warning(f"Failed to set up event listeners: {e}")
    
    def _on_document_processed(self, event_data: Dict[str, Any]):
        """Handle document processed events"""
        try:
            doc_id = event_data.get("document_id")
            if doc_id and doc_id in self._distributed_docs:
                doc = self._distributed_docs[doc_id]
                self._emit_distribution_events(doc)
        except Exception as e:
            logger.error(f"Error handling document processed event: {e}")
    
    def distribute_document(
        self,
        document_id: str,
        user_id: str,
        registry_id: Optional[str] = None,
        filename: str = "",
        mime_type: str = "",
        file_size: int = 0,
        storage_path: Optional[str] = None,
        content_hash: Optional[str] = None,
        doc_type: Optional[str] = None,
        confidence: float = 0.0,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        full_text: Optional[str] = None,
        key_dates: Optional[List[Dict]] = None,
        key_parties: Optional[List[Dict]] = None,
        key_amounts: Optional[List[Dict]] = None,
        key_terms: Optional[List[str]] = None,
        case_numbers: Optional[List[str]] = None,
        law_references: Optional[List[Dict]] = None,
        matched_statutes: Optional[List[str]] = None,
        urgency_level: Optional[str] = None,
        action_items: Optional[List[Dict]] = None,
        timeline_events: Optional[List[Dict]] = None,
        is_duplicate: bool = False,
        integrity_verified: bool = False,
        forgery_score: float = 0.0,
        requires_review: bool = False,
    ) -> DistributedDocument:
        """
        Distribute a processed document to all Semptify modules.
        
        This is the main entry point called after unified upload processing.
        """
        # Determine category from doc_type
        category = self._determine_category(doc_type)
        
        # Create distributed document
        doc = DistributedDocument(
            document_id=document_id,
            registry_id=registry_id,
            user_id=user_id,
            filename=filename,
            mime_type=mime_type,
            file_size=file_size,
            storage_path=storage_path,
            content_hash=content_hash,
            doc_type=doc_type,
            category=category,
            confidence=confidence,
            title=title,
            summary=summary,
            full_text=full_text,
            key_dates=key_dates or [],
            key_parties=key_parties or [],
            key_amounts=key_amounts or [],
            key_terms=key_terms or [],
            case_numbers=case_numbers or [],
            law_references=law_references or [],
            matched_statutes=matched_statutes or [],
            urgency_level=urgency_level,
            action_items=action_items or [],
            timeline_events=timeline_events or [],
            is_duplicate=is_duplicate,
            integrity_verified=integrity_verified,
            forgery_score=forgery_score,
            requires_review=requires_review,
            uploaded_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )
        
        # Store document
        self._distributed_docs[document_id] = doc
        if user_id not in self._user_docs:
            self._user_docs[user_id] = []
        if document_id not in self._user_docs[user_id]:
            self._user_docs[user_id].append(document_id)
        
        # Emit distribution events
        self._emit_distribution_events(doc)
        
        logger.info(f"Distributed document {document_id} to all modules")
        return doc
    
    def _determine_category(self, doc_type: Optional[str]) -> DocumentCategory:
        """Determine document category from type"""
        if not doc_type:
            return DocumentCategory.OTHER
        
        court_types = ["court_summons", "court_complaint", "court_filing", "court_order", 
                       "eviction_notice", "notice_to_quit", "motion", "affidavit"]
        evidence_types = ["photo_evidence", "video_evidence", "inspection_report"]
        correspondence_types = ["email_communication", "text_message", "letter", 
                               "repair_request", "repair_response"]
        financial_types = ["receipt", "payment_record", "bank_statement", "utility_bill",
                          "rent_increase_notice", "late_fee_notice"]
        lease_types = ["lease", "lease_amendment", "move_in_checklist", "move_out_checklist",
                      "security_deposit_receipt", "security_deposit_itemization"]
        
        if doc_type in court_types:
            return DocumentCategory.COURT
        elif doc_type in evidence_types:
            return DocumentCategory.EVIDENCE
        elif doc_type in correspondence_types:
            return DocumentCategory.CORRESPONDENCE
        elif doc_type in financial_types:
            return DocumentCategory.FINANCIAL
        elif doc_type in lease_types:
            return DocumentCategory.LEASE
        
        return DocumentCategory.OTHER
    
    def _emit_distribution_events(self, doc: DistributedDocument):
        """Emit events to notify all modules"""
        try:
            # Event for Briefcase
            event_bus.publish_sync(
                EventType.DOCUMENT_READY_FOR_BRIEFCASE,
                doc.to_briefcase_format(),
                source="document_distributor",
                user_id=doc.user_id,
            )
            
            # Event for Form Data
            event_bus.publish_sync(
                EventType.DOCUMENT_READY_FOR_FORMS,
                doc.to_form_data_format(),
                source="document_distributor",
                user_id=doc.user_id,
            )
            
            # Event for Court Packet
            event_bus.publish_sync(
                EventType.DOCUMENT_READY_FOR_COURT_PACKET,
                doc.to_court_packet_format(),
                source="document_distributor",
                user_id=doc.user_id,
            )
            
            # General fully processed event
            event_bus.publish_sync(
                EventType.DOCUMENT_FULLY_PROCESSED,
                doc.to_dict(),
                source="document_distributor",
                user_id=doc.user_id,
            )
            
            logger.debug(f"Emitted distribution events for {doc.document_id}")
        except Exception as e:
            logger.error(f"Error emitting distribution events: {e}")
    
    def get_document(self, document_id: str) -> Optional[DistributedDocument]:
        """Get a distributed document by ID"""
        return self._distributed_docs.get(document_id)
    
    def get_user_documents(self, user_id: str) -> List[DistributedDocument]:
        """Get all distributed documents for a user"""
        doc_ids = self._user_docs.get(user_id, [])
        return [self._distributed_docs[did] for did in doc_ids if did in self._distributed_docs]
    
    def get_briefcase_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all documents formatted for briefcase"""
        docs = self.get_user_documents(user_id)
        return [doc.to_briefcase_format() for doc in docs]
    
    def get_form_data_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all documents formatted for form data"""
        docs = self.get_user_documents(user_id)
        return [doc.to_form_data_format() for doc in docs]
    
    def get_court_packet_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all documents formatted for court packet"""
        docs = self.get_user_documents(user_id)
        return [doc.to_court_packet_format() for doc in docs]
    
    def get_documents_by_category(
        self, user_id: str, category: DocumentCategory
    ) -> List[DistributedDocument]:
        """Get documents by category"""
        docs = self.get_user_documents(user_id)
        return [doc for doc in docs if doc.category == category]
    
    def get_urgent_documents(self, user_id: str) -> List[DistributedDocument]:
        """Get urgent documents requiring attention"""
        docs = self.get_user_documents(user_id)
        return [doc for doc in docs if doc.urgency_level in ["critical", "high"]]
    
    def get_documents_with_action_items(self, user_id: str) -> List[DistributedDocument]:
        """Get documents that have pending action items"""
        docs = self.get_user_documents(user_id)
        return [doc for doc in docs if doc.action_items]
    
    def get_extracted_case_info(self, user_id: str) -> Dict[str, Any]:
        """Aggregate case information from all documents"""
        docs = self.get_user_documents(user_id)
        
        all_dates = []
        all_parties = []
        all_amounts = []
        all_case_numbers = []
        all_action_items = []
        all_timeline_events = []
        
        for doc in docs:
            all_dates.extend(doc.key_dates)
            all_parties.extend(doc.key_parties)
            all_amounts.extend(doc.key_amounts)
            all_case_numbers.extend(doc.case_numbers)
            all_action_items.extend(doc.action_items)
            all_timeline_events.extend(doc.timeline_events)
        
        # Deduplicate case numbers
        unique_case_numbers = list(set(all_case_numbers))
        
        return {
            "documents_count": len(docs),
            "dates": all_dates,
            "parties": all_parties,
            "amounts": all_amounts,
            "case_numbers": unique_case_numbers,
            "action_items": all_action_items,
            "timeline_events": all_timeline_events,
            "urgent_count": len([d for d in docs if d.urgency_level in ["critical", "high"]]),
        }


# =============================================================================
# Singleton accessor
# =============================================================================

_distributor: Optional[DocumentDistributor] = None


def get_document_distributor() -> DocumentDistributor:
    """Get or create the document distributor singleton"""
    global _distributor
    if _distributor is None:
        _distributor = DocumentDistributor()
    return _distributor
