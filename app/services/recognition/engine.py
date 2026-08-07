"""
Document Recognition Engine
===========================

Main orchestration engine that coordinates all recognition components.
This is the primary interface for document analysis.

Usage:
    engine = DocumentRecognitionEngine()
    result = await engine.analyze(document_text, filename="notice.pdf")

    # Access results
    logger.info(result.document_type)          # DocumentType.EVICTION_NOTICE
    logger.info(result.confidence.overall_score)  # 87.5
    logger.info(result.legal_analysis.issues)  # List of detected issues
    logger.info(result.relationships.get_tenant())  # Extracted tenant info
"""

import asyncio
import logging
import time
from typing import Any

from app.core.utc import utc_now

from .confidence_scorer import ConfidenceScorer
from .context_analyzer import ContextAnalyzer
from .legal_dictionary import get_legal_dictionary
from .legal_expert import MinnesotaTenantLawExpert
from .models import (
    ConfidenceMetrics,
    DocumentCategory,
    DocumentContext,
    DocumentType,
    EntityType,
    ExtractedEntity,
    LegalAnalysis,
    LegalIssue,
    ReasoningChain,
    RecognitionResult,
    RelationshipMap,
    TimelineEntry,
)
from .multi_pass_reasoner import MultiPassReasoner
from .relationship_mapper import RelationshipMapper
from .text_preprocessor import get_preprocessor
from .tone_analyzer import get_tone_analyzer

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
    1. Context Analysis ▸ Understand document structure
    2. Multi-Pass Reasoning ▸ Extract and validate entities
    3. Legal Analysis ▸ Apply MN tenant law rules
    4. Relationship Mapping ▸ Connect entities logically
    5. Confidence Scoring ▸ Quantify certainty
    """

    VERSION = "2.0.0"  # Upgraded with preprocessing and legal dictionary

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the recognition engine.

        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}

        # Initialize components
        self.preprocessor = get_preprocessor()
        self.legal_dictionary = get_legal_dictionary()
        self.tone_analyzer = get_tone_analyzer()
        self.context_analyzer = ContextAnalyzer()
        self.reasoner = MultiPassReasoner(max_passes=self.config.get("max_passes", 4))
        self.legal_expert = MinnesotaTenantLawExpert()
        self.relationship_mapper = RelationshipMapper()
        self.confidence_scorer = ConfidenceScorer()

        # Configuration
        self.enable_legal_analysis = self.config.get("enable_legal_analysis", True)
        self.enable_preprocessing = self.config.get("enable_preprocessing", True)
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.0)

        logger.info(f"DocumentRecognitionEngine v{self.VERSION} initialized")

    async def analyze(
        self,
        text: str,
        filename: str | None = None,
        file_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RecognitionResult:
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
            # ============================================================
            # PASS 0: TEXT PREPROCESSING (NEW - Courtroom Accuracy)
            # ============================================================
            working_text = text
            if self.enable_preprocessing:
                logger.debug("Pass 0: Preprocessing text for accuracy...")
                preprocess_result = self.preprocessor.preprocess(text)
                working_text = preprocess_result.cleaned_text
                result.cleaned_text = working_text

                # Add preprocessing info to result
                if preprocess_result.corrections_made:
                    result.notes.append(f"Applied {len(preprocess_result.corrections_made)} OCR corrections")
                if preprocess_result.warnings:
                    result.warnings.extend(preprocess_result.warnings)

                # Quality check
                if preprocess_result.quality_score < 50:
                    result.warnings.append(
                        f"Low text quality score ({preprocess_result.quality_score:.0f}%) - OCR may have issues"
                    )

            # ============================================================
            # PASS 0.5: DICTIONARY-BASED PHRASE RECOGNITION (NEW)
            # ============================================================
            logger.debug("Pass 0.5: Dictionary-based phrase recognition...")

            # Identify legal phrases
            legal_phrases = self.legal_dictionary.identify_phrases(working_text)

            # Quick document type detection via dictionary
            dict_doc_type, dict_confidence, dict_patterns = self.legal_dictionary.identify_document_type(working_text)

            # Extract statute references
            statutes_found = self.legal_dictionary.extract_statutes(working_text)

            # Extract critical numbers
            critical_numbers = self.legal_dictionary.extract_critical_numbers(working_text)

            # Store for later use
            result.notes.append(f"Dictionary identified {len(legal_phrases)} legal phrases")
            if statutes_found:
                result.notes.append(f"Found {len(statutes_found)} MN statute references")

            # ============================================================
            # PASS 1: Context Analysis
            # ============================================================
            logger.debug("Pass 1: Context analysis...")
            context, context_chain = await self._analyze_context(working_text, filename, file_type)
            result.context = context
            result.reasoning_chains.append(context_chain)

            # ============================================================
            # PASS 2: Multi-Pass Reasoning (Entity Extraction)
            # ============================================================
            logger.debug("Pass 2: Multi-pass reasoning...")
            entities, reasoning_chains, initial_confidence = await self._reason(working_text, context)

            # Enhance entities with dictionary findings
            entities = self._enhance_entities_from_dictionary(entities, legal_phrases, statutes_found, critical_numbers)
            result.entities = entities
            result.reasoning_chains.extend(reasoning_chains)

            # ============================================================
            # PASS 3: Document Type Classification
            # ============================================================
            # Use both dictionary and pattern-based classification
            result.document_type = await self._classify_document_enhanced(
                working_text, context, entities, dict_doc_type, dict_confidence
            )
            result.document_category = self._get_category(result.document_type)

            # ============================================================
            # PASS 4: Legal Analysis (if enabled)
            # ============================================================
            if self.enable_legal_analysis:
                logger.debug("Pass 4: Legal analysis...")
                legal_analysis, legal_chain = await self._analyze_legal(working_text, entities, result.document_type)

                # Enhance with statute information
                if statutes_found:
                    for statute in statutes_found:
                        legal_analysis.statute_references.append(
                            {
                                "citation": statute["full_citation"],
                                "title": statute["title"],
                                "summary": statute["summary"],
                            }
                        )

                result.legal_analysis = legal_analysis
                result.reasoning_chains.append(legal_chain)

            # ============================================================
            # PASS 5: Relationship Mapping
            # ============================================================
            logger.debug("Pass 5: Relationship mapping...")
            relationships, rel_chain = await self._map_relationships(
                working_text, entities, result.legal_analysis.upcoming_deadlines if result.legal_analysis else []
            )
            result.relationships = relationships
            result.reasoning_chains.append(rel_chain)

            # ============================================================
            # PASS 6: Tone & Direction Analysis (NEW)
            # ============================================================
            logger.debug("Pass 6: Tone & Direction analysis...")
            tone_result = self.tone_analyzer.analyze(working_text, result.document_type.value)
            result.tone_analysis = tone_result

            # ============================================================
            # PASS 7: Confidence Scoring
            # ============================================================
            logger.debug("Pass 7: Confidence scoring...")
            confidence, conf_chain = await self._score_confidence(
                context,
                entities,
                result.document_type,
                relationships,
                result.legal_analysis.issues if result.legal_analysis else [],
                relationships.timeline,
                result.reasoning_chains,
            )
            result.confidence = confidence
            result.reasoning_chains.append(conf_chain)

            # ============================================================
            # FINAL: Post-processing and Quality Assurance
            # ============================================================
            result.passes_completed = len(reasoning_chains) + 4  # Include new passes

            # Add warnings for low confidence areas
            if confidence.overall_score < 60:
                result.warnings.append("Overall confidence is low - manual review recommended")

            for item in confidence.missing_information[:3]:
                result.notes.append(f"Missing: {item}")

        except Exception as e:
            logger.error(f"Analysis error: {e}", exc_info=True)
            result.warnings.append(f"Analysis error: {str(e)}")
            result.confidence.overall_score = 10.0

        # Record processing time
        result.processing_time_ms = (time.time() - start_time) * 1000
        result.analyzed_at = utc_now()

        logger.info(
            f"Analysis complete: {result.document_type.value}, "
            f"confidence={result.confidence.overall_score:.1f}%, "
            f"time={result.processing_time_ms:.0f}ms"
        )

        return result

    async def analyze_batch(self, documents: list[dict[str, Any]], parallel: bool = True) -> list[RecognitionResult]:
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
                    metadata=doc.get("metadata"),
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
                    metadata=doc.get("metadata"),
                )
                results.append(result)
            return results

    async def _analyze_context(
        self, text: str, filename: str | None, file_type: str | None
    ) -> tuple[DocumentContext, ReasoningChain]:
        """Analyze document context and structure"""
        context, chain = self.context_analyzer.analyze(text, filename=filename, file_type=file_type)
        return context, chain

    async def _reason(
        self, text: str, context: DocumentContext
    ) -> tuple[list[ExtractedEntity], list[ReasoningChain], ConfidenceMetrics]:
        """Perform multi-pass reasoning for entity extraction"""
        return await self.reasoner.reason(text, context)

    async def _classify_document(
        self, text: str, context: DocumentContext, entities: list[ExtractedEntity]
    ) -> DocumentType:
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

    async def _analyze_legal(
        self, text: str, entities: list[ExtractedEntity], document_type: DocumentType
    ) -> tuple[LegalAnalysis, ReasoningChain]:
        """Perform legal analysis"""
        # Get timeline entries from entities
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
        issues, statutes, defenses, reasoning = await self.legal_expert.analyze(text, entities, document_type, timeline)

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
        if document_type in [
            DocumentType.EVICTION_NOTICE,
            DocumentType.FOURTEEN_DAY_NOTICE,
            DocumentType.THIRTY_DAY_NOTICE,
            DocumentType.NOTICE_TO_QUIT,
        ]:
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

    def _calculate_urgency(self, issues: list[LegalIssue], timeline: list[TimelineEntry]) -> str:
        """Calculate urgency level"""
        critical_count = sum(1 for i in issues if i.severity.value == "critical")
        high_count = sum(1 for i in issues if i.severity.value == "high")

        # Check for imminent deadlines
        from datetime import date

        today = date.today()
        imminent_deadlines = sum(
            1 for t in timeline if t.is_deadline and t.event_date and 0 <= (t.event_date - today).days <= 7
        )

        if critical_count > 0 or imminent_deadlines > 0:
            return "critical"
        elif high_count >= 2:
            return "high"
        elif high_count > 0:
            return "normal"
        return "low"

    def _calculate_risk_score(self, issues: list[LegalIssue]) -> float:
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

        total_risk = sum(severity_weights.get(i.severity.value, 0) * i.confidence for i in issues)

        # Cap at 100
        return min(100.0, total_risk)

    async def _map_relationships(
        self, text: str, entities: list[ExtractedEntity], timeline: list[TimelineEntry]
    ) -> tuple[RelationshipMap, ReasoningChain]:
        """Map relationships between entities"""
        return await self.relationship_mapper.map_relationships(text, entities, timeline)

    async def _score_confidence(
        self,
        context: DocumentContext,
        entities: list[ExtractedEntity],
        document_type: DocumentType,
        relationships: RelationshipMap,
        issues: list[LegalIssue],
        timeline: list[TimelineEntry],
        reasoning_chains: list[ReasoningChain],
    ) -> tuple[ConfidenceMetrics, ReasoningChain]:
        """Calculate comprehensive confidence metrics"""
        return await self.confidence_scorer.score(
            context, entities, document_type, relationships, issues, timeline, reasoning_chains
        )

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        import re

        # Remove excessive whitespace
        cleaned = re.sub(r"\s+", " ", text)

        # Remove common OCR artifacts
        cleaned = re.sub(r"[|]", "l", cleaned)  # Pipe to lowercase L

        # Normalize quotes
        cleaned = cleaned.replace('"', '"').replace('"', '"')
        cleaned = cleaned.replace(""", "'").replace(""", "'")

        return cleaned.strip()

    def _enhance_entities_from_dictionary(
        self,
        entities: list[ExtractedEntity],
        legal_phrases: list[dict],
        statutes_found: list[dict],
        critical_numbers: dict,
    ) -> list[ExtractedEntity]:
        """
        Enhance extracted entities with dictionary-based findings.

        This adds high-confidence entities from the legal dictionary
        that may have been missed by pattern matching.
        """
        enhanced = list(entities)
        existing_values = {e.value.lower() for e in entities}

        # Add statute citations as entities
        for statute in statutes_found:
            if statute["full_citation"].lower() not in existing_values:
                enhanced.append(
                    ExtractedEntity(
                        entity_type=EntityType.STATUTE,
                        value=statute["full_citation"],
                        confidence=0.98,  # Very high - dictionary match
                        extraction_method="legal_dictionary",
                        start_position=statute["position"][0],
                        end_position=statute["position"][1],
                        attributes={
                            "title": statute["title"],
                            "summary": statute["summary"],
                        },
                    )
                )

        # Add critical amounts with validation
        if "money_amount" in critical_numbers:
            for amount in critical_numbers["money_amount"]:
                amount_str = f"${amount['value']}"
                if amount_str.lower() not in existing_values and amount["valid"]:
                    enhanced.append(
                        ExtractedEntity(
                            entity_type=EntityType.MONEY,
                            value=amount_str,
                            confidence=0.95,
                            extraction_method="critical_number_extraction",
                            start_position=amount["position"][0],
                            end_position=amount["position"][1],
                        )
                    )

        # Add deadline days
        if "deadline_days" in critical_numbers:
            for deadline in critical_numbers["deadline_days"]:
                if deadline["valid"]:
                    enhanced.append(
                        ExtractedEntity(
                            entity_type=EntityType.DEADLINE,
                            value=f"{deadline['value']} days",
                            confidence=0.95,
                            extraction_method="critical_number_extraction",
                            start_position=deadline["position"][0],
                            end_position=deadline["position"][1],
                            attributes={"full_text": deadline["full_match"]},
                        )
                    )

        return enhanced

    async def _classify_document_enhanced(
        self,
        text: str,
        context: DocumentContext,
        entities: list[ExtractedEntity],
        dict_doc_type: str,
        dict_confidence: float,
    ) -> DocumentType:
        """
        Enhanced document classification using both dictionary and pattern matching.

        This combines the legal dictionary's pattern-based detection with
        the original classification logic for maximum accuracy.
        """
        # If dictionary has high confidence, use it directly
        if dict_confidence >= 80:
            # Map dictionary type to DocumentType enum
            type_mapping = {
                "EVICTION_NOTICE_14_DAY": DocumentType.FOURTEEN_DAY_NOTICE,
                "SUMMONS": DocumentType.SUMMONS,
                "COMPLAINT": DocumentType.COMPLAINT,
                "LEASE_AGREEMENT": DocumentType.LEASE,
                "RENT_RECEIPT": DocumentType.RENT_RECEIPT,
                "SECURITY_DEPOSIT_STATEMENT": DocumentType.SECURITY_DEPOSIT_ITEMIZATION,
                "REPAIR_REQUEST": DocumentType.REPAIR_REQUEST,
                "RENT_INCREASE": DocumentType.RENT_INCREASE_NOTICE,
                "WRIT_OF_RECOVERY": DocumentType.WRIT_OF_RECOVERY,
            }
            if dict_doc_type in type_mapping:
                return type_mapping[dict_doc_type]

        # Fall back to original classification
        return await self._classify_document(text, context, entities)

    def get_quick_summary(self, result: RecognitionResult) -> dict[str, Any]:
        """Get a quick summary of recognition result"""
        return {
            "document_type": result.document_type.value,
            "category": result.document_category.value,
            "confidence": {
                "score": result.confidence.overall_score,
                "level": result.confidence.level.value,
            },
            "parties": {
                "tenant": result.relationships.get_tenant().value if result.relationships.get_tenant() else None,
                "landlord": result.relationships.get_landlord().value if result.relationships.get_landlord() else None,
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
            "● Document Analysis Report",
            "=" * 40,
            "",
            f"● Document Type: {result.document_type.value.replace('_', ' ').title()}",
            f"◆ Confidence: {result.confidence.overall_score:.1f}% ({result.confidence.level.value})",
            "",
        ]

        # Parties
        tenant = result.relationships.get_tenant()
        landlord = result.relationships.get_landlord()
        if tenant or landlord:
            lines.append("● Parties:")
            if tenant:
                lines.append(f"   Tenant: {tenant.value}")
            if landlord:
                lines.append(f"   Landlord: {landlord.value}")
            lines.append("")

        # Property
        if result.relationships.primary_property:
            lines.append(f"○ Property: {result.relationships.primary_property}")
            lines.append("")

        # Financial
        total = result.relationships.get_total_claimed()
        if total > 0:
            lines.append(f"● Amount Claimed: ${total:,.2f}")
            lines.append("")

        # Issues
        if result.legal_analysis.issues:
            lines.append(f"◆  Legal Issues Found: {len(result.legal_analysis.issues)}")
            for issue in result.legal_analysis.issues[:5]:
                severity_emoji = {
                    "critical": "◆",
                    "high": "◆",
                    "medium": "◆",
                    "low": "●",
                    "informational": "ℹ",
                }
                emoji = severity_emoji.get(issue.severity.value, "•")
                lines.append(f"   {emoji} {issue.title}")
            lines.append("")

        # Deadlines
        deadlines = result.get_deadlines(within_days=30)
        if deadlines:
            lines.append("◆ Upcoming Deadlines:")
            for d in deadlines[:3]:
                if d.event_date:
                    lines.append(f"   • {d.event_date.strftime('%B %d, %Y')}: {d.title}")
            lines.append("")

        # Defenses
        if result.legal_analysis.defense_options:
            lines.append("◆  Potential Defenses:")
            for defense in result.legal_analysis.defense_options[:3]:
                lines.append(f"   • {defense}")
            lines.append("")

        # Immediate actions
        if result.legal_analysis.immediate_actions:
            lines.append("○ Recommended Actions:")
            for action in result.legal_analysis.immediate_actions[:3]:
                lines.append(f"   ▸ {action}")

        return "\n".join(lines)
