"""
Tone & Direction Analyzer
==========================

Analyzes the tone (threatening, demanding, etc.) and direction 
(where this is headed) of legal documents.

Courtroom-accurate interpretation of document intent.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum


class DocumentTone(str, Enum):
    """The overall tone/mood of the document"""
    THREATENING = "threatening"      # Implying harm/consequences
    DEMANDING = "demanding"          # Requiring action
    URGENT = "urgent"                # Time-sensitive, immediate
    WARNING = "warning"              # Cautionary, heads-up
    INFORMATIONAL = "informational"  # Just providing info
    FORMAL_LEGAL = "formal_legal"    # Standard legal language
    FRIENDLY = "friendly"            # Cordial, cooperative
    NEUTRAL = "neutral"              # No strong tone
    HOSTILE = "hostile"              # Aggressive, adversarial
    CONCILIATORY = "conciliatory"    # Seeking resolution


class ProcessDirection(str, Enum):
    """Where this document is heading in the legal process"""
    # Pre-litigation
    INITIAL_CONTACT = "initial_contact"           # First communication
    DEMAND = "demand"                              # Demanding action
    FINAL_WARNING = "final_warning"               # Last chance before legal
    
    # Eviction process stages
    EVICTION_START = "eviction_start"             # Beginning eviction
    COURT_FILING_IMMINENT = "court_filing_imminent"  # About to file
    COURT_FILED = "court_filed"                   # Already in court
    HEARING_SCHEDULED = "hearing_scheduled"       # Court date set
    JUDGMENT_ENTERED = "judgment_entered"         # Court decided
    ENFORCEMENT = "enforcement"                   # Sheriff removal
    
    # Resolution paths
    NEGOTIATION = "negotiation"                   # Working out deal
    SETTLEMENT = "settlement"                     # Agreeing to terms
    COMPLIANCE_REQUEST = "compliance_request"    # Asking to fix issue
    
    # Administrative
    ROUTINE = "routine"                           # Normal business
    RECORD_KEEPING = "record_keeping"            # Documentation only
    
    UNKNOWN = "unknown"


class CommunicationFlow(str, Enum):
    """Who is communicating to whom"""
    LANDLORD_TO_TENANT = "landlord_to_tenant"
    TENANT_TO_LANDLORD = "tenant_to_landlord"
    COURT_TO_TENANT = "court_to_tenant"
    COURT_TO_LANDLORD = "court_to_landlord"
    COURT_TO_BOTH = "court_to_both"
    ATTORNEY_TO_TENANT = "attorney_to_tenant"
    ATTORNEY_TO_LANDLORD = "attorney_to_landlord"
    PROPERTY_MANAGER_TO_TENANT = "property_manager_to_tenant"
    TENANT_TO_COURT = "tenant_to_court"
    LANDLORD_TO_COURT = "landlord_to_court"
    SHERIFF_TO_TENANT = "sheriff_to_tenant"
    CITY_TO_TENANT = "city_to_tenant"
    CITY_TO_LANDLORD = "city_to_landlord"
    COLLECTION_AGENCY_TO_TENANT = "collection_agency_to_tenant"
    UNKNOWN = "unknown"


@dataclass
class PartyInfo:
    """Information about a party in the communication"""
    name: str = ""
    role: str = ""  # landlord, tenant, attorney, court, etc.
    organization: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    confidence: float = 0.0


@dataclass
class ToneIndicator:
    """Evidence of a particular tone"""
    phrase: str
    tone: DocumentTone
    weight: float  # How strongly this indicates the tone
    position: Tuple[int, int]
    context: str = ""


@dataclass
class DirectionIndicator:
    """Evidence of process direction"""
    phrase: str
    direction: ProcessDirection
    weight: float
    implies_next_step: str = ""
    days_until_escalation: Optional[int] = None


@dataclass
class ToneAnalysisResult:
    """Complete tone and direction analysis"""
    # Primary classifications
    primary_tone: DocumentTone = DocumentTone.NEUTRAL
    primary_direction: ProcessDirection = ProcessDirection.UNKNOWN
    
    # WHO sent it and WHO received it
    sender: PartyInfo = field(default_factory=PartyInfo)
    recipient: PartyInfo = field(default_factory=PartyInfo)
    communication_flow: CommunicationFlow = CommunicationFlow.UNKNOWN
    
    # Confidence scores (0-100)
    tone_confidence: float = 0.0
    direction_confidence: float = 0.0
    
    # All detected tones with weights
    tone_breakdown: Dict[DocumentTone, float] = field(default_factory=dict)
    
    # Evidence
    tone_indicators: List[ToneIndicator] = field(default_factory=list)
    direction_indicators: List[DirectionIndicator] = field(default_factory=list)
    
    # Interpretation
    plain_english_tone: str = ""
    what_this_means: str = ""
    likely_next_step: str = ""
    recommended_response_tone: str = ""
    
    # Urgency derived from tone + direction
    urgency_score: float = 0.0  # 0-100
    days_to_respond: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            "sender": {
                "name": self.sender.name,
                "role": self.sender.role,
                "organization": self.sender.organization,
                "confidence": self.sender.confidence,
            },
            "recipient": {
                "name": self.recipient.name,
                "role": self.recipient.role,
                "organization": self.recipient.organization,
                "confidence": self.recipient.confidence,
            },
            "communication_flow": self.communication_flow.value,
            "from_to_summary": f"From {self.sender.role or 'Unknown'} → To {self.recipient.role or 'Unknown'}",
            "tone": {
                "primary": self.primary_tone.value,
                "confidence": self.tone_confidence,
                "breakdown": {k.value: v for k, v in self.tone_breakdown.items()},
                "plain_english": self.plain_english_tone,
            },
            "direction": {
                "primary": self.primary_direction.value,
                "confidence": self.direction_confidence,
                "what_this_means": self.what_this_means,
                "likely_next_step": self.likely_next_step,
            },
            "indicators": {
                "tone": [
                    {"phrase": t.phrase, "tone": t.tone.value, "weight": t.weight}
                    for t in self.tone_indicators[:10]
                ],
                "direction": [
                    {"phrase": d.phrase, "direction": d.direction.value, "next_step": d.implies_next_step}
                    for d in self.direction_indicators[:10]
                ],
            },
            "urgency": {
                "score": self.urgency_score,
                "days_to_respond": self.days_to_respond,
            },
            "recommended_response_tone": self.recommended_response_tone,
        }


class ToneAnalyzer:
    """
    Analyzes document tone and direction.
    
    Uses pattern matching against known legal language to determine:
    1. How the document "feels" (threatening, demanding, etc.)
    2. Where in the legal process this sits
    3. What's likely to happen next
    """
    
    def __init__(self):
        self.tone_patterns = self._build_tone_patterns()
        self.direction_patterns = self._build_direction_patterns()
        self.escalation_sequences = self._build_escalation_sequences()
    
    def _build_tone_patterns(self) -> Dict[DocumentTone, List[Dict]]:
        """Build patterns that indicate specific tones"""
        return {
            DocumentTone.THREATENING: [
                {"pattern": r"(?i)will\s+(?:be\s+)?(?:forced|compelled)\s+to", "weight": 0.9},
                {"pattern": r"(?i)legal\s+(?:action|proceedings)\s+will\s+(?:be\s+)?(?:taken|commenced|initiated)", "weight": 0.95},
                {"pattern": r"(?i)you\s+will\s+(?:be\s+)?(?:evicted|removed|sued)", "weight": 0.95},
                {"pattern": r"(?i)sheriff\s+will", "weight": 0.9},
                {"pattern": r"(?i)failure\s+to\s+(?:comply|respond|pay).*(?:will\s+result|shall\s+result)", "weight": 0.85},
                {"pattern": r"(?i)judgment\s+(?:will|shall)\s+be\s+entered\s+against", "weight": 0.9},
                {"pattern": r"(?i)(?:full\s+)?consequences", "weight": 0.7},
                {"pattern": r"(?i)held\s+(?:liable|responsible|accountable)", "weight": 0.8},
                {"pattern": r"(?i)pursue\s+(?:all|any)\s+(?:legal\s+)?(?:remedies|options)", "weight": 0.85},
                {"pattern": r"(?i)without\s+(?:further\s+)?(?:notice|warning)", "weight": 0.8},
            ],
            DocumentTone.DEMANDING: [
                {"pattern": r"(?i)you\s+(?:must|shall|are\s+required\s+to)", "weight": 0.9},
                {"pattern": r"(?i)demand(?:s|ed|ing)?\s+(?:that\s+)?(?:you|payment|immediate)", "weight": 0.95},
                {"pattern": r"(?i)(?:hereby\s+)?(?:demand|require)", "weight": 0.9},
                {"pattern": r"(?i)pay\s+(?:the\s+)?(?:full\s+)?(?:amount|sum|balance)\s+(?:due|owed)", "weight": 0.85},
                {"pattern": r"(?i)(?:immediately|forthwith|at\s+once)", "weight": 0.8},
                {"pattern": r"(?i)comply\s+with", "weight": 0.7},
                {"pattern": r"(?i)required\s+(?:by\s+law\s+)?to", "weight": 0.8},
                {"pattern": r"(?i)(?:cease\s+and\s+desist|stop\s+immediately)", "weight": 0.9},
            ],
            DocumentTone.URGENT: [
                {"pattern": r"(?i)(?:immediate|urgent|emergency|time[\s-]?sensitive)", "weight": 0.95},
                {"pattern": r"(?i)(?:within|before)\s+(?:\d+|twenty-?four|48|72)\s*(?:hours?|days?)", "weight": 0.9},
                {"pattern": r"(?i)deadline", "weight": 0.8},
                {"pattern": r"(?i)(?:as\s+soon\s+as\s+possible|asap|promptly)", "weight": 0.75},
                {"pattern": r"(?i)time\s+is\s+of\s+the\s+essence", "weight": 0.95},
                {"pattern": r"(?i)(?:act|respond|reply)\s+(?:now|immediately|today)", "weight": 0.9},
                {"pattern": r"(?i)(?:final|last)\s+(?:notice|warning|chance|opportunity)", "weight": 0.95},
                {"pattern": r"(?i)expires?\s+(?:on|at|by)", "weight": 0.85},
            ],
            DocumentTone.WARNING: [
                {"pattern": r"(?i)(?:be\s+)?(?:advised|warned|aware)\s+that", "weight": 0.85},
                {"pattern": r"(?i)this\s+(?:is\s+)?(?:a\s+)?(?:notice|warning)", "weight": 0.8},
                {"pattern": r"(?i)please\s+(?:be\s+)?(?:advised|aware)", "weight": 0.75},
                {"pattern": r"(?i)(?:may|might|could)\s+result\s+in", "weight": 0.7},
                {"pattern": r"(?i)(?:risk|danger)\s+of", "weight": 0.75},
                {"pattern": r"(?i)(?:caution|note|important)", "weight": 0.6},
                {"pattern": r"(?i)we\s+(?:may|reserve\s+the\s+right\s+to)", "weight": 0.7},
            ],
            DocumentTone.INFORMATIONAL: [
                {"pattern": r"(?i)(?:for\s+your\s+)?(?:information|records|reference)", "weight": 0.8},
                {"pattern": r"(?i)(?:please\s+)?(?:note|be\s+aware)\s+that", "weight": 0.7},
                {"pattern": r"(?i)this\s+(?:letter|notice)\s+(?:is\s+)?(?:to\s+)?(?:inform|notify|advise)", "weight": 0.85},
                {"pattern": r"(?i)(?:enclosed|attached)\s+(?:please\s+find|is|are)", "weight": 0.75},
                {"pattern": r"(?i)(?:as\s+(?:a\s+)?(?:reminder|follow[\s-]?up))", "weight": 0.7},
                {"pattern": r"(?i)(?:we\s+)?(?:wanted\s+to|would\s+like\s+to)\s+(?:let\s+you\s+know|inform)", "weight": 0.7},
            ],
            DocumentTone.FORMAL_LEGAL: [
                {"pattern": r"(?i)(?:hereby|herein|hereto|thereof|therein|whereas)", "weight": 0.9},
                {"pattern": r"(?i)(?:pursuant\s+to|in\s+accordance\s+with)", "weight": 0.85},
                {"pattern": r"(?i)(?:minn\.?\s*stat\.?|minnesota\s+statutes?)", "weight": 0.9},
                {"pattern": r"(?i)(?:§|section)\s*\d+", "weight": 0.8},
                {"pattern": r"(?i)(?:plaintiff|defendant|petitioner|respondent)", "weight": 0.9},
                {"pattern": r"(?i)(?:court|judge|hearing|trial|judgment)", "weight": 0.85},
                {"pattern": r"(?i)(?:affidavit|stipulation|motion|order)", "weight": 0.9},
                {"pattern": r"(?i)(?:sworn|subscribed|notarized|witnessed)", "weight": 0.85},
            ],
            DocumentTone.HOSTILE: [
                {"pattern": r"(?i)(?:your\s+)?(?:fault|responsibility|problem)", "weight": 0.7},
                {"pattern": r"(?i)(?:refuse|refused|refusing)\s+to", "weight": 0.75},
                {"pattern": r"(?i)(?:unacceptable|intolerable|outrageous)", "weight": 0.8},
                {"pattern": r"(?i)(?:violation|breach|default)", "weight": 0.6},
                {"pattern": r"(?i)(?:bad\s+faith|willful|intentional|deliberate)", "weight": 0.85},
                {"pattern": r"(?i)(?:disregard|ignore|neglect)(?:ed|ing)?", "weight": 0.7},
            ],
            DocumentTone.CONCILIATORY: [
                {"pattern": r"(?i)(?:we\s+)?(?:hope|trust|believe)\s+(?:we\s+can|that|this)", "weight": 0.8},
                {"pattern": r"(?i)(?:work(?:ing)?\s+(?:with\s+you|together|this\s+out))", "weight": 0.85},
                {"pattern": r"(?i)(?:resolve|resolution|settle|settlement)", "weight": 0.75},
                {"pattern": r"(?i)(?:willing\s+to|open\s+to)\s+(?:discuss|negotiate|work)", "weight": 0.9},
                {"pattern": r"(?i)(?:payment\s+plan|arrangement|agreement)", "weight": 0.7},
                {"pattern": r"(?i)(?:please\s+)?(?:contact|call|reach\s+out)", "weight": 0.6},
                {"pattern": r"(?i)(?:avoid|prevent)\s+(?:legal\s+action|court|eviction)", "weight": 0.8},
            ],
            DocumentTone.FRIENDLY: [
                {"pattern": r"(?i)(?:thank\s+you|thanks|appreciate)", "weight": 0.7},
                {"pattern": r"(?i)(?:dear|hello|hi)\s+", "weight": 0.5},
                {"pattern": r"(?i)(?:please\s+)?(?:let\s+(?:me|us)\s+know|feel\s+free)", "weight": 0.7},
                {"pattern": r"(?i)(?:happy\s+to|glad\s+to|pleased\s+to)", "weight": 0.75},
                {"pattern": r"(?i)(?:sincerely|regards|best|warmly)", "weight": 0.5},
            ],
        }
    
    def _build_direction_patterns(self) -> Dict[ProcessDirection, List[Dict]]:
        """Build patterns that indicate process direction"""
        return {
            ProcessDirection.EVICTION_START: [
                {"pattern": r"(?i)(?:14|fourteen)[\s-]?day\s+notice", "weight": 0.95, "next": "Court filing if not resolved", "days": 14},
                {"pattern": r"(?i)notice\s+to\s+(?:quit|vacate)", "weight": 0.9, "next": "Eviction filing", "days": 14},
                {"pattern": r"(?i)(?:first|initial)\s+notice", "weight": 0.8, "next": "Further notices or court", "days": 14},
                {"pattern": r"(?i)pay\s+(?:rent\s+)?or\s+(?:quit|vacate)", "weight": 0.95, "next": "Court filing", "days": 14},
            ],
            ProcessDirection.FINAL_WARNING: [
                {"pattern": r"(?i)(?:final|last)\s+(?:notice|warning|chance)", "weight": 0.95, "next": "Immediate legal action", "days": 3},
                {"pattern": r"(?i)(?:this\s+is\s+)?(?:your\s+)?last\s+opportunity", "weight": 0.9, "next": "Filing with court", "days": 3},
                {"pattern": r"(?i)(?:no\s+)?further\s+(?:notice|warning)s?\s+will\s+be\s+(?:given|sent)", "weight": 0.95, "next": "Court action", "days": 1},
            ],
            ProcessDirection.COURT_FILING_IMMINENT: [
                {"pattern": r"(?i)(?:will|shall)\s+(?:file|commence|initiate)\s+(?:legal|court|eviction)", "weight": 0.9, "next": "Summons", "days": 7},
                {"pattern": r"(?i)(?:intend|plan)\s+to\s+(?:file|sue|take.*court)", "weight": 0.85, "next": "Court filing", "days": 7},
                {"pattern": r"(?i)(?:attorney|lawyer)\s+(?:has\s+been\s+)?(?:instructed|retained)", "weight": 0.8, "next": "Legal action", "days": 14},
            ],
            ProcessDirection.COURT_FILED: [
                {"pattern": r"(?i)case\s+(?:no\.?|number|#)", "weight": 0.95, "next": "Court hearing", "days": 14},
                {"pattern": r"(?i)(?:summons|complaint)\s+(?:is\s+)?(?:attached|enclosed|served)", "weight": 0.95, "next": "Answer deadline", "days": 7},
                {"pattern": r"(?i)you\s+(?:are|have)\s+(?:been\s+)?(?:sued|served)", "weight": 0.95, "next": "Must respond", "days": 7},
                {"pattern": r"(?i)(?:district|housing)\s+court", "weight": 0.8, "next": "Court appearance", "days": 14},
            ],
            ProcessDirection.HEARING_SCHEDULED: [
                {"pattern": r"(?i)(?:hearing|trial|court\s+date)\s+(?:is\s+)?(?:set|scheduled)", "weight": 0.95, "next": "Appear in court", "days": 7},
                {"pattern": r"(?i)(?:appear|attendance)\s+(?:is\s+)?(?:required|mandatory)", "weight": 0.9, "next": "Court appearance", "days": 7},
                {"pattern": r"(?i)(?:courtroom|location|address).*(?:date|time)", "weight": 0.8, "next": "Hearing", "days": 14},
            ],
            ProcessDirection.JUDGMENT_ENTERED: [
                {"pattern": r"(?i)judgment\s+(?:has\s+been\s+)?(?:entered|issued|granted)", "weight": 0.95, "next": "Writ of recovery", "days": 7},
                {"pattern": r"(?i)(?:court|judge)\s+(?:has\s+)?(?:ruled|ordered|decided)", "weight": 0.9, "next": "Compliance required", "days": 7},
                {"pattern": r"(?i)(?:default|summary)\s+judgment", "weight": 0.95, "next": "Enforcement", "days": 7},
            ],
            ProcessDirection.ENFORCEMENT: [
                {"pattern": r"(?i)writ\s+of\s+(?:recovery|restitution)", "weight": 0.95, "next": "Sheriff removal", "days": 3},
                {"pattern": r"(?i)sheriff\s+(?:will|shall|is\s+authorized)", "weight": 0.95, "next": "Physical removal", "days": 3},
                {"pattern": r"(?i)(?:remove|removal|evict)\s+(?:you|tenant|defendant)", "weight": 0.9, "next": "Lockout", "days": 3},
                {"pattern": r"(?i)(?:vacate|leave)\s+(?:the\s+)?(?:premises|property)\s+(?:by|before)", "weight": 0.9, "next": "Removal", "days": 3},
            ],
            ProcessDirection.NEGOTIATION: [
                {"pattern": r"(?i)(?:willing\s+to|open\s+to)\s+(?:discuss|negotiate|work)", "weight": 0.85, "next": "Agreement possible", "days": None},
                {"pattern": r"(?i)(?:payment\s+plan|payment\s+arrangement|installment)", "weight": 0.9, "next": "Structured payment", "days": None},
                {"pattern": r"(?i)(?:contact|call|reach\s+out).*(?:discuss|arrange|work\s+out)", "weight": 0.8, "next": "Conversation", "days": None},
            ],
            ProcessDirection.SETTLEMENT: [
                {"pattern": r"(?i)(?:settlement|stipulation)\s+(?:agreement|offer)", "weight": 0.95, "next": "Sign agreement", "days": None},
                {"pattern": r"(?i)(?:agreed|agree)\s+to\s+(?:the\s+following|terms)", "weight": 0.9, "next": "Compliance", "days": None},
                {"pattern": r"(?i)(?:in\s+exchange\s+for|condition(?:al|ed)\s+(?:on|upon))", "weight": 0.85, "next": "Meet conditions", "days": None},
            ],
            ProcessDirection.ROUTINE: [
                {"pattern": r"(?i)(?:annual|monthly|regular)\s+(?:notice|inspection|statement)", "weight": 0.8, "next": "Normal business", "days": None},
                {"pattern": r"(?i)(?:renewal|renew(?:ing)?)\s+(?:your\s+)?lease", "weight": 0.85, "next": "Sign renewal", "days": 30},
                {"pattern": r"(?i)(?:thank\s+you\s+for\s+your\s+payment|received\s+your\s+(?:rent|payment))", "weight": 0.9, "next": "None needed", "days": None},
            ],
        }
    
    def _build_escalation_sequences(self) -> Dict[ProcessDirection, Dict]:
        """Build escalation sequence knowledge"""
        return {
            ProcessDirection.INITIAL_CONTACT: {
                "next": ProcessDirection.DEMAND,
                "description": "First contact about an issue",
            },
            ProcessDirection.DEMAND: {
                "next": ProcessDirection.FINAL_WARNING,
                "description": "Formal demand for action",
            },
            ProcessDirection.FINAL_WARNING: {
                "next": ProcessDirection.EVICTION_START,
                "description": "Last chance before legal action",
            },
            ProcessDirection.EVICTION_START: {
                "next": ProcessDirection.COURT_FILING_IMMINENT,
                "description": "Eviction process beginning",
            },
            ProcessDirection.COURT_FILING_IMMINENT: {
                "next": ProcessDirection.COURT_FILED,
                "description": "About to file in court",
            },
            ProcessDirection.COURT_FILED: {
                "next": ProcessDirection.HEARING_SCHEDULED,
                "description": "Case filed, awaiting hearing",
            },
            ProcessDirection.HEARING_SCHEDULED: {
                "next": ProcessDirection.JUDGMENT_ENTERED,
                "description": "Court date set",
            },
            ProcessDirection.JUDGMENT_ENTERED: {
                "next": ProcessDirection.ENFORCEMENT,
                "description": "Court has decided",
            },
            ProcessDirection.ENFORCEMENT: {
                "next": None,
                "description": "Final enforcement stage",
            },
        }
    
    def analyze(self, text: str, document_type: Optional[str] = None) -> ToneAnalysisResult:
        """
        Perform full tone and direction analysis.
        
        Args:
            text: Document text to analyze
            document_type: Optional document type hint
            
        Returns:
            ToneAnalysisResult with complete analysis
        """
        result = ToneAnalysisResult()
        
        # Extract sender and recipient (WHO sent this, WHO received it)
        sender, recipient, comm_flow = self._extract_parties(text)
        result.sender = sender
        result.recipient = recipient
        result.communication_flow = comm_flow
        
        # Analyze tone
        tone_scores, tone_indicators = self._analyze_tone(text)
        result.tone_breakdown = tone_scores
        result.tone_indicators = tone_indicators
        
        if tone_scores:
            result.primary_tone = max(tone_scores.keys(), key=lambda k: tone_scores[k])
            result.tone_confidence = min(100, tone_scores[result.primary_tone] * 100)
        
        # Analyze direction
        direction_scores, direction_indicators = self._analyze_direction(text)
        result.direction_indicators = direction_indicators
        
        if direction_scores:
            result.primary_direction = max(direction_scores.keys(), key=lambda k: direction_scores[k])
            result.direction_confidence = min(100, direction_scores[result.primary_direction] * 100)
        
        # Get likely next step
        if direction_indicators:
            best_indicator = max(direction_indicators, key=lambda d: d.weight)
            result.likely_next_step = best_indicator.implies_next_step
            result.days_to_respond = best_indicator.days_until_escalation
        
        # Generate plain English interpretations
        result.plain_english_tone = self._get_tone_description(result.primary_tone)
        result.what_this_means = self._get_direction_meaning(result.primary_direction)
        result.recommended_response_tone = self._get_recommended_response(result.primary_tone, result.primary_direction)
        
        # Calculate urgency
        result.urgency_score = self._calculate_urgency(
            result.primary_tone, 
            result.primary_direction,
            result.days_to_respond
        )
        
        return result
    
    def _analyze_tone(self, text: str) -> Tuple[Dict[DocumentTone, float], List[ToneIndicator]]:
        """Analyze document tone"""
        scores = {tone: 0.0 for tone in DocumentTone}
        indicators = []
        
        for tone, patterns in self.tone_patterns.items():
            for pattern_info in patterns:
                matches = list(re.finditer(pattern_info["pattern"], text))
                for match in matches:
                    scores[tone] += pattern_info["weight"]
                    
                    # Get surrounding context
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    context = text[start:end].strip()
                    
                    indicators.append(ToneIndicator(
                        phrase=match.group(),
                        tone=tone,
                        weight=pattern_info["weight"],
                        position=(match.start(), match.end()),
                        context=context,
                    ))
        
        # Normalize scores
        max_score = max(scores.values()) if scores.values() else 1.0
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}
        
        # Filter out zero scores
        scores = {k: v for k, v in scores.items() if v > 0}
        
        return scores, indicators
    
    def _analyze_direction(self, text: str) -> Tuple[Dict[ProcessDirection, float], List[DirectionIndicator]]:
        """Analyze process direction"""
        scores = {direction: 0.0 for direction in ProcessDirection}
        indicators = []
        
        for direction, patterns in self.direction_patterns.items():
            for pattern_info in patterns:
                matches = list(re.finditer(pattern_info["pattern"], text))
                for match in matches:
                    scores[direction] += pattern_info["weight"]
                    
                    indicators.append(DirectionIndicator(
                        phrase=match.group(),
                        direction=direction,
                        weight=pattern_info["weight"],
                        implies_next_step=pattern_info.get("next", ""),
                        days_until_escalation=pattern_info.get("days"),
                    ))
        
        # Normalize scores
        max_score = max(scores.values()) if scores.values() else 1.0
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}
        
        # Filter out zero scores
        scores = {k: v for k, v in scores.items() if v > 0}
        
        return scores, indicators
    
    def _get_tone_description(self, tone: DocumentTone) -> str:
        """Get plain English description of tone"""
        descriptions = {
            DocumentTone.THREATENING: "This document is threatening consequences if you don't act. The sender means business.",
            DocumentTone.DEMANDING: "This document is demanding specific action from you. It's not a request - it's a requirement.",
            DocumentTone.URGENT: "This is time-sensitive! The sender wants immediate action and there are deadlines involved.",
            DocumentTone.WARNING: "This is a heads-up about potential consequences. It's giving you a chance to act before things escalate.",
            DocumentTone.INFORMATIONAL: "This is mostly providing information. No immediate action may be required, but review carefully.",
            DocumentTone.FORMAL_LEGAL: "This is formal legal language. Take it seriously - it may be part of an official legal process.",
            DocumentTone.FRIENDLY: "This has a cooperative tone. The sender seems willing to work with you.",
            DocumentTone.NEUTRAL: "This is neutral in tone - standard business communication.",
            DocumentTone.HOSTILE: "This document has a hostile or aggressive tone. The sender seems adversarial.",
            DocumentTone.CONCILIATORY: "This document seems to be seeking resolution. There may be room for negotiation.",
        }
        return descriptions.get(tone, "Unable to determine tone.")
    
    def _get_direction_meaning(self, direction: ProcessDirection) -> str:
        """Get plain English meaning of direction"""
        meanings = {
            ProcessDirection.INITIAL_CONTACT: "This is the first communication about this issue. You have time to respond.",
            ProcessDirection.DEMAND: "This is a formal demand for action. Take it seriously but you likely have time.",
            ProcessDirection.FINAL_WARNING: "THIS IS YOUR LAST CHANCE. The next step is legal action.",
            ProcessDirection.EVICTION_START: "The eviction process is starting. You typically have 14 days to respond or cure the issue.",
            ProcessDirection.COURT_FILING_IMMINENT: "They're about to file in court. Act now to avoid having a court case.",
            ProcessDirection.COURT_FILED: "A court case has been filed. You MUST respond or you'll lose by default.",
            ProcessDirection.HEARING_SCHEDULED: "A court date is set. You MUST appear or you'll lose automatically.",
            ProcessDirection.JUDGMENT_ENTERED: "The court has ruled. You may have limited time before enforcement.",
            ProcessDirection.ENFORCEMENT: "CRITICAL: Sheriff enforcement is imminent. Seek help immediately.",
            ProcessDirection.NEGOTIATION: "There's room to negotiate. Contact the other party to work something out.",
            ProcessDirection.SETTLEMENT: "A settlement is being offered. Review carefully - this could end the dispute.",
            ProcessDirection.COMPLIANCE_REQUEST: "You're being asked to fix something. Complying may resolve the issue.",
            ProcessDirection.ROUTINE: "This appears to be routine business. No urgent action likely needed.",
            ProcessDirection.RECORD_KEEPING: "This seems to be for documentation purposes.",
            ProcessDirection.UNKNOWN: "Unable to determine where this is heading.",
        }
        return meanings.get(direction, "Unable to determine process direction.")
    
    def _get_recommended_response(self, tone: DocumentTone, direction: ProcessDirection) -> str:
        """Get recommended response approach"""
        # Critical situations
        if direction in [ProcessDirection.ENFORCEMENT, ProcessDirection.JUDGMENT_ENTERED]:
            return "URGENT: Seek legal help immediately. Contact a tenant rights organization or legal aid."
        
        if direction in [ProcessDirection.COURT_FILED, ProcessDirection.HEARING_SCHEDULED]:
            return "Respond promptly and professionally. Consider seeking legal assistance. Document everything."
        
        if direction == ProcessDirection.FINAL_WARNING:
            return "Act now. Respond in writing, keep copies. Try to resolve the issue or seek help."
        
        # Based on tone
        if tone == DocumentTone.THREATENING:
            return "Stay calm. Don't respond emotionally. Document the threat and respond factually."
        
        if tone == DocumentTone.DEMANDING:
            return "Review the demands carefully. Respond in writing within any stated deadline."
        
        if tone == DocumentTone.CONCILIATORY:
            return "This is an opportunity. Respond positively and try to work out an agreement."
        
        if tone == DocumentTone.HOSTILE:
            return "Don't escalate. Respond professionally and stick to facts. Keep copies of everything."
        
        return "Review carefully and respond in writing. Keep copies of all communications."
    
    def _extract_parties(self, text: str) -> Tuple[PartyInfo, PartyInfo, CommunicationFlow]:
        """
        Extract WHO sent this document and WHO received it.
        
        Returns:
            (sender, recipient, communication_flow)
        """
        sender = PartyInfo()
        recipient = PartyInfo()
        flow = CommunicationFlow.UNKNOWN
        
        text_lower = text.lower()
        
        # ========================================
        # SENDER DETECTION PATTERNS
        # ========================================
        
        # Court documents
        court_patterns = [
            r"(?i)state\s+of\s+minnesota.*?district\s+court",
            r"(?i)(?:hennepin|ramsey|dakota|anoka|washington|olmsted|st\.?\s*louis|stearns|scott|carver)\s+county\s+(?:district\s+)?court",
            r"(?i)court\s+administrator",
            r"(?i)(?:the\s+)?honorable\s+(?:judge\s+)?[\w\s]+",
            r"(?i)in\s+the\s+matter\s+of",
            r"(?i)case\s+(?:no\.?|number)[:\s]*\d+",
        ]
        
        # Sheriff/law enforcement
        sheriff_patterns = [
            r"(?i)(?:hennepin|ramsey|dakota)\s+county\s+sheriff",
            r"(?i)office\s+of\s+the\s+sheriff",
            r"(?i)writ\s+of\s+(?:recovery|restitution)",
            r"(?i)served\s+by\s+(?:deputy|officer)",
        ]
        
        # Landlord patterns
        landlord_patterns = [
            r"(?i)(?:your\s+)?landlord",
            r"(?i)property\s+(?:owner|management|manager)",
            r"(?i)(?:from|signed)[:\s]*(?:the\s+)?(?:management|landlord|owner)",
            r"(?i)(?:rental|property)\s+management",
            r"(?i)(?:abc|xyz|\w+)\s+(?:properties|management|realty)",
        ]
        
        # Attorney patterns
        attorney_patterns = [
            r"(?i)(?:law\s+)?(?:office|firm)\s+of",
            r"(?i)attorney\s+(?:at\s+law|for\s+(?:plaintiff|landlord))",
            r"(?i)counsel\s+for\s+(?:plaintiff|landlord|defendant)",
            r"(?i)\besq\.?\b",
            r"(?i)(?:from|signed)[:\s]*[\w\s]+,?\s*(?:attorney|lawyer|counsel)",
        ]
        
        # City/municipality patterns
        city_patterns = [
            r"(?i)city\s+of\s+(?:minneapolis|st\.?\s*paul|duluth|rochester|bloomington|\w+)",
            r"(?i)(?:housing|building)\s+(?:inspection|code\s+enforcement)",
            r"(?i)(?:code|zoning)\s+(?:enforcement|compliance)",
            r"(?i)municipal\s+(?:court|office)",
        ]
        
        # Collection agency patterns
        collection_patterns = [
            r"(?i)collection\s+(?:agency|services|bureau)",
            r"(?i)debt\s+collect(?:or|ion)",
            r"(?i)(?:this|we)\s+are?\s+(?:a\s+)?debt\s+collector",
        ]
        
        # ========================================
        # RECIPIENT DETECTION PATTERNS
        # ========================================
        
        # "TO:" header extraction
        to_pattern = r"(?i)(?:^|\n)\s*TO[:\s]+([^\n]+)"
        to_match = re.search(to_pattern, text)
        
        # "Dear X" extraction
        dear_pattern = r"(?i)dear\s+([^,:\n]+)"
        dear_match = re.search(dear_pattern, text)
        
        # Tenant indicators
        tenant_indicators = [
            "tenant", "renter", "lessee", "occupant", "resident"
        ]
        
        # Landlord as recipient indicators
        landlord_recipient_indicators = [
            "landlord", "lessor", "property owner", "management"
        ]
        
        # ========================================
        # DETERMINE SENDER
        # ========================================
        
        # Check for court
        for pattern in court_patterns:
            if re.search(pattern, text):
                sender.role = "Court"
                sender.organization = self._extract_court_name(text)
                sender.confidence = 0.9
                break
        
        # Check for sheriff
        if not sender.role:
            for pattern in sheriff_patterns:
                if re.search(pattern, text):
                    sender.role = "Sheriff"
                    sender.organization = self._extract_sheriff_office(text)
                    sender.confidence = 0.85
                    break
        
        # Check for attorney
        if not sender.role:
            for pattern in attorney_patterns:
                if re.search(pattern, text):
                    sender.role = "Attorney"
                    sender.name = self._extract_attorney_name(text)
                    sender.confidence = 0.85
                    break
        
        # Check for city
        if not sender.role:
            for pattern in city_patterns:
                if re.search(pattern, text):
                    sender.role = "City/Municipality"
                    sender.organization = self._extract_city_name(text)
                    sender.confidence = 0.85
                    break
        
        # Check for collection agency
        if not sender.role:
            for pattern in collection_patterns:
                if re.search(pattern, text):
                    sender.role = "Collection Agency"
                    sender.confidence = 0.8
                    break
        
        # Check for landlord/property manager
        if not sender.role:
            for pattern in landlord_patterns:
                if re.search(pattern, text):
                    sender.role = "Landlord"
                    sender.name = self._extract_landlord_name(text)
                    sender.confidence = 0.75
                    break
        
        # Check for tenant as sender (complaint, repair request, etc.)
        if not sender.role:
            tenant_sender_phrases = [
                r"(?i)i\s+(?:am|have\s+been)\s+(?:a\s+)?tenant",
                r"(?i)as\s+(?:your|the)\s+tenant",
                r"(?i)i\s+(?:am\s+)?writing\s+(?:to\s+)?(?:request|complain|notify)",
                r"(?i)my\s+rent",
                r"(?i)my\s+(?:apartment|unit|lease)",
            ]
            for pattern in tenant_sender_phrases:
                if re.search(pattern, text):
                    sender.role = "Tenant"
                    sender.confidence = 0.7
                    break
        
        # ========================================
        # DETERMINE RECIPIENT
        # ========================================
        
        # Extract from "TO:" line
        if to_match:
            recipient.name = to_match.group(1).strip()
            recipient.confidence = 0.9
        elif dear_match:
            recipient.name = dear_match.group(1).strip()
            recipient.confidence = 0.8
        
        # Determine recipient role
        if recipient.name:
            name_lower = recipient.name.lower()
            if any(ind in name_lower for ind in tenant_indicators):
                recipient.role = "Tenant"
            elif any(ind in name_lower for ind in landlord_recipient_indicators):
                recipient.role = "Landlord"
            else:
                # Guess based on sender
                if sender.role in ["Landlord", "Attorney", "Court", "Sheriff", "City/Municipality", "Collection Agency"]:
                    recipient.role = "Tenant"
                elif sender.role == "Tenant":
                    recipient.role = "Landlord"
        else:
            # No explicit recipient - infer from context
            if sender.role in ["Landlord", "Attorney", "Sheriff", "Collection Agency"]:
                recipient.role = "Tenant"
                recipient.confidence = 0.6
            elif sender.role == "Tenant":
                recipient.role = "Landlord"
                recipient.confidence = 0.6
            elif sender.role == "Court":
                # Court could be to either party
                if "defendant" in text_lower or "tenant" in text_lower:
                    recipient.role = "Tenant"
                    recipient.confidence = 0.7
                elif "plaintiff" in text_lower or "landlord" in text_lower:
                    recipient.role = "Both Parties"
                    recipient.confidence = 0.6
        
        # ========================================
        # DETERMINE COMMUNICATION FLOW
        # ========================================
        
        flow_map = {
            ("Landlord", "Tenant"): CommunicationFlow.LANDLORD_TO_TENANT,
            ("Tenant", "Landlord"): CommunicationFlow.TENANT_TO_LANDLORD,
            ("Court", "Tenant"): CommunicationFlow.COURT_TO_TENANT,
            ("Court", "Landlord"): CommunicationFlow.COURT_TO_LANDLORD,
            ("Court", "Both Parties"): CommunicationFlow.COURT_TO_BOTH,
            ("Attorney", "Tenant"): CommunicationFlow.ATTORNEY_TO_TENANT,
            ("Attorney", "Landlord"): CommunicationFlow.ATTORNEY_TO_LANDLORD,
            ("Sheriff", "Tenant"): CommunicationFlow.SHERIFF_TO_TENANT,
            ("City/Municipality", "Tenant"): CommunicationFlow.CITY_TO_TENANT,
            ("City/Municipality", "Landlord"): CommunicationFlow.CITY_TO_LANDLORD,
            ("Collection Agency", "Tenant"): CommunicationFlow.COLLECTION_AGENCY_TO_TENANT,
            ("Property Manager", "Tenant"): CommunicationFlow.PROPERTY_MANAGER_TO_TENANT,
        }
        
        flow = flow_map.get((sender.role, recipient.role), CommunicationFlow.UNKNOWN)
        
        return sender, recipient, flow
    
    def _extract_court_name(self, text: str) -> str:
        """Extract court name from text"""
        patterns = [
            r"(?i)((?:hennepin|ramsey|dakota|anoka|washington|olmsted|st\.?\s*louis|stearns|scott|carver)\s+county\s+(?:district\s+)?court)",
            r"(?i)(minnesota\s+(?:district|housing)\s+court)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip().title()
        return "District Court"
    
    def _extract_sheriff_office(self, text: str) -> str:
        """Extract sheriff office from text"""
        pattern = r"(?i)((?:hennepin|ramsey|dakota|anoka|washington)\s+county\s+sheriff)"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip().title()
        return "County Sheriff"
    
    def _extract_attorney_name(self, text: str) -> str:
        """Extract attorney name from text"""
        patterns = [
            r"(?i)(?:law\s+office\s+of|firm\s+of)\s+([\w\s&,]+?)(?:\n|,|\.|LLC|PA|PLLC)",
            r"(?i)([\w\s]+),?\s*(?:esq\.?|attorney)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                if len(name) > 3 and len(name) < 60:
                    return name.title()
        return ""
    
    def _extract_city_name(self, text: str) -> str:
        """Extract city/municipality name"""
        pattern = r"(?i)city\s+of\s+(minneapolis|st\.?\s*paul|duluth|rochester|bloomington|\w+)"
        match = re.search(pattern, text)
        if match:
            return f"City of {match.group(1).strip().title()}"
        return "City/Municipality"
    
    def _extract_landlord_name(self, text: str) -> str:
        """Extract landlord/property manager name"""
        patterns = [
            r"(?i)(?:from|signed)[:\s]*([\w\s]+?)(?:\n|,|landlord|owner|manager)",
            r"(?i)([\w\s]+)\s+(?:properties|management|realty)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                if len(name) > 2 and len(name) < 50:
                    return name.title()
        return ""
    
    def _calculate_urgency(self, tone: DocumentTone, direction: ProcessDirection, 
                          days_to_respond: Optional[int]) -> float:
        """Calculate urgency score (0-100)"""
        score = 0.0
        
        # Direction-based urgency
        direction_urgency = {
            ProcessDirection.ENFORCEMENT: 100,
            ProcessDirection.JUDGMENT_ENTERED: 90,
            ProcessDirection.HEARING_SCHEDULED: 80,
            ProcessDirection.COURT_FILED: 75,
            ProcessDirection.FINAL_WARNING: 70,
            ProcessDirection.COURT_FILING_IMMINENT: 65,
            ProcessDirection.EVICTION_START: 60,
            ProcessDirection.DEMAND: 40,
            ProcessDirection.INITIAL_CONTACT: 20,
            ProcessDirection.ROUTINE: 10,
        }
        score = direction_urgency.get(direction, 30)
        
        # Tone modifier
        tone_modifier = {
            DocumentTone.THREATENING: 1.2,
            DocumentTone.URGENT: 1.3,
            DocumentTone.HOSTILE: 1.1,
            DocumentTone.DEMANDING: 1.1,
            DocumentTone.WARNING: 1.0,
            DocumentTone.CONCILIATORY: 0.8,
            DocumentTone.FRIENDLY: 0.7,
            DocumentTone.INFORMATIONAL: 0.6,
        }
        score *= tone_modifier.get(tone, 1.0)
        
        # Days modifier
        if days_to_respond is not None:
            if days_to_respond <= 3:
                score *= 1.3
            elif days_to_respond <= 7:
                score *= 1.1
        
        return min(100, score)


# Singleton
_analyzer = None

def get_tone_analyzer() -> ToneAnalyzer:
    """Get or create singleton analyzer"""
    global _analyzer
    if _analyzer is None:
        _analyzer = ToneAnalyzer()
    return _analyzer
