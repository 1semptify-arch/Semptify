"""
Document Recognition Engine
===========================

Main orchestration engine that coordinates all recognition components.
This is the primary interface for document analysis.

Usage:
    engine = DocumentRecognitionEngine()
    result = await engine.analyze(document_text, filename="notice.pdf")
    
    # Access results
    print(result.document_type)          # DocumentType.EVICTION_NOTICE
    print(result.confidence.overall_score)  # 87.5
    print(result.legal_analysis.issues)  # List of detected issues
    print(result.relationships.get_tenant())  # Extracted tenant info
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from .models import (
    RecognitionResult, DocumentContext, DocumentType, DocumentCategory,
    ExtractedEntity, EntityType, LegalAnalysis, RelationshipMap,
    ConfidenceMetrics, ReasoningChain, LegalIssue, TimelineEntry,
)
from .context_analyzer import ContextAnalyzer
from .multi_pass_reasoner import MultiPassReasoner
from .legal_expert import MinnesotaTenantLawExpert
from .relationship_mapper import RelationshipMapper
from .confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)


class DocumentRecognitionEngine:
    """
    World-class document recognition engine for Minnesota tenant law.
    
    Features:
    - Context-aware analysis
    - Multi-pass reasoning with cross-validation
    - Minnesota tenant law expertise
    - Comprehensive relationship mapping
    - Multi-dimensional confidence scoring
    
    Architecture:
    1. Context Analysis → Understand document structure
    2. Multi-Pass Reasoning → Extract and validate entities
    3. Legal Analysis → Apply MN tenant law rules
    4. Relationship Mapping → Connect entities logically
    5. Confidence Scoring → Quantify certainty
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the recognition engine.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        
        # Initialize components
        self.context_analyzer = ContextAnalyzer()
        self.reasoner = MultiPassReasoner(
            max_passes=self.config.get("max_passes", 4)
        )
        self.legal_expert = MinnesotaTenantLawExpert()
        self.relationship_mapper = RelationshipMapper()
        self.confidence_scorer = ConfidenceScorer()
        
        # Configuration
        self.enable_legal_analysis = self.config.get("enable_legal_analysis", True)
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.0)
        
        logger.info(f"DocumentRecognitionEngine v{self.VERSION} initialized")
    
    async def analyze(self, text: str, 
                      filename: Optional[str] = None,
                      file_type: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> RecognitionResult:
        """
        Perform comprehensive document analysis.
        
        Args:
            text: Document text to analyze
            filename: Optional filename for context
            file_type: Optional file type (pdf, jpg, etc.)
            metadata: Optional additional metadata
        
        Returns:
            RecognitionResult with all analysis data
        """
        start_time = time.time()
        
        result = RecognitionResult(
            engine_version=self.VERSION,
            original_text=text,
        )
        
        try:
            # Step 1: Context Analysis
            logger.debug("Starting context analysis...")
            context, context_chain = await self._analyze_context(
                text, filename, file_type
            )
            result.context = context
            result.reasoning_chains.append(context_chain)
            
            # Step 2: Multi-Pass Reasoning
            logger.debug("Starting multi-pass reasoning...")
            entities, reasoning_chains, initial_confidence = await self._reason(
                text, context
            )
            result.entities = entities
            result.reasoning_chains.extend(reasoning_chains)
            
            # Step 3: Document Type Classification
            result.document_type = await self._classify_document(
                text, context, entities
            )
            result.document_category = self._get_category(result.document_type)
            
            # Step 4: Legal Analysis (if enabled)
            if self.enable_legal_analysis:
                logger.debug("Starting legal analysis...")
                legal_analysis, legal_chain = await self._analyze_legal(
                    text, entities, result.document_type
                )
                result.legal_analysis = legal_analysis
                result.reasoning_chains.append(legal_chain)
            
            # Step 5: Relationship Mapping
            logger.debug("Starting relationship mapping...")
            relationships, rel_chain = await self._map_relationships(
                text, entities, result.legal_analysis.upcoming_deadlines
                if result.legal_analysis else []
            )
            result.relationships = relationships
            result.reasoning_chains.append(rel_chain)
            
            # Step 6: Confidence Scoring
            logger.debug("Calculating confidence scores...")
            confidence, conf_chain = await self._score_confidence(
                context, entities, result.document_type,
                relationships, 
                result.legal_analysis.issues if result.legal_analysis else [],
                relationships.timeline,
                result.reasoning_chains
            )
            result.confidence = confidence
            result.reasoning_chains.append(conf_chain)
            
            # Step 7: Post-processing
            result.cleaned_text = self._clean_text(text)
            result.passes_completed = len(reasoning_chains)
            
            # Add warnings for low confidence areas
            if confidence.overall_score < 60:
                result.warnings.append(
                    "Overall confidence is low - manual review recommended"
                )
            
            for item in confidence.missing_information[:3]:
                result.notes.append(f"Missing: {item}")
            
        except Exception as e:
            logger.error(f"Analysis error: {e}", exc_info=True)
            result.warnings.append(f"Analysis error: {str(e)}")
            result.confidence.overall_score = 10.0
        
        # Record processing time
        result.processing_time_ms = (time.time() - start_time) * 1000
        result.analyzed_at = datetime.now()
        
        logger.info(
            f"Analysis complete: {result.document_type.value}, "
            f"confidence={result.confidence.overall_score:.1f}%, "
            f"time={result.processing_time_ms:.0f}ms"
        )
        
        return result
    
    async def analyze_batch(self, documents: List[Dict[str, Any]],
                            parallel: bool = True) -> List[RecognitionResult]:
        """
        Analyze multiple documents.
        
        Args:
            documents: List of dicts with 'text' and optional 'filename', 'file_type'
            parallel: Whether to process in parallel
        
        Returns:
            List of RecognitionResult
        """
        if parallel:
            tasks = [
                self.analyze(
                    doc.get("text", ""),
                    filename=doc.get("filename"),
                    file_type=doc.get("file_type"),
                    metadata=doc.get("metadata")
                )
                for doc in documents
            ]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for doc in documents:
                result = await self.analyze(
                    doc.get("text", ""),
                    filename=doc.get("filename"),
                    file_type=doc.get("file_type"),
                    metadata=doc.get("metadata")
                )
                results.append(result)
            return results
    
    async def _analyze_context(self, text: str, 
                                filename: Optional[str],
                                file_type: Optional[str]) -> Tuple[DocumentContext, ReasoningChain]:
        """Analyze document context and structure"""
        context, chain = self.context_analyzer.analyze(
            text, filename=filename, file_type=file_type
        )
        return context, chain
    
    async def _reason(self, text: str, 
                      context: DocumentContext) -> Tuple[
        List[ExtractedEntity], List[ReasoningChain], ConfidenceMetrics
    ]:
        """Perform multi-pass reasoning for entity extraction"""
        return await self.reasoner.reason(text, context)
    
    async def _classify_document(self, text: str,
                                  context: DocumentContext,
                                  entities: List[ExtractedEntity]) -> DocumentType:
        """Classify the document type"""
        # Use context hints
        text_lower = text.lower()
        
        # Court documents (check first as they're distinctive)
        if context.has_case_caption:
            if "summons" in text_lower:
                return DocumentType.SUMMONS
            elif "complaint" in text_lower:
                return DocumentType.COMPLAINT
            elif "writ" in text_lower:
                return DocumentType.WRIT_OF_RECOVERY
            elif "order" in text_lower or "judgment" in text_lower:
                return DocumentType.JUDGMENT
            elif "stipulation" in text_lower:
                return DocumentType.STIPULATION
        
        # Eviction notices
        notice_keywords = {
            "14 day": DocumentType.FOURTEEN_DAY_NOTICE,
            "fourteen day": DocumentType.FOURTEEN_DAY_NOTICE,
            "14-day": DocumentType.FOURTEEN_DAY_NOTICE,
            "30 day": DocumentType.THIRTY_DAY_NOTICE,
            "thirty day": DocumentType.THIRTY_DAY_NOTICE,
            "30-day": DocumentType.THIRTY_DAY_NOTICE,
            "notice to quit": DocumentType.NOTICE_TO_QUIT,
            "notice to vacate": DocumentType.NOTICE_TO_VACATE,
            "eviction notice": DocumentType.EVICTION_NOTICE,
        }
        
        for keyword, doc_type in notice_keywords.items():
            if keyword in text_lower:
                return doc_type
        
        # Lease documents
        if any(phrase in text_lower for phrase in ["lease agreement", "rental agreement", "hereby lease"]):
            return DocumentType.LEASE
        
        # Financial documents
        if "security deposit" in text_lower and "itemization" in text_lower:
            return DocumentType.SECURITY_DEPOSIT_ITEMIZATION
        if "rent increase" in text_lower:
            return DocumentType.RENT_INCREASE_NOTICE
        if any(phrase in text_lower for phrase in ["rent receipt", "payment received"]):
            return DocumentType.RENT_RECEIPT
        
        # Correspondence
        if context.document_flow_type == "letter":
            if "landlord" in text_lower or "property" in text_lower:
                return DocumentType.LANDLORD_LETTER
            return DocumentType.TENANT_LETTER
        
        # Default
        return DocumentType.UNKNOWN
    
    def _get_category(self, doc_type: DocumentType) -> DocumentCategory:
        """Get document category from type"""
        category_map = {
            # Notices
            DocumentType.EVICTION_NOTICE: DocumentCategory.NOTICE,
            DocumentType.NOTICE_TO_QUIT: DocumentCategory.NOTICE,
            DocumentType.NOTICE_TO_VACATE: DocumentCategory.NOTICE,
            DocumentType.FOURTEEN_DAY_NOTICE: DocumentCategory.NOTICE,
            DocumentType.THIRTY_DAY_NOTICE: DocumentCategory.NOTICE,
            DocumentType.RENT_INCREASE_NOTICE: DocumentCategory.NOTICE,
            DocumentType.LATE_FEE_NOTICE: DocumentCategory.NOTICE,
            
            # Court filings
            DocumentType.SUMMONS: DocumentCategory.COURT_FILING,
            DocumentType.COMPLAINT: DocumentCategory.COURT_FILING,
            DocumentType.WRIT_OF_RECOVERY: DocumentCategory.COURT_FILING,
            DocumentType.JUDGMENT: DocumentCategory.COURT_FILING,
            DocumentType.STIPULATION: DocumentCategory.COURT_FILING,
            DocumentType.MOTION: DocumentCategory.COURT_FILING,
            DocumentType.AFFIDAVIT: DocumentCategory.COURT_FILING,
            DocumentType.COURT_ORDER: DocumentCategory.COURT_FILING,
            DocumentType.ORDER_FOR_JUDGMENT: DocumentCategory.COURT_FILING,
            DocumentType.SUBPOENA: DocumentCategory.COURT_FILING,
            
            # Lease
            DocumentType.LEASE: DocumentCategory.LEASE_AGREEMENT,
            DocumentType.LEASE_AMENDMENT: DocumentCategory.LEASE_AGREEMENT,
            DocumentType.LEASE_RENEWAL: DocumentCategory.LEASE_AGREEMENT,
            DocumentType.LEASE_TERMINATION: DocumentCategory.LEASE_AGREEMENT,
            
            # Financial
            DocumentType.RENT_RECEIPT: DocumentCategory.FINANCIAL,
            DocumentType.RENT_LEDGER: DocumentCategory.FINANCIAL,
            DocumentType.SECURITY_DEPOSIT_RECEIPT: DocumentCategory.FINANCIAL,
            DocumentType.SECURITY_DEPOSIT_ITEMIZATION: DocumentCategory.FINANCIAL,
            
            # Correspondence
            DocumentType.LANDLORD_LETTER: DocumentCategory.CORRESPONDENCE,
            DocumentType.TENANT_LETTER: DocumentCategory.CORRESPONDENCE,
            DocumentType.ATTORNEY_LETTER: DocumentCategory.CORRESPONDENCE,
            
            # Evidence
            DocumentType.PHOTOGRAPH: DocumentCategory.EVIDENCE,
            DocumentType.TEXT_MESSAGES: DocumentCategory.EVIDENCE,
            DocumentType.EMAIL: DocumentCategory.EVIDENCE,
            DocumentType.BANK_STATEMENT: DocumentCategory.EVIDENCE,
            
            # Government
            DocumentType.HUD_FORM: DocumentCategory.GOVERNMENT_FORM,
            DocumentType.HOUSING_ASSISTANCE_NOTICE: DocumentCategory.GOVERNMENT_FORM,
            DocumentType.SECTION_8_DOCUMENT: DocumentCategory.GOVERNMENT_FORM,
        }
        return category_map.get(doc_type, DocumentCategory.UNKNOWN)
    
    async def _analyze_legal(self, text: str,
                              entities: List[ExtractedEntity],
                              document_type: DocumentType) -> Tuple[LegalAnalysis, ReasoningChain]:
        """Perform legal analysis"""
        # Get timeline entries from entities
        from datetime import date
        timeline = []
        for entity in entities:
            if entity.entity_type == EntityType.DATE:
                entry = TimelineEntry(
                    date_text=entity.value,
                    confidence=entity.confidence,
                    source_text=entity.value,
                )
                timeline.append(entry)
        
        # Run legal expert analysis
        issues, statutes, defenses, reasoning = await self.legal_expert.analyze(
            text, entities, document_type, timeline
        )
        
        # Build legal analysis result
        analysis = LegalAnalysis(
            document_category=self._get_category(document_type),
            document_type=document_type,
            issues=issues,
            critical_issues=[i for i in issues if i.severity.value == "critical"],
            applicable_mn_statutes=statutes,
            defense_options=defenses,
        )
        
        # Calculate urgency and risk
        analysis.urgency_level = self._calculate_urgency(issues, timeline)
        analysis.risk_score = self._calculate_risk_score(issues)
        
        # Extract notice-specific info if applicable
        if document_type in [DocumentType.EVICTION_NOTICE, DocumentType.FOURTEEN_DAY_NOTICE,
                            DocumentType.THIRTY_DAY_NOTICE, DocumentType.NOTICE_TO_QUIT]:
            analysis.notice_type = document_type.value
        
        # Set immediate actions based on issues
        if analysis.critical_issues:
            analysis.immediate_actions = [
                "Review critical issues immediately",
                "Consider contacting legal aid",
            ]
            for issue in analysis.critical_issues[:3]:
                if issue.recommended_actions:
                    analysis.immediate_actions.append(issue.recommended_actions[0])
        
        return analysis, reasoning
    
    def _calculate_urgency(self, issues: List[LegalIssue], 
                           timeline: List[TimelineEntry]) -> str:
        """Calculate urgency level"""
        critical_count = sum(1 for i in issues if i.severity.value == "critical")
        high_count = sum(1 for i in issues if i.severity.value == "high")
        
        # Check for imminent deadlines
        from datetime import date
        today = date.today()
        imminent_deadlines = sum(
            1 for t in timeline 
            if t.is_deadline and t.event_date and 
            0 <= (t.event_date - today).days <= 7
        )
        
        if critical_count > 0 or imminent_deadlines > 0:
            return "critical"
        elif high_count >= 2:
            return "high"
        elif high_count > 0:
            return "normal"
        return "low"
    
    def _calculate_risk_score(self, issues: List[LegalIssue]) -> float:
        """Calculate overall risk score (0-100)"""
        if not issues:
            return 0.0
        
        severity_weights = {
            "critical": 25,
            "high": 15,
            "medium": 8,
            "low": 3,
            "informational": 0,
        }
        
        total_risk = sum(
            severity_weights.get(i.severity.value, 0) * i.confidence
            for i in issues
        )
        
        # Cap at 100
        return min(100.0, total_risk)
    
    async def _map_relationships(self, text: str,
                                  entities: List[ExtractedEntity],
                                  timeline: List[TimelineEntry]) -> Tuple[RelationshipMap, ReasoningChain]:
        """Map relationships between entities"""
        return await self.relationship_mapper.map_relationships(
            text, entities, timeline
        )
    
    async def _score_confidence(self, context: DocumentContext,
                                 entities: List[ExtractedEntity],
                                 document_type: DocumentType,
                                 relationships: RelationshipMap,
                                 issues: List[LegalIssue],
                                 timeline: List[TimelineEntry],
                                 reasoning_chains: List[ReasoningChain]) -> Tuple[ConfidenceMetrics, ReasoningChain]:
        """Calculate comprehensive confidence metrics"""
        return await self.confidence_scorer.score(
            context, entities, document_type,
            relationships, issues, timeline, reasoning_chains
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        import re
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text)
        
        # Remove common OCR artifacts
        cleaned = re.sub(r'[|]', 'l', cleaned)  # Pipe to lowercase L
        
        # Normalize quotes
        cleaned = cleaned.replace('"', '"').replace('"', '"')
        cleaned = cleaned.replace(''', "'").replace(''', "'")
        
        return cleaned.strip()
    
    def get_quick_summary(self, result: RecognitionResult) -> Dict[str, Any]:
        """Get a quick summary of recognition result"""
        return {
            "document_type": result.document_type.value,
            "category": result.document_category.value,
            "confidence": {
                "score": result.confidence.overall_score,
                "level": result.confidence.level.value,
            },
            "parties": {
                "tenant": result.relationships.get_tenant().value 
                         if result.relationships.get_tenant() else None,
                "landlord": result.relationships.get_landlord().value 
                           if result.relationships.get_landlord() else None,
            },
            "property": result.relationships.primary_property,
            "issues": {
                "total": len(result.legal_analysis.issues),
                "critical": len(result.legal_analysis.critical_issues),
            },
            "urgency": result.legal_analysis.urgency_level,
            "risk_score": result.legal_analysis.risk_score,
            "deadlines": len(result.get_deadlines(within_days=14)),
            "processing_time_ms": result.processing_time_ms,
        }
    
    def explain_analysis(self, result: RecognitionResult) -> str:
        """Generate human-readable analysis explanation"""
        lines = [
            f"📄 Document Analysis Report",
            f"=" * 40,
            f"",
            f"📋 Document Type: {result.document_type.value.replace('_', ' ').title()}",
            f"📊 Confidence: {result.confidence.overall_score:.1f}% ({result.confidence.level.value})",
            f"",
        ]
        
        # Parties
        tenant = result.relationships.get_tenant()
        landlord = result.relationships.get_landlord()
        if tenant or landlord:
            lines.append("👥 Parties:")
            if tenant:
                lines.append(f"   Tenant: {tenant.value}")
            if landlord:
                lines.append(f"   Landlord: {landlord.value}")
            lines.append("")
        
        # Property
        if result.relationships.primary_property:
            lines.append(f"🏠 Property: {result.relationships.primary_property}")
            lines.append("")
        
        # Financial
        total = result.relationships.get_total_claimed()
        if total > 0:
            lines.append(f"💰 Amount Claimed: ${total:,.2f}")
            lines.append("")
        
        # Issues
        if result.legal_analysis.issues:
            lines.append(f"⚠️  Legal Issues Found: {len(result.legal_analysis.issues)}")
            for issue in result.legal_analysis.issues[:5]:
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠", 
                    "medium": "🟡",
                    "low": "🟢",
                    "informational": "ℹ️",
                }
                emoji = severity_emoji.get(issue.severity.value, "•")
                lines.append(f"   {emoji} {issue.title}")
            lines.append("")
        
        # Deadlines
        deadlines = result.get_deadlines(within_days=30)
        if deadlines:
            lines.append("📅 Upcoming Deadlines:")
            for d in deadlines[:3]:
                if d.event_date:
                    lines.append(f"   • {d.event_date.strftime('%B %d, %Y')}: {d.title}")
            lines.append("")
        
        # Defenses
        if result.legal_analysis.defense_options:
            lines.append("🛡️  Potential Defenses:")
            for defense in result.legal_analysis.defense_options[:3]:
                lines.append(f"   • {defense}")
            lines.append("")
        
        # Immediate actions
        if result.legal_analysis.immediate_actions:
            lines.append("📌 Recommended Actions:")
            for action in result.legal_analysis.immediate_actions[:3]:
                lines.append(f"   → {action}")
        
        return "\n".join(lines)
