"""
Legal Trails Module - Track violations, claims, and filing deadlines
Supports: Legal Claims Trail, Eviction Threat Trail, Broker Oversight, Late Fee Violations

All records persist per-user as LEGAL_TRAIL_RECORD overlays in the tenant's
own vault (VAULT_RECORDS_FILE). There is no shared/global store — a record is
only ever readable by the tenant who logged it (and, through the tenant
timeline, by a linked advocate when the relationship's share_timeline scope
is on). Every endpoint requires an authenticated session.
"""

import logging
from datetime import date, datetime
from enum import StrEnum

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.core.security import UserContext, get_current_user, require_tier
from app.modules.legal_trails import service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/legal-trails", tags=["Legal Trails"])


# ============== ENUMS ==============


class ViolationType(StrEnum):
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


class StatuteType(StrEnum):
    MN_504B_177 = "MN 504B.177"  # Late fee limits
    MN_504B_285 = "MN 504B.285"  # Retaliatory eviction
    MN_504B_161 = "MN 504B.161"  # Tenant remedies
    MN_504B_211 = "MN 504B.211"  # Security deposits
    HUD_FAIR_HOUSING = "HUD Fair Housing Act"
    CIVIL_FRAUD = "Civil Fraud"
    CIVIL_COERCION = "Civil Coercion"
    FEDERAL_HOUSING_FUNDS = "Federal Housing Fund Misuse"


class ClaimStatus(StrEnum):
    DOCUMENTING = "documenting"
    READY_TO_FILE = "ready_to_file"
    FILED = "filed"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class FilingDestination(StrEnum):
    MN_ATTORNEY_GENERAL = "Minnesota Attorney General"
    MN_DEPT_COMMERCE = "MN Dept of Commerce"
    HUD_FAIR_HOUSING = "HUD Office of Fair Housing"
    DISTRICT_COURT = "District Court"
    FEDERAL_COURT = "Federal Court"
    LOCAL_HOUSING_AUTHORITY = "Local Housing Authority"


# ============== MODELS ==============


class Violation(BaseModel):
    """A single violation record"""

    id: str | None = None
    violation_type: ViolationType
    date_occurred: date
    description: str
    amount_if_financial: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    witnesses: list[str] = Field(default_factory=list)
    perpetrator: str  # Name of person who committed violation
    perpetrator_role: str  # e.g., "Property Manager", "Broker"
    company: str  # e.g., "Example Property Management"
    statutes_violated: list[StatuteType] = Field(default_factory=list)
    created_at: datetime | None = None


class EvictionThreat(BaseModel):
    """Track eviction threats for retaliation claims"""

    id: str | None = None
    date_threatened: date
    threat_method: str  # "verbal", "written", "notice"
    threat_content: str
    context: str  # What was happening when threat was made
    was_retaliatory: bool = True
    prior_complaint_date: date | None = None  # Date of complaint that triggered retaliation
    prior_complaint_type: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    perpetrator: str
    perpetrator_role: str
    created_at: datetime | None = None


class LateFeeViolation(BaseModel):
    """Track false or illegal late fees"""

    id: str | None = None
    date_charged: date
    amount_charged: float
    rent_amount: float
    days_late: int
    lease_allows_late_fee: bool
    lease_late_fee_amount: float | None = None
    exceeds_8_percent: bool = False  # MN law caps at 8%
    legal_max_fee: float = 0  # Calculated 8% of rent
    overcharge_amount: float = 0  # Amount over legal max
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class BrokerOversight(BaseModel):
    """Track broker responsibility for violations"""

    broker_name: str
    broker_license: str | None = None
    broker_company: str
    company_address: str
    managed_properties: list[str] = Field(default_factory=list)
    violations_under_watch: list[str] = Field(default_factory=list)  # Violation IDs
    license_complaint_filed: bool = False
    license_complaint_date: date | None = None
    license_status: str = "active"
    notes: str = ""


class LegalClaim(BaseModel):
    """A formal legal claim combining violations"""

    id: str | None = None
    title: str
    claim_type: str  # "civil", "criminal", "regulatory"
    violations: list[str] = Field(default_factory=list)  # Violation IDs
    statutes: list[StatuteType] = Field(default_factory=list)
    defendants: list[str] = Field(default_factory=list)
    status: ClaimStatus = ClaimStatus.DOCUMENTING
    filing_destination: FilingDestination | None = None
    statute_of_limitations_date: date
    filing_deadline: date
    damages_sought: float | None = None
    attorney: str | None = None
    case_number: str | None = None
    notes: str = ""
    created_at: datetime | None = None


class FilingWindow(BaseModel):
    """Track statute of limitations and deadlines"""

    claim_type: str
    violation_date: date
    limitation_years: int
    deadline: date
    days_remaining: int
    urgency: str  # "critical", "warning", "safe"


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

# Which limitation clock matters most for each logged violation type.
# Display guidance only — the page labels these as common windows, not advice.
_VIOLATION_TO_CLAIM = {
    ViolationType.RETALIATION: "civil_retaliation",
    ViolationType.EVICTION_THREAT: "civil_retaliation",
    ViolationType.FRAUD: "civil_fraud",
    ViolationType.COERCION: "civil_coercion",
    ViolationType.LEASE_BREACH: "civil_breach",
    ViolationType.HABITABILITY: "civil_breach",
    ViolationType.HARASSMENT: "civil_coercion",
    ViolationType.DISCRIMINATION: "hud_complaint",
    ViolationType.FALSE_LATE_FEE: "civil_breach",
    ViolationType.MISUSE_FEDERAL_FUNDS: "civil_fraud",
    ViolationType.LICENSE_VIOLATION: "license_complaint",
}

_URGENCY_ORDER = {"expired": 0, "critical": 1, "warning": 2, "safe": 3}


def _filing_window(violation_date: date, claim_type: str, years: int) -> dict:
    """Compute one deadline row for a violation date + claim type."""
    from datetime import timedelta

    deadline = violation_date + timedelta(days=years * 365)
    days_remaining = (deadline - date.today()).days
    if days_remaining < 0:
        urgency = "expired"
    elif days_remaining < 90:
        urgency = "critical"
    elif days_remaining < 365:
        urgency = "warning"
    else:
        urgency = "safe"
    return {
        "claim_type": claim_type,
        "violation_date": violation_date.isoformat(),
        "limitation_years": years,
        "deadline": deadline.isoformat(),
        "days_remaining": max(0, days_remaining),
        "urgency": urgency,
    }


def _window_for_violation(record: dict) -> dict | None:
    """Deadline row for one logged violation record, or None if undated."""
    raw_date = record.get("date_occurred")
    if not raw_date:
        return None
    try:
        occurred = date.fromisoformat(str(raw_date)[:10])
    except ValueError:
        return None
    try:
        vtype = ViolationType(record.get("violation_type") or "")
    except ValueError:
        vtype = None
    claim_type = _VIOLATION_TO_CLAIM.get(vtype, "civil_breach")
    window = _filing_window(occurred, claim_type, STATUTE_OF_LIMITATIONS[claim_type])
    window["record_id"] = record.get("id")
    window["violation_type"] = record.get("violation_type")
    return window


_STATUTES_INFO = {
    "MN 504B.177": {
        "title": "Late Fees",
        "summary": "Late fees must be in lease and cannot exceed 8% of overdue rent",
        "url": "https://www.revisor.mn.gov/statutes/cite/504B.177",
    },
    "MN 504B.285": {
        "title": "Retaliatory Eviction",
        "summary": "Landlords cannot evict tenants for asserting legal rights",
        "url": "https://www.revisor.mn.gov/statutes/cite/504B.285",
    },
    "MN 504B.161": {
        "title": "Covenants of Habitability",
        "summary": "Landlords must keep rentals fit and in reasonable repair; remedies go through a rent escrow action",
        "url": "https://www.revisor.mn.gov/statutes/cite/504B.161",
    },
}

_DRAFT_NOTE = (
    "Draft for review only — not a filed document and not legal advice. "
    "An attorney or legal aid office should review it before anything is filed."
)


def _storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "error": "storage_unavailable",
            "message": "Your records could not be saved right now. Nothing was written — try again in a moment.",
        },
    )


# ============== PAGE ==============


@router.get("/", response_class=HTMLResponse)
async def legal_trails_page(request: Request, user: UserContext | None = Depends(get_current_user)):
    """Serve the Legal Trails page — log violations, see records, deadlines, next steps."""
    from app.main import templates

    context: dict = {"user": user, "authed": user is not None}
    if user is None:
        return templates.TemplateResponse(request, "pages/legal_trails.html", context)

    violations, threats, late_fees, brokers, claims = (
        await service.list_records(user, service.KIND_VIOLATION),
        await service.list_records(user, service.KIND_EVICTION_THREAT),
        await service.list_records(user, service.KIND_LATE_FEE),
        await service.list_records(user, service.KIND_BROKER_OVERSIGHT),
        await service.list_records(user, service.KIND_CLAIM),
    )

    windows = [w for w in (_window_for_violation(v) for v in violations) if w]
    windows.sort(key=lambda w: (_URGENCY_ORDER.get(w["urgency"], 9), w["days_remaining"]))

    records = []
    for v in violations:
        records.append(
            {
                "id": v.get("id"),
                "kind_label": "Violation",
                "when": v.get("date_occurred"),
                "who": " — ".join(p for p in (v.get("perpetrator"), v.get("company")) if p),
                "summary": v.get("description"),
            }
        )
    for t in threats:
        records.append(
            {
                "id": t.get("id"),
                "kind_label": "Eviction threat",
                "when": t.get("date_threatened"),
                "who": " — ".join(p for p in (t.get("perpetrator"), t.get("perpetrator_role")) if p),
                "summary": t.get("threat_content"),
            }
        )
    for f in late_fees:
        over = f.get("overcharge_amount") or 0
        records.append(
            {
                "id": f.get("id"),
                "kind_label": "Late fee",
                "when": f.get("date_charged"),
                "who": "",
                "summary": (
                    f"${f.get('amount_charged', 0):.2f} charged"
                    + (f" — ${over:.2f} over the 8% cap" if f.get("exceeds_8_percent") else " — within the 8% cap")
                ),
            }
        )
    for b in brokers:
        records.append(
            {
                "id": b.get("id"),
                "kind_label": "Broker record",
                "when": b.get("created_at"),
                "who": b.get("broker_name"),
                "summary": b.get("broker_company"),
            }
        )
    for c in claims:
        records.append(
            {
                "id": c.get("id"),
                "kind_label": "Claim",
                "when": c.get("created_at"),
                "who": c.get("title"),
                "summary": f"{(c.get('status') or 'documenting').replace('_', ' ')} — deadline {c.get('filing_deadline') or 'not set'}",
            }
        )
    records.sort(key=lambda r: str(r.get("when") or ""), reverse=True)

    context.update(
        {
            "records": records,
            "violations": violations,
            "threats": threats,
            "brokers": brokers,
            "claims": claims,
            "windows": windows,
            "violation_types": [(v.value, v.name.replace("_", " ").title()) for v in ViolationType],
            "statutes": _STATUTES_INFO,
        }
    )
    return templates.TemplateResponse(request, "pages/legal_trails.html", context)


# ============== OVERVIEW (JSON) ==============


@router.get("/overview")
async def get_legal_trails_overview(user: UserContext = Depends(require_tier("T2"))):
    """Get overview of all legal trails for the current user."""
    c = await service.counts(user)
    return {
        "violations_count": c[service.KIND_VIOLATION],
        "eviction_threats_count": c[service.KIND_EVICTION_THREAT],
        "late_fee_violations_count": c[service.KIND_LATE_FEE],
        "broker_oversight_count": c[service.KIND_BROKER_OVERSIGHT],
        "legal_claims_count": c[service.KIND_CLAIM],
        "modules": [
            {
                "name": "Legal Claims Trail",
                "description": "Track violations, statutes, and filing windows",
                "endpoint": "/legal-trails/claims",
            },
            {
                "name": "Eviction Threat Trail",
                "description": "Document eviction threats and retaliation",
                "endpoint": "/legal-trails/eviction-threats",
            },
            {
                "name": "Late Fee Violation Trail",
                "description": "Track illegal late fee charges",
                "endpoint": "/legal-trails/late-fees",
            },
            {
                "name": "Broker Oversight Trail",
                "description": "Track broker accountability and license challenges",
                "endpoint": "/legal-trails/broker-oversight",
            },
        ],
        "statutes": _STATUTES_INFO,
        "filing_windows": STATUTE_OF_LIMITATIONS,
    }


# ---------- VIOLATIONS ----------


@router.post("/violations")
async def add_violation(violation: Violation, user: UserContext = Depends(require_tier("T2"))):
    """Log a new violation"""
    record = await service.create_record(
        user,
        service.KIND_VIOLATION,
        violation.model_dump(exclude={"id", "created_at"}),
    )
    if record is None:
        raise _storage_unavailable()
    return {"message": "Violation logged", "violation_id": record["id"], "violation": record}


@router.get("/violations")
async def list_violations(
    violation_type: ViolationType | None = None,
    perpetrator: str | None = None,
    user: UserContext = Depends(require_tier("T2")),
):
    """List the current user's logged violations"""
    results = await service.list_records(user, service.KIND_VIOLATION)
    if violation_type:
        results = [v for v in results if v["violation_type"] == violation_type]
    if perpetrator:
        results = [v for v in results if perpetrator.lower() in (v.get("perpetrator") or "").lower()]
    return {"count": len(results), "violations": results}


@router.get("/violations/{violation_id}")
async def get_violation(violation_id: str, user: UserContext = Depends(require_tier("T2"))):
    """Get a specific violation"""
    record = await service.get_record(user, service.KIND_VIOLATION, violation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Violation not found")
    return record


# ---------- EVICTION THREATS ----------


@router.post("/eviction-threats")
async def add_eviction_threat(threat: EvictionThreat, user: UserContext = Depends(require_tier("T2"))):
    """Log an eviction threat"""
    record = await service.create_record(
        user,
        service.KIND_EVICTION_THREAT,
        threat.model_dump(exclude={"id", "created_at"}),
    )
    if record is None:
        raise _storage_unavailable()
    return {
        "message": "Eviction threat logged",
        "threat_id": record["id"],
        "warning": "If this was retaliatory, you may have a claim under MN 504B.285",
        "statute_of_limitations": "6 years for civil retaliation claims",
        "threat": record,
    }


@router.get("/eviction-threats")
async def list_eviction_threats(user: UserContext = Depends(require_tier("T2"))):
    """List the current user's eviction threats"""
    results = await service.list_records(user, service.KIND_EVICTION_THREAT)
    return {"count": len(results), "threats": results}


# ---------- LATE FEE VIOLATIONS ----------


@router.post("/late-fees")
async def add_late_fee_violation(fee: LateFeeViolation, user: UserContext = Depends(require_tier("T2"))):
    """Log a late fee violation"""
    legal_max = round(fee.rent_amount * 0.08, 2)
    exceeds = fee.amount_charged > legal_max
    fields = fee.model_dump(exclude={"id", "created_at"})
    fields.update(
        {
            "legal_max_fee": legal_max,
            "exceeds_8_percent": exceeds,
            "overcharge_amount": max(0, round(fee.amount_charged - legal_max, 2)),
        }
    )
    record = await service.create_record(user, service.KIND_LATE_FEE, fields)
    if record is None:
        raise _storage_unavailable()

    violations = []
    if not fee.lease_allows_late_fee:
        violations.append("Late fee charged without lease authorization (MN 504B.177)")
    if exceeds:
        violations.append(f"Late fee exceeds 8% cap by ${record['overcharge_amount']:.2f} (MN 504B.177)")

    return {
        "message": "Late fee violation logged",
        "fee_id": record["id"],
        "legal_max_fee": record["legal_max_fee"],
        "exceeds_8_percent": record["exceeds_8_percent"],
        "overcharge_amount": record["overcharge_amount"],
        "violations_detected": violations,
        "fee": record,
    }


@router.get("/late-fees")
async def list_late_fee_violations(user: UserContext = Depends(require_tier("T2"))):
    """List the current user's late fee violations"""
    records = await service.list_records(user, service.KIND_LATE_FEE)
    total_overcharged = round(sum(f.get("overcharge_amount") or 0 for f in records), 2)
    return {
        "count": len(records),
        "total_overcharged": total_overcharged,
        "violations": records,
    }


@router.get("/late-fees/calculate")
async def calculate_late_fee_legal_max(
    rent_amount: float = Query(..., description="Monthly rent amount"),
    days_late: int = Query(default=1, description="Days late"),
    user: UserContext = Depends(require_tier("T2")),
):
    """Calculate the legal maximum late fee under MN 504B.177"""
    legal_max = round(rent_amount * 0.08, 2)
    return {
        "rent_amount": rent_amount,
        "days_late": days_late,
        "legal_max_late_fee": legal_max,
        "statute": "MN 504B.177",
        "note": "Late fees cannot exceed 8% of overdue rent and must be specified in lease",
    }


# ---------- BROKER OVERSIGHT ----------


@router.post("/broker-oversight")
async def add_broker_oversight(broker: BrokerOversight, user: UserContext = Depends(require_tier("T2"))):
    """Add a broker to track for oversight accountability"""
    record = await service.create_record(
        user,
        service.KIND_BROKER_OVERSIGHT,
        broker.model_dump(),
    )
    if record is None:
        raise _storage_unavailable()
    return {
        "message": "Broker oversight record created",
        "broker": record,
        "note": "As the broker of record, this person has legal responsibility for ensuring compliance with Minnesota housing laws and ethical conduct of property managers.",
    }


@router.get("/broker-oversight")
async def list_broker_oversight(user: UserContext = Depends(require_tier("T2"))):
    """List the current user's tracked brokers"""
    results = await service.list_records(user, service.KIND_BROKER_OVERSIGHT)
    return {"count": len(results), "brokers": results}


@router.get("/broker-oversight/{broker_name}")
async def get_broker_oversight(broker_name: str, user: UserContext = Depends(require_tier("T2"))):
    """Get broker oversight details"""
    record = await service.get_record(user, service.KIND_BROKER_OVERSIGHT, broker_name)
    if record is None:
        raise HTTPException(status_code=404, detail="Broker not found")
    return record


@router.post("/broker-oversight/{broker_name}/link-violation")
async def link_violation_to_broker(
    broker_name: str, violation_id: str, user: UserContext = Depends(require_tier("T2"))
):
    """Link a violation to a broker's oversight record"""
    broker = await service.get_record(user, service.KIND_BROKER_OVERSIGHT, broker_name)
    if broker is None:
        raise HTTPException(status_code=404, detail="Broker not found")
    if await service.get_record(user, service.KIND_VIOLATION, violation_id) is None:
        raise HTTPException(status_code=404, detail="Violation not found")

    watched = list(broker.get("violations_under_watch") or [])
    if violation_id not in watched:
        watched.append(violation_id)
    updated = await service.update_record_payload(
        user, service.KIND_BROKER_OVERSIGHT, broker_name, {"violations_under_watch": watched}
    )
    if updated is None:
        raise _storage_unavailable()
    return {
        "message": f"Violation {violation_id} linked to broker {broker_name}",
        "broker": updated,
    }


# ---------- LEGAL CLAIMS ----------


@router.post("/claims")
async def create_legal_claim(claim: LegalClaim, user: UserContext = Depends(require_tier("T2"))):
    """Create a formal legal claim"""
    record = await service.create_record(
        user,
        service.KIND_CLAIM,
        claim.model_dump(exclude={"id", "created_at"}),
    )
    if record is None:
        raise _storage_unavailable()
    return {"message": "Legal claim created", "claim_id": record["id"], "claim": record}


@router.get("/claims")
async def list_legal_claims(
    status: ClaimStatus | None = None, user: UserContext = Depends(require_tier("T2"))
):
    """List the current user's legal claims"""
    results = await service.list_records(user, service.KIND_CLAIM)
    if status:
        results = [c for c in results if c["status"] == status]
    return {"count": len(results), "claims": results}


@router.get("/claims/{claim_id}")
async def get_legal_claim(claim_id: str, user: UserContext = Depends(require_tier("T2"))):
    """Get a specific legal claim"""
    record = await service.get_record(user, service.KIND_CLAIM, claim_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return record


@router.put("/claims/{claim_id}/status")
async def update_claim_status(
    claim_id: str, status: ClaimStatus, user: UserContext = Depends(require_tier("T2"))
):
    """Update claim status"""
    updated = await service.update_record_payload(
        user, service.KIND_CLAIM, claim_id, {"status": status.value}
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return {"message": f"Claim status updated to {status}", "claim": updated}


# ---------- FILING WINDOWS ----------


@router.get("/filing-windows")
async def calculate_filing_windows(
    violation_date: date = Query(..., description="Date violation occurred"),
    user: UserContext = Depends(require_tier("T2")),
):
    """Calculate all filing windows/deadlines for a violation date"""
    windows = [
        _filing_window(violation_date, claim_type, years)
        for claim_type, years in STATUTE_OF_LIMITATIONS.items()
    ]
    return {
        "violation_date": violation_date,
        "windows": sorted(windows, key=lambda x: x["days_remaining"]),
    }


# ---------- COMPLAINT GENERATORS ----------


@router.post("/generate/retaliation-complaint")
async def generate_retaliation_complaint(
    tenant_name: str,
    property_address: str,
    landlord_name: str,
    management_company: str,
    violation_ids: list[str] = Query(default=[]),
    threat_ids: list[str] = Query(default=[]),
    user: UserContext = Depends(require_tier("T2")),
):
    """Generate a retaliation complaint draft from the user's own logged records"""
    violations = []
    for vid in violation_ids:
        record = await service.get_record(user, service.KIND_VIOLATION, vid)
        if record:
            violations.append(record)
    threats = []
    for tid in threat_ids:
        record = await service.get_record(user, service.KIND_EVICTION_THREAT, tid)
        if record:
            threats.append(record)

    return {
        "status": "draft",
        "draft_note": _DRAFT_NOTE,
        "title": "COMPLAINT FOR RETALIATORY EVICTION — DRAFT",
        "statute": "Minnesota Statute 504B.285",
        "complainant": tenant_name,
        "property": property_address,
        "respondents": [landlord_name, management_company],
        "allegations": [],
        "relief_sought": [
            "Injunctive relief prohibiting eviction",
            "Actual damages",
            "Attorney's fees",
            "Civil penalty up to $500",
        ],
        "violations_referenced": violations,
        "threats_documented": threats,
    }


@router.post("/generate/license-complaint")
async def generate_license_complaint(
    broker_name: str,
    license_number: str | None = None,
    company: str = "",
    violations_summary: str = "",
    user: UserContext = Depends(require_tier("T2")),
):
    """Generate a license complaint draft for MN Dept of Commerce"""
    return {
        "status": "draft",
        "draft_note": _DRAFT_NOTE,
        "title": "COMPLAINT TO MINNESOTA DEPARTMENT OF COMMERCE — DRAFT",
        "regarding": f"Real Estate Broker License - {broker_name}",
        "license_number": license_number or "Unknown - Request Lookup",
        "company": company,
        "complaint_type": "Broker Negligence / Failure to Supervise",
        "allegations": [
            "Failure to ensure compliance with Minnesota tenant protection laws",
            "Allowing unlicensed or improper management practices",
            "Failure to supervise property management activities",
            violations_summary,
        ],
        "statutes_violated": [
            "MN Statute 82.81 - Broker Duties",
            "MN Statute 504B.177 - Late Fee Violations",
            "MN Statute 504B.285 - Retaliatory Eviction",
        ],
        "relief_sought": ["Investigation of broker practices", "License suspension or revocation", "Civil penalties"],
        "filing_info": {
            "agency": "Minnesota Department of Commerce",
            "url": "https://mn.gov/commerce/consumers/file-a-complaint/",
            "phone": "651-539-1600",
        },
    }


@router.post("/generate/hud-complaint")
async def generate_hud_complaint(
    tenant_name: str,
    property_address: str,
    management_company: str,
    violation_type: str,
    description: str,
    user: UserContext = Depends(require_tier("T2")),
):
    """Generate a HUD Fair Housing complaint draft"""
    return {
        "status": "draft",
        "draft_note": _DRAFT_NOTE,
        "title": "COMPLAINT TO HUD OFFICE OF FAIR HOUSING — DRAFT",
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
            "regional_office": "Chicago Regional Office (covers Minnesota)",
        },
    }


# ---------- LEGAL HELP RESOURCES ----------


@router.get("/attorneys/minnesota")
async def get_mn_tenant_attorneys(user: UserContext = Depends(require_tier("T2"))):
    """Neutral legal-help channels for Minnesota tenants — official and
    legal-aid resources only (Semptify never endorses private firms)."""
    return {
        "legal_aid": [
            {
                "name": "HOME Line",
                "what": "Tenant hotline — talk through your situation with a housing counselor",
                "phone": "612-728-5767",
                "website": "https://homelinemn.org",
            },
            {
                "name": "Legal Aid — Housing",
                "what": "Legal services for low-income tenants",
                "phone": "612-334-5970",
                "website": "https://mylegalaid.org",
            },
            {
                "name": "LawHelpMN",
                "what": "Legal-aid intake and self-help resources statewide",
                "website": "https://www.lawhelpmn.org",
            },
        ],
        "official_channels": [
            {
                "name": "Minnesota State Bar Lawyer Referral",
                "what": "Referral to a licensed attorney for a consultation",
                "website": "https://www.mnfindalawyer.com",
            },
            {
                "name": "Minnesota Attorney General — Consumer Complaints",
                "what": "File a consumer complaint about landlord practices",
                "website": "https://www.ag.state.mn.us/consumer/complaint.asp",
                "phone": "651-296-3353",
            },
            {
                "name": "HUD Fair Housing Complaint",
                "what": "Federal discrimination complaints — file within 1 year",
                "website": "https://www.hud.gov/program_offices/fair_housing_equal_opp/online-complaint",
                "phone": "1-800-669-9777",
            },
            {
                "name": "Minnesota Department of Commerce",
                "what": "Complaints about licensed real estate brokers",
                "website": "https://mn.gov/commerce/consumers/file-a-complaint/",
                "phone": "651-539-1600",
            },
        ],
        "statutes": _STATUTES_INFO,
    }
