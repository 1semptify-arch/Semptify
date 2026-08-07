"""
World-Class Document Recognition Engine
======================================

A sophisticated AI-powered document analysis system designed specifically for
Minnesota tenant law documents. Features multi-pass reasoning, context-aware
analysis, and relationship mapping capabilities.

Architecture:
- Core Engine: DocumentRecognitionEngine - orchestrates all analysis
- Context Analyzer: Understands document structure and flow
- Multi-Pass Reasoner: Cross-validates and refines findings
- Legal Expert: Minnesota tenant law specific patterns
- Relationship Mapper: Connects parties, dates, and amounts
- Confidence Scorer: Provides certainty metrics

Usage:
    from app.services.recognition import DocumentRecognitionEngine
import logging
logger = logging.getLogger(__name__)

    engine = DocumentRecognitionEngine()
    result = await engine.analyze(document_text, filename="eviction_notice.pdf")

    logger.info(f"Document Type: {result.document_type}")
    logger.info(f"Confidence: {result.confidence.overall_score}")
    logger.info(f"Critical Issues: {result.legal_analysis.critical_issues}")
"""

from .confidence_scorer import ConfidenceScorer
from .context_analyzer import ContextAnalyzer
from .engine import DocumentRecognitionEngine
from .handwriting_analyzer import (
    ForgeryIndicator,
    ForgeryType,
    HandwritingAnalysisResult,
    HandwritingAnalyzer,
    HandwritingType,
    HandwrittenElement,
    RiskLevel,
    SignatureComparison,
    SignatureProfile,
    SignatureStatus,
    analyze_handwriting,
)
from .legal_expert import MinnesotaTenantLawExpert
from .models import (
    AmountRelationship,
    ConfidenceLevel,
    ConfidenceMetrics,
    DocumentCategory,
    DocumentContext,
    DocumentType,
    EntityType,
    ExtractedEntity,
    IssueSeverity,
    LegalAnalysis,
    LegalIssue,
    PartyRelationship,
    PartyRole,
    ReasoningChain,
    RecognitionResult,
    RelationshipMap,
    TimelineEntry,
)
from .multi_pass_reasoner import MultiPassReasoner
from .relationship_mapper import RelationshipMapper

__all__ = [
    "DocumentRecognitionEngine",
    "RecognitionResult",
    "DocumentContext",
    "ReasoningChain",
    "LegalAnalysis",
    "RelationshipMap",
    "ConfidenceMetrics",
    "ExtractedEntity",
    "LegalIssue",
    "TimelineEntry",
    "PartyRelationship",
    "AmountRelationship",
    "DocumentType",
    "DocumentCategory",
    "ConfidenceLevel",
    "EntityType",
    "PartyRole",
    "IssueSeverity",
    "ContextAnalyzer",
    "MultiPassReasoner",
    "MinnesotaTenantLawExpert",
    "RelationshipMapper",
    "ConfidenceScorer",
    # Handwriting & Forgery Detection
    "HandwritingAnalyzer",
    "HandwritingAnalysisResult",
    "SignatureProfile",
    "SignatureStatus",
    "HandwrittenElement",
    "HandwritingType",
    "ForgeryIndicator",
    "ForgeryType",
    "RiskLevel",
    "SignatureComparison",
    "analyze_handwriting",
]
