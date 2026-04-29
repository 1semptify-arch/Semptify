"""
Multi-Pass Reasoner
===================

Implements multi-pass reasoning logic for document analysis.
Each pass refines findings, cross-validates entities, and
improves confidence through iterative analysis.

Architecture:
- Pass 1: Initial extraction (patterns, keywords, structure)
- Pass 2: Cross-validation (verify entities against each other)
- Pass 3: Legal reasoning (apply domain rules)
- Pass 4: Confidence calibration (finalize scores)
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict

from .models import (
    ReasoningChain, ReasoningStep, ReasoningType,
    ExtractedEntity, EntityType, PartyRole,
    DocumentType, DocumentCategory, DocumentContext,
    ConfidenceMetrics, ConfidenceLevel,
    TimelineEntry, LegalIssue, IssueSeverity,
)


@dataclass
class ExtractionCandidate:
    """A candidate extraction that needs validation"""
    entity_type: EntityType
    value: str
    confidence: float
    source: str  # pattern name or method
    position: Tuple[int, int]
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    validated: bool = False


@dataclass
class ReasoningContext:
    """Context passed between reasoning passes"""
    text: str
    document_context: DocumentContext
    candidates: Dict[EntityType, List[ExtractionCandidate]] = field(default_factory=lambda: defaultdict(list))
    validated_entities: List[ExtractedEntity] = field(default_factory=list)
    document_type_votes: Dict[DocumentType, float] = field(default_factory=lambda: defaultdict(float))
    issues_found: List[LegalIssue] = field(default_factory=list)
    timeline_entries: List[TimelineEntry] = field(default_factory=list)
    cross_references: Dict[str, List[str]] = field(default_factory=dict)
    pass_results: List[Dict[str, Any]] = field(default_factory=list)


class MultiPassReasoner:
    """
    Multi-pass reasoning engine for document analysis.
    
    Each pass builds on previous findings:
    1. Initial extraction - Find all candidate entities
    2. Cross-validation - Verify entities against document context
    3. Legal reasoning - Apply Minnesota tenant law rules
    4. Confidence calibration - Finalize scores based on agreement
    """
    
    def __init__(self, max_passes: int = 4):
        self.max_passes = max_passes
        self.extraction_patterns = self._build_extraction_patterns()
        self.validation_rules = self._build_validation_rules()
        
    def _build_extraction_patterns(self) -> Dict[EntityType, List[Dict[str, Any]]]:
        """Build comprehensive extraction patterns by entity type"""
        return {
            EntityType.PERSON: [
                {
                    "name": "formal_name",
                    "pattern": r"(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
                    "confidence": 0.9,
                },
                {
                    "name": "tenant_context",
                    "pattern": r"(?:tenant|lessee|occupant)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
                    "confidence": 0.95,
                },
                {
                    "name": "landlord_context",
                    "pattern": r"(?:landlord|lessor|owner|property\s+manager)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
                    "confidence": 0.95,
                },
                {
                    "name": "vs_pattern",
                    "pattern": r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:v\.|vs\.?|versus)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
                    "confidence": 0.9,
                    "multi_match": True,
                },
                {
                    "name": "dear_pattern",
                    "pattern": r"Dear\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                    "confidence": 0.8,
                },
                {
                    "name": "signed_by",
                    "pattern": r"(?:Signed|By|Per)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
                    "confidence": 0.85,
                },
            ],
            EntityType.ORGANIZATION: [
                {
                    "name": "llc_corp",
                    "pattern": r"([A-Z][A-Za-z\s]+(?:LLC|Inc\.|Corp\.|Company|Co\.|Ltd\.))",
                    "confidence": 0.95,
                },
                {
                    "name": "management_company",
                    "pattern": r"([A-Z][A-Za-z\s]+(?:Management|Properties|Realty|Real\s+Estate)(?:\s+(?:LLC|Inc\.|Corp\.))?)",
                    "confidence": 0.9,
                },
                {
                    "name": "housing_authority",
                    "pattern": r"((?:Minneapolis|St\.?\s*Paul|[A-Z][a-z]+)\s+(?:Public\s+)?Housing\s+Authority)",
                    "confidence": 0.95,
                },
                {
                    "name": "court_name",
                    "pattern": r"((?:District|Municipal|Housing)\s+Court(?:\s+of\s+[A-Za-z\s]+)?)",
                    "confidence": 0.95,
                },
            ],
            EntityType.ADDRESS: [
                {
                    "name": "full_address",
                    "pattern": r"(\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*(?:\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir|Place|Pl)\.?)(?:[,\s]+(?:Apt|Apartment|Unit|Suite|Ste|#)\s*[A-Za-z0-9]+)?(?:[,\s]+[A-Za-z\s]+)?[,\s]+(?:MN|Minnesota)[,\s]+\d{5}(?:-\d{4})?)",
                    "confidence": 0.95,
                },
                {
                    "name": "street_only",
                    "pattern": r"(\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir|Place|Pl)\.?)",
                    "confidence": 0.7,
                },
                {
                    "name": "property_at",
                    "pattern": r"(?:property|premises|located)\s+(?:at|known\s+as)[:\s]+([^\n,]+)",
                    "confidence": 0.85,
                },
            ],
            EntityType.DATE: [
                {
                    "name": "full_date",
                    "pattern": r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
                    "confidence": 0.95,
                },
                {
                    "name": "numeric_date",
                    "pattern": r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                    "confidence": 0.8,
                },
                {
                    "name": "ordinal_date",
                    "pattern": r"(\d{1,2}(?:st|nd|rd|th)\s+(?:day\s+of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})",
                    "confidence": 0.9,
                },
                {
                    "name": "relative_date",
                    "pattern": r"(within\s+\d+\s+(?:days?|business\s+days?|weeks?))",
                    "confidence": 0.75,
                    "is_relative": True,
                },
            ],
            EntityType.MONEY: [
                {
                    "name": "dollar_amount",
                    "pattern": r"\$\s*([\d,]+(?:\.\d{2})?)",
                    "confidence": 0.95,
                },
                {
                    "name": "written_amount",
                    "pattern": r"(\d+(?:\.\d{2})?)\s*(?:dollars?|USD)",
                    "confidence": 0.85,
                },
                {
                    "name": "rent_amount",
                    "pattern": r"(?:rent|monthly\s+rent|rental\s+amount)[:\s]+\$?\s*([\d,]+(?:\.\d{2})?)",
                    "confidence": 0.95,
                },
                {
                    "name": "deposit_amount",
                    "pattern": r"(?:security\s+)?deposit[:\s]+\$?\s*([\d,]+(?:\.\d{2})?)",
                    "confidence": 0.9,
                },
                {
                    "name": "late_fee",
                    "pattern": r"late\s+(?:fee|charge)[:\s]+\$?\s*([\d,]+(?:\.\d{2})?)",
                    "confidence": 0.9,
                },
            ],
            EntityType.COURT_CASE: [
                {
                    "name": "case_number",
                    "pattern": r"(?:Case|File|Docket)\s*(?:No\.|Number|#)?[:\s]*(\d{2}[-\s]?[A-Z]{2,4}[-\s]?\d+[-\s]?\d*)",
                    "confidence": 0.95,
                },
                {
                    "name": "simple_case",
                    "pattern": r"(?:Case|File)\s*#?\s*:?\s*(\d+)",
                    "confidence": 0.7,
                },
            ],
            EntityType.STATUTE: [
                {
                    "name": "mn_statute",
                    "pattern": r"(?:Minn(?:esota)?\.?\s*Stat(?:utes?)?\.?\s*(?:§|Section)?\s*)(\d+[A-Za-z]?(?:\.\d+)*)",
                    "confidence": 0.95,
                },
                {
                    "name": "statute_ref",
                    "pattern": r"(?:§|Section)\s*(\d+[A-Za-z]?(?:\.\d+)*)",
                    "confidence": 0.8,
                },
            ],
            EntityType.DEADLINE: [
                {
                    "name": "days_notice",
                    "pattern": r"(\d+)[\s-]?days?\s+(?:notice|to\s+(?:vacate|quit|cure|respond|comply))",
                    "confidence": 0.95,
                },
                {
                    "name": "must_by",
                    "pattern": r"(?:must|shall|required\s+to)\s+(?:\w+\s+)*by\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                    "confidence": 0.9,
                },
                {
                    "name": "appearance_date",
                    "pattern": r"(?:appear|hearing|trial)\s+(?:on|date)[:\s]+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
                    "confidence": 0.95,
                },
            ],
            EntityType.PHONE: [
                {
                    "name": "us_phone",
                    "pattern": r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
                    "confidence": 0.9,
                },
            ],
            EntityType.EMAIL: [
                {
                    "name": "email",
                    "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                    "confidence": 0.95,
                },
            ],
            EntityType.UNIT_NUMBER: [
                {
                    "name": "unit_apt",
                    "pattern": r"(?:Apt|Apartment|Unit|Suite|Ste|#)\s*([A-Za-z]?\d+[A-Za-z]?)",
                    "confidence": 0.9,
                },
            ],
        }
    
    def _build_validation_rules(self) -> Dict[str, callable]:
        """Build validation rules for cross-checking"""
        return {
            "tenant_has_address": self._validate_tenant_address,
            "amounts_have_context": self._validate_amount_context,
            "dates_are_valid": self._validate_dates,
            "parties_are_distinct": self._validate_distinct_parties,
            "court_info_consistent": self._validate_court_info,
        }
    
    async def reason(self, text: str, document_context: DocumentContext) -> Tuple[
        List[ExtractedEntity], 
        List[ReasoningChain],
        ConfidenceMetrics
    ]:
        """
        Perform multi-pass reasoning on document text.
        
        Returns:
            Tuple of (validated_entities, reasoning_chains, confidence_metrics)
        """
        context = ReasoningContext(text=text, document_context=document_context)
        reasoning_chains = []
        
        # Pass 1: Initial Extraction
        chain1, context = await self._pass_initial_extraction(context)
        reasoning_chains.append(chain1)
        
        # Pass 2: Cross-Validation
        chain2, context = await self._pass_cross_validation(context)
        reasoning_chains.append(chain2)
        
        # Pass 3: Legal Reasoning
        chain3, context = await self._pass_legal_reasoning(context)
        reasoning_chains.append(chain3)
        
        # Pass 4: Confidence Calibration
        chain4, context, confidence = await self._pass_confidence_calibration(context)
        reasoning_chains.append(chain4)
        
        return context.validated_entities, reasoning_chains, confidence
    
    async def _pass_initial_extraction(self, context: ReasoningContext) -> Tuple[ReasoningChain, ReasoningContext]:
        """
        Pass 1: Initial extraction using patterns.
        Extract all candidate entities without heavy validation.
        """
        chain = ReasoningChain(pass_number=1)
        chain.add_step(
            ReasoningType.PATTERN_MATCH,
            "Beginning initial entity extraction",
            {"text_length": len(context.text)},
            {}
        )
        
        # Extract entities for each type
        for entity_type, patterns in self.extraction_patterns.items():
            candidates_found = []
            
            for pattern_def in patterns:
                pattern = pattern_def["pattern"]
                base_confidence = pattern_def["confidence"]
                
                try:
                    matches = list(re.finditer(pattern, context.text, re.IGNORECASE))
                    
                    for match in matches:
                        # Handle multi-match patterns (like vs_pattern)
                        if pattern_def.get("multi_match"):
                            for group_idx in range(1, len(match.groups()) + 1):
                                if match.group(group_idx):
                                    candidate = ExtractionCandidate(
                                        entity_type=entity_type,
                                        value=match.group(group_idx).strip(),
                                        confidence=base_confidence,
                                        source=pattern_def["name"],
                                        position=(match.start(group_idx), match.end(group_idx)),
                                    )
                                    candidates_found.append(candidate)
                        else:
                            # Get the first capturing group or full match
                            value = match.group(1) if match.groups() else match.group(0)
                            value = value.strip()
                            
                            if value and len(value) > 1:  # Skip empty or single char matches
                                candidate = ExtractionCandidate(
                                    entity_type=entity_type,
                                    value=value,
                                    confidence=base_confidence,
                                    source=pattern_def["name"],
                                    position=(match.start(), match.end()),
                                )
                                candidates_found.append(candidate)
                                
                except re.error:
                    continue
            
            # Deduplicate candidates with same value
            seen_values = {}
            for candidate in candidates_found:
                if candidate.value not in seen_values:
                    seen_values[candidate.value] = candidate
                elif candidate.confidence > seen_values[candidate.value].confidence:
                    seen_values[candidate.value] = candidate
            
            context.candidates[entity_type] = list(seen_values.values())
        
        # Record findings
        total_candidates = sum(len(v) for v in context.candidates.values())
        chain.add_step(
            ReasoningType.PATTERN_MATCH,
            f"Extracted {total_candidates} candidate entities",
            {},
            {
                "by_type": {
                    et.value: len(candidates) 
                    for et, candidates in context.candidates.items()
                }
            },
            confidence_impact=10 if total_candidates > 5 else 5
        )
        
        chain.completed_at = datetime.now()
        chain.conclusion = f"Found {total_candidates} candidate entities across {len(context.candidates)} types"
        chain.new_findings = [f"{et.value}: {len(c)}" for et, c in context.candidates.items() if c]
        
        context.pass_results.append({
            "pass": 1,
            "total_candidates": total_candidates,
            "by_type": {et.value: len(c) for et, c in context.candidates.items()}
        })
        
        return chain, context
    
    async def _pass_cross_validation(self, context: ReasoningContext) -> Tuple[ReasoningChain, ReasoningContext]:
        """
        Pass 2: Cross-validate extracted entities.
        Check for consistency and supporting evidence.
        """
        chain = ReasoningChain(pass_number=2)
        chain.add_step(
            ReasoningType.CROSS_REFERENCE,
            "Beginning cross-validation of extracted entities",
            {},
            {}
        )
        
        validated_count = 0
        revised_count = 0
        
        # Validate each entity type
        for entity_type, candidates in context.candidates.items():
            for candidate in candidates:
                was_validated, notes = self._cross_validate_candidate(
                    candidate, context
                )
                
                if was_validated:
                    candidate.validated = True
                    validated_count += 1
                    
                    # Convert to ExtractedEntity
                    entity = ExtractedEntity(
                        entity_type=entity_type,
                        value=candidate.value,
                        confidence=candidate.confidence,
                        extraction_method=candidate.source,
                        start_position=candidate.position[0],
                        end_position=candidate.position[1],
                        reasoning=notes,
                    )
                    
                    # Add role for person entities
                    if entity_type == EntityType.PERSON:
                        role = self._infer_party_role(candidate.value, candidate.source, context.text)
                        entity.attributes["role"] = role.value
                    
                    # Add amount type for money entities
                    elif entity_type == EntityType.MONEY:
                        amount_type = self._infer_amount_type(candidate, context.text)
                        entity.attributes["amount_type"] = amount_type
                    
                    context.validated_entities.append(entity)
                else:
                    if candidate.confidence > 0.5:
                        revised_count += 1
        
        chain.add_step(
            ReasoningType.CROSS_REFERENCE,
            f"Validated {validated_count} entities, revised {revised_count}",
            {},
            {"validated": validated_count, "revised": revised_count},
            confidence_impact=validated_count * 2
        )
        
        # Check relationships between entities
        self._check_entity_relationships(context)
        
        chain.completed_at = datetime.now()
        chain.conclusion = f"Cross-validation complete: {validated_count} validated"
        chain.findings_confirmed = [f"{e.entity_type.value}: {e.value}" 
                                     for e in context.validated_entities[:5]]
        chain.findings_revised = [f"Revised {revised_count} low-confidence candidates"]
        
        context.pass_results.append({
            "pass": 2,
            "validated": validated_count,
            "revised": revised_count,
        })
        
        return chain, context
    
    def _cross_validate_candidate(self, candidate: ExtractionCandidate, 
                                   context: ReasoningContext) -> Tuple[bool, str]:
        """Cross-validate a single candidate entity"""
        evidence_score = 0
        notes = []
        
        # Check 1: Position in document (header entities more reliable)
        if candidate.position[0] < 500:
            evidence_score += 10
            notes.append("Found in header region")
        
        # Check 2: Multiple mentions
        text_lower = context.text.lower()
        value_lower = candidate.value.lower()
        mention_count = text_lower.count(value_lower)
        if mention_count > 1:
            evidence_score += min(20, mention_count * 5)
            notes.append(f"Mentioned {mention_count} times")
        
        # Check 3: Context-specific validation
        if candidate.entity_type == EntityType.PERSON:
            # Check if followed by common party indicators
            pos = candidate.position[1]
            following_text = context.text[pos:pos+50].lower()
            if any(term in following_text for term in ["tenant", "landlord", "defendant", "plaintiff"]):
                evidence_score += 20
                notes.append("Associated with party role")
        
        elif candidate.entity_type == EntityType.MONEY:
            # Check if preceded by amount descriptors
            pos = candidate.position[0]
            preceding_text = context.text[max(0, pos-50):pos].lower()
            if any(term in preceding_text for term in ["rent", "deposit", "fee", "owed", "due", "total"]):
                evidence_score += 20
                notes.append("Has financial context")
        
        elif candidate.entity_type == EntityType.ADDRESS:
            # Check for Minnesota indicators
            if "mn" in candidate.value.lower() or "minnesota" in candidate.value.lower():
                evidence_score += 15
                notes.append("Contains Minnesota reference")
            # Check for zip code
            if re.search(r'\d{5}', candidate.value):
                evidence_score += 15
                notes.append("Contains zip code")
        
        elif candidate.entity_type == EntityType.DATE:
            # Validate date is reasonable (not too far in past/future)
            parsed_date = self._parse_date(candidate.value)
            if parsed_date:
                today = date.today()
                days_diff = abs((parsed_date - today).days)
                if days_diff < 365 * 2:  # Within 2 years
                    evidence_score += 15
                    notes.append("Date within reasonable range")
        
        # Threshold for validation
        base_threshold = 30
        required_score = base_threshold * (1 - candidate.confidence)
        
        is_valid = evidence_score >= required_score or candidate.confidence >= 0.85
        
        return is_valid, "; ".join(notes)
    
    def _check_entity_relationships(self, context: ReasoningContext):
        """Check and record relationships between entities"""
        # Link people to addresses
        people = [e for e in context.validated_entities if e.entity_type == EntityType.PERSON]
        addresses = [e for e in context.validated_entities if e.entity_type == EntityType.ADDRESS]
        
        for person in people:
            for address in addresses:
                # Check if near each other in document
                dist = abs(person.start_position - address.start_position)
                if dist < 500:
                    person.related_entities.append(address.id)
                    address.related_entities.append(person.id)
                    context.cross_references.setdefault(person.id, []).append(address.id)
        
        # Link amounts to parties
        amounts = [e for e in context.validated_entities if e.entity_type == EntityType.MONEY]
        for amount in amounts:
            for person in people:
                dist = abs(amount.start_position - person.start_position)
                if dist < 300:
                    amount.related_entities.append(person.id)
                    context.cross_references.setdefault(amount.id, []).append(person.id)
    
    def _infer_party_role(self, name: str, source: str, text: str) -> PartyRole:
        """Infer the role of a person in the document"""
        text_lower = text.lower()
        name_lower = name.lower()
        
        # Find context around the name
        pos = text_lower.find(name_lower)
        if pos == -1:
            return PartyRole.UNKNOWN
        
        context_start = max(0, pos - 100)
        context_end = min(len(text), pos + len(name) + 100)
        context_text = text_lower[context_start:context_end]
        
        # Check for explicit role indicators
        role_keywords = {
            PartyRole.TENANT: ["tenant", "lessee", "renter", "occupant", "defendant"],
            PartyRole.LANDLORD: ["landlord", "lessor", "owner", "plaintiff"],
            PartyRole.PROPERTY_MANAGER: ["property manager", "manager", "management"],
            PartyRole.ATTORNEY: ["attorney", "lawyer", "counsel", "esq"],
            PartyRole.JUDGE: ["judge", "honorable", "court"],
        }
        
        for role, keywords in role_keywords.items():
            if any(kw in context_text for kw in keywords):
                return role
        
        # Use source pattern as hint
        if "tenant" in source:
            return PartyRole.TENANT
        elif "landlord" in source:
            return PartyRole.LANDLORD
        elif "vs_pattern" in source:
            # In vs pattern, first is usually plaintiff (landlord)
            if text_lower.find(name_lower) < text_lower.find(" v"):
                return PartyRole.LANDLORD
            else:
                return PartyRole.TENANT
        
        return PartyRole.UNKNOWN
    
    def _infer_amount_type(self, candidate: ExtractionCandidate, text: str) -> str:
        """Infer the type of monetary amount"""
        pos = candidate.position[0]
        context_start = max(0, pos - 100)
        context_text = text[context_start:pos].lower()
        
        amount_types = {
            "rent": ["rent", "monthly", "rental"],
            "deposit": ["deposit", "security"],
            "late_fee": ["late", "fee", "penalty"],
            "damages": ["damage", "repair", "cleaning"],
            "court_costs": ["court", "filing", "costs"],
            "attorney_fees": ["attorney", "legal"],
            "total_owed": ["total", "owed", "due", "balance"],
        }
        
        for amount_type, keywords in amount_types.items():
            if any(kw in context_text for kw in keywords):
                return amount_type
        
        return "unknown"
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string into a date object"""
        import calendar
        
        # Try common formats
        formats = [
            "%B %d, %Y",      # January 15, 2024
            "%B %d %Y",       # January 15 2024
            "%m/%d/%Y",       # 01/15/2024
            "%m-%d-%Y",       # 01-15-2024
            "%m/%d/%y",       # 01/15/24
            "%Y-%m-%d",       # 2024-01-15
        ]
        
        # Clean the string
        cleaned = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        for fmt in formats:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        
        return None
    
    async def _pass_legal_reasoning(self, context: ReasoningContext) -> Tuple[ReasoningChain, ReasoningContext]:
        """
        Pass 3: Apply legal domain reasoning.
        Classify document type and identify legal issues.
        """
        chain = ReasoningChain(pass_number=3)
        chain.add_step(
            ReasoningType.LEGAL_RULE,
            "Beginning legal domain reasoning",
            {},
            {}
        )
        
        # Document type classification
        doc_type = self._classify_document_type(context)
        context.document_type_votes[doc_type] += 1.0
        
        chain.add_step(
            ReasoningType.LEGAL_RULE,
            f"Classified document as {doc_type.value}",
            {"entities_used": len(context.validated_entities)},
            {"document_type": doc_type.value},
            confidence_impact=15
        )
        
        # Build timeline from dates
        self._build_timeline(context)
        
        chain.add_step(
            ReasoningType.TEMPORAL_LOGIC,
            f"Built timeline with {len(context.timeline_entries)} entries",
            {},
            {"timeline_count": len(context.timeline_entries)},
        )
        
        chain.completed_at = datetime.now()
        chain.conclusion = f"Legal analysis complete: {doc_type.value}"
        chain.new_findings = [f"Document type: {doc_type.value}"]
        
        context.pass_results.append({
            "pass": 3,
            "document_type": doc_type.value,
            "timeline_entries": len(context.timeline_entries),
        })
        
        return chain, context
    
    def _classify_document_type(self, context: ReasoningContext) -> DocumentType:
        """Classify the document type based on evidence"""
        text_lower = context.text.lower()
        scores = defaultdict(float)
        
        # Check for court documents
        if context.document_context.has_case_caption:
            scores[DocumentType.SUMMONS] += 30
            scores[DocumentType.COMPLAINT] += 25
        
        # Notice types
        notice_patterns = {
            DocumentType.EVICTION_NOTICE: ["eviction", "evicted", "terminate your tenancy"],
            DocumentType.NOTICE_TO_QUIT: ["notice to quit", "quit the premises"],
            DocumentType.NOTICE_TO_VACATE: ["notice to vacate", "vacate the premises"],
            DocumentType.FOURTEEN_DAY_NOTICE: ["14 day", "fourteen day", "14-day"],
            DocumentType.THIRTY_DAY_NOTICE: ["30 day", "thirty day", "30-day"],
        }
        
        for doc_type, patterns in notice_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    scores[doc_type] += 20
        
        # Court documents
        court_patterns = {
            DocumentType.SUMMONS: ["summons", "you are hereby summoned", "appear in court"],
            DocumentType.COMPLAINT: ["complaint", "plaintiff complains", "causes of action"],
            DocumentType.WRIT_OF_RECOVERY: ["writ of recovery", "writ of restitution"],
            DocumentType.JUDGMENT: ["judgment", "ordered and adjudged"],
            DocumentType.STIPULATION: ["stipulation", "parties stipulate", "agree as follows"],
        }
        
        for doc_type, patterns in court_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    scores[doc_type] += 25
        
        # Lease documents
        lease_patterns = {
            DocumentType.LEASE: ["lease agreement", "rental agreement", "term of lease", "hereby lease"],
            DocumentType.LEASE_AMENDMENT: ["amendment to lease", "lease modification"],
            DocumentType.RENT_INCREASE_NOTICE: ["rent increase", "new rental amount", "rent will be"],
        }
        
        for doc_type, patterns in lease_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    scores[doc_type] += 20
        
        # Financial documents
        financial_patterns = {
            DocumentType.RENT_RECEIPT: ["rent receipt", "payment received", "amount paid"],
            DocumentType.RENT_LEDGER: ["rent ledger", "payment history", "balance due"],
            DocumentType.SECURITY_DEPOSIT_ITEMIZATION: ["security deposit", "itemization", "deductions"],
            DocumentType.LATE_FEE_NOTICE: ["late fee", "late payment", "past due"],
        }
        
        for doc_type, patterns in financial_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    scores[doc_type] += 20
        
        # Letter indicators
        if context.document_context.document_flow_type == "letter":
            if "landlord" in text_lower or "property" in text_lower:
                scores[DocumentType.LANDLORD_LETTER] += 10
        
        # Return highest scoring type
        if scores:
            return max(scores, key=scores.get)
        
        return DocumentType.UNKNOWN
    
    def _build_timeline(self, context: ReasoningContext):
        """Build timeline entries from extracted dates"""
        date_entities = [e for e in context.validated_entities 
                        if e.entity_type == EntityType.DATE]
        deadline_entities = [e for e in context.validated_entities 
                           if e.entity_type == EntityType.DEADLINE]
        
        for date_entity in date_entities:
            parsed = self._parse_date(date_entity.value)
            if parsed:
                # Determine event type from context
                pos = date_entity.start_position
                context_text = context.text[max(0, pos-100):pos+100].lower()
                
                event_type = "date"
                is_deadline = False
                is_court_date = False
                
                if any(term in context_text for term in ["deadline", "must", "shall", "required"]):
                    event_type = "deadline"
                    is_deadline = True
                elif any(term in context_text for term in ["court", "hearing", "trial", "appear"]):
                    event_type = "court_date"
                    is_court_date = True
                elif any(term in context_text for term in ["signed", "executed", "dated"]):
                    event_type = "document_date"
                elif any(term in context_text for term in ["rent", "payment", "due"]):
                    event_type = "payment_date"
                
                entry = TimelineEntry(
                    event_date=parsed,
                    date_text=date_entity.value,
                    event_type=event_type,
                    title=f"{event_type.replace('_', ' ').title()}: {date_entity.value}",
                    is_deadline=is_deadline,
                    is_court_date=is_court_date,
                    confidence=date_entity.confidence,
                    source_text=context.text[max(0, pos-50):min(len(context.text), pos+100)],
                )
                context.timeline_entries.append(entry)
    
    async def _pass_confidence_calibration(self, context: ReasoningContext) -> Tuple[
        ReasoningChain, ReasoningContext, ConfidenceMetrics
    ]:
        """
        Pass 4: Calibrate confidence scores.
        Final adjustments based on cross-pass agreement.
        """
        chain = ReasoningChain(pass_number=4)
        chain.add_step(
            ReasoningType.STATISTICAL,
            "Beginning confidence calibration",
            {},
            {}
        )
        
        metrics = ConfidenceMetrics()
        
        # Calculate component confidences
        if context.validated_entities:
            entity_confidences = [e.confidence for e in context.validated_entities]
            metrics.entity_extraction_confidence = (
                sum(entity_confidences) / len(entity_confidences) * 100
            )
        
        # Document type confidence
        if context.document_type_votes:
            best_vote = max(context.document_type_votes.values())
            total_votes = sum(context.document_type_votes.values())
            metrics.document_type_confidence = (best_vote / total_votes) * 100 if total_votes > 0 else 0
        
        # Text quality from context
        metrics.text_quality_confidence = context.document_context.ocr_quality
        
        # Relationship confidence
        entities_with_relations = sum(
            1 for e in context.validated_entities if e.related_entities
        )
        if context.validated_entities:
            metrics.relationship_confidence = (
                entities_with_relations / len(context.validated_entities)
            ) * 100
        
        # Temporal confidence
        if context.timeline_entries:
            valid_dates = sum(1 for t in context.timeline_entries if t.event_date)
            metrics.temporal_confidence = (valid_dates / len(context.timeline_entries)) * 100
        
        # Calculate overall score
        weights = {
            "entity": 0.25,
            "doc_type": 0.20,
            "text_quality": 0.20,
            "relationship": 0.15,
            "temporal": 0.10,
            "structural": 0.10,
        }
        
        metrics.overall_score = (
            metrics.entity_extraction_confidence * weights["entity"] +
            metrics.document_type_confidence * weights["doc_type"] +
            metrics.text_quality_confidence * weights["text_quality"] +
            metrics.relationship_confidence * weights["relationship"] +
            metrics.temporal_confidence * weights["temporal"] +
            context.document_context.structural_clarity * weights["structural"]
        )
        
        metrics.level = metrics.classify()
        
        # Identify uncertainty factors
        if metrics.document_type_confidence < 60:
            metrics.ambiguous_elements.append("Document type unclear")
        if not context.validated_entities:
            metrics.missing_information.append("No entities extracted")
        if metrics.text_quality_confidence < 70:
            metrics.missing_information.append("Low text quality (possible OCR issues)")
        
        chain.add_step(
            ReasoningType.STATISTICAL,
            f"Calculated overall confidence: {metrics.overall_score:.1f}%",
            {},
            {"overall": metrics.overall_score, "level": metrics.level.value},
            confidence_impact=0
        )
        
        chain.completed_at = datetime.now()
        chain.conclusion = f"Final confidence: {metrics.overall_score:.1f}% ({metrics.level.value})"
        chain.confidence_delta = metrics.overall_score
        
        context.pass_results.append({
            "pass": 4,
            "confidence": metrics.overall_score,
            "level": metrics.level.value,
        })
        
        return chain, context, metrics
    
    # Validation rules
    def _validate_tenant_address(self, context: ReasoningContext) -> bool:
        """Validate that tenant has associated address"""
        tenants = [e for e in context.validated_entities 
                   if e.entity_type == EntityType.PERSON 
                   and e.attributes.get("role") == PartyRole.TENANT.value]
        addresses = [e for e in context.validated_entities 
                    if e.entity_type == EntityType.ADDRESS]
        return bool(tenants and addresses)
    
    def _validate_amount_context(self, context: ReasoningContext) -> bool:
        """Validate that amounts have proper context"""
        amounts = [e for e in context.validated_entities 
                   if e.entity_type == EntityType.MONEY]
        return all(a.attributes.get("amount_type", "unknown") != "unknown" 
                   for a in amounts)
    
    def _validate_dates(self, context: ReasoningContext) -> bool:
        """Validate that dates are parseable and reasonable"""
        return all(t.event_date is not None for t in context.timeline_entries)
    
    def _validate_distinct_parties(self, context: ReasoningContext) -> bool:
        """Validate that tenant and landlord are distinct"""
        roles = set()
        for entity in context.validated_entities:
            if entity.entity_type == EntityType.PERSON:
                role = entity.attributes.get("role")
                if role:
                    roles.add(role)
        return len(roles) >= 2
    
    def _validate_court_info(self, context: ReasoningContext) -> bool:
        """Validate court information consistency"""
        case_numbers = [e for e in context.validated_entities 
                       if e.entity_type == EntityType.COURT_CASE]
        return len(set(c.value for c in case_numbers)) <= 1  # At most one unique case number
