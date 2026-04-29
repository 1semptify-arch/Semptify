"""
Minnesota Legal Document Dictionary
====================================

Rock-solid phrase definitions, legal terms, and pattern recognition
for courtroom-accurate document analysis.

This is the "training data" - exact patterns and phrases the system
must recognize with 100% accuracy.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum
import re


class LegalPhraseCategory(str, Enum):
    """Categories of legal phrases"""
    # Document Headers/Titles
    DOCUMENT_HEADER = "document_header"
    
    # Legal Demands
    DEMAND = "demand"
    
    # Legal Notices
    NOTICE_TYPE = "notice_type"
    
    # Timeframes
    DEADLINE = "deadline"
    
    # Legal Consequences
    CONSEQUENCE = "consequence"
    
    # Rights/Protections
    RIGHTS = "rights"
    
    # Actions/Remedies
    ACTION = "action"
    
    # Court Terms
    COURT = "court"
    
    # Property Terms
    PROPERTY = "property"
    
    # Financial Terms
    FINANCIAL = "financial"


@dataclass
class LegalPhrase:
    """A recognized legal phrase with metadata"""
    canonical: str  # The standard form
    variations: List[str]  # All accepted variations
    category: LegalPhraseCategory
    severity: str  # critical, high, medium, low
    statute: Optional[str] = None  # Minnesota statute reference
    meaning: str = ""  # Plain English meaning
    response_deadline: Optional[int] = None  # Days to respond
    synonyms: List[str] = field(default_factory=list)


class MinnesotaLegalDictionary:
    """
    Comprehensive dictionary of Minnesota tenant law terms and phrases.
    
    This provides word-for-word accuracy for legal document recognition.
    """
    
    def __init__(self):
        self.phrases = self._build_phrase_dictionary()
        self.document_types = self._build_document_type_patterns()
        self.statutory_references = self._build_statute_patterns()
        self.ocr_corrections = self._build_ocr_corrections()
        self.critical_numbers = self._build_critical_numbers()
        
        # Build lookup indices
        self._phrase_index = self._build_phrase_index()
        self._pattern_cache = {}
    
    def _build_phrase_dictionary(self) -> Dict[str, LegalPhrase]:
        """Build comprehensive phrase dictionary"""
        phrases = {}
        
        # ============================================================
        # EVICTION NOTICE TYPES - Critical recognition
        # ============================================================
        
        phrases["14_day_notice"] = LegalPhrase(
            canonical="14-DAY NOTICE TO PAY RENT OR QUIT",
            variations=[
                "14 DAY NOTICE TO PAY RENT OR QUIT",
                "14-DAY NOTICE TO PAY RENT OR VACATE",
                "FOURTEEN (14) DAY NOTICE TO PAY RENT OR QUIT",
                "FOURTEEN DAY NOTICE TO PAY RENT OR QUIT",
                "14 DAY NOTICE",
                "NOTICE TO PAY RENT OR QUIT (14 DAY)",
                "14-DAY NOTICE",
            ],
            category=LegalPhraseCategory.NOTICE_TYPE,
            severity="critical",
            statute="Minn. Stat. § 504B.135",
            meaning="Tenant has 14 days to pay overdue rent or move out before eviction can be filed",
            response_deadline=14,
        )
        
        phrases["notice_to_quit"] = LegalPhrase(
            canonical="NOTICE TO QUIT",
            variations=[
                "NOTICE TO VACATE",
                "NOTICE TO QUIT PREMISES",
                "NOTICE TO VACATE PREMISES",
                "NOTICE OF TERMINATION OF TENANCY",
                "TERMINATION NOTICE",
            ],
            category=LegalPhraseCategory.NOTICE_TYPE,
            severity="critical",
            statute="Minn. Stat. § 504B.135",
            meaning="Formal notice that tenancy is being terminated",
            response_deadline=14,
        )
        
        phrases["emergency_eviction"] = LegalPhrase(
            canonical="EMERGENCY EVICTION NOTICE",
            variations=[
                "IMMEDIATE EVICTION",
                "EXPEDITED EVICTION",
                "24 HOUR NOTICE",
                "24-HOUR NOTICE",
                "EMERGENCY NOTICE",
            ],
            category=LegalPhraseCategory.NOTICE_TYPE,
            severity="critical",
            statute="Minn. Stat. § 504B.321",
            meaning="Emergency eviction for serious lease violations - requires court approval",
            response_deadline=1,
        )
        
        phrases["non_renewal"] = LegalPhrase(
            canonical="NOTICE OF NON-RENEWAL",
            variations=[
                "NON-RENEWAL NOTICE",
                "NOTICE OF LEASE NON-RENEWAL",
                "NOTICE NOT TO RENEW",
                "LEASE WILL NOT BE RENEWED",
            ],
            category=LegalPhraseCategory.NOTICE_TYPE,
            severity="high",
            statute="Minn. Stat. § 504B.145",
            meaning="Lease will not be renewed at end of term",
            response_deadline=30,
        )
        
        # ============================================================
        # COURT DOCUMENTS - Summons, Complaints, etc.
        # ============================================================
        
        phrases["summons"] = LegalPhrase(
            canonical="SUMMONS",
            variations=[
                "SUMMONS AND COMPLAINT",
                "EVICTION SUMMONS",
                "HOUSING COURT SUMMONS",
                "DISTRICT COURT SUMMONS",
            ],
            category=LegalPhraseCategory.COURT,
            severity="critical",
            statute="Minn. Stat. § 504B.321",
            meaning="Official court document requiring you to appear - MUST RESPOND",
            response_deadline=7,
        )
        
        phrases["complaint"] = LegalPhrase(
            canonical="COMPLAINT FOR EVICTION",
            variations=[
                "COMPLAINT",
                "EVICTION COMPLAINT",
                "COMPLAINT FOR RECOVERY OF PREMISES",
                "UNLAWFUL DETAINER COMPLAINT",
            ],
            category=LegalPhraseCategory.COURT,
            severity="critical",
            statute="Minn. Stat. § 504B.321",
            meaning="Legal filing to start eviction - landlord's formal complaint",
            response_deadline=7,
        )
        
        phrases["writ_recovery"] = LegalPhrase(
            canonical="WRIT OF RECOVERY OF PREMISES",
            variations=[
                "WRIT OF RECOVERY",
                "WRIT OF RESTITUTION",
                "EVICTION ORDER",
                "ORDER FOR RECOVERY",
            ],
            category=LegalPhraseCategory.COURT,
            severity="critical",
            statute="Minn. Stat. § 504B.365",
            meaning="Court order authorizing sheriff to physically remove tenant",
            response_deadline=0,
        )
        
        phrases["answer_form"] = LegalPhrase(
            canonical="ANSWER TO EVICTION COMPLAINT",
            variations=[
                "ANSWER",
                "DEFENDANT'S ANSWER",
                "RESPONSE TO COMPLAINT",
                "ANSWER AND COUNTERCLAIM",
            ],
            category=LegalPhraseCategory.COURT,
            severity="high",
            meaning="Tenant's formal response to eviction complaint",
            response_deadline=7,
        )
        
        # ============================================================
        # LEGAL DEMANDS - What landlord is asking
        # ============================================================
        
        phrases["pay_or_quit"] = LegalPhrase(
            canonical="PAY RENT OR QUIT",
            variations=[
                "PAY RENT OR VACATE",
                "PAY OR QUIT",
                "PAY OR VACATE",
                "PAY THE AMOUNT DUE OR VACATE",
                "CURE OR QUIT",
            ],
            category=LegalPhraseCategory.DEMAND,
            severity="critical",
            meaning="Must pay owed rent OR move out by deadline",
        )
        
        phrases["cure_violation"] = LegalPhrase(
            canonical="CURE THE VIOLATION",
            variations=[
                "CORRECT THE VIOLATION",
                "REMEDY THE VIOLATION",
                "CURE THE BREACH",
                "REMEDY THE BREACH",
            ],
            category=LegalPhraseCategory.DEMAND,
            severity="high",
            meaning="Must fix the lease violation by deadline",
        )
        
        phrases["vacate_premises"] = LegalPhrase(
            canonical="VACATE THE PREMISES",
            variations=[
                "VACATE",
                "MOVE OUT",
                "SURRENDER THE PREMISES",
                "LEAVE THE PROPERTY",
                "QUIT THE PREMISES",
            ],
            category=LegalPhraseCategory.DEMAND,
            severity="critical",
            meaning="Must physically move out of the property",
        )
        
        # ============================================================
        # CONSEQUENCES - What happens if you don't respond
        # ============================================================
        
        phrases["legal_action"] = LegalPhrase(
            canonical="LEGAL ACTION WILL BE TAKEN",
            variations=[
                "LEGAL PROCEEDINGS WILL COMMENCE",
                "EVICTION PROCEEDINGS WILL BEGIN",
                "LAWSUIT WILL BE FILED",
                "COURT ACTION WILL BE TAKEN",
                "WE WILL COMMENCE LEGAL ACTION",
            ],
            category=LegalPhraseCategory.CONSEQUENCE,
            severity="high",
            meaning="Landlord will file in court if you don't comply",
        )
        
        phrases["default_judgment"] = LegalPhrase(
            canonical="DEFAULT JUDGMENT",
            variations=[
                "JUDGMENT BY DEFAULT",
                "JUDGMENT WILL BE ENTERED",
                "LOSE THIS CASE BY DEFAULT",
            ],
            category=LegalPhraseCategory.CONSEQUENCE,
            severity="critical",
            statute="Minn. Stat. § 504B.345",
            meaning="If you don't respond/appear, you automatically lose",
        )
        
        # ============================================================
        # TENANT RIGHTS - What protects you
        # ============================================================
        
        phrases["right_to_hearing"] = LegalPhrase(
            canonical="RIGHT TO A HEARING",
            variations=[
                "ENTITLED TO A HEARING",
                "REQUEST A HEARING",
                "APPEAR AT THE HEARING",
                "YOUR RIGHT TO BE HEARD",
            ],
            category=LegalPhraseCategory.RIGHTS,
            severity="high",
            statute="Minn. Stat. § 504B.335",
            meaning="You have the right to appear in court and tell your side",
        )
        
        phrases["right_to_attorney"] = LegalPhrase(
            canonical="RIGHT TO AN ATTORNEY",
            variations=[
                "RIGHT TO COUNSEL",
                "SEEK LEGAL ADVICE",
                "CONSULT AN ATTORNEY",
                "LEGAL REPRESENTATION",
            ],
            category=LegalPhraseCategory.RIGHTS,
            severity="high",
            meaning="You can have a lawyer represent you",
        )
        
        phrases["redemption_right"] = LegalPhrase(
            canonical="RIGHT OF REDEMPTION",
            variations=[
                "REDEMPTION PERIOD",
                "PAY AND STAY",
                "CURE BEFORE EVICTION",
            ],
            category=LegalPhraseCategory.RIGHTS,
            severity="high",
            statute="Minn. Stat. § 504B.291",
            meaning="Right to pay all owed amounts and stop eviction",
        )
        
        # ============================================================
        # FINANCIAL TERMS - Amounts, fees, damages
        # ============================================================
        
        phrases["rent_due"] = LegalPhrase(
            canonical="RENT DUE",
            variations=[
                "RENT OWED",
                "PAST DUE RENT",
                "UNPAID RENT",
                "RENT IN ARREARS",
                "DELINQUENT RENT",
            ],
            category=LegalPhraseCategory.FINANCIAL,
            severity="high",
            meaning="Monthly rent payment that hasn't been paid",
        )
        
        phrases["late_fee"] = LegalPhrase(
            canonical="LATE FEE",
            variations=[
                "LATE CHARGE",
                "LATE PAYMENT FEE",
                "PENALTY FOR LATE PAYMENT",
            ],
            category=LegalPhraseCategory.FINANCIAL,
            severity="medium",
            statute="Minn. Stat. § 504B.177",
            meaning="Fee charged for paying rent late (must be in lease)",
        )
        
        phrases["security_deposit"] = LegalPhrase(
            canonical="SECURITY DEPOSIT",
            variations=[
                "DAMAGE DEPOSIT",
                "RENTAL DEPOSIT",
                "DEPOSIT",
            ],
            category=LegalPhraseCategory.FINANCIAL,
            severity="high",
            statute="Minn. Stat. § 504B.178",
            meaning="Money held by landlord for damages/unpaid rent",
        )
        
        phrases["court_costs"] = LegalPhrase(
            canonical="COURT COSTS",
            variations=[
                "FILING FEES",
                "COURT FEES",
                "LITIGATION COSTS",
            ],
            category=LegalPhraseCategory.FINANCIAL,
            severity="medium",
            meaning="Fees to file and process court case",
        )
        
        phrases["attorneys_fees"] = LegalPhrase(
            canonical="ATTORNEY'S FEES",
            variations=[
                "ATTORNEY FEES",
                "LEGAL FEES",
                "ATTORNEYS' FEES",
            ],
            category=LegalPhraseCategory.FINANCIAL,
            severity="medium",
            meaning="Lawyer fees (only if lease allows)",
        )
        
        return phrases
    
    def _build_document_type_patterns(self) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build document type identification patterns.
        
        Returns dict mapping document type to list of (pattern, weight) tuples.
        Higher weight = stronger indicator.
        """
        return {
            # Eviction Notices
            "EVICTION_NOTICE_14_DAY": [
                (r"(?i)14[\s-]*DAY\s+NOTICE", 10.0),
                (r"(?i)FOURTEEN\s*\(?\s*14\s*\)?\s*DAY", 10.0),
                (r"(?i)PAY\s+RENT\s+OR\s+(?:QUIT|VACATE)", 8.0),
                (r"(?i)NOTICE\s+TO\s+(?:QUIT|VACATE)", 5.0),
                (r"(?i)MINN\.?\s*STAT\.?\s*§?\s*504B\.135", 10.0),
            ],
            
            # Court Summons
            "SUMMONS": [
                (r"(?i)^SUMMONS", 10.0),
                (r"(?i)DISTRICT\s+COURT", 8.0),
                (r"(?i)STATE\s+OF\s+MINNESOTA", 5.0),
                (r"(?i)COUNTY\s+OF\s+(?:HENNEPIN|RAMSEY|DAKOTA|ANOKA)", 5.0),
                (r"(?i)CASE\s+(?:NO\.?|NUMBER|#)", 7.0),
                (r"(?i)YOU\s+ARE\s+BEING\s+SUED", 10.0),
                (r"(?i)YOU\s+MUST\s+(?:REPLY|RESPOND|ANSWER)", 8.0),
            ],
            
            # Complaint
            "COMPLAINT": [
                (r"(?i)COMPLAINT\s+FOR\s+(?:EVICTION|RECOVERY)", 10.0),
                (r"(?i)UNLAWFUL\s+DETAINER", 10.0),
                (r"(?i)PLAINTIFF\s+(?:v\.?|vs\.?|versus)", 8.0),
                (r"(?i)DEFENDANT", 5.0),
            ],
            
            # Lease Agreement
            "LEASE_AGREEMENT": [
                (r"(?i)RESIDENTIAL\s+LEASE\s+AGREEMENT", 10.0),
                (r"(?i)RENTAL\s+AGREEMENT", 8.0),
                (r"(?i)LEASE\s+(?:AGREEMENT|CONTRACT)", 8.0),
                (r"(?i)LANDLORD\s+AND\s+TENANT", 6.0),
                (r"(?i)LESSOR\s+AND\s+LESSEE", 6.0),
                (r"(?i)TERM\s+OF\s+(?:LEASE|TENANCY)", 5.0),
                (r"(?i)SECURITY\s+DEPOSIT", 4.0),
            ],
            
            # Rent Receipt
            "RENT_RECEIPT": [
                (r"(?i)RENT\s+RECEIPT", 10.0),
                (r"(?i)PAYMENT\s+RECEIVED", 8.0),
                (r"(?i)RECEIVED\s+FROM", 6.0),
                (r"(?i)FOR\s+RENT\s+(?:FOR|OF)", 7.0),
            ],
            
            # Security Deposit
            "SECURITY_DEPOSIT_STATEMENT": [
                (r"(?i)SECURITY\s+DEPOSIT\s+(?:ITEMIZATION|STATEMENT|ACCOUNTING)", 10.0),
                (r"(?i)DEPOSIT\s+(?:REFUND|DEDUCTION)", 8.0),
                (r"(?i)ITEMIZED\s+DEDUCTIONS?", 8.0),
                (r"(?i)MOVE[- ]?OUT\s+(?:INSPECTION|DATE)", 6.0),
            ],
            
            # Repair Request
            "REPAIR_REQUEST": [
                (r"(?i)NOTICE\s+OF\s+REPAIR\s+REQUEST", 10.0),
                (r"(?i)REQUEST\s+FOR\s+REPAIR", 8.0),
                (r"(?i)MAINTENANCE\s+REQUEST", 7.0),
                (r"(?i)MINN\.?\s*STAT\.?\s*§?\s*504B\.185", 10.0),
                (r"(?i)COVENANT\s+OF\s+HABITABILITY", 8.0),
            ],
            
            # Rent Increase Notice
            "RENT_INCREASE": [
                (r"(?i)NOTICE\s+OF\s+RENT\s+INCREASE", 10.0),
                (r"(?i)RENT\s+INCREASE", 8.0),
                (r"(?i)NEW\s+(?:RENT|RENTAL)\s+(?:AMOUNT|RATE)", 7.0),
                (r"(?i)CURRENT\s+RENT.*NEW\s+RENT", 8.0),
            ],
            
            # Writ of Recovery
            "WRIT_OF_RECOVERY": [
                (r"(?i)WRIT\s+OF\s+(?:RECOVERY|RESTITUTION)", 10.0),
                (r"(?i)ORDER\s+FOR\s+(?:RECOVERY|EVICTION)", 9.0),
                (r"(?i)SHERIFF", 6.0),
                (r"(?i)REMOVE\s+(?:TENANT|DEFENDANT)", 7.0),
            ],
        }
    
    def _build_statute_patterns(self) -> Dict[str, Dict]:
        """Build Minnesota statute recognition patterns"""
        return {
            "504B.135": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.135",
                "title": "Termination of Lease for Failure to Pay Rent",
                "summary": "14-day notice requirement for non-payment eviction",
            },
            "504B.145": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.145",
                "title": "Notice of Intent Not to Renew",
                "summary": "Notice requirements for lease non-renewal",
            },
            "504B.161": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.161",
                "title": "Covenants of Landlord and Tenant",
                "summary": "Landlord duty to maintain habitable conditions",
            },
            "504B.178": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.178",
                "title": "Security Deposits",
                "summary": "Rules for holding and returning security deposits",
            },
            "504B.185": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.185",
                "title": "Tenant's Right to Repairs",
                "summary": "Tenant remedies for landlord failure to make repairs",
            },
            "504B.291": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.291",
                "title": "Right of Redemption",
                "summary": "Tenant's right to pay and cure before eviction",
            },
            "504B.321": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.321",
                "title": "Eviction Actions",
                "summary": "Court procedures for eviction cases",
            },
            "504B.335": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.335",
                "title": "First Appearance",
                "summary": "Tenant rights at first court appearance",
            },
            "504B.345": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.345",
                "title": "Trial",
                "summary": "Eviction trial procedures",
            },
            "504B.365": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.365",
                "title": "Writ of Recovery",
                "summary": "Court order to remove tenant",
            },
            "504B.385": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.385",
                "title": "Rent Escrow",
                "summary": "Tenant right to pay rent to court for repairs",
            },
            "504B.395": {
                "pattern": r"(?i)(?:MINN\.?\s*STAT\.?\s*)?§?\s*504B\.395",
                "title": "Tenant Remedies Action",
                "summary": "Tenant lawsuit for habitability violations",
            },
        }
    
    def _build_ocr_corrections(self) -> Dict[str, str]:
        """
        Build OCR error correction dictionary.
        
        Common OCR mistakes when reading legal documents.
        """
        return {
            # Character confusion
            "tbe": "the",
            "tlie": "the",
            "tliat": "that",
            "witli": "with",
            "wliich": "which",
            "liave": "have",
            "liis": "his",
            "lier": "her",
            "tliis": "this",
            "tliere": "there",
            "tlieir": "their",
            "wlio": "who",
            "wliat": "what",
            "wlien": "when",
            "wliere": "where",
            "wliy": "why",
            "liow": "how",
            
            # m/n/rn confusion
            "rn": "m",
            "tenn": "term",
            "arnount": "amount",
            "payrnent": "payment",
            "judgrnent": "judgment",
            
            # l/1/I confusion
            "1ease": "lease",
            "1andlord": "landlord",
            "1egal": "legal",
            "1etter": "letter",
            "I0": "10",
            "I4": "14",
            "I5": "15",
            
            # 0/O confusion
            "0rder": "Order",
            "0wner": "Owner",
            
            # Common phrase corrections
            "PAY RENT 0R QUIT": "PAY RENT OR QUIT",
            "N0TICE": "NOTICE",
            "C0URT": "COURT",
            "C0UNTY": "COUNTY",
        }
    
    def _build_critical_numbers(self) -> Dict[str, Dict]:
        """
        Build critical number patterns - these MUST be extracted accurately.
        """
        return {
            "deadline_days": {
                "pattern": r"(?i)(?:within|after|before)\s+(\d+)\s*(?:days?|business\s+days?)",
                "validate": lambda x: 0 < int(x) <= 365,
            },
            "money_amount": {
                "pattern": r"\$\s*([\d,]+(?:\.\d{2})?)",
                "validate": lambda x: float(x.replace(",", "")) > 0,
            },
            "date": {
                "pattern": r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
                "validate": lambda x: True,  # Will be validated by date parser
            },
            "case_number": {
                "pattern": r"(?i)(?:case|file)\s*(?:no\.?|number|#)[:\s]*([A-Z0-9\-]+)",
                "validate": lambda x: len(x) >= 5,
            },
            "apartment_unit": {
                "pattern": r"(?i)(?:apt\.?|apartment|unit|#)\s*([A-Za-z0-9]+)",
                "validate": lambda x: len(x) >= 1,
            },
            "zip_code": {
                "pattern": r"\b(\d{5})(?:-\d{4})?\b",
                "validate": lambda x: 55001 <= int(x) <= 56763,  # MN zip codes
            },
        }
    
    def _build_phrase_index(self) -> Dict[str, List[str]]:
        """Build reverse index from variations to canonical phrases"""
        index = {}
        for key, phrase in self.phrases.items():
            # Index the canonical form
            canonical_words = phrase.canonical.lower().split()
            for word in canonical_words:
                if len(word) >= 4:  # Skip short words
                    if word not in index:
                        index[word] = []
                    index[word].append(key)
            
            # Index variations
            for variation in phrase.variations:
                variation_words = variation.lower().split()
                for word in variation_words:
                    if len(word) >= 4:
                        if word not in index:
                            index[word] = []
                        if key not in index[word]:
                            index[word].append(key)
        
        return index
    
    def correct_ocr_text(self, text: str) -> str:
        """
        Apply OCR corrections to text.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Corrected text
        """
        corrected = text
        
        for wrong, right in self.ocr_corrections.items():
            # Word boundary matching for safety
            pattern = r'\b' + re.escape(wrong) + r'\b'
            corrected = re.sub(pattern, right, corrected)
        
        return corrected
    
    def identify_phrases(self, text: str) -> List[Dict]:
        """
        Identify all legal phrases in text.
        
        Returns list of found phrases with positions and metadata.
        """
        found = []
        text_lower = text.lower()
        
        for key, phrase in self.phrases.items():
            # Check canonical form
            pattern = re.escape(phrase.canonical)
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                found.append({
                    "phrase_key": key,
                    "matched_text": match.group(),
                    "canonical": phrase.canonical,
                    "category": phrase.category.value,
                    "severity": phrase.severity,
                    "statute": phrase.statute,
                    "meaning": phrase.meaning,
                    "position": (match.start(), match.end()),
                    "confidence": 1.0,
                })
            
            # Check variations if canonical not found
            if not matches:
                for variation in phrase.variations:
                    pattern = re.escape(variation)
                    matches = list(re.finditer(pattern, text, re.IGNORECASE))
                    for match in matches:
                        found.append({
                            "phrase_key": key,
                            "matched_text": match.group(),
                            "canonical": phrase.canonical,
                            "category": phrase.category.value,
                            "severity": phrase.severity,
                            "statute": phrase.statute,
                            "meaning": phrase.meaning,
                            "position": (match.start(), match.end()),
                            "confidence": 0.95,
                        })
                    if matches:
                        break  # Found a match, don't need other variations
        
        return found
    
    def identify_document_type(self, text: str) -> Tuple[str, float, List[str]]:
        """
        Identify document type with confidence score.
        
        Returns:
            Tuple of (document_type, confidence, matched_patterns)
        """
        scores = {}
        matches_by_type = {}
        
        for doc_type, patterns in self.document_types.items():
            total_weight = 0.0
            max_possible = sum(weight for _, weight in patterns)
            matched = []
            
            for pattern, weight in patterns:
                if re.search(pattern, text):
                    total_weight += weight
                    matched.append(pattern)
            
            if total_weight > 0:
                # Normalize to 0-100
                scores[doc_type] = (total_weight / max_possible) * 100
                matches_by_type[doc_type] = matched
        
        if not scores:
            return "UNKNOWN", 0.0, []
        
        # Get best match
        best_type = max(scores.keys(), key=lambda k: scores[k])
        return best_type, scores[best_type], matches_by_type.get(best_type, [])
    
    def extract_statutes(self, text: str) -> List[Dict]:
        """Extract Minnesota statute references from text"""
        found = []
        
        for statute_num, info in self.statutory_references.items():
            matches = list(re.finditer(info["pattern"], text))
            for match in matches:
                found.append({
                    "statute": statute_num,
                    "full_citation": f"Minn. Stat. § {statute_num}",
                    "title": info["title"],
                    "summary": info["summary"],
                    "position": (match.start(), match.end()),
                    "matched_text": match.group(),
                })
        
        return found
    
    def extract_critical_numbers(self, text: str) -> Dict[str, List[Dict]]:
        """Extract all critical numbers (deadlines, amounts, dates, etc.)"""
        results = {}
        
        for num_type, config in self.critical_numbers.items():
            matches = []
            for match in re.finditer(config["pattern"], text):
                value = match.group(1) if match.lastindex else match.group()
                
                # Validate if validator provided
                valid = True
                if "validate" in config:
                    try:
                        valid = config["validate"](value)
                    except:
                        valid = False
                
                matches.append({
                    "value": value,
                    "position": (match.start(), match.end()),
                    "full_match": match.group(),
                    "valid": valid,
                })
            
            if matches:
                results[num_type] = matches
        
        return results
    
    def get_phrase_by_key(self, key: str) -> Optional[LegalPhrase]:
        """Get phrase definition by key"""
        return self.phrases.get(key)
    
    def search_phrases(self, query: str) -> List[str]:
        """Search for phrases containing query words"""
        query_words = query.lower().split()
        results = set()
        
        for word in query_words:
            if word in self._phrase_index:
                results.update(self._phrase_index[word])
        
        return list(results)


# Singleton instance
_dictionary = None

def get_legal_dictionary() -> MinnesotaLegalDictionary:
    """Get or create singleton dictionary instance"""
    global _dictionary
    if _dictionary is None:
        _dictionary = MinnesotaLegalDictionary()
    return _dictionary
