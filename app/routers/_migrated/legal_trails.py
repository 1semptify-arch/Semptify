"""
Legal Trails Module - Track violations, claims, and filing deadlines
Supports: Legal Claims Trail, Eviction Threat Trail, Broker Oversight, Late Fee Violations
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

router = APIRouter(prefix="/legal-trails", tags=["Legal Trails"])


# ============== ENUMS ==============

class ViolationType(str, Enum):
    FALSE_LATE_FEE = "false_late_fee"
    EVICTION_THREAT = "eviction_threat"
    RETALIATION = "retaliation"
    COERCION = "coercion"
    FRAUD = "fraud"
    LEASE_BREACH = "lease_breach"
    HABITABILITY = "habitability"
    HARASSMENT = "harassment"
    DISCRIMINATION = "discrimination"
    MISUSE_FEDERAL_FUNDS = "misuse_federal_funds"
    LICENSE_VIOLATION = "license_violation"


class StatuteType(str, Enum):
    MN_504B_177 = "MN 504B.177"  # Late fee limits
    MN_504B_285 = "MN 504B.285"  # Retaliatory eviction
    MN_504B_161 = "MN 504B.161"  # Tenant remedies
    MN_504B_211 = "MN 504B.211"  # Security deposits
    HUD_FAIR_HOUSING = "HUD Fair Housing Act"
    CIVIL_FRAUD = "Civil Fraud"
    CIVIL_COERCION = "Civil Coercion"
    FEDERAL_HOUSING_FUNDS = "Federal Housing Fund Misuse"


class ClaimStatus(str, Enum):
    DOCUMENTING = "documenting"
    READY_TO_FILE = "ready_to_file"
    FILED = "filed"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class FilingDestination(str, Enum):
    MN_ATTORNEY_GENERAL = "Minnesota Attorney General"
    MN_DEPT_COMMERCE = "Minnesota Dept of Commerce"
    HUD_FAIR_HOUSING = "HUD Office of Fair Housing"
    DISTRICT_COURT = "District Court"
    FEDERAL_COURT = "Federal Court"
    LOCAL_HOUSING_AUTHORITY = "Local Housing Authority"


# ============== MODELS ==============

class Violation(BaseModel):
    """A single violation record"""
    id: Optional[str] = None
    violation_type: ViolationType
    date_occurred: date
    description: str
    amount_if_financial: Optional[float] = None
    evidence_ids: List[str] = Field(default_factory=list)
    witnesses: List[str] = Field(default_factory=list)
    perpetrator: str  # Name of person who committed violation
    perpetrator_role: str  # e.g., "Property Manager", "Broker"
    company: str  # e.g., "Velair Property Management"
    statutes_violated: List[StatuteType] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    
    
class EvictionThreat(BaseModel):
    """Track eviction threats for retaliation claims"""
    id: Optional[str] = None
    date_threatened: date
    threat_method: str  # "verbal", "written", "notice"
    threat_content: str
    context: str  # What was happening when threat was made
    was_retaliatory: bool = True
    prior_complaint_date: Optional[date] = None  # Date of complaint that triggered retaliation
    prior_complaint_type: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    perpetrator: str
    perpetrator_role: str
    created_at: Optional[datetime] = None


class LateFeeViolation(BaseModel):
    """Track false or illegal late fees"""
    id: Optional[str] = None
    date_charged: date
    amount_charged: float
    rent_amount: float
    days_late: int
    lease_allows_late_fee: bool
    lease_late_fee_amount: Optional[float] = None
    exceeds_8_percent: bool = False  # MN law caps at 8%
    legal_max_fee: float = 0  # Calculated 8% of rent
    overcharge_amount: float = 0  # Amount over legal max
    evidence_ids: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class BrokerOversight(BaseModel):
    """Track broker responsibility for violations"""
    broker_name: str
    broker_license: Optional[str] = None
    broker_company: str
    company_address: str
    managed_properties: List[str] = Field(default_factory=list)
    violations_under_watch: List[str] = Field(default_factory=list)  # Violation IDs
    license_complaint_filed: bool = False
    license_complaint_date: Optional[date] = None
    license_status: str = "active"
    notes: str = ""


class LegalClaim(BaseModel):
    """A formal legal claim combining violations"""
    id: Optional[str] = None
    title: str
    claim_type: str  # "civil", "criminal", "regulatory"
    violations: List[str] = Field(default_factory=list)  # Violation IDs
    statutes: List[StatuteType] = Field(default_factory=list)
    defendants: List[str] = Field(default_factory=list)
    status: ClaimStatus = ClaimStatus.DOCUMENTING
    filing_destination: Optional[FilingDestination] = None
    statute_of_limitations_date: date
    filing_deadline: date
    damages_sought: Optional[float] = None
    attorney: Optional[str] = None
    case_number: Optional[str] = None
    notes: str = ""
    created_at: Optional[datetime] = None


class FilingWindow(BaseModel):
    """Track statute of limitations and deadlines"""
    claim_type: str
    violation_date: date
    limitation_years: int
    deadline: date
    days_remaining: int
    urgency: str  # "critical", "warning", "safe"


# ============== IN-MEMORY STORAGE ==============
# In production, these would be in database

violations_db: dict = {}
eviction_threats_db: dict = {}
late_fees_db: dict = {}
broker_oversight_db: dict = {}
legal_claims_db: dict = {}


# ============== STATUTE OF LIMITATIONS ==============

STATUTE_OF_LIMITATIONS = {
    "civil_retaliation": 6,
    "civil_fraud": 6,
    "civil_coercion": 6,
    "civil_breach": 6,
    "hud_complaint": 1,
    "criminal_theft": 5,
    "criminal_fraud": 6,
    "license_complaint": 2,
}


# ============== ENDPOINTS ==============

@router.get("/")
async def get_legal_trails_overview():
    """Get overview of all legal trails"""
    return {
        "violations_count": len(violations_db),
        "eviction_threats_count": len(eviction_threats_db),
        "late_fee_violations_count": len(late_fees_db),
        "broker_oversight_count": len(broker_oversight_db),
        "legal_claims_count": len(legal_claims_db),
        "modules": [
            {
                "name": "Legal Claims Trail",
                "description": "Track violations, statutes, and filing windows",
                "endpoint": "/legal-trails/claims"
            },
            {
                "name": "Eviction Threat Trail",
                "description": "Document eviction threats and retaliation",
                "endpoint": "/legal-trails/eviction-threats"
            },
            {
                "name": "Late Fee Violation Trail",
                "description": "Track illegal late fee charges",
                "endpoint": "/legal-trails/late-fees"
            },
            {
                "name": "Broker Oversight Trail",
                "description": "Track broker accountability and license challenges",
                "endpoint": "/legal-trails/broker-oversight"
            }
        ],
        "statutes": {
            "MN 504B.177": {
                "title": "Late Fees",
                "summary": "Late fees must be in lease and cannot exceed 8% of overdue rent",
                "url": "https://www.revisor.mn.gov/statutes/cite/504B.177"
            },
            "MN 504B.285": {
                "title": "Retaliatory Eviction",
                "summary": "Landlords cannot evict tenants for asserting legal rights",
                "url": "https://www.revisor.mn.gov/statutes/cite/504B.285"
            },
            "MN 504B.161": {
                "title": "Tenant Remedies",
                "summary": "Tenant rights to repair and deduct, rent escrow",
                "url": "https://www.revisor.mn.gov/statutes/cite/504B.161"
            }
        },
        "filing_windows": STATUTE_OF_LIMITATIONS
    }


# ---------- VIOLATIONS ----------

@router.post("/violations")
async def add_violation(violation: Violation):
    """Log a new violation"""
    from app.core.id_gen import make_id
    violation.id = make_id("vio")
    violation.created_at = datetime.now()
    violations_db[violation.id] = violation.dict()
    return {
        "message": "Violation logged",
        "violation_id": violation.id,
        "violation": violation
    }


@router.get("/violations")
async def list_violations(
    violation_type: Optional[ViolationType] = None,
    perpetrator: Optional[str] = None
):
    """List all logged violations"""
    results = list(violations_db.values())
    if violation_type:
        results = [v for v in results if v["violation_type"] == violation_type]
    if perpetrator:
        results = [v for v in results if perpetrator.lower() in v["perpetrator"].lower()]
    return {"count": len(results), "violations": results}


@router.get("/violations/{violation_id}")
async def get_violation(violation_id: str):
    """Get a specific violation"""
    if violation_id not in violations_db:
        raise HTTPException(status_code=404, detail="Violation not found")
    return violations_db[violation_id]


# ---------- EVICTION THREATS ----------

@router.post("/eviction-threats")
async def add_eviction_threat(threat: EvictionThreat):
    """Log an eviction threat"""
    from app.core.id_gen import make_id
    threat.id = make_id("thr")
    threat.created_at = datetime.now()
    eviction_threats_db[threat.id] = threat.dict()
    return {
        "message": "Eviction threat logged",
        "threat_id": threat.id,
        "warning": "If this was retaliatory, you may have a claim under MN 504B.285",
        "statute_of_limitations": "6 years for civil retaliation claims",
        "threat": threat
    }


@router.get("/eviction-threats")
async def list_eviction_threats():
    """List all eviction threats"""
    return {
        "count": len(eviction_threats_db),
        "threats": list(eviction_threats_db.values())
    }


# ---------- LATE FEE VIOLATIONS ----------

@router.post("/late-fees")
async def add_late_fee_violation(fee: LateFeeViolation):
    """Log a late fee violation"""
    from app.core.id_gen import make_id
    fee.id = make_id("fee")
    fee.created_at = datetime.now()
    
    # Calculate legal max (8% of rent per MN 504B.177)
    fee.legal_max_fee = round(fee.rent_amount * 0.08, 2)
    fee.exceeds_8_percent = fee.amount_charged > fee.legal_max_fee
    fee.overcharge_amount = max(0, fee.amount_charged - fee.legal_max_fee)
    
    late_fees_db[fee.id] = fee.dict()
    
    violations = []
    if not fee.lease_allows_late_fee:
        violations.append("Late fee charged without lease authorization (MN 504B.177)")
    if fee.exceeds_8_percent:
        violations.append(f"Late fee exceeds 8% cap by ${fee.overcharge_amount:.2f} (MN 504B.177)")
    
    return {
        "message": "Late fee violation logged",
        "fee_id": fee.id,
        "legal_max_fee": fee.legal_max_fee,
        "exceeds_8_percent": fee.exceeds_8_percent,
        "overcharge_amount": fee.overcharge_amount,
        "violations_detected": violations,
        "fee": fee
    }


@router.get("/late-fees")
async def list_late_fee_violations():
    """List all late fee violations"""
    total_overcharged = sum(f.get("overcharge_amount", 0) for f in late_fees_db.values())
    return {
        "count": len(late_fees_db),
        "total_overcharged": total_overcharged,
        "violations": list(late_fees_db.values())
    }


@router.get("/late-fees/calculate")
async def calculate_late_fee_legal_max(
    rent_amount: float = Query(..., description="Monthly rent amount"),
    days_late: int = Query(default=1, description="Days late")
):
    """Calculate the legal maximum late fee under MN 504B.177"""
    legal_max = round(rent_amount * 0.08, 2)
    return {
        "rent_amount": rent_amount,
        "days_late": days_late,
        "legal_max_late_fee": legal_max,
        "statute": "MN 504B.177",
        "note": "Late fees cannot exceed 8% of overdue rent and must be specified in lease"
    }


# ---------- BROKER OVERSIGHT ----------

@router.post("/broker-oversight")
async def add_broker_oversight(broker: BrokerOversight):
    """Add a broker to track for oversight accountability"""
    broker_oversight_db[broker.broker_name] = broker.dict()
    return {
        "message": "Broker oversight record created",
        "broker": broker,
        "note": "As the broker of record, this person has legal responsibility for ensuring compliance with Minnesota housing laws and ethical conduct of property managers."
    }


@router.get("/broker-oversight")
async def list_broker_oversight():
    """List all brokers being tracked"""
    return {
        "count": len(broker_oversight_db),
        "brokers": list(broker_oversight_db.values())
    }


@router.get("/broker-oversight/{broker_name}")
async def get_broker_oversight(broker_name: str):
    """Get broker oversight details"""
    if broker_name not in broker_oversight_db:
        raise HTTPException(status_code=404, detail="Broker not found")
    return broker_oversight_db[broker_name]


@router.post("/broker-oversight/{broker_name}/link-violation")
async def link_violation_to_broker(broker_name: str, violation_id: str):
    """Link a violation to a broker's oversight record"""
    if broker_name not in broker_oversight_db:
        raise HTTPException(status_code=404, detail="Broker not found")
    if violation_id not in violations_db:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    broker_oversight_db[broker_name]["violations_under_watch"].append(violation_id)
    return {
        "message": f"Violation {violation_id} linked to broker {broker_name}",
        "broker": broker_oversight_db[broker_name]
    }


# ---------- LEGAL CLAIMS ----------

@router.post("/claims")
async def create_legal_claim(claim: LegalClaim):
    """Create a formal legal claim"""
    from app.core.id_gen import make_id
    claim.id = make_id("clm")
    claim.created_at = datetime.now()
    legal_claims_db[claim.id] = claim.dict()
    return {
        "message": "Legal claim created",
        "claim_id": claim.id,
        "claim": claim
    }


@router.get("/claims")
async def list_legal_claims(status: Optional[ClaimStatus] = None):
    """List all legal claims"""
    results = list(legal_claims_db.values())
    if status:
        results = [c for c in results if c["status"] == status]
    return {"count": len(results), "claims": results}


@router.get("/claims/{claim_id}")
async def get_legal_claim(claim_id: str):
    """Get a specific legal claim"""
    if claim_id not in legal_claims_db:
        raise HTTPException(status_code=404, detail="Claim not found")
    return legal_claims_db[claim_id]


@router.put("/claims/{claim_id}/status")
async def update_claim_status(claim_id: str, status: ClaimStatus):
    """Update claim status"""
    if claim_id not in legal_claims_db:
        raise HTTPException(status_code=404, detail="Claim not found")
    legal_claims_db[claim_id]["status"] = status
    return {
        "message": f"Claim status updated to {status}",
        "claim": legal_claims_db[claim_id]
    }


# ---------- FILING WINDOWS ----------

@router.get("/filing-windows")
async def calculate_filing_windows(
    violation_date: date = Query(..., description="Date violation occurred")
):
    """Calculate all filing windows/deadlines for a violation date"""
    from datetime import timedelta
    
    windows = []
    today = date.today()
    
    for claim_type, years in STATUTE_OF_LIMITATIONS.items():
        deadline = violation_date + timedelta(days=years * 365)
        days_remaining = (deadline - today).days
        
        if days_remaining < 0:
            urgency = "expired"
        elif days_remaining < 90:
            urgency = "critical"
        elif days_remaining < 365:
            urgency = "warning"
        else:
            urgency = "safe"
        
        windows.append(FilingWindow(
            claim_type=claim_type,
            violation_date=violation_date,
            limitation_years=years,
            deadline=deadline,
            days_remaining=max(0, days_remaining),
            urgency=urgency
        ))
    
    return {
        "violation_date": violation_date,
        "windows": [w.dict() for w in sorted(windows, key=lambda x: x.days_remaining)]
    }


# ---------- COMPLAINT GENERATORS ----------

@router.post("/generate/retaliation-complaint")
async def generate_retaliation_complaint(
    tenant_name: str,
    property_address: str,
    landlord_name: str,
    management_company: str,
    violation_ids: List[str] = Query(default=[]),
    threat_ids: List[str] = Query(default=[])
):
    """Generate a retaliation complaint document"""
    violations = [violations_db[v] for v in violation_ids if v in violations_db]
    threats = [eviction_threats_db[t] for t in threat_ids if t in eviction_threats_db]
    
    complaint = {
        "title": "COMPLAINT FOR RETALIATORY EVICTION",
        "statute": "Minnesota Statute 504B.285",
        "complainant": tenant_name,
        "property": property_address,
        "respondents": [landlord_name, management_company],
        "allegations": [],
        "relief_sought": [
            "Injunctive relief prohibiting eviction",
            "Actual damages",
            "Attorney's fees",
            "Civil penalty up to $500"
        ],
        "violations_referenced": violations,
        "threats_documented": threats
    }
    
    return complaint


@router.post("/generate/license-complaint")
async def generate_license_complaint(
    broker_name: str,
    license_number: Optional[str] = None,
    company: str = "",
    violations_summary: str = ""
):
    """Generate a license complaint for MN Dept of Commerce"""
    return {
        "title": "COMPLAINT TO MINNESOTA DEPARTMENT OF COMMERCE",
        "regarding": f"Real Estate Broker License - {broker_name}",
        "license_number": license_number or "Unknown - Request Lookup",
        "company": company,
        "complaint_type": "Broker Negligence / Failure to Supervise",
        "allegations": [
            "Failure to ensure compliance with Minnesota tenant protection laws",
            "Allowing unlicensed or improper management practices",
            "Failure to supervise property management activities",
            violations_summary
        ],
        "statutes_violated": [
            "MN Statute 82.81 - Broker Duties",
            "MN Statute 504B.177 - Late Fee Violations",
            "MN Statute 504B.285 - Retaliatory Eviction"
        ],
        "relief_sought": [
            "Investigation of broker practices",
            "License suspension or revocation",
            "Civil penalties"
        ],
        "filing_info": {
            "agency": "Minnesota Department of Commerce",
            "url": "https://mn.gov/commerce/consumers/file-a-complaint/",
            "phone": "651-539-1600"
        }
    }


@router.post("/generate/hud-complaint")
async def generate_hud_complaint(
    tenant_name: str,
    property_address: str,
    management_company: str,
    violation_type: str,
    description: str
):
    """Generate a HUD Fair Housing complaint"""
    return {
        "title": "COMPLAINT TO HUD OFFICE OF FAIR HOUSING",
        "complainant": tenant_name,
        "property": property_address,
        "respondent": management_company,
        "violation_type": violation_type,
        "description": description,
        "deadline_warning": "HUD complaints must be filed within 1 year of the discriminatory act",
        "filing_info": {
            "agency": "HUD Office of Fair Housing and Equal Opportunity",
            "online": "https://www.hud.gov/program_offices/fair_housing_equal_opp/online-complaint",
            "phone": "1-800-669-9777",
            "regional_office": "Chicago Regional Office (covers Minnesota)"
        }
    }


# ---------- ATTORNEY RESOURCES ----------

@router.get("/attorneys/minnesota")
async def get_mn_tenant_attorneys():
    """Get list of Minnesota tenant rights attorneys"""
    return {
        "attorneys": [
            {
                "name": "Madia Law LLC",
                "specialty": "Fraud, tenant justice, trial lawyers",
                "note": "Known for 'beating giants' - over $50M recovered",
                "website": "https://madialaw.com",
                "location": "Minneapolis, MN"
            },
            {
                "name": "Burns & Hansen, P.A.",
                "specialty": "Real estate litigation, tenant rights",
                "note": "Fierce litigation in property disputes",
                "website": "https://patrickburnslaw.com",
                "location": "Minneapolis, MN"
            },
            {
                "name": "Aaron Hall Law",
                "specialty": "Landlord-tenant advocacy",
                "website": "https://aaronhall.com",
                "location": "Minnesota"
            },
            {
                "name": "Wilson Law Group LLC",
                "specialty": "Housing disputes, free consultations",
                "phone": "612-430-8022",
                "location": "Minneapolis, MN"
            },
            {
                "name": "HOME Line",
                "specialty": "Free tenant hotline and legal help",
                "phone": "612-728-5767",
                "website": "https://homelinemn.org",
                "note": "Free legal assistance for tenants"
            },
            {
                "name": "Legal Aid - Housing",
                "specialty": "Free legal services for low-income",
                "phone": "612-334-5970",
                "website": "https://mylegalaid.org"
            }
        ],
        "super_lawyers": [
            "Eric Hansen (Burns & Hansen, P.A.)",
            "Kevin J. Dunlevy (LeVander, Gillen & Miller, P.A.)",
            "Paul W. Anderson (Messerli | Kramer)"
        ],
        "directories": [
            "https://www.superlawyers.com/minnesota/",
            "https://www.findlaw.com/minnesota/",
            "https://www.avvo.com/landlord-tenant-lawyer/mn.html"
        ]
    }
