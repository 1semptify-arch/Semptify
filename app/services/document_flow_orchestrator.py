"""
Document Flow Orchestrator
==========================
Ties together the complete document processing pipeline:

User uploads → Vault stores → Extractor processes → 
Timeline updates → FormData updates → Contacts updates → UI refreshes

This orchestrator connects all existing services into a seamless flow.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.core.event_bus import event_bus, BusEventType
from app.services.document_intake import IntakeEngine, IntakeDocument
from app.services.event_extractor import EventExtractor, ExtractedEvent
from app.services.form_field_extractor import FormFieldExtractor

logger = logging.getLogger(__name__)


class DocumentFlowOrchestrator:
    """
    Orchestrates the complete document flow from upload to UI refresh.
    
    Pipeline stages:
    1. UPLOAD: Receive file, validate, store
    2. EXTRACT: OCR/text extraction, classify document type
    3. ANALYZE: Extract events, parties, amounts, dates
    4. TIMELINE: Create timeline events from extracted dates
    5. FORMDATA: Update central form data hub
    6. CONTACTS: Create/update contacts from parties
    7. NOTIFY: Push UI refresh via WebSocket
    """
    
    def __init__(self):
        self.intake_engine = IntakeEngine()
        self.event_extractor = EventExtractor()
        self.form_extractor = FormFieldExtractor()
        
    async def process_document_complete(
        self,
        doc_id: str,
        user_id: str,
        db_session: Any = None,
    ) -> Dict[str, Any]:
        """
        Complete document processing pipeline.
        
        Args:
            doc_id: Document ID from intake upload
            user_id: User who owns the document
            db_session: Optional database session for persistence
            
        Returns:
            Processing results with extracted data and created records
        """
        result = {
            "doc_id": doc_id,
            "status": "processing",
            "stages": {},
            "errors": [],
        }
        
        try:
            # Stage 1: Get document from intake
            logger.info(f"[FLOW] Starting pipeline for document {doc_id}")
            doc = self.intake_engine.get_document(doc_id)
            
            if not doc:
                result["status"] = "error"
                result["errors"].append(f"Document {doc_id} not found")
                return result
                
            result["stages"]["retrieve"] = {"status": "success", "doc_type": doc.doc_type}
            
            # Stage 2: Process document if not already processed
            if doc.status == "pending":
                logger.info(f"[FLOW] Processing document {doc_id}")
                process_result = await self._process_document(doc)
                result["stages"]["process"] = process_result
                # Refresh doc after processing
                doc = self.intake_engine.get_document(doc_id)
            else:
                result["stages"]["process"] = {"status": "skipped", "reason": "already_processed"}
            
            # Stage 3: Extract timeline events
            logger.info(f"[FLOW] Extracting events from {doc_id}")
            events = await self._extract_timeline_events(doc)
            result["stages"]["events"] = {
                "status": "success",
                "count": len(events),
                "events": [e.__dict__ for e in events[:5]],  # First 5 for preview
            }
            
            # Stage 4: Extract form fields
            logger.info(f"[FLOW] Extracting form fields from {doc_id}")
            form_data = await self._extract_form_fields(doc)
            result["stages"]["form_fields"] = {
                "status": "success",
                "fields_extracted": list(form_data.keys()) if form_data else [],
            }
            
            # Stage 5: Update FormData hub
            if form_data and db_session:
                logger.info(f"[FLOW] Updating FormData for user {user_id}")
                await self._update_form_data(user_id, form_data, db_session)
                result["stages"]["form_data_update"] = {"status": "success"}
            
            # Stage 6: Create contacts from parties
            if form_data and db_session:
                contacts_created = await self._create_contacts_from_extraction(
                    user_id, form_data, doc_id, db_session
                )
                result["stages"]["contacts"] = {
                    "status": "success",
                    "created": contacts_created,
                }
            
            # Stage 7: Create timeline events in DB
            if events and db_session:
                timeline_created = await self._create_timeline_events(
                    user_id, events, doc_id, db_session
                )
                result["stages"]["timeline_create"] = {
                    "status": "success",
                    "created": timeline_created,
                }
            
            # Stage 8: Publish events for UI refresh
            await self._publish_completion_events(user_id, doc_id, result)
            result["stages"]["notify"] = {"status": "success"}
            
            result["status"] = "complete"
            logger.info(f"[FLOW] Pipeline complete for {doc_id}")
            
        except Exception as e:
            logger.error(f"[FLOW] Pipeline error for {doc_id}: {e}")
            result["status"] = "error"
            result["errors"].append(str(e))
            
        return result
    
    async def _process_document(self, doc: IntakeDocument) -> Dict[str, Any]:
        """Process document through intake engine."""
        try:
            # Process synchronously (intake engine handles async internally)
            processed = self.intake_engine.process_document(doc.id)
            return {
                "status": "success",
                "doc_type": processed.doc_type if processed else "unknown",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _extract_timeline_events(self, doc: IntakeDocument) -> List[ExtractedEvent]:
        """Extract timeline events from document."""
        if not doc.extraction or not doc.extraction.full_text:
            return []
            
        events = self.event_extractor.extract_events(
            text=doc.extraction.full_text,
            doc_type=doc.doc_type,
        )
        return events
    
    async def _extract_form_fields(self, doc: IntakeDocument) -> Dict[str, Any]:
        """Extract form fields from document."""
        if not doc.extraction or not doc.extraction.full_text:
            return {}
            
        # FormFieldExtractor expects document data structure
        doc_data = {
            "id": doc.id,
            "type": doc.doc_type,
            "text": doc.extraction.full_text,
            "filename": doc.filename,
        }
        
        fields = self.form_extractor.extract_from_documents([doc_data])
        return fields
    
    async def _update_form_data(
        self,
        user_id: str,
        form_data: Dict[str, Any],
        db_session: Any,
    ) -> None:
        """Update FormData hub with extracted data."""
        try:
            from app.services.form_data import FormDataService
            
            service = FormDataService(user_id, db_session)
            await service.merge_extraction(form_data)
            
            # Publish event
            await event_bus.publish(
                BusEventType.FORM_DATA_UPDATED,
                {"user_id": user_id, "fields": list(form_data.keys())},
                user_id=user_id,
            )
        except ImportError:
            logger.warning("FormDataService not available")
        except Exception as e:
            logger.error(f"Error updating form data: {e}")
    
    async def _create_contacts_from_extraction(
        self,
        user_id: str,
        form_data: Dict[str, Any],
        doc_id: str,
        db_session: Any,
    ) -> List[str]:
        """Create contacts from extracted party information."""
        created = []
        
        try:
            from app.models.models import Contact
            import uuid
            
            # Extract landlord if present
            landlord_name = form_data.get("landlord_name") or form_data.get("plaintiff_name")
            if landlord_name:
                # Check if already exists
                existing = await db_session.execute(
                    f"SELECT id FROM contacts WHERE user_id='{user_id}' AND name='{landlord_name}' AND contact_type='landlord'"
                )
                if not existing.scalar_one_or_none():
                    contact = Contact(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        contact_type="landlord",
                        role="opposing_party",
                        name=landlord_name,
                        organization=form_data.get("property_management_company"),
                        phone=form_data.get("landlord_phone"),
                        address_line1=form_data.get("landlord_address"),
                        source="extracted",
                        source_document_id=doc_id,
                    )
                    db_session.add(contact)
                    created.append(f"landlord:{landlord_name}")
            
            # Extract attorney if present
            attorney_name = form_data.get("plaintiff_attorney") or form_data.get("attorney_name")
            if attorney_name:
                existing = await db_session.execute(
                    f"SELECT id FROM contacts WHERE user_id='{user_id}' AND name='{attorney_name}' AND contact_type='attorney'"
                )
                if not existing.scalar_one_or_none():
                    contact = Contact(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        contact_type="attorney",
                        role="opposing_counsel",
                        name=attorney_name,
                        organization=form_data.get("attorney_firm"),
                        source="extracted",
                        source_document_id=doc_id,
                    )
                    db_session.add(contact)
                    created.append(f"attorney:{attorney_name}")
            
            if created:
                await db_session.commit()
                
        except Exception as e:
            logger.error(f"Error creating contacts: {e}")
            
        return created
    
    async def _create_timeline_events(
        self,
        user_id: str,
        events: List[ExtractedEvent],
        doc_id: str,
        db_session: Any,
    ) -> int:
        """Create timeline events in database."""
        created_count = 0
        
        try:
            from app.models.models import TimelineEvent
            import uuid
            
            for event in events:
                if not event.date:
                    continue
                    
                timeline_event = TimelineEvent(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=event.title or event.event_type,
                    description=event.description,
                    event_date=event.date,
                    event_type=event.event_type,
                    source_document_id=doc_id,
                    importance=event.importance or "medium",
                    auto_generated=True,
                )
                db_session.add(timeline_event)
                created_count += 1
            
            if created_count > 0:
                await db_session.commit()
                
                # Publish event
                await event_bus.publish(
                    BusEventType.TIMELINE_UPDATED,
                    {"user_id": user_id, "events_created": created_count},
                    user_id=user_id,
                )
                
        except Exception as e:
            logger.error(f"Error creating timeline events: {e}")
            
        return created_count
    
    async def _publish_completion_events(
        self,
        user_id: str,
        doc_id: str,
        result: Dict[str, Any],
    ) -> None:
        """Publish completion events for UI refresh."""
        # Document processed event
        await event_bus.publish(
            BusEventType.DOCUMENT_PROCESSED,
            {
                "doc_id": doc_id,
                "status": result["status"],
                "stages": list(result["stages"].keys()),
            },
            user_id=user_id,
        )
        
        # UI refresh needed
        await event_bus.publish(
            BusEventType.UI_REFRESH_NEEDED,
            {
                "reason": "document_processed",
                "doc_id": doc_id,
                "refresh_targets": ["timeline", "form_data", "contacts", "documents"],
            },
            user_id=user_id,
        )
    
    # =========================================================================
    # Document Type Detection
    # =========================================================================
    
    def detect_document_type(self, filename: str, text: str) -> str:
        """
        Auto-detect document type from filename and content.
        
        Document types:
        - summons: Court summons/complaint
        - lease: Rental agreement
        - notice: Landlord notices (pay/quit, cure/quit, etc.)
        - payment: Payment receipts/records
        - communication: Emails, letters, texts
        - evidence: Photos, inspection reports
        - court_filing: Motions, answers, orders
        """
        filename_lower = filename.lower()
        text_lower = text.lower() if text else ""
        
        # Summons detection
        summons_keywords = ["summons", "complaint", "eviction", "unlawful detainer", "forcible entry"]
        if any(kw in filename_lower or kw in text_lower for kw in summons_keywords):
            if "complaint" in text_lower or "summons" in text_lower:
                return "summons"
        
        # Lease detection
        lease_keywords = ["lease", "rental agreement", "tenancy agreement", "month-to-month"]
        if any(kw in filename_lower or kw in text_lower for kw in lease_keywords):
            if "landlord" in text_lower and "tenant" in text_lower:
                return "lease"
        
        # Notice detection
        notice_keywords = ["notice to quit", "pay or quit", "cure or quit", "notice to vacate", 
                          "notice of termination", "14-day notice", "3-day notice"]
        if any(kw in filename_lower or kw in text_lower for kw in notice_keywords):
            return "notice"
        
        # Payment detection
        payment_keywords = ["receipt", "payment", "rent paid", "money order", "check"]
        if any(kw in filename_lower or kw in text_lower for kw in payment_keywords):
            if any(x in text_lower for x in ["$", "amount", "paid"]):
                return "payment"
        
        # Court filing detection
        filing_keywords = ["motion", "answer", "order", "judgment", "stipulation"]
        if any(kw in filename_lower or kw in text_lower for kw in filing_keywords):
            if "court" in text_lower or "case no" in text_lower:
                return "court_filing"
        
        # Communication detection
        comm_keywords = ["email", "text message", "letter", "correspondence", "re:"]
        if any(kw in filename_lower or kw in text_lower for kw in comm_keywords):
            return "communication"
        
        # Evidence (photos, inspections)
        if filename_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.heic')):
            return "evidence"
        if "inspection" in filename_lower or "inspection" in text_lower:
            return "evidence"
        
        return "other"
    
    def get_extraction_config(self, doc_type: str) -> Dict[str, Any]:
        """Get extraction configuration for document type."""
        configs = {
            "summons": {
                "extract": ["case_number", "court_name", "filing_date", "hearing_date", 
                           "plaintiff_name", "defendant_name", "amount_claimed", "attorney_name"],
                "priority_fields": ["case_number", "hearing_date"],
            },
            "lease": {
                "extract": ["lease_start", "lease_end", "rent_amount", "security_deposit",
                           "landlord_name", "tenant_name", "property_address", "lease_terms"],
                "priority_fields": ["rent_amount", "lease_start", "lease_end"],
            },
            "notice": {
                "extract": ["notice_type", "notice_date", "compliance_deadline", "amount_due",
                           "cure_period", "vacate_date"],
                "priority_fields": ["notice_type", "compliance_deadline"],
            },
            "payment": {
                "extract": ["payment_date", "payment_amount", "payment_method", "period_covered"],
                "priority_fields": ["payment_date", "payment_amount"],
            },
            "communication": {
                "extract": ["date", "from", "to", "subject", "content_summary"],
                "priority_fields": ["date", "subject"],
            },
            "court_filing": {
                "extract": ["filing_date", "document_type", "case_number", "filed_by"],
                "priority_fields": ["filing_date", "document_type"],
            },
        }
        return configs.get(doc_type, {"extract": [], "priority_fields": []})


# Singleton instance
document_flow = DocumentFlowOrchestrator()
