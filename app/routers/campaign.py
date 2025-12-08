"""
Campaign Orchestration Router
Combines Complaints, Fraud Exposure, and Public Exposure into unified campaigns
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel
import logging
import uuid

from app.core.security import require_user, StorageUser

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
    property_address: Optional[str] = None
    landlord_name: Optional[str] = None

class FraudInput(BaseModel):
    landlord_id: str
    case_docs: List[Dict[str, Any]] = []
    subsidies: List[str] = []
    lenders: List[str] = []
    property_address: Optional[str] = None

class PressInput(BaseModel):
    property: str
    violations: str
    contact: str
    bundle_link: Optional[str] = None
    language: str = "en"

class CampaignLaunchRequest(BaseModel):
    """Full campaign launch combining all three modules"""
    name: str
    complaint: Optional[ComplaintInput] = None
    fraud: Optional[FraudInput] = None
    press: Optional[PressInput] = None
    auto_generate_bundle: bool = True

class CampaignStatus(BaseModel):
    id: str
    name: str
    status: str
    created_at: str
    complaint_id: Optional[str] = None
    fraud_report_id: Optional[str] = None
    press_release_id: Optional[str] = None
    zip_bundle_path: Optional[str] = None

# In-memory storage for campaigns (would use DB in production)
_campaigns: Dict[str, Dict[str, Any]] = {}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def file_complaint_internal(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Internal complaint filing"""
    record = {
        "id": f"cmp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}",
        "user_id": user_id,
        "target_agency": params.get("target_agency"),
        "violation_type": params.get("violation_type"),
        "facts": params.get("facts"),
        "language": params.get("language", "en"),
        "property_address": params.get("property_address"),
        "landlord_name": params.get("landlord_name"),
        "status": "submitted",
        "created_at": datetime.utcnow().isoformat()
    }
    return {"complaint_record": record}

async def analyze_fraud_internal(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Internal fraud analysis"""
    findings = []
    case_docs = params.get("case_docs", [])
    subsidies = params.get("subsidies", [])
    lenders = params.get("lenders", [])
    
    # Check for unsigned documents
    if any(d.get("signature_status") == "missing" for d in case_docs):
        findings.append({
            "rule": "unsigned_documents",
            "severity": "high",
            "description": "Documents found without required signatures"
        })
    
    # Check for HUD subsidy issues
    if "HUD" in subsidies or "Section 8" in subsidies:
        findings.append({
            "rule": "hud_subsidy_review",
            "severity": "medium",
            "description": "Property receives federal housing subsidies - enhanced scrutiny applies"
        })
    
    # Check for multiple lenders (potential fraud indicator)
    if len(lenders) > 2:
        findings.append({
            "rule": "multiple_lenders",
            "severity": "medium",
            "description": f"Property has {len(lenders)} lenders - potential mortgage fraud indicator"
        })
    
    risk_score = len(findings) * 25
    risk_level = "low" if risk_score < 25 else "medium" if risk_score < 75 else "high"
    
    report = {
        "id": f"fraud_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}",
        "landlord_id": params.get("landlord_id"),
        "findings": findings,
        "risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "created_at": datetime.utcnow().isoformat()
    }
    return {"fraud_report": report}

async def generate_press_internal(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
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
        "so": f"Kireystayaashu Waxay Daaha Ka Qaadeen Xadgudubyada Guryaha {property_name}"
    }
    
    release = {
        "id": f"press_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}",
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
{bundle_link if bundle_link else 'Available upon request'}

###
        """.strip(),
        "cta": f"Contact: {contact}",
        "bundle": bundle_link,
        "language": language,
        "created_at": datetime.utcnow().isoformat()
    }
    return {"press_release": release}

async def export_zip_internal(complaint_id: str) -> Dict[str, Any]:
    """Generate export bundle"""
    return {
        "zip_bundle": {
            "complaint_id": complaint_id,
            "zip_path": f"/exports/{complaint_id}.zip",
            "created_at": datetime.utcnow().isoformat()
        }
    }

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/launch", response_model=Dict[str, Any])
async def launch_campaign(
    payload: CampaignLaunchRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Launch a full accountability campaign combining:
    - Complaint filing with regulatory agencies
    - Fraud analysis and documentation
    - Press release generation
    - Evidence bundle export
    """
    user_id = user.user_id if hasattr(user, 'user_id') else "anonymous"
    campaign_id = f"camp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    results = {
        "campaign_id": campaign_id,
        "name": payload.name,
        "status": "launched",
        "created_at": datetime.utcnow().isoformat(),
        "components": {}
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
async def get_campaign_status(
    campaign_id: str,
    user: StorageUser = Depends(require_user)
):
    """Get status of a launched campaign"""
    if campaign_id not in _campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaigns[campaign_id]

@router.get("/list")
async def list_campaigns(
    user: StorageUser = Depends(require_user)
):
    """List all campaigns for the current user"""
    return {
        "campaigns": list(_campaigns.values()),
        "total": len(_campaigns)
    }

@router.post("/quick-file")
async def quick_file_complaint(
    payload: ComplaintInput,
    user: StorageUser = Depends(require_user)
):
    """Quick complaint filing without full campaign"""
    user_id = user.user_id if hasattr(user, 'user_id') else "anonymous"
    return await file_complaint_internal(user_id, payload.dict())

@router.post("/quick-analyze")
async def quick_analyze_fraud(
    payload: FraudInput,
    user: StorageUser = Depends(require_user)
):
    """Quick fraud analysis without full campaign"""
    user_id = user.user_id if hasattr(user, 'user_id') else "anonymous"
    return await analyze_fraud_internal(user_id, payload.dict())

@router.post("/quick-press")
async def quick_generate_press(
    payload: PressInput,
    user: StorageUser = Depends(require_user)
):
    """Quick press release generation without full campaign"""
    user_id = user.user_id if hasattr(user, 'user_id') else "anonymous"
    return await generate_press_internal(user_id, payload.dict())

@router.get("/health")
async def campaign_health():
    """Health check for campaign service"""
    return {
        "status": "ok",
        "service": "campaign_orchestration",
        "active_campaigns": len(_campaigns)
    }
