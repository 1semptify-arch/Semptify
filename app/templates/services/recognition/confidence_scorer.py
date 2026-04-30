"""
Confidence Scorer
=================

Multi-dimensional confidence scoring system.
Evaluates extraction quality, reasoning agreement,
and provides uncertainty quantification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import math

from .models import (
    ConfidenceMetrics, ConfidenceLevel,
    ExtractedEntity, EntityType,
    ReasoningChain, ReasoningStep, ReasoningType,
    DocumentContext, DocumentType,
    LegalIssue, TimelineEntry, RelationshipMap,
)


@dataclass
class ConfidenceFactor:
    """A factor that contributes to confidence"""
    name: str
    weight: float
    score: float  # 0-100
    reasoning: str
    positive_signals: List[str] = field(default_factory=list)
    negative_signals: List[str] = field(default_factory=list)


class ConfidenceScorer:
    """
    Multi-dimensional confidence scoring.
    
    Evaluates:
    - Text quality and completeness
    - Entity extraction reliability
    - Document type classification certainty
    - Relationship mapping confidence
    - Legal analysis reliability
    - Cross-pass reasoning agreement
    """
    
    def __init__(self):
        self.factor_weights = self._define_factor_weights()
        self.quality_thresholds = self._define_quality_thresholds()
        
    def _define_factor_weights(self) -> Dict[str, float]:
        """Define weights for confidence factors"""
        return {
            "text_quality": 0.15,
            "structural_clarity": 0.10,
            "entity_extraction": 0.20,
            "document_type": 0.15,
            "relationship_mapping": 0.15,
            "legal_analysis": 0.15,
            "temporal_consistency": 0.05,
            "reasoning_agreement": 0.05,
        }
    
    def _define_quality_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Define thresholds for quality assessments"""
        return {
            "text_quality": {
                "excellent": 90,
                "good": 75,
                "acceptable": 60,
                "poor": 40,
            },
            "entity_count": {
                "rich": 15,  # Many entities found
                "adequate": 8,
                "sparse": 3,
                "minimal": 1,
            },
            "relationship_density": {
                "dense": 0.5,  # Relationships per entity
                "moderate": 0.3,
                "sparse": 0.1,
            },
        }
    
    async def score(self, 
                    context: DocumentContext,
                    entities: List[ExtractedEntity],
                    document_type: DocumentType,
                    relationships: RelationshipMap,
                    issues: List[LegalIssue],
                    timeline: List[TimelineEntry],
                    reasoning_chains: List[ReasoningChain]) -> Tuple[
        ConfidenceMetrics, ReasoningChain
    ]:
        """
        Calculate comprehensive confidence metrics.
        
        Returns:
            Tuple of (ConfidenceMetrics, ReasoningChain)
        """
        reasoning = ReasoningChain(pass_number=1)
        reasoning.add_step(
            ReasoningType.STATISTICAL,
            "Beginning confidence scoring",
            {
                "entity_count": len(entities),
                "issue_count": len(issues),
            },
            {}
        )
        
        metrics = ConfidenceMetrics()
        factors: List[ConfidenceFactor] = []
        
        # Score each dimension
        text_factor = self._score_text_quality(context, reasoning)
        factors.append(text_factor)
        metrics.text_quality_confidence = text_factor.score
        
        structural_factor = self._score_structural_clarity(context, reasoning)
        factors.append(structural_factor)
        metrics.structural_clarity = structural_factor.score
        
        entity_factor = self._score_entity_extraction(entities, reasoning)
        factors.append(entity_factor)
        metrics.entity_extraction_confidence = entity_factor.score
        
        doctype_factor = self._score_document_type(
            document_type, context, entities, reasoning
        )
        factors.append(doctype_factor)
        metrics.document_type_confidence = doctype_factor.score
        
        relationship_factor = self._score_relationships(
            relationships, entities, reasoning
        )
        factors.append(relationship_factor)
        metrics.relationship_confidence = relationship_factor.score
        
        legal_factor = self._score_legal_analysis(issues, entities, reasoning)
        factors.append(legal_factor)
        metrics.legal_analysis_confidence = legal_factor.score
        
        temporal_factor = self._score_temporal_consistency(timeline, reasoning)
        factors.append(temporal_factor)
        metrics.temporal_confidence = temporal_factor.score
        
        agreement_factor = self._score_reasoning_agreement(reasoning_chains, reasoning)
        factors.append(agreement_factor)
        metrics.reasoning_agreement = agreement_factor.score
        
        # Calculate overall score
        metrics.overall_score = self._calculate_overall_score(factors)
        metrics.level = metrics.classify()
        
        # Identify uncertainty factors
        self._identify_uncertainty(metrics, factors, context, entities)
        
        # Add completeness assessment
        metrics.text_completeness = context.text_completeness if hasattr(context, 'text_completeness') else 100.0
        
        reasoning.add_step(
            ReasoningType.STATISTICAL,
            f"Calculated overall confidence: {metrics.overall_score:.1f}%",
            {},
            {
                "overall": metrics.overall_score,
                "level": metrics.level.value,
                "factors": {f.name: f.score for f in factors},
            },
            confidence_impact=0
        )
        
        reasoning.completed_at = datetime.now()
        reasoning.conclusion = f"Confidence: {metrics.overall_score:.1f}% ({metrics.level.value})"
        
        return metrics, reasoning
    
    def _score_text_quality(self, context: DocumentContext,
                            reasoning: ReasoningChain) -> ConfidenceFactor:
        """Score the quality of extracted text"""
        score = 100.0
        positive = []
        negative = []
        
        # Check OCR quality
        if hasattr(context, 'ocr_quality'):
            if context.ocr_quality < 60:
                score -= 30
                negative.append("Low OCR quality detected")
            elif context.ocr_quality < 80:
                score -= 15
                negative.append("Moderate OCR quality")
            else:
                positive.append("Good text extraction quality")
        
        # Check for scanned document
        if context.is_scanned:
            score -= 10
            negative.append("Document appears to be scanned")
        
        # Check for handwriting
        if context.has_handwriting:
            score -= 15
            negative.append("Contains handwritten content")
        
        # Check word count (reasonable document length)
        if context.total_words < 50:
            score -= 20
            negative.append("Very short document")
        elif context.total_words > 100:
            positive.append(f"Substantial content ({context.total_words} words)")
        
        # Check character to word ratio (garbled text has high ratio)
        if context.total_words > 0:
            ratio = context.total_characters / context.total_words
            if ratio > 10:  # Average word length > 10 suggests garbage
                score -= 25
                negative.append("Possible text extraction errors")
            elif 4 <= ratio <= 7:  # Normal English
                positive.append("Normal word length distribution")
        
        reasoning.add_step(
            ReasoningType.STATISTICAL,
            f"Text quality score: {max(0, score):.1f}",
            {},
            {"score": score, "positive": positive, "negative": negative}
        )
        
        return ConfidenceFactor(
            name="text_quality",
            weight=self.factor_weights["text_quality"],
            score=max(0, min(100, score)),
            reasoning="Text quality assessment",
            positive_signals=positive,
            negative_signals=negative,
        )
    
    def _score_structural_clarity(self, context: DocumentContext,
                                   reasoning: ReasoningChain) -> ConfidenceFactor:
        """Score how clear the document structure is"""
        score = 50.0  # Start at neutral
        positive = []
        negative = []
        
        # Check for structural elements
        if context.has_letterhead:
            score += 10
            positive.append("Has letterhead")
        
        if context.has_date_line:
            score += 10
            positive.append("Has date line")
        
        if context.has_address_block:
            score += 10
            positive.append("Has address block")
        
        if context.has_signature_block:
            score += 10
            positive.append("Has signature block")
        
        if context.has_case_caption:
            score += 15
            positive.append("Has case caption (legal document)")
        
        if context.has_notary_block:
            score += 10
            positive.append("Has notary block")
        
        # Check section identification
        if context.sections:
            if len(context.sections) >= 5:
                score += 15
                positive.append(f"Well-structured ({len(context.sections)} sections)")
            elif len(context.sections) >= 2:
                score += 8
                positive.append(f"Has identifiable sections")
        else:
            score -= 10
            negative.append("No clear sections identified")
        
        # Document flow type identified
        if context.document_flow_type and context.document_flow_type != "unknown":
            score += 10
            positive.append(f"Document flow type: {context.document_flow_type}")
        
        reasoning.add_step(
            ReasoningType.STRUCTURAL_ANALYSIS,
            f"Structural clarity score: {max(0, min(100, score)):.1f}",
            {},
            {"positive": positive, "negative": negative}
        )
        
        return ConfidenceFactor(
            name="structural_clarity",
            weight=self.factor_weights["structural_clarity"],
            score=max(0, min(100, score)),
            reasoning="Document structure assessment",
            positive_signals=positive,
            negative_signals=negative,
        )
    
    def _score_entity_extraction(self, entities: List[ExtractedEntity],
                                  reasoning: ReasoningChain) -> ConfidenceFactor:
        """Score the quality of entity extraction"""
        score = 0.0
        positive = []
        negative = []
        
        if not entities:
            return ConfidenceFactor(
                name="entity_extraction",
                weight=self.factor_weights["entity_extraction"],
                score=20.0,  # Minimal score for no entities
                reasoning="No entities extracted",
                negative_signals=["No entities found in document"],
            )
        
        # Base score from entity count
        entity_count = len(entities)
        thresholds = self.quality_thresholds["entity_count"]
        
        if entity_count >= thresholds["rich"]:
            score = 90
            positive.append(f"Rich extraction ({entity_count} entities)")
        elif entity_count >= thresholds["adequate"]:
            score = 75
            positive.append(f"Adequate extraction ({entity_count} entities)")
        elif entity_count >= thresholds["sparse"]:
            score = 55
            negative.append(f"Sparse extraction ({entity_count} entities)")
        else:
            score = 35
            negative.append(f"Minimal extraction ({entity_count} entities)")
        
        # Adjust for entity confidence
        avg_confidence = sum(e.confidence for e in entities) / len(entities)
        if avg_confidence >= 0.85:
            score += 10
            positive.append(f"High average confidence ({avg_confidence:.0%})")
        elif avg_confidence < 0.6:
            score -= 15
            negative.append(f"Low average confidence ({avg_confidence:.0%})")
        
        # Check for key entity types
        entity_types = set(e.entity_type for e in entities)
        
        key_types_found = sum(1 for t in [EntityType.PERSON, EntityType.ADDRESS, 
                                          EntityType.DATE, EntityType.MONEY] 
                             if t in entity_types)
        
        if key_types_found >= 3:
            score += 10
            positive.append("Multiple key entity types found")
        elif key_types_found < 2:
            score -= 10
            negative.append("Missing key entity types")
        
        # Check for parties (critical for tenant law)
        persons = [e for e in entities if e.entity_type == EntityType.PERSON]
        if len(persons) >= 2:
            positive.append("Multiple parties identified")
        elif len(persons) == 0:
            score -= 20
            negative.append("No parties identified")
        
        reasoning.add_step(
            ReasoningType.STATISTICAL,
            f"Entity extraction score: {max(0, min(100, score)):.1f}",
            {"entity_count": entity_count, "avg_confidence": avg_confidence},
            {"types_found": [t.value for t in entity_types]}
        )
        
        return ConfidenceFactor(
            name="entity_extraction",
            weight=self.factor_weights["entity_extraction"],
            score=max(0, min(100, score)),
            reasoning="Entity extraction quality assessment",
            positive_signals=positive,
            negative_signals=negative,
        )
    
    def _score_document_type(self, document_type: DocumentType,
                              context: DocumentContext,
                              entities: List[ExtractedEntity],
                              reasoning: ReasoningChain) -> ConfidenceFactor:
        """Score confidence in document type classification"""
        score = 50.0  # Start at neutral
        positive = []
        negative = []
        
        if document_type == DocumentType.UNKNOWN:
            score = 20
            negative.append("Document type could not be determined")
        else:
            positive.append(f"Classified as {document_type.value}")
        
        # Check for supporting structural evidence
        if document_type in [DocumentType.SUMMONS, DocumentType.COMPLAINT,
                            DocumentType.COURT_ORDER, DocumentType.JUDGMENT]:
            if context.has_case_caption:
                score += 25
                positive.append("Has case caption supporting court document classification")
            else:
                score -= 15
                negative.append("Court document but no case caption found")
        
        elif document_type in [DocumentType.EVICTION_NOTICE, DocumentType.NOTICE_TO_QUIT,
                               DocumentType.NOTICE_TO_VACATE]:
            if context.has_date_line and context.has_signature_block:
                score += 20
                positive.append("Has date and signature supporting notice classification")
            
            # Check for notice keywords in entities/context
            persons = [e for e in entities if e.entity_type == EntityType.PERSON]
            if persons:
                score += 10
                positive.append("Tenant/landlord parties identified")
        
        elif document_type == DocumentType.LEASE:
            if len(entities) >= 10:  # Leases are entity-rich
                score += 20
                positive.append("Rich entity extraction supporting lease classification")
            if context.has_signature_block:
                score += 10
                positive.append("Has signature block")
        
        # Cross-check with document flow type
        flow_type = context.document_flow_type
        compatible_flows = {
            "letter": [DocumentType.LANDLORD_LETTER, DocumentType.TENANT_LETTER,
                      DocumentType.EVICTION_NOTICE, DocumentType.RENT_INCREASE_NOTICE],
            "legal_filing": [DocumentType.SUMMONS, DocumentType.COMPLAINT,
                           DocumentType.MOTION, DocumentType.AFFIDAVIT],
            "form": [DocumentType.LEASE, DocumentType.HUD_FORM],
            "contract": [DocumentType.LEASE, DocumentType.LEASE_AMENDMENT],
        }
        
        if flow_type in compatible_flows:
            if document_type in compatible_flows[flow_type]:
                score += 15
                positive.append(f"Document flow ({flow_type}) supports classification")
            else:
                score -= 10
                negative.append(f"Document flow ({flow_type}) doesn't match type")
        
        reasoning.add_step(
            ReasoningType.SEMANTIC_ANALYSIS,
            f"Document type confidence: {max(0, min(100, score)):.1f}",
            {"type": document_type.value, "flow": flow_type},
            {}
        )
        
        return ConfidenceFactor(
            name="document_type",
            weight=self.factor_weights["document_type"],
            score=max(0, min(100, score)),
            reasoning="Document classification confidence",
            positive_signals=positive,
            negative_signals=negative,
        )
    
    def _score_relationships(self, relationships: RelationshipMap,
                              entities: List[ExtractedEntity],
                              reasoning: ReasoningChain) -> ConfidenceFactor:
        """Score the quality of relationship mapping"""
        score = 50.0
        positive = []
        negative = []
        
        # Check party relationships
        if relationships.party_relationships:
            score += 20
            positive.append(f"{len(relationships.party_relationships)} party relationships found")
            
            # Check if tenant-landlord relationship exists
            has_tenant_landlord = any(
                r.relationship_type == "landlord_tenant" 
                for r in relationships.party_relationships
            )
            if has_tenant_landlord:
                score += 15
                positive.append("Tenant-landlord relationship identified")
        else:
            negative.append("No party relationships mapped")
        
        # Check financial relationships
        if relationships.amount_relationships:
            score += 10
            positive.append(f"{len(relationships.amount_relationships)} financial amounts mapped")
            
            # Check for potentially illegal amounts
            illegal = [r for r in relationships.amount_relationships if r.may_be_illegal]
            if illegal:
                positive.append(f"Identified {len(illegal)} potentially illegal amounts")
        
        # Check property identification
        if relationships.primary_property:
            score += 10
            positive.append("Primary property identified")
        else:
            negative.append("No primary property identified")
        
        # Check entity linking (relationship density)
        if entities:
            linked_count = sum(1 for e in entities if e.related_entities)
            density = linked_count / len(entities)
            
            if density >= 0.5:
                score += 15
                positive.append(f"High entity linking ({density:.0%} linked)")
            elif density < 0.2:
                score -= 10
                negative.append("Low entity linking")
        
        reasoning.add_step(
            ReasoningType.ENTITY_RELATIONSHIP,
            f"Relationship mapping score: {max(0, min(100, score)):.1f}",
            {},
            {
                "party_relationships": len(relationships.party_relationships),
                "amount_relationships": len(relationships.amount_relationships),
            }
        )
        
        return ConfidenceFactor(
            name="relationship_mapping",
            weight=self.factor_weights["relationship_mapping"],
            score=max(0, min(100, score)),
            reasoning="Relationship mapping quality",
            positive_signals=positive,
            negative_signals=negative,
        )
    
    def _score_legal_analysis(self, issues: List[LegalIssue],
                               entities: List[ExtractedEntity],
                               reasoning: ReasoningChain) -> ConfidenceFactor:
        """Score the quality of legal analysis"""
        score = 60.0  # Start above neutral (legal analysis is specialized)
        positive = []
        negative = []
        
        # Issues detected
        if issues:
            score += min(20, len(issues) * 5)
            positive.append(f"{len(issues)} legal issues identified")
            
            # Check issue quality
            issues_with_statute = sum(1 for i in issues if i.mn_statute)
            if issues_with_statute > 0:
                score += 10
                positive.append(f"{issues_with_statute} issues have statutory basis")
            
            # Check issue confidence
            avg_issue_confidence = sum(i.confidence for i in issues) / len(issues)
            if avg_issue_confidence >= 0.8:
                score += 10
                positive.append("High issue detection confidence")
            elif avg_issue_confidence < 0.6:
                score -= 10
                negative.append("Low issue detection confidence")
            
            # Check for defenses identified
            issues_with_defense = sum(1 for i in issues if i.defense_available)
            if issues_with_defense > 0:
                score += 10
                positive.append(f"Identified defenses for {issues_with_defense} issues")
        else:
            # No issues might be valid
            if entities:
                positive.append("No legal issues detected (may be normal)")
            else:
                score -= 20
                negative.append("No legal analysis possible without entities")
        
        # Check for critical issues
        critical = [i for i in issues if i.severity.value == "critical"]
        if critical:
            score += 5
            positive.append(f"{len(critical)} critical issues flagged")
        
        reasoning.add_step(
            ReasoningType.LEGAL_RULE,
            f"Legal analysis score: {max(0, min(100, score)):.1f}",
            {"issue_count": len(issues)},
            {"critical_count": len(critical) if issues else 0}
        )
        
        return ConfidenceFactor(
            name="legal_analysis",
            weight=self.factor_weights["legal_analysis"],
            score=max(0, min(100, score)),
            reasoning="Legal analysis quality",
            positive_signals=positive,
            negative_signals=negative,
        )
    
    def _score_temporal_consistency(self, timeline: List[TimelineEntry],
                                     reasoning: ReasoningChain) -> ConfidenceFactor:
        """Score the consistency of temporal data"""
        score = 50.0
        positive = []
        negative = []
        
        if not timeline:
            return ConfidenceFactor(
                name="temporal_consistency",
                weight=self.factor_weights["temporal_consistency"],
                score=40.0,
                reasoning="No timeline entries",
                negative_signals=["No dates extracted for timeline"],
            )
        
        # Check date validity
        valid_dates = sum(1 for t in timeline if t.event_date is not None)
        if valid_dates == len(timeline):
            score += 20
            positive.append("All dates parsed successfully")
        elif valid_dates < len(timeline) * 0.5:
            score -= 15
            negative.append("Many dates could not be parsed")
        
        # Check for reasonable date range
        dates = [t.event_date for t in timeline if t.event_date]
        if dates:
            from datetime import date, timedelta
            today = date.today()
            
            # Check if dates are within reasonable range (2 years past, 1 year future)
            in_range = sum(1 for d in dates 
                          if today - timedelta(days=730) <= d <= today + timedelta(days=365))
            
            if in_range == len(dates):
                score += 15
                positive.append("All dates within reasonable range")
            elif in_range < len(dates) * 0.5:
                score -= 20
                negative.append("Some dates outside reasonable range")
        
        # Check for deadlines
        deadlines = [t for t in timeline if t.is_deadline]
        if deadlines:
            score += 10
            positive.append(f"{len(deadlines)} deadlines identified")
        
        # Check for court dates
        court_dates = [t for t in timeline if t.is_court_date]
        if court_dates:
            score += 10
            positive.append(f"{len(court_dates)} court dates identified")
        
        reasoning.add_step(
            ReasoningType.TEMPORAL_LOGIC,
            f"Temporal consistency score: {max(0, min(100, score)):.1f}",
            {"timeline_entries": len(timeline)},
            {"valid_dates": valid_dates}
        )
        
        return ConfidenceFactor(
            name="temporal_consistency",
            weight=self.factor_weights["temporal_consistency"],
            score=max(0, min(100, score)),
            reasoning="Temporal data consistency",
            positive_signals=positive,
            negative_signals=negative,
        )
    
    def _score_reasoning_agreement(self, chains: List[ReasoningChain],
                                    reasoning: ReasoningChain) -> ConfidenceFactor:
        """Score how well multiple reasoning passes agree"""
        score = 70.0  # Start optimistic
        positive = []
        negative = []
        
        if len(chains) < 2:
            return ConfidenceFactor(
                name="reasoning_agreement",
                weight=self.factor_weights["reasoning_agreement"],
                score=50.0,
                reasoning="Single pass only",
                negative_signals=["Only one reasoning pass completed"],
            )
        
        # Check for confirmed findings across passes
        total_confirmed = sum(len(c.findings_confirmed) for c in chains)
        total_revised = sum(len(c.findings_revised) for c in chains)
        
        if total_confirmed > total_revised:
            score += 20
            positive.append(f"More confirmations ({total_confirmed}) than revisions ({total_revised})")
        elif total_revised > total_confirmed * 2:
            score -= 15
            negative.append("Many findings revised between passes")
        
        # Check confidence deltas
        confidence_increases = sum(1 for c in chains if c.confidence_delta > 0)
        if confidence_increases > len(chains) / 2:
            score += 10
            positive.append("Confidence improved through reasoning")
        
        reasoning.add_step(
            ReasoningType.STATISTICAL,
            f"Reasoning agreement score: {max(0, min(100, score)):.1f}",
            {"passes": len(chains)},
            {"confirmed": total_confirmed, "revised": total_revised}
        )
        
        return ConfidenceFactor(
            name="reasoning_agreement",
            weight=self.factor_weights["reasoning_agreement"],
            score=max(0, min(100, score)),
            reasoning="Multi-pass reasoning agreement",
            positive_signals=positive,
            negative_signals=negative,
        )
    
    def _calculate_overall_score(self, factors: List[ConfidenceFactor]) -> float:
        """Calculate weighted overall confidence score"""
        total_weight = sum(f.weight for f in factors)
        weighted_sum = sum(f.score * f.weight for f in factors)
        
        if total_weight > 0:
            return weighted_sum / total_weight
        return 50.0
    
    def _identify_uncertainty(self, metrics: ConfidenceMetrics,
                              factors: List[ConfidenceFactor],
                              context: DocumentContext,
                              entities: List[ExtractedEntity]):
        """Identify sources of uncertainty"""
        # Collect negative signals from low-scoring factors
        for factor in factors:
            if factor.score < 50:
                metrics.ambiguous_elements.extend(factor.negative_signals)
            if factor.score < 30:
                metrics.conflicting_signals.extend(factor.negative_signals)
        
        # Check for missing key information
        entity_types = set(e.entity_type for e in entities)
        
        if EntityType.PERSON not in entity_types:
            metrics.missing_information.append("No parties identified")
        if EntityType.DATE not in entity_types:
            metrics.missing_information.append("No dates extracted")
        if EntityType.ADDRESS not in entity_types:
            metrics.missing_information.append("No property address found")
        
        # Document-level missing info
        if not context.has_date_line:
            metrics.missing_information.append("Document date not found")
        if context.is_scanned and context.ocr_quality < 70:
            metrics.ambiguous_elements.append("OCR quality may affect accuracy")
    
    def explain_confidence(self, metrics: ConfidenceMetrics) -> str:
        """Generate human-readable confidence explanation"""
        level_explanations = {
            ConfidenceLevel.CERTAIN: "Very high confidence in analysis accuracy",
            ConfidenceLevel.HIGH: "High confidence - minor uncertainty in some areas",
            ConfidenceLevel.MEDIUM: "Moderate confidence - some important details may be uncertain",
            ConfidenceLevel.LOW: "Low confidence - significant uncertainty, verify key findings",
            ConfidenceLevel.UNCERTAIN: "Very low confidence - manual review strongly recommended",
        }
        
        explanation = [
            f"Overall Confidence: {metrics.overall_score:.1f}% ({metrics.level.value})",
            level_explanations.get(metrics.level, ""),
            "",
            "Component Scores:",
            f"  • Document Type: {metrics.document_type_confidence:.0f}%",
            f"  • Entity Extraction: {metrics.entity_extraction_confidence:.0f}%",
            f"  • Text Quality: {metrics.text_quality_confidence:.0f}%",
            f"  • Legal Analysis: {metrics.legal_analysis_confidence:.0f}%",
            f"  • Relationships: {metrics.relationship_confidence:.0f}%",
            f"  • Temporal Data: {metrics.temporal_confidence:.0f}%",
        ]
        
        if metrics.ambiguous_elements:
            explanation.append("")
            explanation.append("Uncertain Areas:")
            for item in metrics.ambiguous_elements[:5]:
                explanation.append(f"  ⚠ {item}")
        
        if metrics.missing_information:
            explanation.append("")
            explanation.append("Missing Information:")
            for item in metrics.missing_information[:5]:
                explanation.append(f"  ❓ {item}")
        
        return "\n".join(explanation)
