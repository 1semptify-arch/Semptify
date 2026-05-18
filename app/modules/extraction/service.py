"""
Form Field Extractor Service

Enhanced extraction specifically designed to populate court forms.
Takes raw document extractions and maps them to specific form fields.

This bridges the gap between:
- Document processing (raw extraction)
- Form generation (structured fields)
"""

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum


class FieldConfidence(str, Enum):
    """Confidence level for extracted field values."""
    HIGH = "high"           # 90%+ confidence, likely correct
    MEDIUM = "medium"       # 70-90% confidence, should verify
    LOW = "low"             # 50-70% confidence, needs review
    GUESS = "guess"         # <50% confidence, user must confirm
    EMPTY = "empty"         # No value found


@dataclass
class ExtractedField:
    """A single extracted field with metadata for review."""
    field_name: str
    display_name: str
    value: Any
    confidence: FieldConfidence
    source: str = ""        # Which document/section it came from
    source_text: str = ""   # Original text it was extracted from
    alternatives: List[Any] = field(default_factory=list)  # Other possible values
    needs_review: bool = False
    review_reason: str = ""
    
    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "display_name": self.display_name,
            "value": self.value,
            "confidence": self.confidence.value,
            "source": self.source,
            "source_text": self.source_text,
            "alternatives": self.alternatives,
            "needs_review": self.needs_review,
            "review_reason": self.review_reason,
        }


@dataclass 
class AddressComponents:
    """Parsed address components."""
    full_address: str = ""
    street: str = ""
    unit: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FormFieldsExtraction:
    """Complete extraction result for form filling."""
    
    # Case Information
    case_number: ExtractedField = None
    court_name: ExtractedField = None
    county: ExtractedField = None
    judicial_district: ExtractedField = None
    
    # Tenant Information
    tenant_name: ExtractedField = None
    tenant_address: ExtractedField = None
    tenant_city: ExtractedField = None
    tenant_state: ExtractedField = None
    tenant_zip: ExtractedField = None
    tenant_phone: ExtractedField = None
    tenant_email: ExtractedField = None
    
    # Landlord Information
    landlord_name: ExtractedField = None
    landlord_address: ExtractedField = None
    landlord_city: ExtractedField = None
    landlord_state: ExtractedField = None
    landlord_zip: ExtractedField = None
    landlord_phone: ExtractedField = None
    landlord_email: ExtractedField = None
    
    # Property Information
    property_address: ExtractedField = None
    property_city: ExtractedField = None
    property_state: ExtractedField = None
    property_zip: ExtractedField = None
    unit_number: ExtractedField = None
    
    # Lease Information
    lease_start_date: ExtractedField = None
    lease_end_date: ExtractedField = None
    monthly_rent: ExtractedField = None
    security_deposit: ExtractedField = None
    lease_type: ExtractedField = None
    
    # Case Dates
    notice_date: ExtractedField = None
    notice_type: ExtractedField = None
    summons_date: ExtractedField = None
    service_date: ExtractedField = None
    answer_deadline: ExtractedField = None
    hearing_date: ExtractedField = None
    hearing_time: ExtractedField = None
    
    # Amounts Claimed
    rent_claimed: ExtractedField = None
    late_fees_claimed: ExtractedField = None
    other_fees_claimed: ExtractedField = None
    total_claimed: ExtractedField = None
    
    # Metadata
    extraction_date: str = ""
    documents_processed: List[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    fields_needing_review: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        result = {
            "case": {},
            "tenant": {},
            "landlord": {},
            "property": {},
            "lease": {},
            "dates": {},
            "amounts": {},
            "metadata": {
                "extraction_date": self.extraction_date,
                "documents_processed": self.documents_processed,
                "overall_confidence": self.overall_confidence,
                "fields_needing_review": self.fields_needing_review,
            }
        }
        
        # Map fields to categories
        field_mapping = {
            "case": ["case_number", "court_name", "county", "judicial_district"],
            "tenant": ["tenant_name", "tenant_address", "tenant_city", "tenant_state", 
                      "tenant_zip", "tenant_phone", "tenant_email"],
            "landlord": ["landlord_name", "landlord_address", "landlord_city", "landlord_state",
                        "landlord_zip", "landlord_phone", "landlord_email"],
            "property": ["property_address", "property_city", "property_state", "property_zip", "unit_number"],
            "lease": ["lease_start_date", "lease_end_date", "monthly_rent", "security_deposit", "lease_type"],
            "dates": ["notice_date", "notice_type", "summons_date", "service_date", 
                     "answer_deadline", "hearing_date", "hearing_time"],
            "amounts": ["rent_claimed", "late_fees_claimed", "other_fees_claimed", "total_claimed"],
        }
        
        for category, fields in field_mapping.items():
            for field_name in fields:
                field_obj = getattr(self, field_name, None)
                if field_obj:
                    result[category][field_name] = field_obj.to_dict()
        
        return result
    
    def get_review_items(self) -> List[ExtractedField]:
        """Get all fields that need user review."""
        items = []
        for field_name in dir(self):
            if field_name.startswith('_'):
                continue
            field_obj = getattr(self, field_name, None)
            if isinstance(field_obj, ExtractedField) and field_obj.needs_review:
                items.append(field_obj)
        return items


class FormFieldExtractor:
    """
    Extract and map document data to form fields.
    
    Takes raw extraction results and produces structured form-ready data.
    """
    
    # Case number patterns for different courts
    CASE_NUMBER_PATTERNS = [
        # Dakota County: 19AV-CV-25-3477
        (r'\b(\d{2}[A-Z]{2}-CV-\d{2}-\d+)\b', "Dakota County"),
        # Hennepin: 27-CV-HC-24-5847
        (r'\b(\d{2}-CV-[A-Z]{2}-\d{2}-\d+)\b', "Hennepin County"),
        # Generic: Case No. 12345
        (r'Case\s*(?:No\.?|Number|#)\s*:?\s*([A-Z0-9-]+)', "Generic"),
        # File number
        (r'File\s*(?:No\.?|Number|#)\s*:?\s*([A-Z0-9-]+)', "File Number"),
    ]
    
    # Court patterns
    COURT_PATTERNS = [
        (r'(Dakota County)\s*(?:District)?\s*Court', "Dakota"),
        (r'(Hennepin County)\s*(?:District)?\s*Court', "Hennepin"),
        (r'(Ramsey County)\s*(?:District)?\s*Court', "Ramsey"),
        (r'(\w+\s+County)\s*(?:District)?\s*Court', "Generic"),
        (r'(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s+Judicial\s+District', "District"),
    ]
    
    # Enhanced address pattern
    ADDRESS_PATTERN = re.compile(
        r'(\d+)\s+'  # Street number
        r'([\w\s]+?)\s+'  # Street name
        r'(Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Drive|Dr\.?|Lane|Ln\.?|Court|Ct\.?|Boulevard|Blvd\.?|Way|Circle|Cir\.?|Place|Pl\.?)'
        r'(?:\s*,?\s*(?:Apt\.?|Unit|Suite|#|Apartment)\s*([A-Za-z0-9-]+))?'  # Optional unit
        r'(?:\s*,?\s*([A-Za-z\s]+))?'  # Optional city
        r'(?:\s*,?\s*([A-Z]{2}))?'  # Optional state
        r'(?:\s*,?\s*(\d{5}(?:-\d{4})?))?',  # Optional zip
        re.IGNORECASE
    )
    
    # Minnesota cities for better matching
    MN_CITIES = [
        "Minneapolis", "Saint Paul", "St. Paul", "Rochester", "Duluth", "Bloomington",
        "Brooklyn Park", "Plymouth", "Maple Grove", "Woodbury", "St. Cloud", "Eagan",
        "Eden Prairie", "Burnsville", "Lakeville", "Blaine", "Minnetonka", "Apple Valley",
        "Edina", "Coon Rapids", "Hastings", "Farmington", "Rosemount", "Inver Grove Heights",
        "South St. Paul", "West St. Paul", "Mendota Heights", "Cottage Grove", "Oakdale",
    ]
    
    def __init__(self):
        self.result = FormFieldsExtraction()
        self.raw_text = ""
        self.documents = []
    
    def extract_from_documents(self, documents: List[Dict[str, Any]]) -> FormFieldsExtraction:
        """
        Extract form fields from multiple documents.
        
        Args:
            documents: List of document dicts with 'text', 'filename', 'type', etc.
        
        Returns:
            FormFieldsExtraction with all extracted fields
        """
        self.documents = documents
        self.result = FormFieldsExtraction()
        self.result.extraction_date = datetime.now(timezone.utc).isoformat()
        
        # Combine all document text for analysis
        combined_text = ""
        for doc in documents:
            text = doc.get('text', '') or doc.get('full_text', '') or ''
            combined_text += f"\n\n--- {doc.get('filename', 'Unknown')} ---\n\n{text}"
            self.result.documents_processed.append(doc.get('filename', 'Unknown'))
        
        self.raw_text = combined_text
        
        # Extract each category
        self._extract_case_info()
        self._extract_parties()
        self._extract_property_info()
        self._extract_lease_info()
        self._extract_dates()
        self._extract_amounts()
        
        # Calculate overall confidence and review count
        self._calculate_confidence()
        
        return self.result
    
    def _extract_case_info(self):
        """Extract case number and court information."""
        text = self.raw_text
        
        # Case number
        for pattern, source in self.CASE_NUMBER_PATTERNS:
            match = re.search(pattern, text)
            if match:
                self.result.case_number = ExtractedField(
                    field_name="case_number",
                    display_name="Case Number",
                    value=match.group(1),
                    confidence=FieldConfidence.HIGH,
                    source=source,
                    source_text=match.group(0),
                )
                break
        
        if not self.result.case_number:
            self.result.case_number = ExtractedField(
                field_name="case_number",
                display_name="Case Number",
                value="",
                confidence=FieldConfidence.EMPTY,
                needs_review=True,
                review_reason="No case number found in documents",
            )
        
        # Court and county
        for pattern, county_hint in self.COURT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                court_text = match.group(0)
                if "Dakota" in court_text:
                    self.result.court_name = ExtractedField(
                        field_name="court_name",
                        display_name="Court Name",
                        value="Dakota County District Court",
                        confidence=FieldConfidence.HIGH,
                        source_text=court_text,
                    )
                    self.result.county = ExtractedField(
                        field_name="county",
                        display_name="County",
                        value="Dakota",
                        confidence=FieldConfidence.HIGH,
                    )
                    self.result.judicial_district = ExtractedField(
                        field_name="judicial_district",
                        display_name="Judicial District",
                        value="First Judicial District",
                        confidence=FieldConfidence.HIGH,
                    )
                elif "Hennepin" in court_text:
                    self.result.court_name = ExtractedField(
                        field_name="court_name",
                        display_name="Court Name",
                        value="Hennepin County District Court",
                        confidence=FieldConfidence.HIGH,
                        source_text=court_text,
                    )
                    self.result.county = ExtractedField(
                        field_name="county",
                        display_name="County",
                        value="Hennepin",
                        confidence=FieldConfidence.HIGH,
                    )
                    self.result.judicial_district = ExtractedField(
                        field_name="judicial_district",
                        display_name="Judicial District",
                        value="Fourth Judicial District",
                        confidence=FieldConfidence.HIGH,
                    )
                break
        
        # Default to Dakota County if not found
        if not self.result.county:
            self.result.county = ExtractedField(
                field_name="county",
                display_name="County",
                value="Dakota",
                confidence=FieldConfidence.LOW,
                needs_review=True,
                review_reason="County not found, defaulting to Dakota",
            )
    
    def _extract_parties(self):
        """Extract tenant and landlord information."""
        text = self.raw_text

        # Party patterns - look for labeled parties in various formats
        # Order matters - more specific patterns first
        tenant_patterns = [
            # "To the above-named Defendant: John Smith"
            r'(?:above-named|named)\s+(?:Defendant|Tenant)[:\s]+([A-Z][a-zA-Z\s\.]+?)(?:\s+You|\s+is|\s*$)',
            # Standard summons format: "John Smith, Defendant"
            r'([A-Z][a-zA-Z\s\.]+?),?\s+Defendant(?:\.|,|\s)',
            # "Defendant: John Smith" format
            r'(?:defendant|tenant|lessee|renter)[:\s]+([A-Z][a-zA-Z\s,\.]+?)(?:\s*\n|,\s*(?:and|v\.?|vs\.?)|\d)',
            # "v. John Smith," format - name between v. and comma/period
            r'\bv\.?\s+([A-Z][a-zA-Z\s\.]+?),',
        ]

        landlord_patterns = [
            # "Landlord Address: ABC LLC," - name before comma
            r'Landlord(?:\s+Address)?[:\s]+([A-Z][a-zA-Z\s\.,]+?(?:LLC|Inc|Corp|Company|Properties|Management))\s*,',
            # Standard summons format: "ABC LLC, Plaintiff"
            r'([A-Z][a-zA-Z\s\.,]+?(?:LLC|Inc|Corp|Company|Properties|Management)),?\s+Plaintiff(?:\.|,|\s)',
            # "Plaintiff: ABC LLC" format
            r'(?:plaintiff|landlord|lessor|property owner|petitioner)[:\s]+([A-Z][a-zA-Z\s,\.]+?(?:LLC|Inc|Corp|Company|Properties|Management)?)(?:\s*\n|,\s*(?:and|v\.?|vs\.?)|\d)',
        ]        # Extract tenant name
        for pattern in tenant_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
                if len(name) > 2 and len(name) < 100:
                    self.result.tenant_name = ExtractedField(
                        field_name="tenant_name",
                        display_name="Tenant Name",
                        value=name,
                        confidence=FieldConfidence.MEDIUM,
                        source_text=match.group(0)[:100],
                        needs_review=True,
                        review_reason="Please verify tenant name is correct",
                    )
                    break
        
        if not self.result.tenant_name:
            self.result.tenant_name = ExtractedField(
                field_name="tenant_name",
                display_name="Tenant Name",
                value="",
                confidence=FieldConfidence.EMPTY,
                needs_review=True,
                review_reason="Tenant name not found",
            )
        
        # Extract landlord name
        for pattern in landlord_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'\s+', ' ', name)
                if len(name) > 2 and len(name) < 100:
                    self.result.landlord_name = ExtractedField(
                        field_name="landlord_name",
                        display_name="Landlord/Plaintiff Name",
                        value=name,
                        confidence=FieldConfidence.MEDIUM,
                        source_text=match.group(0)[:100],
                        needs_review=True,
                        review_reason="Please verify landlord name is correct",
                    )
                    break
        
        if not self.result.landlord_name:
            self.result.landlord_name = ExtractedField(
                field_name="landlord_name",
                display_name="Landlord/Plaintiff Name",
                value="",
                confidence=FieldConfidence.EMPTY,
                needs_review=True,
                review_reason="Landlord name not found",
            )
        
        # Extract contact info
        self._extract_contact_info()
    
    def _extract_contact_info(self):
        """Extract phone numbers and emails."""
        text = self.raw_text
        
        # Phone patterns
        phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phones:
            # First phone often is landlord/plaintiff
            self.result.landlord_phone = ExtractedField(
                field_name="landlord_phone",
                display_name="Landlord Phone",
                value=phones[0] if len(phones) > 0 else "",
                confidence=FieldConfidence.LOW,
                alternatives=phones[1:] if len(phones) > 1 else [],
                needs_review=True,
                review_reason="Multiple phone numbers found, please verify",
            )
        
        # Email patterns
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if emails:
            self.result.landlord_email = ExtractedField(
                field_name="landlord_email",
                display_name="Landlord Email",
                value=emails[0] if len(emails) > 0 else "",
                confidence=FieldConfidence.LOW,
                alternatives=emails[1:] if len(emails) > 1 else [],
                needs_review=True,
                review_reason="Multiple emails found, please verify",
            )
    
    def _extract_property_info(self):
        """Extract property address and unit information."""
        text = self.raw_text
        
        # Look for "premises" or "property" labeled addresses
        property_patterns = [
            r'(?:premises|property|rental unit|rental property|located at|property address)[:\s]+(\d+[^,\n]+)',
            r'(?:evict(?:ed|ion)?\s+from)[:\s]+(\d+[^,\n]+)',
        ]
        
        addresses_found = []
        
        for pattern in property_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                addr_text = match.group(1).strip()
                parsed = self._parse_address(addr_text)
                if parsed.street:
                    addresses_found.append((parsed, match.group(0), "property_label"))
        
        # Also find all addresses and try to identify property vs mailing
        all_addresses = re.findall(
            r'\d+\s+[\w\s]+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Drive|Dr\.?|Lane|Ln\.?)[^,\n]*',
            text, re.IGNORECASE
        )
        
        for addr_text in all_addresses:
            parsed = self._parse_address(addr_text)
            if parsed.street:
                addresses_found.append((parsed, addr_text, "general"))
        
        # Set property address
        if addresses_found:
            best_addr, source_text, source_type = addresses_found[0]
            confidence = FieldConfidence.HIGH if source_type == "property_label" else FieldConfidence.MEDIUM
            
            self.result.property_address = ExtractedField(
                field_name="property_address",
                display_name="Property Address",
                value=best_addr.street,
                confidence=confidence,
                source_text=source_text[:100],
                needs_review=True,
                review_reason="Please verify this is the rental property address",
            )
            
            if best_addr.unit:
                self.result.unit_number = ExtractedField(
                    field_name="unit_number",
                    display_name="Unit Number",
                    value=best_addr.unit,
                    confidence=FieldConfidence.HIGH,
                )
            
            if best_addr.city:
                self.result.property_city = ExtractedField(
                    field_name="property_city",
                    display_name="City",
                    value=best_addr.city,
                    confidence=FieldConfidence.MEDIUM,
                )
            
            if best_addr.state:
                self.result.property_state = ExtractedField(
                    field_name="property_state",
                    display_name="State",
                    value=best_addr.state,
                    confidence=FieldConfidence.HIGH,
                )
            else:
                self.result.property_state = ExtractedField(
                    field_name="property_state",
                    display_name="State",
                    value="MN",
                    confidence=FieldConfidence.LOW,
                )
            
            if best_addr.zip_code:
                self.result.property_zip = ExtractedField(
                    field_name="property_zip",
                    display_name="ZIP Code",
                    value=best_addr.zip_code,
                    confidence=FieldConfidence.HIGH,
                )
            
            # Store alternatives
            if len(addresses_found) > 1:
                alt_addrs = [a[0].full_address for a in addresses_found[1:4]]
                self.result.property_address.alternatives = alt_addrs
        else:
            self.result.property_address = ExtractedField(
                field_name="property_address",
                display_name="Property Address",
                value="",
                confidence=FieldConfidence.EMPTY,
                needs_review=True,
                review_reason="Property address not found",
            )
    
    def _parse_address(self, text: str) -> AddressComponents:
        """Parse an address string into components."""
        result = AddressComponents(full_address=text.strip())
        
        # Try to extract unit number
        unit_match = re.search(r'(?:Apt\.?|Unit|Suite|#|Apartment)\s*([A-Za-z0-9-]+)', text, re.IGNORECASE)
        if unit_match:
            result.unit = unit_match.group(1)
            text = text[:unit_match.start()] + text[unit_match.end():]
        
        # Try to find city
        for city in self.MN_CITIES:
            if city.lower() in text.lower():
                result.city = city
                break
        
        # Try to find state
        state_match = re.search(r'\b(MN|Minnesota|WI|Wisconsin|ND|North Dakota|SD|South Dakota|IA|Iowa)\b', text, re.IGNORECASE)
        if state_match:
            state = state_match.group(1).upper()
            if state == "MINNESOTA":
                state = "MN"
            result.state = state
        
        # Try to find ZIP
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', text)
        if zip_match:
            result.zip_code = zip_match.group(1)
        
        # Street is everything before city/state/zip
        street_text = text
        if result.city:
            idx = street_text.lower().find(result.city.lower())
            if idx > 0:
                street_text = street_text[:idx]
        
        # Clean up street
        street_text = re.sub(r'\s*,\s*$', '', street_text.strip())
        result.street = street_text
        
        return result
    
    def _extract_lease_info(self):
        """Extract lease information."""
        text = self.raw_text
        
        # Monthly rent
        rent_patterns = [
            r'(?:monthly\s+)?rent[:\s]+\$?\s*([\d,]+(?:\.\d{2})?)',
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s+month|monthly|/\s*month)',
            r'rent\s+(?:of|is|was)\s+\$?\s*([\d,]+(?:\.\d{2})?)',
        ]
        
        for pattern in rent_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1).replace(',', ''))
                if 200 <= amount <= 10000:  # Reasonable rent range
                    self.result.monthly_rent = ExtractedField(
                        field_name="monthly_rent",
                        display_name="Monthly Rent",
                        value=amount,
                        confidence=FieldConfidence.MEDIUM,
                        source_text=match.group(0),
                        needs_review=True,
                        review_reason="Please verify rent amount",
                    )
                    break
        
        # Security deposit
        deposit_patterns = [
            r'security\s+deposit[:\s]+\$?\s*([\d,]+(?:\.\d{2})?)',
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:security\s+)?deposit',
        ]
        
        for pattern in deposit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1).replace(',', ''))
                if 100 <= amount <= 10000:
                    self.result.security_deposit = ExtractedField(
                        field_name="security_deposit",
                        display_name="Security Deposit",
                        value=amount,
                        confidence=FieldConfidence.MEDIUM,
                        source_text=match.group(0),
                    )
                    break
    
    def _extract_dates(self):
        """Extract important dates."""
        text = self.raw_text
        
        # Date patterns
        date_patterns = [
            (r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'mdy'),
            (r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', 'ymd'),
        ]
        
        month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7,
            'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        }
        
        # Find all dates with context
        dates_found = []
        
        # Pattern: Month DD, YYYY
        for match in re.finditer(
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
            text, re.IGNORECASE
        ):
            try:
                month = month_names[match.group(1).lower()]
                day = int(match.group(2))
                year = int(match.group(3))
                dt = datetime(year, month, day)
                
                # Get context
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 20)
                context = text[start:end].lower()
                
                dates_found.append({
                    'date': dt,
                    'text': match.group(0),
                    'context': context,
                })
            except (ValueError, KeyError):
                continue
        
        # Pattern: MM/DD/YYYY
        for match in re.finditer(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text):
            try:
                month = int(match.group(1))
                day = int(match.group(2))
                year = int(match.group(3))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    dt = datetime(year, month, day)
                    
                    start = max(0, match.start() - 80)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end].lower()
                    
                    dates_found.append({
                        'date': dt,
                        'text': match.group(0),
                        'context': context,
                    })
            except ValueError:
                continue
        
        # Categorize dates by context
        for date_info in dates_found:
            context = date_info['context']
            dt = date_info['date']
            text_found = date_info['text']
            
            if any(word in context for word in ['hearing', 'court date', 'appear', 'trial']):
                if not self.result.hearing_date:
                    self.result.hearing_date = ExtractedField(
                        field_name="hearing_date",
                        display_name="Hearing Date",
                        value=dt.strftime("%Y-%m-%d"),
                        confidence=FieldConfidence.HIGH,
                        source_text=text_found,
                    )
                    # Try to get time
                    time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.)', context, re.IGNORECASE)
                    if time_match:
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2) or 0)
                        ampm = time_match.group(3).lower().replace('.', '')
                        if ampm == 'pm' and hour < 12:
                            hour += 12
                        self.result.hearing_time = ExtractedField(
                            field_name="hearing_time",
                            display_name="Hearing Time",
                            value=f"{hour:02d}:{minute:02d}",
                            confidence=FieldConfidence.HIGH,
                        )
            
            elif any(word in context for word in ['summons', 'served', 'service']):
                if not self.result.summons_date:
                    self.result.summons_date = ExtractedField(
                        field_name="summons_date",
                        display_name="Summons Date",
                        value=dt.strftime("%Y-%m-%d"),
                        confidence=FieldConfidence.MEDIUM,
                        source_text=text_found,
                    )
            
            elif any(word in context for word in ['notice', 'vacate', 'quit', 'evict']):
                if not self.result.notice_date:
                    self.result.notice_date = ExtractedField(
                        field_name="notice_date",
                        display_name="Notice Date",
                        value=dt.strftime("%Y-%m-%d"),
                        confidence=FieldConfidence.MEDIUM,
                        source_text=text_found,
                    )
            
            elif any(word in context for word in ['answer', 'respond', 'deadline', 'due', 'must']):
                if not self.result.answer_deadline:
                    self.result.answer_deadline = ExtractedField(
                        field_name="answer_deadline",
                        display_name="Answer Deadline",
                        value=dt.strftime("%Y-%m-%d"),
                        confidence=FieldConfidence.HIGH,
                        source_text=text_found,
                    )
        
        # Calculate answer deadline if we have summons but no deadline
        if self.result.summons_date and not self.result.answer_deadline:
            try:
                summons_dt = datetime.strptime(self.result.summons_date.value, "%Y-%m-%d")
                deadline_dt = summons_dt + timedelta(days=7)
                self.result.answer_deadline = ExtractedField(
                    field_name="answer_deadline",
                    display_name="Answer Deadline",
                    value=deadline_dt.strftime("%Y-%m-%d"),
                    confidence=FieldConfidence.MEDIUM,
                    needs_review=True,
                    review_reason="Calculated as 7 days from summons date",
                )
            except:
                pass
        
        # Notice type
        if '14' in text.lower() and 'day' in text.lower() and 'notice' in text.lower():
            self.result.notice_type = ExtractedField(
                field_name="notice_type",
                display_name="Notice Type",
                value="14-day",
                confidence=FieldConfidence.MEDIUM,
            )
        elif '30' in text.lower() and 'day' in text.lower() and 'notice' in text.lower():
            self.result.notice_type = ExtractedField(
                field_name="notice_type",
                display_name="Notice Type", 
                value="30-day",
                confidence=FieldConfidence.MEDIUM,
            )
    
    def _extract_amounts(self):
        """Extract claimed amounts."""
        text = self.raw_text
        
        # Amounts claimed
        claimed_patterns = [
            (r'(?:rent\s+)?(?:owed|due|owing|claimed)[:\s]+\$?\s*([\d,]+(?:\.\d{2})?)', 'rent_claimed'),
            (r'(?:unpaid\s+)?rent[:\s]+\$?\s*([\d,]+(?:\.\d{2})?)', 'rent_claimed'),
            (r'late\s+fees?[:\s]+\$?\s*([\d,]+(?:\.\d{2})?)', 'late_fees'),
            (r'total\s+(?:amount\s+)?(?:owed|due|claimed)[:\s]+\$?\s*([\d,]+(?:\.\d{2})?)', 'total'),
        ]
        
        for pattern, field_type in claimed_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1).replace(',', ''))
                if amount > 0:
                    if field_type == 'rent_claimed' and not self.result.rent_claimed:
                        self.result.rent_claimed = ExtractedField(
                            field_name="rent_claimed",
                            display_name="Rent Claimed",
                            value=amount,
                            confidence=FieldConfidence.MEDIUM,
                            source_text=match.group(0),
                        )
                    elif field_type == 'late_fees' and not self.result.late_fees_claimed:
                        self.result.late_fees_claimed = ExtractedField(
                            field_name="late_fees_claimed",
                            display_name="Late Fees Claimed",
                            value=amount,
                            confidence=FieldConfidence.MEDIUM,
                            source_text=match.group(0),
                        )
                    elif field_type == 'total' and not self.result.total_claimed:
                        self.result.total_claimed = ExtractedField(
                            field_name="total_claimed",
                            display_name="Total Amount Claimed",
                            value=amount,
                            confidence=FieldConfidence.MEDIUM,
                            source_text=match.group(0),
                        )
    
    def _calculate_confidence(self):
        """Calculate overall confidence score and count review items."""
        total_fields = 0
        confident_fields = 0
        review_count = 0
        
        confidence_scores = {
            FieldConfidence.HIGH: 1.0,
            FieldConfidence.MEDIUM: 0.75,
            FieldConfidence.LOW: 0.5,
            FieldConfidence.GUESS: 0.25,
            FieldConfidence.EMPTY: 0.0,
        }
        
        for field_name in dir(self.result):
            if field_name.startswith('_'):
                continue
            field_obj = getattr(self.result, field_name, None)
            if isinstance(field_obj, ExtractedField):
                total_fields += 1
                confident_fields += confidence_scores.get(field_obj.confidence, 0)
                if field_obj.needs_review:
                    review_count += 1
        
        self.result.overall_confidence = confident_fields / total_fields if total_fields > 0 else 0
        self.result.fields_needing_review = review_count


# Singleton extractor
_extractor_instance: Optional[FormFieldExtractor] = None


def get_form_field_extractor() -> FormFieldExtractor:
    """Get form field extractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = FormFieldExtractor()
    return _extractor_instance
