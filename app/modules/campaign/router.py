"""
Campaign Orchestration Router
Combines Complaints, Fraud Exposure, and Public Exposure into unified campaigns
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.id_gen import make_id
from app.core.security import StorageUser, yellow_access
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaign", tags=["Campaign Orchestration"])

# =============================================================================
# MODELS
# =============================================================================


class ComplaintInput(BaseModel):
    target_agency: str
    violation_type: str
    facts: str
    language: str = "en"
    property_address: str | None = None
    landlord_name: str | None = None


class FraudInput(BaseModel):
    landlord_id: str
    case_docs: list[dict[str, Any]] = []
    subsidies: list[str] = []
    lenders: list[str] = []
    property_address: str | None = None


class PressInput(BaseModel):
    property: str
    violations: str
    contact: str
    bundle_link: str | None = None
    language: str = "en"


class LeaderLetterInput(BaseModel):
    """Facts for a letter to an elected official. All fields are factual
    statements the tenant supplies — no accusations beyond what they can
    document."""

    leader_name: str = ""
    leader_role: str = "council_member"  # mayor / council_member / county_commissioner / state_legislator / city_staff
    city: str = ""
    tenant_name: str = ""
    property_address: str = ""
    issue_summary: str = ""
    complaints_filed: list[str] = []
    ask: str = "Bring these conditions to the attention of the relevant city departments and help ensure they are addressed."


class CampaignLaunchRequest(BaseModel):
    """Full campaign launch combining all three modules"""

    name: str
    complaint: ComplaintInput | None = None
    fraud: FraudInput | None = None
    press: PressInput | None = None
    auto_generate_bundle: bool = True


class CampaignStatus(BaseModel):
    id: str
    name: str
    status: str
    created_at: str
    complaint_id: str | None = None
    fraud_report_id: str | None = None
    press_release_id: str | None = None
    zip_bundle_path: str | None = None


# In-memory storage for campaigns (would use DB in production)
_campaigns: dict[str, dict[str, Any]] = {}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


async def file_complaint_internal(user_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Internal complaint filing"""
    record = {
        "id": make_id("cmp"),
        "user_id": user_id,
        "target_agency": params.get("target_agency"),
        "violation_type": params.get("violation_type"),
        "facts": params.get("facts"),
        "language": params.get("language", "en"),
        "property_address": params.get("property_address"),
        "landlord_name": params.get("landlord_name"),
        "status": "submitted",
        "created_at": utc_now().isoformat(),
    }
    return {"complaint_record": record}


async def analyze_fraud_internal(user_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Internal fraud analysis"""
    findings = []
    case_docs = params.get("case_docs", [])
    subsidies = params.get("subsidies", [])
    lenders = params.get("lenders", [])

    # Check for unsigned documents
    if any(d.get("signature_status") == "missing" for d in case_docs):
        findings.append(
            {
                "rule": "unsigned_documents",
                "severity": "high",
                "description": "Documents found without required signatures",
            }
        )

    # Check for HUD subsidy issues
    if "HUD" in subsidies or "Section 8" in subsidies:
        findings.append(
            {
                "rule": "hud_subsidy_review",
                "severity": "medium",
                "description": "Property receives federal housing subsidies - enhanced scrutiny applies",
            }
        )

    # Check for multiple lenders (potential fraud indicator)
    if len(lenders) > 2:
        findings.append(
            {
                "rule": "multiple_lenders",
                "severity": "medium",
                "description": f"Property has {len(lenders)} lenders - potential mortgage fraud indicator",
            }
        )

    risk_score = len(findings) * 25
    risk_level = "low" if risk_score < 25 else "medium" if risk_score < 75 else "high"

    report = {
        "id": make_id("frd"),
        "landlord_id": params.get("landlord_id"),
        "findings": findings,
        "risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "created_at": utc_now().isoformat(),
    }
    return {"fraud_report": report}


async def generate_press_internal(user_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Internal press release generation"""
    property_name = params.get("property", "Unknown Property")
    violations = params.get("violations", "housing violations")
    contact = params.get("contact", "tenant advocate")
    bundle_link = params.get("bundle_link", "")
    language = params.get("language", "en")

    headlines = {
        "en": f"Tenants Expose Housing Violations at {property_name}",
        "es": f"Inquilinos Denuncian Violaciones de Vivienda en {property_name}",
        "hmn": f"Cov Neeg Xauj Tsev Qhia Txog Kev Ua Txhaum Tsev nyob {property_name}",
        "so": f"Kireystayaashu Waxay Daaha Ka Qaadeen Xadgudubyada Guryaha {property_name}",
    }

    release = {
        "id": make_id("prs"),
        "headline": headlines.get(language, headlines["en"]),
        "lede": f"Residents of {property_name} have documented serious issues including: {violations}",
        "body": f"""
FOR IMMEDIATE RELEASE

{headlines.get(language, headlines["en"])}

Residents of {property_name} are speaking out about ongoing housing issues that have affected their quality of life and safety.

DOCUMENTED ISSUES:
{violations}

Tenants have compiled evidence documenting these conditions and are calling for immediate action from property management and regulatory agencies.

CONTACT:
{contact}

SUPPORTING DOCUMENTATION:
{bundle_link if bundle_link else "Available upon request"}

###
        """.strip(),
        "cta": f"Contact: {contact}",
        "bundle": bundle_link,
        "language": language,
        "created_at": utc_now().isoformat(),
    }
    return {"press_release": release}


LEADER_ROLE_LABELS = {
    "mayor": "Mayor",
    "council_member": "Council Member",
    "county_commissioner": "County Commissioner",
    "state_legislator": "State Legislator",
    "city_staff": "City Staff",
}


def _leader_letter_text(params: dict[str, Any]) -> str:
    """Build a factual letter to an elected official.

    Plain-language, respectful, and strictly factual — the tenant states
    what they documented and filed, and asks the official's office for
    help. No threats, no unverified accusations: a letter a council member
    can act on is also one that can't be dismissed as a rant.
    """
    role_label = LEADER_ROLE_LABELS.get(params.get("leader_role", ""), "Official")
    salutation = (
        f"Dear {role_label} {params['leader_name']},"
        if params.get("leader_name")
        else f"Dear {role_label},"
    )
    place = params.get("city") or "your city"
    address_line = (
        f"I am a resident of {place} writing about housing conditions at {params['property_address']}."
        if params.get("property_address")
        else f"I am a resident of {place} writing about housing conditions I have been documenting."
    )

    complaints = params.get("complaints_filed") or []
    complaints_line = ""
    if complaints:
        complaints_line = (
            "\n\nI have filed formal complaints with: "
            + "; ".join(complaints)
            + "."
        )

    return f"""{salutation}

{address_line}

WHAT I HAVE DOCUMENTED:
{params.get('issue_summary') or '(describe the conditions and dates here — stick to what you can point to a document for)'}{complaints_line}

WHAT I AM ASKING:
{params.get('ask')}

I am not asking your office to take my word for anything — I have dated documentation and am happy to share it. I would appreciate a response letting me know how your office can help.

Respectfully,
{params.get('tenant_name') or '(your name)'}
"""


async def export_zip_internal(complaint_id: str) -> dict[str, Any]:
    """Generate export bundle"""
    return {
        "zip_bundle": {
            "complaint_id": complaint_id,
            "zip_path": f"/exports/{complaint_id}.zip",
            "created_at": utc_now().isoformat(),
        }
    }


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("/launch", response_model=dict[str, Any])
async def launch_campaign(payload: CampaignLaunchRequest, user: StorageUser = Depends(yellow_access)):
    """
    Launch a full accountability campaign combining:
    - Complaint filing with regulatory agencies
    - Fraud analysis and documentation
    - Press release generation
    - Evidence bundle export
    """
    user_id = user.user_id if hasattr(user, "user_id") else "anonymous"
    campaign_id = make_id("camp")

    results = {
        "campaign_id": campaign_id,
        "name": payload.name,
        "status": "launched",
        "created_at": utc_now().isoformat(),
        "components": {},
    }

    # File complaint if provided
    complaint_id = None
    if payload.complaint:
        complaint_result = await file_complaint_internal(user_id, payload.complaint.dict())
        results["components"]["complaint"] = complaint_result
        complaint_id = complaint_result["complaint_record"]["id"]

    # Analyze fraud if provided
    if payload.fraud:
        fraud_result = await analyze_fraud_internal(user_id, payload.fraud.dict())
        results["components"]["fraud"] = fraud_result

    # Generate press release if provided
    if payload.press:
        press_data = payload.press.dict()
        if payload.auto_generate_bundle and complaint_id:
            press_data["bundle_link"] = f"/api/campaign/download/{campaign_id}"
        press_result = await generate_press_internal(user_id, press_data)
        results["components"]["press"] = press_result

    # Generate export bundle if complaint was filed
    if complaint_id and payload.auto_generate_bundle:
        export_result = await export_zip_internal(complaint_id)
        results["components"]["export"] = export_result

    # Store campaign
    _campaigns[campaign_id] = results

    logger.info(f"🚀 Campaign launched: {campaign_id} by user {user_id}")
    return results


@router.get("/status/{campaign_id}")
async def get_campaign_status(campaign_id: str, user: StorageUser = Depends(yellow_access)):
    """Get status of a launched campaign"""
    if campaign_id not in _campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaigns[campaign_id]


@router.get("/list")
async def list_campaigns(user: StorageUser = Depends(yellow_access)):
    """List all campaigns for the current user"""
    return {"campaigns": list(_campaigns.values()), "total": len(_campaigns)}


@router.post("/quick-file")
async def quick_file_complaint(payload: ComplaintInput, user: StorageUser = Depends(yellow_access)):
    """Quick complaint filing without full campaign"""
    user_id = user.user_id if hasattr(user, "user_id") else "anonymous"
    return await file_complaint_internal(user_id, payload.dict())


@router.post("/quick-analyze")
async def quick_analyze_fraud(payload: FraudInput, user: StorageUser = Depends(yellow_access)):
    """Quick fraud analysis without full campaign"""
    user_id = user.user_id if hasattr(user, "user_id") else "anonymous"
    return await analyze_fraud_internal(user_id, payload.dict())


@router.post("/quick-press")
async def quick_generate_press(payload: PressInput, user: StorageUser = Depends(yellow_access)):
    """Quick press release generation without full campaign"""
    user_id = user.user_id if hasattr(user, "user_id") else "anonymous"
    return await generate_press_internal(user_id, payload.dict())


@router.get("/pressure-map")
async def pressure_map(user: StorageUser = Depends(yellow_access)):
    """The full accountability sequence — complaints, city leaders, and press —
    as one ordered map. Each step names the endpoint that powers it."""
    return {
        "title": "Accountability pressure map",
        "note": (
            "Every step is something you do yourself, in order, with your own "
            "documentation. Nothing here files or sends anything for you."
        ),
        "steps": [
            {
                "step": 1,
                "name": "Document everything",
                "why": "Every later step leans on dated, verifiable records.",
                "endpoint": "Timeline, journal, and document vault (RECORD pillar)",
            },
            {
                "step": 2,
                "name": "Get advice first",
                "why": "Legal aid and HOME Line can tell you which complaints fit your facts.",
                "endpoint": "GET /api/complaints/quick-start",
            },
            {
                "step": 3,
                "name": "File agency complaints",
                "why": "AG, HUD, Commerce, and others create official records and investigations.",
                "endpoint": "POST /api/complaints/drafts → POST /api/complaints/drafts/{id}/file",
            },
            {
                "step": 4,
                "name": "Tell city leaders",
                "why": "Mayors, council members, and county commissioners can route city departments and put the landlord on notice that the record exists.",
                "endpoint": "POST /api/campaign/leader-letter",
            },
            {
                "step": 5,
                "name": "Press release & media",
                "why": "Public visibility is pressure a landlord can't ignore — keep it factual and you stay on solid ground.",
                "endpoint": "POST /api/exposure/press-release → POST /api/exposure/media-kit",
            },
            {
                "step": 6,
                "name": "Follow up on a schedule",
                "why": "Agencies and offices respond to documented persistence, not volume.",
                "endpoint": "GET /api/campaign/status/{id} + contact interaction logs",
            },
        ],
    }


@router.post("/leader-letter")
async def generate_leader_letter(payload: LeaderLetterInput, user: StorageUser = Depends(yellow_access)):
    """Draft a factual letter to an elected official (mayor, council member,
    county commissioner, state legislator). The tenant supplies the facts;
    the output is a draft for them to review and send themselves."""
    user_id = user.user_id if hasattr(user, "user_id") else "anonymous"
    letter = {
        "id": make_id("ltr"),
        "to_role": payload.leader_role,
        "to_name": payload.leader_name,
        "text": _leader_letter_text(payload.dict()),
        "note": (
            "Review before sending — state only what you can document. "
            "A factual letter carries weight; an exaggerated one gets set aside."
        ),
        "created_at": utc_now().isoformat(),
    }
    logger.info(f"Leader letter drafted: {letter['id']} by user {user_id}")
    return letter


@router.get("/health")
async def campaign_health():
    """Health check for campaign service"""
    return {"status": "ok", "service": "campaign_orchestration", "active_campaigns": len(_campaigns)}
