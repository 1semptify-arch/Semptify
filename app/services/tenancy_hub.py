"""
Tenancy Documentation Hub

Central service for organizing, indexing, and cross-referencing all tenancy information.
This is the core data model for a complete tenancy case management system.

Categories of Information:
1. PARTIES - Tenant, Landlord, Property Manager, Attorneys, Witnesses
2. PROPERTY - Address, Unit, Building, Conditions, Photos
3. LEASE - Terms, Rent, Deposits, Rules, Amendments
4. PAYMENTS - Rent History, Receipts, Late Fees, Disputes
5. COMMUNICATIONS - Letters, Emails, Texts, Calls, Notices
6. DOCUMENTS - Lease, Notices, Court Papers, Evidence
7. TIMELINE - All Events in Chronological Order
8. ISSUES - Problems, Complaints, Violations, Repairs
9. LEGAL - Court Cases, Filings, Hearings, Deadlines
10. EVIDENCE - Photos, Videos, Recordings, Witnesses
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, List, Set
from enum import Enum
import re
import json
import hashlib
from pathlib import Path


# =============================================================================
# ENUMS - Category Classifications
# =============================================================================

class PartyRole(str, Enum):
    TENANT = "tenant"
    LANDLORD = "landlord"
    PROPERTY_MANAGER = "property_manager"
    ATTORNEY_TENANT = "attorney_tenant"
    ATTORNEY_LANDLORD = "attorney_landlord"
    WITNESS = "witness"
    JUDGE = "judge"
    PROCESS_SERVER = "process_server"
    MEDIATOR = "mediator"
    INSPECTOR = "inspector"
    CONTRACTOR = "contractor"
    OTHER = "other"


class DocumentCategory(str, Enum):
    LEASE = "lease"
    AMENDMENT = "amendment"
    NOTICE = "notice"
    EVICTION = "eviction"
    COURT_FILING = "court_filing"
    CORRESPONDENCE = "correspondence"
    PAYMENT_RECORD = "payment_record"
    PHOTO_EVIDENCE = "photo_evidence"
    VIDEO_EVIDENCE = "video_evidence"
    INSPECTION_REPORT = "inspection_report"
    REPAIR_REQUEST = "repair_request"
    LEGAL_FORM = "legal_form"
    IDENTIFICATION = "identification"
    OTHER = "other"


class EventType(str, Enum):
    # Lease Events
    LEASE_SIGNED = "lease_signed"
    LEASE_START = "lease_start"
    LEASE_END = "lease_end"
    LEASE_RENEWED = "lease_renewed"
    LEASE_TERMINATED = "lease_terminated"
    
    # Payment Events
    RENT_DUE = "rent_due"
    RENT_PAID = "rent_paid"
    RENT_LATE = "rent_late"
    LATE_FEE_CHARGED = "late_fee_charged"
    DEPOSIT_PAID = "deposit_paid"
    DEPOSIT_RETURNED = "deposit_returned"
    
    # Notice Events
    NOTICE_SENT = "notice_sent"
    NOTICE_RECEIVED = "notice_received"
    NOTICE_POSTED = "notice_posted"
    NOTICE_EXPIRED = "notice_expired"
    
    # Communication Events
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    LETTER_SENT = "letter_sent"
    LETTER_RECEIVED = "letter_received"
    PHONE_CALL = "phone_call"
    TEXT_MESSAGE = "text_message"
    IN_PERSON_MEETING = "in_person_meeting"
    
    # Issue Events
    ISSUE_REPORTED = "issue_reported"
    REPAIR_REQUESTED = "repair_requested"
    REPAIR_SCHEDULED = "repair_scheduled"
    REPAIR_COMPLETED = "repair_completed"
    INSPECTION_REQUESTED = "inspection_requested"
    INSPECTION_COMPLETED = "inspection_completed"
    VIOLATION_CITED = "violation_cited"
    
    # Legal Events
    COMPLAINT_FILED = "complaint_filed"
    SUMMONS_SERVED = "summons_served"
    ANSWER_DUE = "answer_due"
    ANSWER_FILED = "answer_filed"
    HEARING_SCHEDULED = "hearing_scheduled"
    HEARING_HELD = "hearing_held"
    MOTION_FILED = "motion_filed"
    ORDER_ISSUED = "order_issued"
    JUDGMENT_ENTERED = "judgment_entered"
    APPEAL_FILED = "appeal_filed"
    WRIT_ISSUED = "writ_issued"
    LOCKOUT_SCHEDULED = "lockout_scheduled"
    
    # Evidence Events
    PHOTO_TAKEN = "photo_taken"
    VIDEO_RECORDED = "video_recorded"
    WITNESS_STATEMENT = "witness_statement"
    DOCUMENT_RECEIVED = "document_received"
    
    # Other
    NOTE_ADDED = "note_added"
    OTHER = "other"


class IssueCategory(str, Enum):
    HABITABILITY = "habitability"
    MAINTENANCE = "maintenance"
    SAFETY = "safety"
    NOISE = "noise"
    PEST = "pest"
    MOLD = "mold"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HEATING_COOLING = "heating_cooling"
    STRUCTURAL = "structural"
    SECURITY = "security"
    LEASE_VIOLATION = "lease_violation"
    NEIGHBOR_DISPUTE = "neighbor_dispute"
    DISCRIMINATION = "discrimination"
    RETALIATION = "retaliation"
    ILLEGAL_ENTRY = "illegal_entry"
    HARASSMENT = "harassment"
    OTHER = "other"


class IssueSeverity(str, Enum):
    CRITICAL = "critical"      # Immediate health/safety risk
    HIGH = "high"              # Serious problem requiring urgent attention
    MEDIUM = "medium"          # Significant issue but not urgent
    LOW = "low"                # Minor issue
    INFORMATIONAL = "informational"  # For record keeping only


class CaseStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    APPEALED = "appealed"
    CLOSED = "closed"


# =============================================================================
# DATA CLASSES - Core Data Structures
# =============================================================================

@dataclass
class Party:
    """A person or entity involved in the tenancy."""
    id: str
    role: PartyRole
    name: str
    
    # Contact Information
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    phone: str = ""
    email: str = ""
    
    # Additional Details
    company_name: str = ""  # If representing a company
    attorney_bar_number: str = ""  # If attorney
    relationship_notes: str = ""
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    
    # Cross-references
    document_ids: List[str] = field(default_factory=list)
    event_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value if isinstance(self.role, PartyRole) else self.role,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "phone": self.phone,
            "email": self.email,
            "company_name": self.company_name,
            "attorney_bar_number": self.attorney_bar_number,
            "relationship_notes": self.relationship_notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "document_ids": self.document_ids,
            "event_ids": self.event_ids,
        }


@dataclass
class Property:
    """The rental property details."""
    id: str
    
    # Address
    street_address: str = ""
    unit_number: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    county: str = ""
    
    # Property Details
    property_type: str = ""  # apartment, house, townhouse, etc.
    bedrooms: int = 0
    bathrooms: float = 0.0
    square_feet: int = 0
    year_built: int = 0
    
    # Landlord/Management
    owner_id: str = ""  # Reference to Party
    manager_id: str = ""  # Reference to Party
    
    # Condition Notes
    move_in_condition: str = ""
    current_condition: str = ""
    condition_photos: List[str] = field(default_factory=list)  # Document IDs
    
    # Amenities
    amenities: List[str] = field(default_factory=list)
    utilities_included: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "street_address": self.street_address,
            "unit_number": self.unit_number,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "county": self.county,
            "property_type": self.property_type,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "square_feet": self.square_feet,
            "year_built": self.year_built,
            "owner_id": self.owner_id,
            "manager_id": self.manager_id,
            "move_in_condition": self.move_in_condition,
            "current_condition": self.current_condition,
            "condition_photos": self.condition_photos,
            "amenities": self.amenities,
            "utilities_included": self.utilities_included,
            "full_address": f"{self.street_address}{', ' + self.unit_number if self.unit_number else ''}, {self.city}, {self.state} {self.zip_code}",
        }


@dataclass
class LeaseTerms:
    """Lease agreement details."""
    id: str
    
    # Dates
    lease_start: str = ""
    lease_end: str = ""
    move_in_date: str = ""
    move_out_date: str = ""
    
    # Financial Terms
    monthly_rent: float = 0.0
    security_deposit: float = 0.0
    pet_deposit: float = 0.0
    last_month_rent: float = 0.0
    
    # Payment Details
    rent_due_day: int = 1  # Day of month rent is due
    grace_period_days: int = 0
    late_fee_amount: float = 0.0
    late_fee_type: str = "flat"  # flat, percentage, daily
    
    # Lease Type
    lease_type: str = "fixed"  # fixed, month-to-month
    auto_renewal: bool = False
    notice_to_vacate_days: int = 30
    
    # Occupants & Pets
    authorized_occupants: List[str] = field(default_factory=list)
    pets_allowed: bool = False
    pet_restrictions: str = ""
    
    # Utilities
    tenant_pays: List[str] = field(default_factory=list)
    landlord_pays: List[str] = field(default_factory=list)
    
    # Rules & Restrictions
    rules: List[str] = field(default_factory=list)
    parking_spaces: int = 0
    storage_included: bool = False
    
    # Document Reference
    lease_document_id: str = ""
    amendment_document_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "lease_start": self.lease_start,
            "lease_end": self.lease_end,
            "move_in_date": self.move_in_date,
            "move_out_date": self.move_out_date,
            "monthly_rent": self.monthly_rent,
            "security_deposit": self.security_deposit,
            "pet_deposit": self.pet_deposit,
            "last_month_rent": self.last_month_rent,
            "rent_due_day": self.rent_due_day,
            "grace_period_days": self.grace_period_days,
            "late_fee_amount": self.late_fee_amount,
            "late_fee_type": self.late_fee_type,
            "lease_type": self.lease_type,
            "auto_renewal": self.auto_renewal,
            "notice_to_vacate_days": self.notice_to_vacate_days,
            "authorized_occupants": self.authorized_occupants,
            "pets_allowed": self.pets_allowed,
            "pet_restrictions": self.pet_restrictions,
            "tenant_pays": self.tenant_pays,
            "landlord_pays": self.landlord_pays,
            "rules": self.rules,
            "parking_spaces": self.parking_spaces,
            "storage_included": self.storage_included,
            "lease_document_id": self.lease_document_id,
            "amendment_document_ids": self.amendment_document_ids,
        }


@dataclass
class Payment:
    """A payment record."""
    id: str
    
    # Payment Details
    payment_date: str = ""
    due_date: str = ""
    amount: float = 0.0
    payment_type: str = "rent"  # rent, deposit, late_fee, other
    payment_method: str = ""  # check, cash, online, money_order
    
    # Status
    status: str = "pending"  # pending, completed, bounced, disputed
    
    # Reference
    receipt_number: str = ""
    check_number: str = ""
    confirmation_number: str = ""
    
    # For Period
    period_start: str = ""
    period_end: str = ""
    
    # Notes
    notes: str = ""
    
    # Document Reference
    receipt_document_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "payment_date": self.payment_date,
            "due_date": self.due_date,
            "amount": self.amount,
            "payment_type": self.payment_type,
            "payment_method": self.payment_method,
            "status": self.status,
            "receipt_number": self.receipt_number,
            "check_number": self.check_number,
            "confirmation_number": self.confirmation_number,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "notes": self.notes,
            "receipt_document_id": self.receipt_document_id,
        }


@dataclass
class TenancyDocument:
    """A document in the tenancy case."""
    id: str
    
    # Document Info
    filename: str = ""
    title: str = ""
    category: DocumentCategory = DocumentCategory.OTHER
    description: str = ""
    
    # Dates
    document_date: str = ""  # Date on document
    received_date: str = ""  # When we got it
    created_at: str = ""
    
    # Content
    full_text: str = ""
    summary: str = ""
    key_points: List[str] = field(default_factory=list)
    
    # Extracted Data
    extracted_dates: List[Dict[str, Any]] = field(default_factory=list)
    extracted_amounts: List[Dict[str, Any]] = field(default_factory=list)
    extracted_parties: List[Dict[str, Any]] = field(default_factory=list)
    
    # Storage
    storage_path: str = ""
    content_hash: str = ""
    file_size: int = 0
    mime_type: str = ""
    
    # Cross-references
    related_party_ids: List[str] = field(default_factory=list)
    related_event_ids: List[str] = field(default_factory=list)
    related_issue_ids: List[str] = field(default_factory=list)
    
    # Tags for searching
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "title": self.title,
            "category": self.category.value if isinstance(self.category, DocumentCategory) else self.category,
            "description": self.description,
            "document_date": self.document_date,
            "received_date": self.received_date,
            "created_at": self.created_at,
            "summary": self.summary,
            "key_points": self.key_points,
            "extracted_dates": self.extracted_dates,
            "extracted_amounts": self.extracted_amounts,
            "extracted_parties": self.extracted_parties,
            "storage_path": self.storage_path,
            "content_hash": self.content_hash,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "related_party_ids": self.related_party_ids,
            "related_event_ids": self.related_event_ids,
            "related_issue_ids": self.related_issue_ids,
            "tags": self.tags,
        }


@dataclass
class TimelineEvent:
    """An event in the tenancy timeline."""
    id: str
    
    # Event Details
    event_type: EventType = EventType.OTHER
    event_date: str = ""
    event_time: str = ""
    title: str = ""
    description: str = ""
    
    # Location
    location: str = ""
    
    # Parties Involved
    party_ids: List[str] = field(default_factory=list)
    
    # Document References
    document_ids: List[str] = field(default_factory=list)
    
    # Deadline Info
    is_deadline: bool = False
    deadline_date: str = ""
    deadline_completed: bool = False
    
    # For Court Events
    case_number: str = ""
    court_name: str = ""
    judge_name: str = ""
    outcome: str = ""
    
    # Notes
    notes: str = ""
    
    # Metadata
    created_at: str = ""
    created_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "event_date": self.event_date,
            "event_time": self.event_time,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "party_ids": self.party_ids,
            "document_ids": self.document_ids,
            "is_deadline": self.is_deadline,
            "deadline_date": self.deadline_date,
            "deadline_completed": self.deadline_completed,
            "case_number": self.case_number,
            "court_name": self.court_name,
            "judge_name": self.judge_name,
            "outcome": self.outcome,
            "notes": self.notes,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }


@dataclass
class Issue:
    """A problem or complaint in the tenancy."""
    id: str
    
    # Issue Details
    category: IssueCategory = IssueCategory.OTHER
    severity: IssueSeverity = IssueSeverity.MEDIUM
    title: str = ""
    description: str = ""
    
    # Dates
    reported_date: str = ""
    resolved_date: str = ""
    
    # Status
    status: str = "open"  # open, in_progress, resolved, disputed
    
    # Location in Property
    location_in_property: str = ""  # kitchen, bathroom, etc.
    
    # Response
    landlord_response: str = ""
    landlord_response_date: str = ""
    
    # Resolution
    resolution: str = ""
    resolution_satisfactory: bool = False
    
    # Evidence
    photo_ids: List[str] = field(default_factory=list)
    document_ids: List[str] = field(default_factory=list)
    
    # Related Events
    event_ids: List[str] = field(default_factory=list)
    
    # Legal Relevance
    is_habitability_issue: bool = False
    is_lease_violation: bool = False
    violates_statute: str = ""  # Reference to specific law
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value if isinstance(self.category, IssueCategory) else self.category,
            "severity": self.severity.value if isinstance(self.severity, IssueSeverity) else self.severity,
            "title": self.title,
            "description": self.description,
            "reported_date": self.reported_date,
            "resolved_date": self.resolved_date,
            "status": self.status,
            "location_in_property": self.location_in_property,
            "landlord_response": self.landlord_response,
            "landlord_response_date": self.landlord_response_date,
            "resolution": self.resolution,
            "resolution_satisfactory": self.resolution_satisfactory,
            "photo_ids": self.photo_ids,
            "document_ids": self.document_ids,
            "event_ids": self.event_ids,
            "is_habitability_issue": self.is_habitability_issue,
            "is_lease_violation": self.is_lease_violation,
            "violates_statute": self.violates_statute,
        }


@dataclass
class LegalCase:
    """A court case related to the tenancy."""
    id: str
    
    # Case Info
    case_number: str = ""
    case_type: str = ""  # eviction, small_claims, housing_court
    court_name: str = ""
    county: str = ""
    judicial_district: str = ""
    
    # Status
    status: CaseStatus = CaseStatus.ACTIVE
    
    # Parties in Case
    plaintiff_ids: List[str] = field(default_factory=list)
    defendant_ids: List[str] = field(default_factory=list)
    
    # Key Dates
    filed_date: str = ""
    served_date: str = ""
    answer_due_date: str = ""
    hearing_date: str = ""
    hearing_time: str = ""
    
    # Claims
    amount_claimed: float = 0.0
    claims: List[str] = field(default_factory=list)
    
    # Defense
    defenses: List[str] = field(default_factory=list)
    counterclaims: List[str] = field(default_factory=list)
    
    # Outcome
    outcome: str = ""
    judgment_amount: float = 0.0
    judgment_date: str = ""
    
    # Documents
    complaint_document_id: str = ""
    summons_document_id: str = ""
    answer_document_id: str = ""
    related_document_ids: List[str] = field(default_factory=list)
    
    # Events
    event_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "case_number": self.case_number,
            "case_type": self.case_type,
            "court_name": self.court_name,
            "county": self.county,
            "judicial_district": self.judicial_district,
            "status": self.status.value if isinstance(self.status, CaseStatus) else self.status,
            "plaintiff_ids": self.plaintiff_ids,
            "defendant_ids": self.defendant_ids,
            "filed_date": self.filed_date,
            "served_date": self.served_date,
            "answer_due_date": self.answer_due_date,
            "hearing_date": self.hearing_date,
            "hearing_time": self.hearing_time,
            "amount_claimed": self.amount_claimed,
            "claims": self.claims,
            "defenses": self.defenses,
            "counterclaims": self.counterclaims,
            "outcome": self.outcome,
            "judgment_amount": self.judgment_amount,
            "judgment_date": self.judgment_date,
            "complaint_document_id": self.complaint_document_id,
            "summons_document_id": self.summons_document_id,
            "answer_document_id": self.answer_document_id,
            "related_document_ids": self.related_document_ids,
            "event_ids": self.event_ids,
        }


# =============================================================================
# TENANCY CASE - The Master Container
# =============================================================================

@dataclass
class TenancyCase:
    """
    The master container for all tenancy information.
    This is the central hub that ties everything together.
    """
    id: str
    user_id: str
    
    # Case Metadata
    case_name: str = ""  # User-friendly name
    status: str = "active"  # active, resolved, archived
    created_at: str = ""
    updated_at: str = ""
    
    # Core Entities
    tenant: Optional[Party] = None
    landlord: Optional[Party] = None
    property: Optional[Property] = None
    lease: Optional[LeaseTerms] = None
    
    # Collections
    parties: Dict[str, Party] = field(default_factory=dict)
    documents: Dict[str, TenancyDocument] = field(default_factory=dict)
    events: Dict[str, TimelineEvent] = field(default_factory=dict)
    payments: Dict[str, Payment] = field(default_factory=dict)
    issues: Dict[str, Issue] = field(default_factory=dict)
    legal_cases: Dict[str, LegalCase] = field(default_factory=dict)
    
    # Search Index
    _index: Dict[str, Set[str]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "case_name": self.case_name,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tenant": self.tenant.to_dict() if self.tenant else None,
            "landlord": self.landlord.to_dict() if self.landlord else None,
            "property": self.property.to_dict() if self.property else None,
            "lease": self.lease.to_dict() if self.lease else None,
            "parties": {k: v.to_dict() for k, v in self.parties.items()},
            "documents": {k: v.to_dict() for k, v in self.documents.items()},
            "events": {k: v.to_dict() for k, v in self.events.items()},
            "payments": {k: v.to_dict() for k, v in self.payments.items()},
            "issues": {k: v.to_dict() for k, v in self.issues.items()},
            "legal_cases": {k: v.to_dict() for k, v in self.legal_cases.items()},
            "summary": self.get_summary(),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a high-level summary of the case."""
        return {
            "total_parties": len(self.parties),
            "total_documents": len(self.documents),
            "total_events": len(self.events),
            "total_payments": len(self.payments),
            "total_issues": len(self.issues),
            "total_legal_cases": len(self.legal_cases),
            "open_issues": sum(1 for i in self.issues.values() if i.status == "open"),
            "pending_deadlines": sum(1 for e in self.events.values() if e.is_deadline and not e.deadline_completed),
            "monthly_rent": self.lease.monthly_rent if self.lease else 0,
            "property_address": self.property.to_dict().get("full_address", "") if self.property else "",
        }


# =============================================================================
# TENANCY HUB SERVICE - The Brain
# =============================================================================

class TenancyHubService:
    """
    Central service for managing tenancy cases.
    Provides indexing, search, and cross-referencing capabilities.
    """
    
    def __init__(self):
        self.cases: Dict[str, TenancyCase] = {}
        self._global_index: Dict[str, Dict[str, Set[str]]] = {}  # term -> {case_id -> set of entity_ids}
    
    def create_case(self, user_id: str, case_name: str = "") -> TenancyCase:
        """Create a new tenancy case."""
        case_id = self._generate_id("case")
        now = datetime.now(timezone.utc).isoformat()
        
        case = TenancyCase(
            id=case_id,
            user_id=user_id,
            case_name=case_name or f"Tenancy Case {case_id[:8]}",
            created_at=now,
            updated_at=now,
        )
        
        self.cases[case_id] = case
        return case
    
    def get_case(self, case_id: str) -> Optional[TenancyCase]:
        """Get a case by ID."""
        return self.cases.get(case_id)
    
    def get_user_cases(self, user_id: str) -> List[TenancyCase]:
        """Get all cases for a user."""
        return [c for c in self.cases.values() if c.user_id == user_id]
    
    # -------------------------------------------------------------------------
    # Party Management
    # -------------------------------------------------------------------------
    
    def add_party(self, case_id: str, party: Party) -> Party:
        """Add a party to a case."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        if not party.id:
            party.id = self._generate_id("party")
        
        party.created_at = datetime.now(timezone.utc).isoformat()
        party.updated_at = party.created_at
        
        case.parties[party.id] = party
        
        # Set as tenant/landlord if appropriate
        if party.role == PartyRole.TENANT and not case.tenant:
            case.tenant = party
        elif party.role == PartyRole.LANDLORD and not case.landlord:
            case.landlord = party
        
        # Index the party
        self._index_entity(case_id, "party", party.id, [
            party.name, party.email, party.phone, party.address,
            party.city, party.company_name
        ])
        
        case.updated_at = datetime.now(timezone.utc).isoformat()
        return party
    
    # -------------------------------------------------------------------------
    # Document Management
    # -------------------------------------------------------------------------
    
    def add_document(self, case_id: str, document: TenancyDocument) -> TenancyDocument:
        """Add a document to a case."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        if not document.id:
            document.id = self._generate_id("doc")
        
        document.created_at = datetime.now(timezone.utc).isoformat()
        
        case.documents[document.id] = document
        
        # Index the document
        self._index_entity(case_id, "document", document.id, [
            document.filename, document.title, document.description,
            document.summary, document.full_text[:1000] if document.full_text else "",
        ] + document.tags + document.key_points)
        
        case.updated_at = datetime.now(timezone.utc).isoformat()
        return document
    
    # -------------------------------------------------------------------------
    # Event Management
    # -------------------------------------------------------------------------
    
    def add_event(self, case_id: str, event: TimelineEvent) -> TimelineEvent:
        """Add an event to a case."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        if not event.id:
            event.id = self._generate_id("event")
        
        event.created_at = datetime.now(timezone.utc).isoformat()
        
        case.events[event.id] = event
        
        # Index the event
        self._index_entity(case_id, "event", event.id, [
            event.title, event.description, event.location,
            event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
            event.case_number, event.court_name,
        ])
        
        case.updated_at = datetime.now(timezone.utc).isoformat()
        return event
    
    # -------------------------------------------------------------------------
    # Payment Management
    # -------------------------------------------------------------------------
    
    def add_payment(self, case_id: str, payment: Payment) -> Payment:
        """Add a payment to a case."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        if not payment.id:
            payment.id = self._generate_id("payment")
        
        case.payments[payment.id] = payment
        
        # Index the payment
        self._index_entity(case_id, "payment", payment.id, [
            payment.payment_type, payment.payment_method,
            payment.receipt_number, payment.check_number,
            str(payment.amount),
        ])
        
        case.updated_at = datetime.now(timezone.utc).isoformat()
        return payment
    
    # -------------------------------------------------------------------------
    # Issue Management
    # -------------------------------------------------------------------------
    
    def add_issue(self, case_id: str, issue: Issue) -> Issue:
        """Add an issue to a case."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        if not issue.id:
            issue.id = self._generate_id("issue")
        
        case.issues[issue.id] = issue
        
        # Index the issue
        self._index_entity(case_id, "issue", issue.id, [
            issue.title, issue.description,
            issue.category.value if isinstance(issue.category, IssueCategory) else issue.category,
            issue.location_in_property, issue.resolution,
        ])
        
        case.updated_at = datetime.now(timezone.utc).isoformat()
        return issue
    
    # -------------------------------------------------------------------------
    # Legal Case Management
    # -------------------------------------------------------------------------
    
    def add_legal_case(self, case_id: str, legal_case: LegalCase) -> LegalCase:
        """Add a legal case to a tenancy case."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        if not legal_case.id:
            legal_case.id = self._generate_id("legal")
        
        case.legal_cases[legal_case.id] = legal_case
        
        # Index the legal case
        self._index_entity(case_id, "legal_case", legal_case.id, [
            legal_case.case_number, legal_case.court_name,
            legal_case.county, legal_case.case_type,
        ] + legal_case.claims + legal_case.defenses)
        
        case.updated_at = datetime.now(timezone.utc).isoformat()
        return legal_case
    
    # -------------------------------------------------------------------------
    # Search & Cross-Reference
    # -------------------------------------------------------------------------
    
    def search(self, case_id: str, query: str, entity_types: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across all entities in a case.
        
        Args:
            case_id: The case to search in
            query: Search query (keywords)
            entity_types: Filter to specific types (party, document, event, payment, issue, legal_case)
        
        Returns:
            Dict mapping entity type to list of matching entities
        """
        case = self.get_case(case_id)
        if not case:
            return {}
        
        results = {
            "parties": [],
            "documents": [],
            "events": [],
            "payments": [],
            "issues": [],
            "legal_cases": [],
        }
        
        # Normalize query
        terms = self._tokenize(query)
        
        # Search each entity type
        if not entity_types or "party" in entity_types:
            for party in case.parties.values():
                if self._matches(party, terms):
                    results["parties"].append(party.to_dict())
        
        if not entity_types or "document" in entity_types:
            for doc in case.documents.values():
                if self._matches(doc, terms):
                    results["documents"].append(doc.to_dict())
        
        if not entity_types or "event" in entity_types:
            for event in case.events.values():
                if self._matches(event, terms):
                    results["events"].append(event.to_dict())
        
        if not entity_types or "payment" in entity_types:
            for payment in case.payments.values():
                if self._matches(payment, terms):
                    results["payments"].append(payment.to_dict())
        
        if not entity_types or "issue" in entity_types:
            for issue in case.issues.values():
                if self._matches(issue, terms):
                    results["issues"].append(issue.to_dict())
        
        if not entity_types or "legal_case" in entity_types:
            for legal_case in case.legal_cases.values():
                if self._matches(legal_case, terms):
                    results["legal_cases"].append(legal_case.to_dict())
        
        return results
    
    def get_timeline(self, case_id: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get chronological timeline of all events."""
        case = self.get_case(case_id)
        if not case:
            return []
        
        events = list(case.events.values())
        
        # Filter by date if specified
        if start_date:
            events = [e for e in events if e.event_date >= start_date]
        if end_date:
            events = [e for e in events if e.event_date <= end_date]
        
        # Sort by date
        events.sort(key=lambda e: e.event_date or "9999-99-99")
        
        return [e.to_dict() for e in events]
    
    def get_deadlines(self, case_id: str, include_completed: bool = False) -> List[Dict[str, Any]]:
        """Get all deadlines for a case."""
        case = self.get_case(case_id)
        if not case:
            return []
        
        deadlines = [e for e in case.events.values() if e.is_deadline]
        
        if not include_completed:
            deadlines = [d for d in deadlines if not d.deadline_completed]
        
        # Sort by deadline date
        deadlines.sort(key=lambda d: d.deadline_date or d.event_date or "9999-99-99")
        
        return [d.to_dict() for d in deadlines]
    
    def get_cross_references(self, case_id: str, entity_type: str, entity_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all entities that reference the given entity.
        
        For example, get all documents that reference a specific party,
        or all events related to a specific issue.
        """
        case = self.get_case(case_id)
        if not case:
            return {}
        
        refs = {
            "parties": [],
            "documents": [],
            "events": [],
            "issues": [],
            "legal_cases": [],
        }
        
        # Find references based on entity type
        if entity_type == "party":
            # Find documents referencing this party
            for doc in case.documents.values():
                if entity_id in doc.related_party_ids:
                    refs["documents"].append(doc.to_dict())
            
            # Find events with this party
            for event in case.events.values():
                if entity_id in event.party_ids:
                    refs["events"].append(event.to_dict())
            
            # Find legal cases with this party
            for legal_case in case.legal_cases.values():
                if entity_id in legal_case.plaintiff_ids or entity_id in legal_case.defendant_ids:
                    refs["legal_cases"].append(legal_case.to_dict())
        
        elif entity_type == "document":
            # Find parties referenced by this document
            doc = case.documents.get(entity_id)
            if doc:
                for party_id in doc.related_party_ids:
                    if party_id in case.parties:
                        refs["parties"].append(case.parties[party_id].to_dict())
                
                for event_id in doc.related_event_ids:
                    if event_id in case.events:
                        refs["events"].append(case.events[event_id].to_dict())
                
                for issue_id in doc.related_issue_ids:
                    if issue_id in case.issues:
                        refs["issues"].append(case.issues[issue_id].to_dict())
        
        elif entity_type == "event":
            event = case.events.get(entity_id)
            if event:
                for party_id in event.party_ids:
                    if party_id in case.parties:
                        refs["parties"].append(case.parties[party_id].to_dict())
                
                for doc_id in event.document_ids:
                    if doc_id in case.documents:
                        refs["documents"].append(case.documents[doc_id].to_dict())
        
        elif entity_type == "issue":
            issue = case.issues.get(entity_id)
            if issue:
                for photo_id in issue.photo_ids:
                    if photo_id in case.documents:
                        refs["documents"].append(case.documents[photo_id].to_dict())
                
                for doc_id in issue.document_ids:
                    if doc_id in case.documents:
                        refs["documents"].append(case.documents[doc_id].to_dict())
                
                for event_id in issue.event_ids:
                    if event_id in case.events:
                        refs["events"].append(case.events[event_id].to_dict())
        
        return refs
    
    def get_context_pack(self, case_id: str, context: str) -> Dict[str, Any]:
        """
        Get a context-specific pack of information.
        
        Contexts:
        - "court_hearing": All info needed for a court hearing
        - "repair_history": All issues and repairs
        - "payment_history": All payment records
        - "communication_log": All communications
        - "evidence_pack": All evidence documents
        - "lease_summary": Lease terms and amendments
        """
        case = self.get_case(case_id)
        if not case:
            return {}
        
        if context == "court_hearing":
            return self._get_court_hearing_pack(case)
        elif context == "repair_history":
            return self._get_repair_history_pack(case)
        elif context == "payment_history":
            return self._get_payment_history_pack(case)
        elif context == "communication_log":
            return self._get_communication_log_pack(case)
        elif context == "evidence_pack":
            return self._get_evidence_pack(case)
        elif context == "lease_summary":
            return self._get_lease_summary_pack(case)
        else:
            return {"error": f"Unknown context: {context}"}
    
    # -------------------------------------------------------------------------
    # Context Pack Generators
    # -------------------------------------------------------------------------
    
    def _get_court_hearing_pack(self, case: TenancyCase) -> Dict[str, Any]:
        """Get all info needed for a court hearing."""
        pack = {
            "case_info": {},
            "parties": [],
            "legal_cases": [],
            "key_documents": [],
            "timeline": [],
            "issues": [],
            "defenses": [],
            "deadlines": [],
        }
        
        # Basic case info
        pack["case_info"] = {
            "tenant": case.tenant.to_dict() if case.tenant else None,
            "landlord": case.landlord.to_dict() if case.landlord else None,
            "property": case.property.to_dict() if case.property else None,
            "lease": case.lease.to_dict() if case.lease else None,
        }
        
        # Legal cases
        pack["legal_cases"] = [lc.to_dict() for lc in case.legal_cases.values()]
        
        # Key documents (court filings, notices, evidence)
        court_docs = [d for d in case.documents.values() 
                      if d.category in [DocumentCategory.COURT_FILING, DocumentCategory.NOTICE, 
                                        DocumentCategory.EVICTION, DocumentCategory.PHOTO_EVIDENCE]]
        pack["key_documents"] = [d.to_dict() for d in court_docs]
        
        # Timeline of court-related events
        court_events = [e for e in case.events.values() 
                        if e.event_type.value.startswith(('hearing', 'complaint', 'summons', 
                                                          'answer', 'motion', 'order', 'judgment'))]
        court_events.sort(key=lambda e: e.event_date or "")
        pack["timeline"] = [e.to_dict() for e in court_events]
        
        # Issues (especially habitability)
        pack["issues"] = [i.to_dict() for i in case.issues.values()]
        
        # Deadlines
        pack["deadlines"] = self.get_deadlines(case.id)
        
        return pack
    
    def _get_repair_history_pack(self, case: TenancyCase) -> Dict[str, Any]:
        """Get repair and maintenance history."""
        pack = {
            "issues": [],
            "repair_events": [],
            "photos": [],
            "communications": [],
        }
        
        # All issues
        issues = list(case.issues.values())
        issues.sort(key=lambda i: i.reported_date or "")
        pack["issues"] = [i.to_dict() for i in issues]
        
        # Repair-related events
        repair_types = [EventType.ISSUE_REPORTED, EventType.REPAIR_REQUESTED,
                        EventType.REPAIR_SCHEDULED, EventType.REPAIR_COMPLETED,
                        EventType.INSPECTION_REQUESTED, EventType.INSPECTION_COMPLETED]
        repair_events = [e for e in case.events.values() if e.event_type in repair_types]
        repair_events.sort(key=lambda e: e.event_date or "")
        pack["repair_events"] = [e.to_dict() for e in repair_events]
        
        # Photo evidence
        photos = [d for d in case.documents.values() if d.category == DocumentCategory.PHOTO_EVIDENCE]
        pack["photos"] = [p.to_dict() for p in photos]
        
        return pack
    
    def _get_payment_history_pack(self, case: TenancyCase) -> Dict[str, Any]:
        """Get payment history."""
        pack = {
            "lease_terms": None,
            "payments": [],
            "payment_events": [],
            "summary": {},
        }
        
        if case.lease:
            pack["lease_terms"] = {
                "monthly_rent": case.lease.monthly_rent,
                "rent_due_day": case.lease.rent_due_day,
                "late_fee_amount": case.lease.late_fee_amount,
                "security_deposit": case.lease.security_deposit,
            }
        
        # All payments sorted by date
        payments = list(case.payments.values())
        payments.sort(key=lambda p: p.payment_date or "")
        pack["payments"] = [p.to_dict() for p in payments]
        
        # Payment events
        payment_types = [EventType.RENT_DUE, EventType.RENT_PAID, EventType.RENT_LATE,
                         EventType.LATE_FEE_CHARGED, EventType.DEPOSIT_PAID, EventType.DEPOSIT_RETURNED]
        payment_events = [e for e in case.events.values() if e.event_type in payment_types]
        payment_events.sort(key=lambda e: e.event_date or "")
        pack["payment_events"] = [e.to_dict() for e in payment_events]
        
        # Summary
        total_paid = sum(p.amount for p in payments if p.status == "completed")
        total_rent = sum(p.amount for p in payments if p.payment_type == "rent" and p.status == "completed")
        pack["summary"] = {
            "total_paid": total_paid,
            "total_rent_paid": total_rent,
            "payment_count": len(payments),
        }
        
        return pack
    
    def _get_communication_log_pack(self, case: TenancyCase) -> Dict[str, Any]:
        """Get all communications."""
        pack = {
            "communications": [],
            "documents": [],
        }
        
        # Communication events
        comm_types = [EventType.EMAIL_SENT, EventType.EMAIL_RECEIVED,
                      EventType.LETTER_SENT, EventType.LETTER_RECEIVED,
                      EventType.PHONE_CALL, EventType.TEXT_MESSAGE,
                      EventType.IN_PERSON_MEETING, EventType.NOTICE_SENT,
                      EventType.NOTICE_RECEIVED, EventType.NOTICE_POSTED]
        comm_events = [e for e in case.events.values() if e.event_type in comm_types]
        comm_events.sort(key=lambda e: e.event_date or "")
        pack["communications"] = [e.to_dict() for e in comm_events]
        
        # Correspondence documents
        docs = [d for d in case.documents.values() 
                if d.category in [DocumentCategory.CORRESPONDENCE, DocumentCategory.NOTICE]]
        docs.sort(key=lambda d: d.document_date or "")
        pack["documents"] = [d.to_dict() for d in docs]
        
        return pack
    
    def _get_evidence_pack(self, case: TenancyCase) -> Dict[str, Any]:
        """Get all evidence."""
        pack = {
            "photos": [],
            "videos": [],
            "documents": [],
            "witness_statements": [],
        }
        
        for doc in case.documents.values():
            if doc.category == DocumentCategory.PHOTO_EVIDENCE:
                pack["photos"].append(doc.to_dict())
            elif doc.category == DocumentCategory.VIDEO_EVIDENCE:
                pack["videos"].append(doc.to_dict())
            else:
                pack["documents"].append(doc.to_dict())
        
        # Witness statement events
        witness_events = [e for e in case.events.values() if e.event_type == EventType.WITNESS_STATEMENT]
        pack["witness_statements"] = [e.to_dict() for e in witness_events]
        
        return pack
    
    def _get_lease_summary_pack(self, case: TenancyCase) -> Dict[str, Any]:
        """Get lease summary and amendments."""
        pack = {
            "lease": None,
            "amendments": [],
            "lease_document": None,
            "amendment_documents": [],
        }
        
        if case.lease:
            pack["lease"] = case.lease.to_dict()
            
            # Get lease document
            if case.lease.lease_document_id and case.lease.lease_document_id in case.documents:
                pack["lease_document"] = case.documents[case.lease.lease_document_id].to_dict()
            
            # Get amendment documents
            for doc_id in case.lease.amendment_document_ids:
                if doc_id in case.documents:
                    pack["amendment_documents"].append(case.documents[doc_id].to_dict())
        
        return pack
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for searching."""
        if not text:
            return []
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.split(r'[^a-z0-9]+', text)
        return [t for t in tokens if len(t) > 1]
    
    def _index_entity(self, case_id: str, entity_type: str, entity_id: str, texts: List[str]):
        """Index an entity for searching."""
        if case_id not in self._global_index:
            self._global_index[case_id] = {}
        
        for text in texts:
            for term in self._tokenize(text):
                if term not in self._global_index[case_id]:
                    self._global_index[case_id][term] = set()
                self._global_index[case_id][term].add(f"{entity_type}:{entity_id}")
    
    def _matches(self, entity: Any, terms: List[str]) -> bool:
        """Check if an entity matches search terms."""
        entity_dict = entity.to_dict() if hasattr(entity, 'to_dict') else entity
        entity_text = json.dumps(entity_dict).lower()
        
        # All terms must match
        return all(term in entity_text for term in terms)


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_tenancy_hub_service: Optional[TenancyHubService] = None


def get_tenancy_hub_service() -> TenancyHubService:
    """Get the singleton TenancyHubService instance."""
    global _tenancy_hub_service
    if _tenancy_hub_service is None:
        _tenancy_hub_service = TenancyHubService()
    return _tenancy_hub_service
