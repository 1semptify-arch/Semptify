"""
Fraud Exposure Router - API Endpoints for Fraud Analysis
========================================================

Provides API access to fraud detection and analysis capabilities.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.core.security import require_user, StorageUser
from app.services.fraud_exposure import (
    get_fraud_service,
    FraudReport,
)

router = APIRouter(prefix="/api/fraud", tags=["Fraud Exposure"])


# Request Models
class AnalyzeFraudRequest(BaseModel):
    """Request to analyze potential fraud"""
    landlord_id: Optional[str] = None
    landlord_name: Optional[str] = None  # Alias for landlord_id
    case_id: Optional[str] = None  # Alternative identifier
    property_address: Optional[str] = None
    case_docs: List[Dict[str, Any]] = []
    subsidies: List[Dict[str, Any]] = []
    lenders: List[Dict[str, Any]] = []
    code_violations: Optional[List[Dict[str, Any]]] = None
    rent_history: Optional[List[Dict[str, Any]]] = None
    complaint_history: Optional[List[Dict[str, Any]]] = None


class PatternCheckRequest(BaseModel):
    """Request to check for fraud patterns"""
    pattern_type: str
    details: Dict[str, Any]


# Response Models
class FraudReportResponse(BaseModel):
    """Fraud analysis report response"""
    id: str
    landlord_id: str
    property_address: Optional[str] = None
    findings: List[Dict[str, Any]] = []
    findings_count: int = 0
    total_potential_damages: float = 0.0
    risk_score: int = 0
    risk_level: Optional[str] = None
    statute_of_limitations: Optional[Dict[str, Any]] = None
    whistleblower_info: Optional[Dict[str, Any]] = None
    recommendations: List[str] = []
    created_at: str


@router.get("/health")
async def fraud_health_check():
    """Health check for fraud exposure service"""
    return {"status": "healthy", "service": "fraud_exposure"}


@router.post("/analyze", response_model=FraudReportResponse)
async def analyze_fraud(
    request: AnalyzeFraudRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Analyze potential fraud in a tenant rights case.
    
    Examines:
    - HUD subsidy violations
    - Mortgage fraud indicators
    - Landlord misconduct patterns
    - Statute of limitations
    - Whistleblower protections
    """
    service = get_fraud_service()

    # Resolve landlord_id from various sources - require at least one identifier
    landlord_id = request.landlord_id or request.landlord_name or request.case_id
    if not landlord_id:
        raise HTTPException(
            status_code=422, 
            detail="At least one identifier required: landlord_id, landlord_name, or case_id"
        )

    try:
        report = await service.analyze_fraud(
            landlord_id=landlord_id,
            case_docs=request.case_docs,
            subsidies=request.subsidies,
            lenders=request.lenders,
            property_address=request.property_address,
            code_violations=request.code_violations or [],
            rent_history=request.rent_history or [],
            complaint_history=request.complaint_history or [],
        )
        # Build response with all required fields
        result = report.to_dict()
        # Compute risk_level from risk_score
        risk_score = result.get("risk_score", 0)
        if risk_score >= 70:
            result["risk_level"] = "critical"
        elif risk_score >= 50:
            result["risk_level"] = "high"
        elif risk_score >= 30:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"
        # Add statute and whistleblower info if findings exist
        if result.get("findings"):
            result["statute_of_limitations"] = service.get_statute_of_limitations("general")
            result["whistleblower_info"] = service.get_whistleblower_protections(None)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fraud analysis failed: {str(e)}")
@router.get("/report/{report_id}")
async def get_fraud_report(
    report_id: str,
    user: StorageUser = Depends(require_user)
):
    """Get a fraud analysis report by ID"""
    service = get_fraud_service()
    report = service.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report.to_dict()


@router.post("/check-pattern")
async def check_fraud_pattern(
    request: PatternCheckRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Check for a specific fraud pattern.
    
    Pattern types:
    - habitability: Check habitability fraud (requires violations list)
    - hud_subsidy: Check HUD subsidy fraud (requires subsidy_info)
    - mortgage: Check mortgage fraud (requires lender_info)
    - security_deposit: Check security deposit fraud (requires deposit_amount)
    """
    service = get_fraud_service()
    
    pattern_type = request.pattern_type.lower()
    details = request.details
    
    try:
        if pattern_type == "habitability":
            result = service.check_habitability_fraud(details.get("violations", []))
        elif pattern_type == "hud_subsidy":
            result = service.check_hud_subsidy_fraud(details.get("subsidy_info"))
        elif pattern_type == "mortgage":
            result = service.check_mortgage_fraud(details.get("lender_info"))
        elif pattern_type == "security_deposit":
            result = service.check_security_deposit_fraud(
                details.get("deposit_amount"),
                details.get("rent_amount"),
                details.get("deductions")
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown pattern type: {pattern_type}. Valid types: habitability, hud_subsidy, mortgage, security_deposit"
            )
        
        return {"pattern_type": pattern_type, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern check failed: {str(e)}")


@router.get("/statute-of-limitations")
async def get_statute_of_limitations(
    fraud_type: str = Query(..., description="Type of fraud (e.g., habitability, hud, mortgage)"),
    discovery_date: Optional[str] = Query(None, description="Date fraud was discovered (YYYY-MM-DD)"),
    user: StorageUser = Depends(require_user)
):
    """
    Get statute of limitations information for a fraud type.
    
    Fraud types:
    - habitability: Landlord habitability fraud
    - hud: HUD subsidy fraud
    - mortgage: Mortgage fraud
    - consumer_fraud: General consumer fraud
    """
    service = get_fraud_service()
    
    sol_info = service.get_statute_of_limitations(fraud_type, discovery_date)
    if not sol_info:
        raise HTTPException(status_code=404, detail=f"No SOL info for fraud type: {fraud_type}")
    
    return sol_info


@router.get("/whistleblower-info")
async def get_whistleblower_info(
    fraud_type: Optional[str] = Query(None, description="Type of fraud for specific protections"),
    user: StorageUser = Depends(require_user)
):
    """
    Get whistleblower protection information.
    
    Returns federal and state protections applicable to fraud reporting.
    """
    service = get_fraud_service()
    return service.get_whistleblower_protections(fraud_type)


@router.get("/patterns")
async def list_fraud_patterns(
    user: StorageUser = Depends(require_user)
):
    """List all known fraud patterns the system can detect"""
    service = get_fraud_service()
    patterns = service.get_all_patterns()
    return {
        "patterns": patterns,
        "count": len(patterns)
    }


@router.get("/agencies")
async def list_reporting_agencies(
    user: StorageUser = Depends(require_user)
):
    """List agencies where fraud can be reported"""
    service = get_fraud_service()
    agencies = service.get_reporting_agencies()
    
    # Group by jurisdiction
    federal = [a for a in agencies if a.get("jurisdiction") == "federal"]
    state = [a for a in agencies if a.get("jurisdiction") == "state"]
    local = [a for a in agencies if a.get("jurisdiction") == "local"]
    
    return {
        "federal": federal,
        "state": state,
        "local": local,
        "total": len(agencies)
    }
