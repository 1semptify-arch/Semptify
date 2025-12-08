"""
Legal Analysis API Router

Provides endpoints for analyzing legal merit, consistency, corroboration,
and evidentiary value of tenancy case information.

Integrated with 🧠 Positronic Brain for real-time event communication.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..services.legal_analysis_engine import (
    get_legal_analysis_engine,
    EvidenceType,
    DocumentLegalStatus,
    CredibilityLevel,
    ConsistencyStatus,
    LegalMeritLevel,
    NoticeComplianceStatus,
)
from ..services.tenancy_hub import get_tenancy_hub_service
from ..services.positronic_brain import get_brain, PositronicBrain, BrainEvent, EventType, ModuleType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/legal-analysis", tags=["Legal Analysis"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DocumentAnalysisRequest(BaseModel):
    document: Dict[str, Any]

class ConsistencyCheckRequest(BaseModel):
    items: List[Dict[str, Any]]
    fields_to_check: List[str] = []

class CorroborationRequest(BaseModel):
    claim: str
    evidence_items: List[Dict[str, Any]]

class TimelineAnalysisRequest(BaseModel):
    events: List[Dict[str, Any]]
    eviction_type: str = "non_payment"

class MeritAssessmentRequest(BaseModel):
    case_data: Dict[str, Any]
    perspective: str = "defendant"  # defendant (tenant) or plaintiff (landlord)


# =============================================================================
# DOCUMENT ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/classify-evidence")
async def classify_evidence(request: DocumentAnalysisRequest):
    """
    Classify a document for legal purposes.
    
    Returns:
    - Evidence type (direct, hearsay, documentary, etc.)
    - Legal status (binding, informational, inadmissible)
    - Credibility level
    - Evidence weight (0.0 to 1.0)
    - Admissibility issues
    """
    engine = get_legal_analysis_engine()
    classification = engine.classify_evidence(request.document)
    
    return {
        "success": True,
        "classification": classification.to_dict(),
        "summary": {
            "is_binding": classification.legal_status == DocumentLegalStatus.LEGALLY_BINDING,
            "is_hearsay": classification.evidence_type == EvidenceType.HEARSAY,
            "is_strong_evidence": classification.weight >= 0.7,
            "needs_attention": len(classification.admissibility_issues) > 0,
        }
    }


@router.post("/classify-evidence/batch")
async def classify_evidence_batch(documents: List[Dict[str, Any]]):
    """
    Classify multiple documents at once.
    """
    engine = get_legal_analysis_engine()
    
    results = []
    for doc in documents:
        classification = engine.classify_evidence(doc)
        results.append({
            "id": doc.get("id", "unknown"),
            "title": doc.get("title", doc.get("filename", "unknown")),
            "classification": classification.to_dict(),
        })
    
    # Summary statistics
    total = len(results)
    binding = sum(1 for r in results if r["classification"]["legal_status"] == "legally_binding")
    hearsay = sum(1 for r in results if r["classification"]["evidence_type"] == "hearsay")
    strong = sum(1 for r in results if r["classification"]["weight"] >= 0.7)
    
    return {
        "success": True,
        "count": total,
        "results": results,
        "summary": {
            "binding_documents": binding,
            "hearsay_documents": hearsay,
            "strong_evidence": strong,
            "weak_evidence": total - strong,
        }
    }


# =============================================================================
# CONSISTENCY ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/check-consistency")
async def check_consistency(request: ConsistencyCheckRequest):
    """
    Check consistency across multiple documents/events.
    
    Looks for contradictions in:
    - Names (tenant, landlord)
    - Addresses
    - Dates
    - Amounts (rent, deposits, claims)
    - Case numbers
    """
    engine = get_legal_analysis_engine()
    
    fields = request.fields_to_check if request.fields_to_check else None
    checks = engine.check_consistency(request.items, fields)
    
    # Group by severity
    consistent = [c for c in checks if c.status == ConsistencyStatus.CONSISTENT]
    minor = [c for c in checks if c.status == ConsistencyStatus.MINOR_DISCREPANCY]
    major = [c for c in checks if c.status == ConsistencyStatus.MAJOR_CONTRADICTION]
    
    return {
        "success": True,
        "total_checks": len(checks),
        "consistent": len(consistent),
        "minor_discrepancies": len(minor),
        "major_contradictions": len(major),
        "has_critical_issues": any(c.significance == "critical" for c in major),
        "discrepancies": [c.to_dict() for c in checks if c.status != ConsistencyStatus.CONSISTENT],
        "summary": _generate_consistency_summary(checks),
    }


def _generate_consistency_summary(checks: List) -> str:
    """Generate a human-readable consistency summary."""
    major = [c for c in checks if c.status == ConsistencyStatus.MAJOR_CONTRADICTION]
    
    if not major:
        return "All checked items are consistent. No contradictions found."
    
    critical = [c for c in major if c.significance == "critical"]
    if critical:
        fields = set(c.field_checked for c in critical)
        return f"CRITICAL: Found {len(critical)} major contradiction(s) in: {', '.join(fields)}. This may undermine the case."
    
    return f"Found {len(major)} inconsistency(ies) that should be reviewed."


# =============================================================================
# CORROBORATION ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/analyze-corroboration")
async def analyze_corroboration(request: CorroborationRequest):
    """
    Analyze how well evidence supports a specific claim.
    
    Example claims:
    - "Landlord failed to make repairs"
    - "Tenant did not pay rent"
    - "Property was uninhabitable"
    """
    engine = get_legal_analysis_engine()
    analysis = engine.analyze_corroboration(request.claim, request.evidence_items)
    
    return {
        "success": True,
        "claim": request.claim,
        "analysis": analysis.to_dict(),
        "verdict": _get_corroboration_verdict(analysis.corroboration_strength),
    }


def _get_corroboration_verdict(strength: float) -> Dict[str, Any]:
    """Get a verdict based on corroboration strength."""
    if strength >= 0.8:
        return {
            "level": "strong",
            "description": "Strong corroboration - claim is well-supported by evidence",
            "court_ready": True,
        }
    elif strength >= 0.6:
        return {
            "level": "moderate",
            "description": "Moderate corroboration - claim has support but could be stronger",
            "court_ready": True,
        }
    elif strength >= 0.4:
        return {
            "level": "weak",
            "description": "Weak corroboration - claim needs more supporting evidence",
            "court_ready": False,
        }
    else:
        return {
            "level": "insufficient",
            "description": "Insufficient corroboration - claim is not adequately supported",
            "court_ready": False,
        }


@router.post("/analyze-corroboration/multi")
async def analyze_multiple_claims(
    claims: List[str] = Body(...),
    evidence_items: List[Dict[str, Any]] = Body(...)
):
    """
    Analyze corroboration for multiple claims at once.
    """
    engine = get_legal_analysis_engine()
    
    results = []
    for claim in claims:
        analysis = engine.analyze_corroboration(claim, evidence_items)
        results.append({
            "claim": claim,
            "strength": analysis.corroboration_strength,
            "supporting_count": len(analysis.supporting_evidence),
            "contradicting_count": len(analysis.contradicting_evidence),
            "verdict": _get_corroboration_verdict(analysis.corroboration_strength)["level"],
        })
    
    # Sort by strength
    results.sort(key=lambda x: x["strength"], reverse=True)
    
    return {
        "success": True,
        "count": len(results),
        "results": results,
        "strongest_claim": results[0]["claim"] if results else None,
        "weakest_claim": results[-1]["claim"] if results else None,
    }


# =============================================================================
# TIMELINE ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/analyze-timeline")
async def analyze_timeline(request: TimelineAnalysisRequest):
    """
    Analyze timeline for legal compliance.
    
    Checks:
    - Notice periods (14-day notice, etc.)
    - Proper sequence of events
    - Missed deadlines
    - Gaps in documentation
    - Statute of limitations
    """
    engine = get_legal_analysis_engine()
    analysis = engine.analyze_timeline(request.events, request.eviction_type)
    
    return {
        "success": True,
        "eviction_type": request.eviction_type,
        "analysis": analysis.to_dict(),
        "compliance_issues": _get_compliance_issues(analysis),
        "defense_opportunities": _get_defense_opportunities(analysis) if analysis.notice_compliance != NoticeComplianceStatus.COMPLIANT else [],
    }


def _get_compliance_issues(analysis) -> List[Dict[str, Any]]:
    """Extract compliance issues from timeline analysis."""
    issues = []
    
    if analysis.notice_compliance == NoticeComplianceStatus.NON_COMPLIANT:
        issues.append({
            "type": "notice",
            "severity": "critical",
            "description": "Notice requirements were not met",
            "impact": "Case may be dismissed",
        })
    elif analysis.notice_compliance == NoticeComplianceStatus.PARTIALLY_COMPLIANT:
        issues.append({
            "type": "notice",
            "severity": "high",
            "description": "Notice period was insufficient",
            "impact": "May be grounds for dismissal",
        })
    
    for issue in analysis.sequence_issues:
        issues.append({
            "type": "procedure",
            "severity": "high",
            "description": issue,
            "impact": "Procedural defense may apply",
        })
    
    for deadline in analysis.missed_deadlines:
        issues.append({
            "type": "deadline",
            "severity": "medium",
            "description": f"Missed deadline: {deadline['title']}",
            "impact": "May affect case progression",
        })
    
    return issues


def _get_defense_opportunities(analysis) -> List[Dict[str, Any]]:
    """Identify defense opportunities from timeline issues."""
    opportunities = []
    
    if analysis.notice_compliance != NoticeComplianceStatus.COMPLIANT:
        opportunities.append({
            "defense": "Improper Notice",
            "basis": "Minnesota requires proper notice before eviction filing",
            "statute": "Minn. Stat. § 504B.135",
            "strength": "strong" if analysis.notice_compliance == NoticeComplianceStatus.NON_COMPLIANT else "moderate",
        })
    
    for issue in analysis.sequence_issues:
        if "without proper notice" in issue.lower():
            opportunities.append({
                "defense": "Procedural Defect",
                "basis": issue,
                "statute": "Minn. Stat. § 504B.321",
                "strength": "moderate",
            })
    
    return opportunities


# =============================================================================
# COMPREHENSIVE MERIT ASSESSMENT
# =============================================================================

@router.post("/assess-merit")
async def assess_legal_merit(request: MeritAssessmentRequest):
    """
    Comprehensive assessment of legal merit.
    
    Analyzes:
    - All evidence quality and admissibility
    - Consistency across all documents
    - Timeline compliance
    - Overall case strength
    
    Perspective:
    - "defendant" (tenant) - looks for defenses
    - "plaintiff" (landlord) - evaluates prosecution strength
    """
    engine = get_legal_analysis_engine()
    assessment = engine.assess_legal_merit(request.case_data, request.perspective)
    
    return {
        "success": True,
        "perspective": request.perspective,
        "assessment": assessment.to_dict(),
        "action_items": _generate_action_items(assessment),
    }


def _generate_action_items(assessment) -> List[Dict[str, Any]]:
    """Generate prioritized action items from assessment."""
    items = []
    
    # Critical issues first
    for issue in assessment.critical_issues:
        items.append({
            "priority": "critical",
            "action": f"Address: {issue}",
            "deadline": "immediate",
        })
    
    # Then recommendations
    for rec in assessment.recommendations:
        items.append({
            "priority": "high",
            "action": rec,
            "deadline": "before hearing",
        })
    
    # Address weaknesses
    for weakness in assessment.weaknesses[:3]:  # Top 3 weaknesses
        items.append({
            "priority": "medium",
            "action": f"Improve: {weakness}",
            "deadline": "when possible",
        })
    
    return items


@router.get("/assess-merit/from-case/{case_id}")
async def assess_merit_from_case(
    case_id: str,
    perspective: str = Query(default="defendant"),
    brain: PositronicBrain = Depends(get_brain)
):
    """
    Assess legal merit directly from a tenancy case.
    """
    hub_service = get_tenancy_hub_service()
    case = hub_service.get_case(case_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    engine = get_legal_analysis_engine()
    case_data = case.to_dict()
    assessment = engine.assess_legal_merit(case_data, perspective)

    # Emit event to brain
    try:
        await brain.emit(BrainEvent(
            event_type=EventType.LEGAL_MERIT_ASSESSED,
            source_module=ModuleType.LEGAL_ANALYSIS,
            data={
                "case_id": case_id,
                "case_name": case.case_name,
                "perspective": perspective,
                "overall_merit": assessment.overall_merit.value,
                "score": assessment.score,
                "strengths_count": len(assessment.strengths),
                "weaknesses_count": len(assessment.weaknesses),
                "critical_issues_count": len(assessment.critical_issues),
            }
        ))
    except Exception as e:
        logger.warning(f"Failed to emit brain event: {e}")

    return {
        "success": True,
        "case_id": case_id,
        "case_name": case.case_name,
        "perspective": perspective,
        "assessment": assessment.to_dict(),
        "action_items": _generate_action_items(assessment),
    }
# =============================================================================
# FACT VS HEARSAY ANALYSIS
# =============================================================================

@router.post("/analyze-hearsay")
async def analyze_hearsay(documents: List[Dict[str, Any]]):
    """
    Analyze documents for hearsay content.
    
    Identifies:
    - Direct evidence (first-hand)
    - Hearsay statements (second-hand)
    - Potentially inadmissible content
    """
    engine = get_legal_analysis_engine()
    
    results = {
        "direct_evidence": [],
        "hearsay": [],
        "needs_review": [],
    }
    
    for doc in documents:
        classification = engine.classify_evidence(doc)
        
        entry = {
            "id": doc.get("id"),
            "title": doc.get("title", doc.get("filename")),
            "evidence_type": classification.evidence_type.value,
            "weight": classification.weight,
        }
        
        if classification.evidence_type == EvidenceType.HEARSAY:
            entry["issue"] = "Contains hearsay - may be inadmissible"
            entry["recommendation"] = "Obtain direct evidence or witness testimony"
            results["hearsay"].append(entry)
        elif classification.evidence_type in [EvidenceType.DIRECT, EvidenceType.DOCUMENTARY, EvidenceType.PHYSICAL]:
            entry["status"] = "Admissible as direct evidence"
            results["direct_evidence"].append(entry)
        else:
            entry["status"] = "Review for admissibility"
            results["needs_review"].append(entry)
    
    return {
        "success": True,
        "summary": {
            "total_documents": len(documents),
            "direct_evidence": len(results["direct_evidence"]),
            "hearsay": len(results["hearsay"]),
            "needs_review": len(results["needs_review"]),
            "hearsay_percentage": len(results["hearsay"]) / len(documents) * 100 if documents else 0,
        },
        "results": results,
        "recommendation": "Replace hearsay with direct evidence where possible" if results["hearsay"] else "Evidence appears admissible",
    }


# =============================================================================
# BINDING DOCUMENT ANALYSIS
# =============================================================================

@router.post("/analyze-binding-status")
async def analyze_binding_status(documents: List[Dict[str, Any]]):
    """
    Analyze which documents are legally binding.
    """
    engine = get_legal_analysis_engine()
    
    results = {
        "binding": [],
        "potentially_binding": [],
        "informational": [],
        "issues": [],
    }
    
    for doc in documents:
        classification = engine.classify_evidence(doc)
        
        entry = {
            "id": doc.get("id"),
            "title": doc.get("title", doc.get("filename")),
            "category": doc.get("category"),
            "legal_status": classification.legal_status.value,
            "authentication_required": classification.authentication_required,
        }
        
        if classification.legal_status == DocumentLegalStatus.LEGALLY_BINDING:
            results["binding"].append(entry)
        elif classification.legal_status == DocumentLegalStatus.POTENTIALLY_BINDING:
            results["potentially_binding"].append(entry)
        elif classification.legal_status == DocumentLegalStatus.INFORMATIONAL:
            results["informational"].append(entry)
        
        if classification.admissibility_issues:
            for issue in classification.admissibility_issues:
                results["issues"].append({
                    "document": entry["title"],
                    "issue": issue,
                })
    
    return {
        "success": True,
        "summary": {
            "binding": len(results["binding"]),
            "potentially_binding": len(results["potentially_binding"]),
            "informational": len(results["informational"]),
            "issues_found": len(results["issues"]),
        },
        "results": results,
    }


# =============================================================================
# QUICK ANALYSIS ENDPOINTS
# =============================================================================

@router.get("/quick-check/{case_id}")
async def quick_case_check(case_id: str, brain: PositronicBrain = Depends(get_brain)):
    """
    Quick legal health check for a case.
    Returns traffic-light style status for key areas.
    """
    hub_service = get_tenancy_hub_service()
    case = hub_service.get_case(case_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    engine = get_legal_analysis_engine()
    case_data = case.to_dict()

    # Quick checks
    checks = {
        "evidence": _check_evidence_status(case_data, engine),
        "consistency": _check_consistency_status(case_data, engine),
        "timeline": _check_timeline_status(case_data, engine),
        "documentation": _check_documentation_status(case_data),
    }

    # Overall status
    statuses = [c["status"] for c in checks.values()]
    if "red" in statuses:
        overall = "red"
    elif "yellow" in statuses:
        overall = "yellow"
    else:
        overall = "green"

    # Emit event to brain
    try:
        await brain.emit(BrainEvent(
            event_type=EventType.LEGAL_QUICK_CHECK,
            source_module=ModuleType.LEGAL_ANALYSIS,
            data={
                "case_id": case_id,
                "overall_status": overall,
                "evidence_status": checks["evidence"]["status"],
                "consistency_status": checks["consistency"]["status"],
                "timeline_status": checks["timeline"]["status"],
                "documentation_status": checks["documentation"]["status"],
            }
        ))
    except Exception as e:
        logger.warning(f"Failed to emit brain event: {e}")

    return {
        "success": True,
        "case_id": case_id,
        "overall_status": overall,
        "checks": checks,
    }
def _check_evidence_status(case_data: Dict[str, Any], engine) -> Dict[str, Any]:
    """Check evidence quality status."""
    documents = list(case_data.get("documents", {}).values())
    
    if not documents:
        return {"status": "red", "message": "No documents uploaded", "count": 0}
    
    # Classify all documents
    hearsay_count = 0
    strong_count = 0
    
    for doc in documents:
        classification = engine.classify_evidence(doc)
        if classification.evidence_type == EvidenceType.HEARSAY:
            hearsay_count += 1
        if classification.weight >= 0.7:
            strong_count += 1
    
    if strong_count == 0:
        return {"status": "red", "message": "No strong evidence", "count": len(documents)}
    elif hearsay_count > len(documents) / 2:
        return {"status": "yellow", "message": "High hearsay ratio", "count": len(documents)}
    else:
        return {"status": "green", "message": f"{strong_count} strong evidence items", "count": len(documents)}


def _check_consistency_status(case_data: Dict[str, Any], engine) -> Dict[str, Any]:
    """Check consistency status."""
    documents = list(case_data.get("documents", {}).values())
    events = list(case_data.get("events", {}).values())
    all_items = documents + events
    
    if len(all_items) < 2:
        return {"status": "yellow", "message": "Not enough items to check", "contradictions": 0}
    
    checks = engine.check_consistency(all_items)
    contradictions = [c for c in checks if c.status == ConsistencyStatus.MAJOR_CONTRADICTION]
    
    if any(c.significance == "critical" for c in contradictions):
        return {"status": "red", "message": "Critical contradictions found", "contradictions": len(contradictions)}
    elif contradictions:
        return {"status": "yellow", "message": f"{len(contradictions)} contradiction(s)", "contradictions": len(contradictions)}
    else:
        return {"status": "green", "message": "All items consistent", "contradictions": 0}


def _check_timeline_status(case_data: Dict[str, Any], engine) -> Dict[str, Any]:
    """Check timeline compliance status."""
    events = list(case_data.get("events", {}).values())
    
    if not events:
        return {"status": "yellow", "message": "No timeline events", "issues": 0}
    
    analysis = engine.analyze_timeline(events)
    
    issues = len(analysis.sequence_issues) + len(analysis.missed_deadlines)
    
    if analysis.notice_compliance == NoticeComplianceStatus.NON_COMPLIANT:
        return {"status": "green", "message": "Notice defect found (defense opportunity)", "issues": issues}
    elif analysis.missed_deadlines:
        return {"status": "red", "message": f"{len(analysis.missed_deadlines)} missed deadline(s)", "issues": issues}
    elif analysis.sequence_issues:
        return {"status": "yellow", "message": "Sequence issues detected", "issues": issues}
    else:
        return {"status": "green", "message": "Timeline compliant", "issues": 0}


def _check_documentation_status(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check documentation completeness."""
    has_tenant = case_data.get("tenant") is not None
    has_landlord = case_data.get("landlord") is not None
    has_property = case_data.get("property") is not None
    has_lease = case_data.get("lease") is not None
    has_legal_case = len(case_data.get("legal_cases", {})) > 0
    
    complete = sum([has_tenant, has_landlord, has_property, has_lease])
    
    missing = []
    if not has_tenant:
        missing.append("tenant")
    if not has_landlord:
        missing.append("landlord")
    if not has_property:
        missing.append("property")
    if not has_lease:
        missing.append("lease")
    
    if complete == 4:
        return {"status": "green", "message": "Core documentation complete", "missing": []}
    elif complete >= 2:
        return {"status": "yellow", "message": f"Missing: {', '.join(missing)}", "missing": missing}
    else:
        return {"status": "red", "message": "Critical documentation missing", "missing": missing}


# =============================================================================
# METADATA ENDPOINTS
# =============================================================================

@router.get("/evidence-types")
async def get_evidence_types():
    """Get all evidence type classifications."""
    return {
        "success": True,
        "evidence_types": [
            {"value": e.value, "description": _get_evidence_description(e)}
            for e in EvidenceType
        ]
    }


def _get_evidence_description(evidence_type: EvidenceType) -> str:
    descriptions = {
        EvidenceType.DIRECT: "First-hand evidence directly observed",
        EvidenceType.CIRCUMSTANTIAL: "Indirect evidence requiring inference",
        EvidenceType.DOCUMENTARY: "Written documents and records",
        EvidenceType.TESTIMONIAL: "Witness statements and testimony",
        EvidenceType.PHYSICAL: "Photos, videos, and physical items",
        EvidenceType.HEARSAY: "Second-hand information (often inadmissible)",
        EvidenceType.EXPERT: "Expert opinion and professional assessments",
    }
    return descriptions.get(evidence_type, "")


@router.get("/legal-statuses")
async def get_legal_statuses():
    """Get all document legal status classifications."""
    return {
        "success": True,
        "legal_statuses": [
            {"value": s.value, "description": _get_status_description(s)}
            for s in DocumentLegalStatus
        ]
    }


def _get_status_description(status: DocumentLegalStatus) -> str:
    descriptions = {
        DocumentLegalStatus.LEGALLY_BINDING: "Document creates legal obligations",
        DocumentLegalStatus.POTENTIALLY_BINDING: "May be binding under certain conditions",
        DocumentLegalStatus.INFORMATIONAL: "For information only, not binding",
        DocumentLegalStatus.HEARSAY: "Contains hearsay, may be inadmissible",
        DocumentLegalStatus.INADMISSIBLE: "Cannot be used as evidence",
        DocumentLegalStatus.NEEDS_AUTHENTICATION: "Requires verification of authenticity",
    }
    return descriptions.get(status, "")


@router.get("/mn-eviction-requirements")
async def get_mn_eviction_requirements():
    """Get Minnesota eviction notice requirements."""
    engine = get_legal_analysis_engine()
    return {
        "success": True,
        "requirements": engine.mn_requirements,
        "service_methods": engine.service_requirements,
    }
