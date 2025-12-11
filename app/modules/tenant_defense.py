"""
Tenant Defense Module
=====================

Comprehensive tenant defense toolkit that helps tenants:
- Collect and index evidence for their case
- Prepare sealing/expungement petitions
- Generate demand letters for landlords
- Dispute screening service reports
- Track case progress through court

This module integrates with the Semptify Positronic Mesh for
workflow orchestration and inter-module communication.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.sdk.module_sdk import (
    ModuleSDK,
    ModuleDefinition,
    ModuleCategory,
    DocumentType,
    PackType,
)

logger = logging.getLogger(__name__)

# =============================================================================
# API Router
# =============================================================================

router = APIRouter(prefix="/api/tenant-defense", tags=["Tenant Defense"])


# =============================================================================
# MODULE DEFINITION
# =============================================================================

module_definition = ModuleDefinition(
    name="tenant_defense",
    display_name="Tenant Defense Module",
    description="Comprehensive tenant defense toolkit for evidence collection, "
                "sealing petitions, demand letters, and screening disputes",
    version="1.0.0",
    category=ModuleCategory.LEGAL,
    
    # Document types this module can process
    handles_documents=[
        DocumentType.COURT_FILING,
        DocumentType.PAYMENT_RECORD,
        DocumentType.COMMUNICATION,
        DocumentType.PHOTO,
        DocumentType.EVICTION_NOTICE,
        DocumentType.LEASE,
    ],
    
    # Info pack types this module accepts
    accepts_packs=[
        PackType.CASE_DATA,
        PackType.USER_DATA,
        PackType.EVICTION_DATA,
        PackType.LEASE_DATA,
    ],
    
    # Info pack types this module produces
    produces_packs=[
        PackType.ANALYSIS_RESULT,
        PackType.CASE_DATA,
        PackType.FORM_DATA,
        PackType.DEADLINE_DATA,
    ],
    
    # Dependencies on other modules
    depends_on=[
        "documents",
        "timeline",
        "calendar",
        "forms",
        "eviction_defense",
    ],
    
    has_ui=True,
    has_background_tasks=True,
    requires_auth=True,
)


# =============================================================================
# CREATE SDK INSTANCE
# =============================================================================

sdk = ModuleSDK(module_definition)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class EvidenceItem(BaseModel):
    """A single piece of evidence"""
    id: str = Field(default_factory=lambda: f"evid_{uuid.uuid4().hex[:12]}")
    type: str  # document, photo, communication, witness, payment
    title: str
    description: Optional[str] = None
    document_id: Optional[str] = None  # Link to document registry
    date_collected: datetime = Field(default_factory=datetime.utcnow)
    relevance_score: int = 5  # 1-10, how relevant to the case
    tags: List[str] = []


class EvidenceIndex(BaseModel):
    """Index of collected evidence for a case"""
    id: str
    case_id: str
    user_id: str
    items: List[EvidenceItem] = []
    total_count: int = 0
    categories: Dict[str, int] = {}  # Count by type
    created_at: datetime
    updated_at: datetime


class SealingPetition(BaseModel):
    """Sealing/expungement petition draft"""
    petition_id: str
    case_id: str
    user_id: str
    court_name: str = "Minnesota District Court"
    petition_type: str = "expungement"  # expungement, sealing
    draft_text: str
    checklist: List[str]
    required_documents: List[str]
    filing_fee: Optional[float] = None
    deadline: Optional[datetime] = None
    status: str = "draft"  # draft, ready, filed, granted, denied
    created_at: datetime


class DemandLetter(BaseModel):
    """Demand letter to landlord or property manager"""
    letter_id: str
    case_id: str
    tenant_name: str
    landlord_name: str
    landlord_address: Optional[str] = None
    property_address: Optional[str] = None
    demand_type: str  # withdrawal, correction, repair, refund
    letter_text: str
    response_deadline: datetime
    sent_via: Optional[str] = None  # certified_mail, email, hand_delivered
    sent_date: Optional[datetime] = None
    response_received: bool = False
    created_at: datetime


class ScreeningDispute(BaseModel):
    """Tenant screening service dispute"""
    dispute_id: str
    user_id: str
    screening_company: str
    disputed_items: List[str]
    correct_information: Dict[str, str]
    supporting_documents: List[str]
    dispute_letter: str
    submitted_date: Optional[datetime] = None
    response_deadline: datetime
    status: str = "pending"  # pending, submitted, under_review, resolved, escalated


class CaseProgress(BaseModel):
    """Track overall case progress"""
    case_id: str
    user_id: str
    status: str = "active"  # active, pending_court, settled, dismissed, won, lost
    evidence_count: int = 0
    forms_completed: int = 0
    deadlines_met: int = 0
    deadlines_missed: int = 0
    next_deadline: Optional[datetime] = None
    next_action: Optional[str] = None
    strength_score: int = 0  # 0-100, case strength estimate
    created_at: datetime
    updated_at: datetime


# Request/Response Models
class CollectEvidenceRequest(BaseModel):
    case_id: str
    evidence: List[EvidenceItem]


class SealingPetitionRequest(BaseModel):
    case_id: str
    petition_type: str = "expungement"
    court_county: str = "Dakota"
    reason_for_sealing: Optional[str] = None


class DemandLetterRequest(BaseModel):
    case_id: str
    tenant_name: str
    landlord_name: str
    landlord_address: Optional[str] = None
    property_address: Optional[str] = None
    demand_type: str = "withdrawal"
    specific_demands: Optional[List[str]] = None


class ScreeningDisputeRequest(BaseModel):
    screening_company: str
    disputed_items: List[str]
    correct_information: Dict[str, str]
    supporting_document_ids: List[str] = []


class ActionRequest(BaseModel):
    """Generic action request for SDK actions"""
    user_id: str
    params: Dict[str, Any] = {}
    context: Optional[Dict[str, Any]] = None


class ActionResponse(BaseModel):
    """Generic action response"""
    success: bool
    result: Dict[str, Any] = {}
    error: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _make_id(prefix: str = "id") -> str:
    """Generate a unique ID with prefix"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _calculate_case_strength(
    evidence_count: int,
    has_lease: bool,
    has_payment_records: bool,
    has_communications: bool,
    deadlines_met: int,
    deadlines_missed: int,
) -> int:
    """Calculate case strength score (0-100)"""
    score = 0
    
    # Evidence strength (up to 40 points)
    score += min(evidence_count * 5, 40)
    
    # Key documents (up to 30 points)
    if has_lease:
        score += 15
    if has_payment_records:
        score += 10
    if has_communications:
        score += 5
    
    # Deadline compliance (up to 30 points)
    total_deadlines = deadlines_met + deadlines_missed
    if total_deadlines > 0:
        compliance_rate = deadlines_met / total_deadlines
        score += int(compliance_rate * 30)
    else:
        score += 15  # Neutral if no deadlines yet
    
    return min(score, 100)


# =============================================================================
# IN-MEMORY STORAGE (Replace with database in production)
# =============================================================================

_evidence_indices: Dict[str, EvidenceIndex] = {}
_petitions: Dict[str, SealingPetition] = {}
_demand_letters: Dict[str, DemandLetter] = {}
_screening_disputes: Dict[str, ScreeningDispute] = {}
_case_progress: Dict[str, CaseProgress] = {}


# =============================================================================
# SDK ACTION HANDLERS
# =============================================================================

@sdk.action(
    "collect_evidence",
    description="Store and index evidence for a tenant defense case",
    required_params=["case_id", "evidence"],
    produces=["evidence_index_id", "evidence_index"],
)
async def collect_evidence(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Collect and index evidence for a case.
    
    Each piece of evidence is categorized and linked to documents
    in the Semptify vault for chain of custody tracking.
    """
    case_id = params.get("case_id")
    evidence_items = params.get("evidence", [])
    
    if not case_id:
        raise ValueError("case_id is required")
    if not evidence_items:
        raise ValueError("At least one evidence item is required")
    
    logger.info(f"tenant_defense: Collecting {len(evidence_items)} evidence items for case {case_id}")
    
    # Get or create evidence index
    index_key = f"{user_id}:{case_id}"
    if index_key in _evidence_indices:
        index = _evidence_indices[index_key]
    else:
        index = EvidenceIndex(
            id=_make_id("eidx"),
            case_id=case_id,
            user_id=user_id,
            items=[],
            total_count=0,
            categories={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    
    # Add new evidence items
    for item_data in evidence_items:
        if isinstance(item_data, dict):
            item = EvidenceItem(**item_data)
        else:
            item = item_data
        
        index.items.append(item)
        index.total_count += 1
        
        # Update category counts
        category = item.type
        index.categories[category] = index.categories.get(category, 0) + 1
    
    index.updated_at = datetime.utcnow()
    _evidence_indices[index_key] = index
    
    # Create info pack for other modules
    sdk.create_pack(
        pack_type=PackType.CASE_DATA,
        user_id=user_id,
        data={
            "case_id": case_id,
            "evidence_index_id": index.id,
            "evidence_count": index.total_count,
            "categories": index.categories,
        },
        target_module=None,  # Broadcast to all
        priority=7,
    )
    
    return {
        "evidence_index_id": index.id,
        "evidence_index": index.model_dump(),
    }


@sdk.action(
    "prepare_sealing_petition",
    description="Generate a sealing/expungement petition draft with checklist",
    required_params=["case_id"],
    optional_params=["petition_type", "court_county", "reason_for_sealing"],
    produces=["petition_id", "petition", "checklist"],
)
async def prepare_sealing_petition(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate a sealing or expungement petition draft.
    
    Under Minnesota law, certain eviction records can be sealed:
    - Dismissed cases
    - Cases where tenant prevailed
    - Settled cases with sealing agreement
    - Cases older than specified time period
    """
    case_id = params.get("case_id")
    petition_type = params.get("petition_type", "expungement")
    court_county = params.get("court_county", "Dakota")
    reason = params.get("reason_for_sealing", "Case was dismissed")
    
    if not case_id:
        raise ValueError("case_id is required")
    
    logger.info(f"tenant_defense: Preparing {petition_type} petition for case {case_id}")
    
    petition_id = _make_id("pet")
    now = datetime.utcnow()
    
    # Minnesota-specific petition text
    draft_text = f"""STATE OF MINNESOTA                    DISTRICT COURT
COUNTY OF {court_county.upper()}                   HOUSING COURT

In the Matter of:                     Case No: {case_id}
Petition for Expungement of
Eviction Record

PETITION FOR EXPUNGEMENT

TO THE ABOVE-NAMED COURT:

The undersigned Petitioner respectfully states:

1. IDENTITY: Petitioner was a party to an eviction action in this Court.

2. CASE INFORMATION: 
   - Case Number: {case_id}
   - Original Filing Date: [TO BE COMPLETED]
   - Disposition: {reason}

3. GROUNDS FOR EXPUNGEMENT:
   Under Minn. Stat. § 484.014, Petitioner requests expungement because:
   {reason}

4. HARDSHIP: The continued existence of this record causes ongoing harm
   to Petitioner's ability to secure housing, as tenant screening services
   report this record to prospective landlords.

5. PUBLIC INTEREST: Expungement serves the public interest by allowing
   Petitioner to secure stable housing and contribute to the community.

WHEREFORE, Petitioner respectfully requests that this Court:
   a. Order the expungement of all records related to this case;
   b. Direct all agencies to seal records related to this case;
   c. Grant such other relief as the Court deems just and proper.

Dated: {now.strftime('%B %d, %Y')}

_______________________________
Petitioner Signature

_______________________________
Petitioner Printed Name

_______________________________
Address

_______________________________
Phone Number
"""
    
    # Required documents checklist
    checklist = [
        "Copy of case dismissal order or judgment",
        "Photo identification (driver's license or state ID)",
        "Proof of current address",
        "Payment receipts showing rent was current",
        "Any correspondence showing resolution",
        "Affidavit of hardship (optional but recommended)",
    ]
    
    # Required supporting documents
    required_documents = [
        "dismissal_order",
        "identification",
        "proof_of_address",
        "payment_records",
    ]
    
    petition = SealingPetition(
        petition_id=petition_id,
        case_id=case_id,
        user_id=user_id,
        court_name=f"Minnesota District Court - {court_county} County",
        petition_type=petition_type,
        draft_text=draft_text,
        checklist=checklist,
        required_documents=required_documents,
        filing_fee=0.00,  # No fee for expungement petitions
        deadline=now + timedelta(days=30),  # Suggest filing within 30 days
        status="draft",
        created_at=now,
    )
    
    _petitions[petition_id] = petition
    
    # Broadcast to modules
    sdk.create_pack(
        pack_type=PackType.FORM_DATA,
        user_id=user_id,
        data={
            "form_type": "sealing_petition",
            "petition_id": petition_id,
            "case_id": case_id,
            "status": "draft",
        },
        target_module="forms",
        priority=5,
    )
    
    # Add deadline to calendar
    sdk.create_pack(
        pack_type=PackType.DEADLINE_DATA,
        user_id=user_id,
        data={
            "deadline_type": "petition_filing",
            "title": f"File Sealing Petition - Case {case_id}",
            "due_date": petition.deadline.isoformat() if petition.deadline else None,
            "case_id": case_id,
            "priority": "medium",
        },
        target_module="calendar",
        priority=6,
    )
    
    return {
        "petition_id": petition_id,
        "petition": petition.model_dump(),
        "checklist": checklist,
    }


@sdk.action(
    "generate_demand_letter",
    description="Create a demand letter to send to landlord or property manager",
    required_params=["case_id", "tenant_name", "landlord_name"],
    optional_params=["landlord_address", "property_address", "demand_type", "specific_demands"],
    produces=["letter_id", "letter_text", "demand_letter"],
)
async def generate_demand_letter(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate a formal demand letter to the landlord.
    
    Types of demand letters:
    - withdrawal: Request to withdraw eviction filing
    - correction: Request to correct false reporting
    - repair: Demand for repairs (habitability issues)
    - refund: Demand for security deposit refund
    """
    case_id = params.get("case_id")
    tenant_name = params.get("tenant_name")
    landlord_name = params.get("landlord_name")
    landlord_address = params.get("landlord_address", "[LANDLORD ADDRESS]")
    property_address = params.get("property_address", "[PROPERTY ADDRESS]")
    demand_type = params.get("demand_type", "withdrawal")
    specific_demands = params.get("specific_demands", [])
    
    if not all([case_id, tenant_name, landlord_name]):
        raise ValueError("case_id, tenant_name, and landlord_name are required")
    
    logger.info(f"tenant_defense: Generating {demand_type} demand letter for case {case_id}")
    
    letter_id = _make_id("ltr")
    now = datetime.utcnow()
    response_deadline = now + timedelta(days=14)
    
    # Generate letter text based on demand type
    demand_paragraphs = {
        "withdrawal": """
I am writing regarding the eviction action you filed against me. After reviewing 
the circumstances, I believe this filing was made in error and request that you 
immediately withdraw the case from court.

Specifically, I request that you:
1. File a dismissal or stipulation to dismiss with the court
2. Notify any tenant screening services of the dismissal
3. Remove any negative reporting related to this matter
""",
        "correction": """
I have discovered that inaccurate information about my tenancy is being reported 
to tenant screening services. Under the Fair Credit Reporting Act (15 U.S.C. § 1681), 
you have a duty to provide accurate information.

I demand that you immediately correct the following inaccurate information:
{specific_items}
""",
        "repair": """
The rental unit at the above address has serious habitability issues that require 
immediate attention. Under Minnesota Statute § 504B.161, you are required to 
maintain the premises in reasonable repair and fit for the use intended.

The following issues require immediate repair:
{specific_items}

I am providing you with 14 days written notice to make these repairs. Failure to 
do so may result in my exercising remedies available under Minnesota law, including 
rent escrow (Minn. Stat. § 504B.385).
""",
        "refund": """
My tenancy at the above address ended on [DATE]. Under Minnesota Statute § 504B.178, 
you are required to return my security deposit within 21 days, along with an itemized 
statement of any deductions.

More than 21 days have passed and I have not received my deposit or proper accounting. 
I demand immediate return of my security deposit in the amount of $[AMOUNT].

Failure to comply may result in my seeking damages equal to twice the deposit amount, 
plus costs and attorney fees as provided by law.
""",
    }
    
    # Format specific demands if provided
    specific_items = ""
    if specific_demands:
        specific_items = "\n".join([f"• {item}" for item in specific_demands])
    
    demand_text = demand_paragraphs.get(demand_type, demand_paragraphs["withdrawal"])
    demand_text = demand_text.replace("{specific_items}", specific_items)
    
    letter_text = f"""
{now.strftime('%B %d, %Y')}

{landlord_name}
{landlord_address}

Re: {property_address}
    Case Reference: {case_id}

Dear {landlord_name}:
{demand_text}

Please respond to this letter in writing within fourteen (14) days of the date above. 
Failure to respond may result in further legal action.

I reserve all rights and remedies available to me under law.

Sincerely,

_______________________________
{tenant_name}

_______________________________
Address

_______________________________
Phone Number

_______________________________
Email

SENT VIA: ☐ Certified Mail  ☐ Email  ☐ Hand Delivery
"""
    
    demand_letter = DemandLetter(
        letter_id=letter_id,
        case_id=case_id,
        tenant_name=tenant_name,
        landlord_name=landlord_name,
        landlord_address=landlord_address,
        property_address=property_address,
        demand_type=demand_type,
        letter_text=letter_text,
        response_deadline=response_deadline,
        created_at=now,
    )
    
    _demand_letters[letter_id] = demand_letter
    
    # Add deadline to calendar
    sdk.create_pack(
        pack_type=PackType.DEADLINE_DATA,
        user_id=user_id,
        data={
            "deadline_type": "demand_response",
            "title": f"Demand Letter Response Due - {landlord_name}",
            "due_date": response_deadline.isoformat(),
            "case_id": case_id,
            "letter_id": letter_id,
            "priority": "high",
        },
        target_module="calendar",
        priority=7,
    )
    
    return {
        "letter_id": letter_id,
        "letter_text": letter_text,
        "demand_letter": demand_letter.model_dump(),
    }


@sdk.action(
    "dispute_screening_report",
    description="Generate a dispute letter for tenant screening services",
    required_params=["screening_company", "disputed_items", "correct_information"],
    optional_params=["supporting_document_ids"],
    produces=["dispute_id", "dispute_letter", "screening_dispute"],
)
async def dispute_screening_report(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate a formal dispute letter for tenant screening services.
    
    Under the Fair Credit Reporting Act (FCRA), consumers have the right
    to dispute inaccurate information. Screening services must investigate
    and correct or remove inaccurate information within 30 days.
    """
    screening_company = params.get("screening_company")
    disputed_items = params.get("disputed_items", [])
    correct_information = params.get("correct_information", {})
    document_ids = params.get("supporting_document_ids", [])
    
    if not screening_company:
        raise ValueError("screening_company is required")
    if not disputed_items:
        raise ValueError("At least one disputed item is required")
    
    logger.info(f"tenant_defense: Creating screening dispute for {screening_company}")
    
    dispute_id = _make_id("disp")
    now = datetime.utcnow()
    response_deadline = now + timedelta(days=30)  # FCRA requires 30-day response
    
    # Format disputed items
    disputed_list = "\n".join([f"• {item}" for item in disputed_items])
    
    # Format correct information
    correct_list = "\n".join([
        f"• {key}: {value}" 
        for key, value in correct_information.items()
    ])
    
    dispute_letter = f"""
{now.strftime('%B %d, %Y')}

{screening_company}
Dispute Department
[ADDRESS]

Re: Formal Dispute of Inaccurate Information
    Consumer: [YOUR NAME]
    SSN (last 4): XXXX

To Whom It May Concern:

I am writing pursuant to my rights under the Fair Credit Reporting Act, 
15 U.S.C. § 1681i, to dispute inaccurate information in my tenant screening report.

DISPUTED INFORMATION:
{disputed_list}

CORRECT INFORMATION:
{correct_list}

SUPPORTING DOCUMENTATION:
I have enclosed copies of documents supporting my dispute, including:
• Court records showing case disposition
• Payment records
• Correspondence with landlord
• Other relevant documentation

LEGAL REQUIREMENTS:
Under the FCRA, you are required to:
1. Conduct a reasonable investigation within 30 days
2. Forward all relevant information I provide to the source
3. Notify me of the results of your investigation
4. Delete or correct the disputed information if found inaccurate
5. Provide me with a free copy of my updated report

ENFORCEMENT:
If you fail to comply with these requirements, I reserve the right to pursue 
all remedies available under federal and state law, including but not limited to:
• Actual damages
• Statutory damages up to $1,000
• Punitive damages
• Attorney's fees and costs

Please conduct your investigation and notify me of the results within 30 days 
as required by law.

Sincerely,

_______________________________
[YOUR NAME]

_______________________________
Address

_______________________________
Date of Birth

_______________________________
Social Security Number (last 4 digits)

Enclosures: [List supporting documents]
"""
    
    dispute = ScreeningDispute(
        dispute_id=dispute_id,
        user_id=user_id,
        screening_company=screening_company,
        disputed_items=disputed_items,
        correct_information=correct_information,
        supporting_documents=document_ids,
        dispute_letter=dispute_letter,
        response_deadline=response_deadline,
        status="pending",
    )
    
    _screening_disputes[dispute_id] = dispute
    
    # Add deadline
    sdk.create_pack(
        pack_type=PackType.DEADLINE_DATA,
        user_id=user_id,
        data={
            "deadline_type": "screening_dispute_response",
            "title": f"Screening Dispute Response Due - {screening_company}",
            "due_date": response_deadline.isoformat(),
            "dispute_id": dispute_id,
            "priority": "high",
        },
        target_module="calendar",
        priority=7,
    )
    
    return {
        "dispute_id": dispute_id,
        "dispute_letter": dispute_letter,
        "screening_dispute": dispute.model_dump(),
    }


@sdk.action(
    "get_case_progress",
    description="Get overall progress and strength of the tenant defense case",
    required_params=["case_id"],
    produces=["case_progress", "recommendations"],
)
async def get_case_progress(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Analyze and return the current case progress and strength.
    
    This action aggregates data from evidence collection, deadlines,
    and forms to provide an overall case assessment.
    """
    case_id = params.get("case_id")
    
    if not case_id:
        raise ValueError("case_id is required")
    
    logger.info(f"tenant_defense: Calculating case progress for {case_id}")
    
    now = datetime.utcnow()
    progress_key = f"{user_id}:{case_id}"
    
    # Get evidence stats
    evidence_key = f"{user_id}:{case_id}"
    evidence_index = _evidence_indices.get(evidence_key)
    evidence_count = evidence_index.total_count if evidence_index else 0
    categories = evidence_index.categories if evidence_index else {}
    
    # Check for key document types
    has_lease = categories.get("lease", 0) > 0
    has_payment_records = categories.get("payment", 0) > 0
    has_communications = categories.get("communication", 0) > 0
    
    # Count petitions and letters
    forms_completed = sum(
        1 for p in _petitions.values() 
        if p.case_id == case_id and p.status in ["ready", "filed"]
    )
    forms_completed += sum(
        1 for l in _demand_letters.values()
        if l.case_id == case_id and l.sent_date is not None
    )
    
    # Calculate case strength
    strength = _calculate_case_strength(
        evidence_count=evidence_count,
        has_lease=has_lease,
        has_payment_records=has_payment_records,
        has_communications=has_communications,
        deadlines_met=0,  # Would get from calendar module
        deadlines_missed=0,
    )
    
    # Generate recommendations
    recommendations = []
    
    if evidence_count < 3:
        recommendations.append({
            "priority": "high",
            "action": "collect_evidence",
            "message": "Collect more evidence to strengthen your case. "
                      "Upload documents, photos, and communications.",
        })
    
    if not has_lease:
        recommendations.append({
            "priority": "high",
            "action": "upload_lease",
            "message": "Upload your lease agreement. This is critical evidence.",
        })
    
    if not has_payment_records:
        recommendations.append({
            "priority": "medium",
            "action": "upload_payments",
            "message": "Upload payment records (receipts, bank statements, etc.)",
        })
    
    if forms_completed == 0:
        recommendations.append({
            "priority": "medium",
            "action": "prepare_forms",
            "message": "Consider preparing a demand letter or sealing petition.",
        })
    
    # Create or update progress record
    progress = CaseProgress(
        case_id=case_id,
        user_id=user_id,
        status="active",
        evidence_count=evidence_count,
        forms_completed=forms_completed,
        deadlines_met=0,
        deadlines_missed=0,
        next_deadline=None,
        next_action=recommendations[0]["action"] if recommendations else None,
        strength_score=strength,
        created_at=now,
        updated_at=now,
    )
    
    _case_progress[progress_key] = progress
    
    return {
        "case_progress": progress.model_dump(),
        "recommendations": recommendations,
    }


@sdk.action(
    "get_state",
    description="Get the current state of the tenant defense module",
    produces=["tenant_defense_state"],
)
async def get_state(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Return the current module state for sync operations"""
    return {
        "tenant_defense_state": {
            "status": "active",
            "user_id": user_id,
            "evidence_indices_count": len(_evidence_indices),
            "petitions_count": len(_petitions),
            "demand_letters_count": len(_demand_letters),
            "screening_disputes_count": len(_screening_disputes),
        }
    }


# =============================================================================
# EVENT HANDLERS
# =============================================================================

@sdk.on_event("document_uploaded")
async def on_document_uploaded(event_type: str, data: Dict[str, Any]):
    """Handle document upload events to auto-index evidence"""
    logger.debug(f"tenant_defense: Document uploaded - {data.get('document_id')}")
    # Could auto-categorize and add to evidence index


@sdk.on_event("workflow_started")
async def on_workflow_started(event_type: str, data: Dict[str, Any]):
    """Handle workflow started events"""
    logger.debug(f"tenant_defense: Workflow started - {data.get('workflow_id')}")


@sdk.on_event("deadline_approaching")
async def on_deadline_approaching(event_type: str, data: Dict[str, Any]):
    """Handle deadline reminders"""
    logger.info(f"tenant_defense: Deadline approaching - {data.get('title')}")


# =============================================================================
# FASTAPI ENDPOINTS
# =============================================================================

# Import security after module setup to avoid circular imports
try:
    from app.core.security import require_user, StorageUser
    HAS_SECURITY = True
except ImportError:
    HAS_SECURITY = False
    logger.warning("Security module not available, endpoints will be unprotected")


def get_user_id(user=None) -> str:
    """Get user ID from StorageUser or return test ID"""
    if user and hasattr(user, 'user_id'):
        return user.user_id
    return "test_user"


@router.post("/initialize")
async def initialize_endpoint():
    """Initialize the tenant defense module"""
    try:
        sdk.initialize()
        return ActionResponse(
            success=True,
            result={
                "status": "initialized",
                "actions": list(sdk.actions.keys()),
                "module": module_definition.to_dict(),
            }
        )
    except Exception as e:
        logger.exception("Failed to initialize tenant defense module")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get module status"""
    return sdk.get_status()


@router.post("/evidence/collect", response_model=ActionResponse)
async def collect_evidence_endpoint(
    request: CollectEvidenceRequest,
    user: "StorageUser" = Depends(require_user) if HAS_SECURITY else None,
):
    """Collect and index evidence for a case"""
    try:
        user_id = get_user_id(user)
        result = await collect_evidence(
            user_id=user_id,
            params={
                "case_id": request.case_id,
                "evidence": [e.model_dump() for e in request.evidence],
            },
            context={},
        )
        return ActionResponse(success=True, result=result)
    except Exception as e:
        logger.exception("Evidence collection failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence/{case_id}")
async def get_evidence_index(
    case_id: str,
    user: "StorageUser" = Depends(require_user) if HAS_SECURITY else None,
):
    """Get evidence index for a case"""
    user_id = get_user_id(user)
    key = f"{user_id}:{case_id}"
    
    if key not in _evidence_indices:
        raise HTTPException(status_code=404, detail="Evidence index not found")
    
    return _evidence_indices[key].model_dump()


@router.post("/petition/sealing", response_model=ActionResponse)
async def create_sealing_petition(
    request: SealingPetitionRequest,
    user: "StorageUser" = Depends(require_user) if HAS_SECURITY else None,
):
    """Generate a sealing/expungement petition"""
    try:
        user_id = get_user_id(user)
        result = await prepare_sealing_petition(
            user_id=user_id,
            params={
                "case_id": request.case_id,
                "petition_type": request.petition_type,
                "court_county": request.court_county,
                "reason_for_sealing": request.reason_for_sealing,
            },
            context={},
        )
        return ActionResponse(success=True, result=result)
    except Exception as e:
        logger.exception("Petition generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/petition/{petition_id}")
async def get_petition(
    petition_id: str,
    user: "StorageUser" = Depends(require_user) if HAS_SECURITY else None,
):
    """Get a specific petition"""
    if petition_id not in _petitions:
        raise HTTPException(status_code=404, detail="Petition not found")
    
    return _petitions[petition_id].model_dump()


@router.post("/demand-letter", response_model=ActionResponse)
async def create_demand_letter(
    request: DemandLetterRequest,
    user: "StorageUser" = Depends(require_user) if HAS_SECURITY else None,
):
    """Generate a demand letter"""
    try:
        user_id = get_user_id(user)
        result = await generate_demand_letter(
            user_id=user_id,
            params={
                "case_id": request.case_id,
                "tenant_name": request.tenant_name,
                "landlord_name": request.landlord_name,
                "landlord_address": request.landlord_address,
                "property_address": request.property_address,
                "demand_type": request.demand_type,
                "specific_demands": request.specific_demands,
            },
            context={},
        )
        return ActionResponse(success=True, result=result)
    except Exception as e:
        logger.exception("Demand letter generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demand-letter/{letter_id}")
async def get_demand_letter(
    letter_id: str,
    user: "StorageUser" = Depends(require_user) if HAS_SECURITY else None,
):
    """Get a specific demand letter"""
    if letter_id not in _demand_letters:
        raise HTTPException(status_code=404, detail="Demand letter not found")
    
    return _demand_letters[letter_id].model_dump()


@router.post("/screening-dispute", response_model=ActionResponse)
async def create_screening_dispute(
    request: ScreeningDisputeRequest,
    user: "StorageUser" = Depends(require_user) if HAS_SECURITY else None,
):
    """Generate a screening service dispute"""
    try:
        user_id = get_user_id(user)
        result = await dispute_screening_report(
            user_id=user_id,
            params={
                "screening_company": request.screening_company,
                "disputed_items": request.disputed_items,
                "correct_information": request.correct_information,
                "supporting_document_ids": request.supporting_document_ids,
            },
            context={},
        )
        return ActionResponse(success=True, result=result)
    except Exception as e:
        logger.exception("Screening dispute generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/case/{case_id}/progress", response_model=ActionResponse)
async def get_case_progress_endpoint(
    case_id: str,
    user: "StorageUser" = Depends(require_user) if HAS_SECURITY else None,
):
    """Get case progress and recommendations"""
    try:
        user_id = get_user_id(user)
        result = await get_case_progress(
            user_id=user_id,
            params={"case_id": case_id},
            context={},
        )
        return ActionResponse(success=True, result=result)
    except Exception as e:
        logger.exception("Failed to get case progress")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/action/{action_name}", response_model=ActionResponse)
async def run_action(
    action_name: str,
    request: ActionRequest,
    user: "StorageUser" = Depends(require_user) if HAS_SECURITY else None,
):
    """Run any registered action by name"""
    action = sdk.actions.get(action_name)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action '{action_name}' not found")
    
    # Validate required params
    for param in action.required_params:
        if param not in request.params:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required parameter: {param}"
            )
    
    try:
        user_id = request.user_id or get_user_id(user)
        result = await action.handler(
            user_id,
            request.params,
            request.context or {},
        )
        return ActionResponse(success=True, result=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Action '{action_name}' failed")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize():
    """Initialize this module - call on application startup"""
    sdk.initialize()
    logger.info(f"✅ {module_definition.display_name} ready (v{module_definition.version})")


def register_with_mesh():
    """Register this module with the Positronic Mesh"""
    initialize()


# Export for easy importing
__all__ = [
    "router",
    "sdk", 
    "module_definition",
    "initialize",
    "register_with_mesh",
]
