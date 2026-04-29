"""
Recognition Service Integration
===============================

Integrates the DocumentRecognitionEngine with Semptify's
existing document processing infrastructure.

This service provides:
- Easy integration with existing document intake
- Conversion between recognition results and existing data models
- Enhanced document processing pipeline
- Backwards-compatible API
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import asdict

from .recognition import (
    DocumentRecognitionEngine, RecognitionResult,
    DocumentType, DocumentCategory, ConfidenceLevel,
    ExtractedEntity, EntityType, PartyRole,
    LegalIssue, IssueSeverity, TimelineEntry,
)
from .document_intake import (
    DocumentType as IntakeDocumentType,
    ExtractionResult, ExtractedDate, ExtractedParty, 
    ExtractedAmount, DetectedIssue,
)

logger = logging.getLogger(__name__)


class EnhancedDocumentProcessor:
    """
    Enhanced document processor using the recognition engine.
    
    Provides backwards-compatible interface while leveraging
    the advanced recognition capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the enhanced processor"""
        self.engine = DocumentRecognitionEngine(config or {})
        self.config = config or {}
        
    async def process(self, text: str,
                      filename: Optional[str] = None,
                      file_type: Optional[str] = None) -> ExtractionResult:
        """
        Process document and return backwards-compatible ExtractionResult.
        
        Args:
            text: Document text
            filename: Optional filename
            file_type: Optional file type
            
        Returns:
            ExtractionResult compatible with existing intake system
        """
        # Run recognition engine
        result = await self.engine.analyze(text, filename, file_type)
        
        # Convert to ExtractionResult
        return self._convert_to_extraction_result(result)
    
    async def process_enhanced(self, text: str,
                               filename: Optional[str] = None,
                               file_type: Optional[str] = None) -> Tuple[
        ExtractionResult, RecognitionResult
    ]:
        """
        Process document and return both legacy and enhanced results.
        
        Returns:
            Tuple of (ExtractionResult, RecognitionResult)
        """
        result = await self.engine.analyze(text, filename, file_type)
        extraction = self._convert_to_extraction_result(result)
        return extraction, result
    
    def _convert_to_extraction_result(self, result: RecognitionResult) -> ExtractionResult:
        """Convert RecognitionResult to ExtractionResult"""
        # Map document type
        doc_type = self._map_document_type(result.document_type)
        
        # Extract dates
        dates = self._extract_dates(result)
        
        # Extract parties
        parties = self._extract_parties(result)
        
        # Extract amounts
        amounts = self._extract_amounts(result)
        
        # Extract issues
        issues = self._extract_issues(result)
        
        # Build summary
        summary = self._build_summary(result)
        
        # Build clauses from legal analysis
        clauses = self._extract_clauses(result)
        
        return ExtractionResult(
            doc_type=doc_type,
            language=result.context.language,
            text=result.original_text[:5000],  # Truncate for storage
            summary=summary,
            dates=dates,
            parties=parties,
            amounts=amounts,
            issues=issues,
            clauses=clauses,
            confidence=result.confidence.overall_score / 100.0,  # Convert to 0-1
            metadata={
                "recognition_version": result.engine_version,
                "analysis_id": result.analysis_id,
                "document_category": result.document_category.value,
                "processing_time_ms": result.processing_time_ms,
                "passes_completed": result.passes_completed,
                "confidence_level": result.confidence.level.value,
                "urgency": result.legal_analysis.urgency_level,
                "risk_score": result.legal_analysis.risk_score,
            }
        )
    
    def _map_document_type(self, doc_type: DocumentType) -> IntakeDocumentType:
        """Map recognition DocumentType to intake DocumentType"""
        mapping = {
            DocumentType.EVICTION_NOTICE: IntakeDocumentType.EVICTION_NOTICE,
            DocumentType.NOTICE_TO_QUIT: IntakeDocumentType.NOTICE_TO_QUIT,
            DocumentType.NOTICE_TO_VACATE: IntakeDocumentType.EVICTION_NOTICE,
            DocumentType.FOURTEEN_DAY_NOTICE: IntakeDocumentType.EVICTION_NOTICE,
            DocumentType.THIRTY_DAY_NOTICE: IntakeDocumentType.EVICTION_NOTICE,
            DocumentType.SUMMONS: IntakeDocumentType.COURT_SUMMONS,
            DocumentType.COMPLAINT: IntakeDocumentType.COURT_FILING,
            DocumentType.WRIT_OF_RECOVERY: IntakeDocumentType.COURT_FILING,
            DocumentType.JUDGMENT: IntakeDocumentType.COURT_FILING,
            DocumentType.LEASE: IntakeDocumentType.LEASE,
            DocumentType.LEASE_AMENDMENT: IntakeDocumentType.LEASE,
            DocumentType.RENT_RECEIPT: IntakeDocumentType.RECEIPT,
            DocumentType.RENT_INCREASE_NOTICE: IntakeDocumentType.RENT_INCREASE_NOTICE,
            DocumentType.SECURITY_DEPOSIT_ITEMIZATION: IntakeDocumentType.SECURITY_DEPOSIT_ITEMIZATION,
            DocumentType.REPAIR_REQUEST: IntakeDocumentType.REPAIR_REQUEST,
            DocumentType.PHOTOGRAPH: IntakeDocumentType.PHOTO_EVIDENCE,
        }
        return mapping.get(doc_type, IntakeDocumentType.UNKNOWN)
    
    def _extract_dates(self, result: RecognitionResult) -> List[ExtractedDate]:
        """Extract dates from recognition result"""
        dates = []
        today = date.today()
        
        for entry in result.relationships.timeline:
            if entry.event_date:
                days_until = (entry.event_date - today).days
                
                extracted = ExtractedDate(
                    date=entry.event_date,
                    label=entry.title or entry.event_type,
                    confidence=entry.confidence,
                    is_deadline=entry.is_deadline,
                    days_until=days_until if days_until >= 0 else None,
                )
                dates.append(extracted)
        
        # Add dates from entities not in timeline
        for entity in result.entities:
            if entity.entity_type == EntityType.DATE:
                # Check if already in timeline
                if not any(entry.date_text == entity.value 
                          for entry in result.relationships.timeline):
                    extracted = ExtractedDate(
                        date=None,  # May not be parsed
                        label=entity.value,
                        confidence=entity.confidence,
                        is_deadline=False,
                    )
                    dates.append(extracted)
        
        return dates
    
    def _extract_parties(self, result: RecognitionResult) -> List[ExtractedParty]:
        """Extract parties from recognition result"""
        parties = []
        
        for entity in result.entities:
            if entity.entity_type == EntityType.PERSON:
                role = entity.attributes.get("role", PartyRole.UNKNOWN.value)
                
                # Find contact info for this party
                phone = None
                email = None
                address = None
                
                for related_id in entity.related_entities:
                    related = next(
                        (e for e in result.entities if e.id == related_id), 
                        None
                    )
                    if related:
                        if related.entity_type == EntityType.PHONE:
                            phone = related.value
                        elif related.entity_type == EntityType.EMAIL:
                            email = related.value
                        elif related.entity_type == EntityType.ADDRESS:
                            address = related.value
                
                party = ExtractedParty(
                    name=entity.value,
                    role=role,
                    address=address,
                    phone=phone,
                    email=email,
                )
                parties.append(party)
        
        # Add organizations
        for entity in result.entities:
            if entity.entity_type == EntityType.ORGANIZATION:
                role = entity.attributes.get("role", "organization")
                party = ExtractedParty(
                    name=entity.value,
                    role=role,
                )
                parties.append(party)
        
        return parties
    
    def _extract_amounts(self, result: RecognitionResult) -> List[ExtractedAmount]:
        """Extract amounts from recognition result"""
        amounts = []
        
        for rel in result.relationships.amount_relationships:
            extracted = ExtractedAmount(
                amount=rel.amount,
                label=rel.amount_type.replace("_", " ").title(),
                currency="USD",
                period=rel.period,
            )
            amounts.append(extracted)
        
        return amounts
    
    def _extract_issues(self, result: RecognitionResult) -> List[DetectedIssue]:
        """Extract issues from recognition result"""
        issues = []
        
        for issue in result.legal_analysis.issues:
            # Map severity
            severity_map = {
                IssueSeverity.CRITICAL: "critical",
                IssueSeverity.HIGH: "high",
                IssueSeverity.MEDIUM: "medium",
                IssueSeverity.LOW: "low",
                IssueSeverity.INFORMATIONAL: "info",
            }
            
            detected = DetectedIssue(
                issue_type=issue.issue_type,
                severity=severity_map.get(issue.severity, "medium"),
                description=issue.description,
                legal_basis=issue.legal_basis[0] if issue.legal_basis else None,
                recommended_action=issue.recommended_actions[0] if issue.recommended_actions else None,
                confidence=issue.confidence,
            )
            issues.append(detected)
        
        return issues
    
    def _build_summary(self, result: RecognitionResult) -> str:
        """Build document summary"""
        lines = []
        
        # Document type
        doc_type_display = result.document_type.value.replace("_", " ").title()
        lines.append(f"Document Type: {doc_type_display}")
        
        # Parties
        tenant = result.relationships.get_tenant()
        landlord = result.relationships.get_landlord()
        
        if tenant:
            lines.append(f"Tenant: {tenant.value}")
        if landlord:
            lines.append(f"Landlord: {landlord.value}")
        
        # Property
        if result.relationships.primary_property:
            lines.append(f"Property: {result.relationships.primary_property}")
        
        # Amount
        total = result.relationships.get_total_claimed()
        if total > 0:
            lines.append(f"Amount Claimed: ${total:,.2f}")
        
        # Issues
        if result.legal_analysis.issues:
            critical = len(result.legal_analysis.critical_issues)
            total_issues = len(result.legal_analysis.issues)
            lines.append(f"Issues Found: {total_issues} ({critical} critical)")
        
        # Urgency
        if result.legal_analysis.urgency_level in ["critical", "high"]:
            lines.append(f"⚠️ URGENCY: {result.legal_analysis.urgency_level.upper()}")
        
        return "\n".join(lines)
    
    def _extract_clauses(self, result: RecognitionResult) -> List[str]:
        """Extract important clauses/provisions mentioned"""
        clauses = []
        
        # Add applicable statutes as clauses
        for statute in result.legal_analysis.applicable_mn_statutes:
            clauses.append(f"Minn. Stat. § {statute}")
        
        # Add defense options as important clauses
        for defense in result.legal_analysis.defense_options[:3]:
            clauses.append(f"Defense: {defense}")
        
        # Add procedural requirements
        for req in result.legal_analysis.procedural_requirements[:3]:
            clauses.append(f"Requirement: {req}")
        
        return clauses


class RecognitionServiceFactory:
    """
    Factory for creating recognition service instances.
    """
    
    _instance: Optional['EnhancedDocumentProcessor'] = None
    
    @classmethod
    def get_processor(cls, config: Optional[Dict[str, Any]] = None) -> EnhancedDocumentProcessor:
        """Get or create processor instance"""
        if cls._instance is None:
            cls._instance = EnhancedDocumentProcessor(config)
        return cls._instance
    
    @classmethod
    def create_processor(cls, config: Optional[Dict[str, Any]] = None) -> EnhancedDocumentProcessor:
        """Create new processor instance"""
        return EnhancedDocumentProcessor(config)


# Convenience function
async def analyze_document(text: str,
                           filename: Optional[str] = None,
                           file_type: Optional[str] = None,
                           enhanced: bool = False) -> Any:
    """
    Convenience function for document analysis.
    
    Args:
        text: Document text
        filename: Optional filename
        file_type: Optional file type
        enhanced: If True, returns RecognitionResult; else ExtractionResult
        
    Returns:
        ExtractionResult or RecognitionResult based on enhanced flag
    """
    processor = RecognitionServiceFactory.get_processor()
    
    if enhanced:
        _, result = await processor.process_enhanced(text, filename, file_type)
        return result
    else:
        return await processor.process(text, filename, file_type)


# Export for easy access
__all__ = [
    'EnhancedDocumentProcessor',
    'RecognitionServiceFactory',
    'analyze_document',
]
