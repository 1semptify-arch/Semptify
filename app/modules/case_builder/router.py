"""
Case Builder API Router
=======================

REST API endpoints for the Case Builder module.
Provides endpoints for creating cases, managing timelines, evidence,
counterclaims, motions, and generating court documents.

Migrated from app/routers/case_builder.py into the case_builder SDK module.
All imports remain absolute since case_builder is an EXTENDED module that
depends on shared infrastructure (security, database, document_hub).

Now integrated with DocumentHub for auto-population from uploaded documents.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel
from enum import Enum

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_user, StorageUser, yellow_access
from app.core.database import get_db_session
from app.core.document_hub import get_document_hub, CaseData
from app.core.id_gen import make_id
from app.core.utc import utc_now
from app.models.models import Incident

# Import data freshness manager for legal accuracy validation
try:
    from app.core.data_freshness_manager import data_freshness_manager, FreshnessStatus
    FRESHNESS_AVAILABLE = True
except ImportError:
    logger.warning("Data freshness manager not available - legal accuracy validation disabled")
    FRESHNESS_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/case-builder", tags=["Case Builder"])


# =============================================================================
# FRESHNESS VALIDATION
# =============================================================================

def validate_case_freshness(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate freshness of legal data for case creation.
    
    Returns:
        Dict with validation results and warnings
    """
    if not FRESHNESS_AVAILABLE:
        return {"status": "unavailable", "warnings": []}
    
    validation_results = {
        "status": "validated",
        "freshness_score": 100.0,
        "warnings": [],
        "stale_items": [],
        "recommendations": []
    }
    
    # Check legal content freshness for case type
    case_type = case_data.get("case_type", "eviction_defense")
    legal_freshness = data_freshness_manager.check_freshness(f"legal_content_{case_type}")
    if legal_freshness != FreshnessStatus.FRESH:
        validation_results["warnings"].append(f"Legal content for {case_type} may be outdated")
        validation_results["stale_items"].append("legal_content")
        validation_results["recommendations"].append("Review latest eviction defense laws")
    
    # Check court rules freshness
    court = case_data.get("court", "")
    if court:
        court_freshness = data_freshness_manager.check_freshness(f"court_rules_{court}")
        if court_freshness != FreshnessStatus.FRESH:
            validation_results["warnings"].append(f"Court rules for {court} may be outdated")
            validation_results["stale_items"].append("court_rules")
            validation_results["recommendations"].append("Verify current court procedures")
    
    # Check form requirements freshness
    form_freshness = data_freshness_manager.check_freshness("court_forms")
    if form_freshness != FreshnessStatus.FRESH:
        validation_results["warnings"].append("Court form requirements may be outdated")
        validation_results["stale_items"].append("court_forms")
        validation_results["recommendations"].append("Update form templates")
    
    # Check deadline rules freshness
    deadline_freshness = data_freshness_manager.check_freshness("deadline_rules")
    if deadline_freshness != FreshnessStatus.FRESH:
        validation_results["warnings"].append("Deadline calculation rules may be outdated")
        validation_results["stale_items"].append("deadline_rules")
        validation_results["recommendations"].append("Verify deadline calculations")
    
    # Calculate overall freshness score
    total_checks = 4  # legal_content, court_rules, court_forms, deadline_rules
    fresh_count = total_checks - len(validation_results["stale_items"])
    validation_results["freshness_score"] = (fresh_count / total_checks) * 100
    
    return validation_results


def get_freshness_action_recommendations(freshness_results: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Generate action recommendations based on freshness validation results.
    
    Returns a list of actionable recommendations prioritized by urgency.
    """
    recommendations = []
    
    # Check overall freshness score
    score = freshness_results.get("freshness_score", 100)
    stale_items = freshness_results.get("stale_items", [])
    warnings = freshness_results.get("warnings", [])
    
    if score < 50:
        recommendations.append({
            "priority": "critical",
            "action": "Verify all legal information before proceeding",
            "description": "Multiple data sources are outdated. Legal accuracy cannot be guaranteed.",
            "cta": "Review Updates",
            "icon": "warning"
        })
    elif score < 80:
        recommendations.append({
            "priority": "high",
            "action": "Review outdated information",
            "description": "Some legal data may be stale. Verify before filing.",
            "cta": "Check Updates",
            "icon": "alert"
        })
    
    # Specific recommendations based on stale items
    if "legal_content" in stale_items:
        recommendations.append({
            "priority": "high",
            "action": "Update legal content knowledge",
            "description": "Eviction defense laws may have changed. Review latest statutes.",
            "cta": "View Laws",
            "icon": "book"
        })
    
    if "court_rules" in stale_items:
        recommendations.append({
            "priority": "medium",
            "action": "Verify court procedures",
            "description": "Court rules may have been updated. Check with court clerk.",
            "cta": "Contact Court",
            "icon": "court"
        })
    
    if "court_forms" in stale_items:
        recommendations.append({
            "priority": "medium",
            "action": "Download latest court forms",
            "description": "Form requirements may have changed. Get current versions.",
            "cta": "Get Forms",
            "icon": "document"
        })
    
    if "deadline_rules" in stale_items:
        recommendations.append({
            "priority": "critical",
            "action": "Verify all deadlines immediately",
            "description": "Deadline calculations may be incorrect. Missing a deadline could be fatal to your case.",
            "cta": "Check Deadlines",
            "icon": "clock"
        })
    
    # General recommendations based on warnings
    if any("Minnesota" in w for w in warnings):
        recommendations.append({
            "priority": "high",
            "action": "Review Minnesota-specific requirements",
            "description": "Minnesota law requires specific notice periods and service methods.",
            "cta": "MN Guide",
            "icon": "map"
        })
    
    if any("COVID" in w for w in warnings):
        recommendations.append({
            "priority": "medium",
            "action": "Check current emergency protections",
            "description": "COVID-19 protections may have changed. Verify current status.",
            "cta": "Check Status",
            "icon": "shield"
        })
    
    # Always add a general recommendation
    if not recommendations:
        recommendations.append({
            "priority": "low",
            "action": "Data is current",
            "description": "All legal information appears up to date.",
            "cta": "Continue",
            "icon": "check"
        })
    
    return recommendations


def validate_court_forms_freshness(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate court form requirements freshness.
    
    Checks:
    - Form templates are current
    - Required forms for case type are available
    - Form versions match court requirements
    - E-filing requirements are up to date
    
    Returns:
        Dict with form validation results
    """
    if not FRESHNESS_AVAILABLE:
        return {"status": "unavailable", "forms": []}
    
    validation_results = {
        "status": "validated",
        "forms": [],
        "warnings": [],
        "recommendations": []
    }
    
    case_type = case_data.get("case_type", "eviction_defense")
    court = case_data.get("court", "")
    
    # Check general court forms freshness
    forms_freshness = data_freshness_manager.check_freshness("court_forms")
    if forms_freshness != FreshnessStatus.FRESH:
        validation_results["warnings"].append("Court forms may be outdated")
        validation_results["recommendations"].append("Download latest forms from court website")
    
    # Check case-type specific forms
    required_forms = {
        "eviction_defense": ["Answer", "Counterclaim", "Motion to Dismiss"],
        "eviction_defense_rent_nonpayment": ["Answer", "Payment Plan Request", "Hardship Declaration"],
        "eviction_defense_lease_violation": ["Answer", "Cure Violation Notice", "Motion for Continuance"]
    }
    
    forms_for_case = required_forms.get(case_type, required_forms["eviction_defense"])
    
    for form_name in forms_for_case:
        form_key = f"form_{form_name.lower().replace(' ', '_')}"
        form_freshness = data_freshness_manager.check_freshness(form_key)
        
        form_status = {
            "form": form_name,
            "status": "current" if form_freshness == FreshnessStatus.FRESH else "stale",
            "required": True
        }
        
        if form_freshness != FreshnessStatus.FRESH:
            validation_results["warnings"].append(f"Form '{form_name}' may be outdated")
            form_status["recommendation"] = f"Verify latest version of {form_name}"
        
        validation_results["forms"].append(form_status)
    
    # Check e-filing requirements if applicable
    if "e-file" in court.lower() or "electronic" in court.lower():
        efiling_freshness = data_freshness_manager.check_freshness("efiling_requirements")
        if efiling_freshness != FreshnessStatus.FRESH:
            validation_results["warnings"].append("E-filing requirements may be outdated")
            validation_results["recommendations"].append("Verify e-filing procedures with court")
    
    return validation_results


def validate_minnesota_legal_requirements(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Minnesota-specific legal requirements for eviction cases.
    
    Minnesota-specific rules:
    - 7-day notice for non-payment of rent (Minn. Stat. § 504B.285)
    - 14-day notice for lease violations (Minn. Stat. § 504B.285)
    - 30-day notice for month-to-month termination (Minn. Stat. § 504B.135)
    - Proper service requirements (personal, substitute, or posting + mailing)
    - Right to counsel in certain counties
    - Notice to vacate requirements
    
    Returns:
        Dict with Minnesota-specific validation results
    """
    validation_results = {
        "state": "Minnesota",
        "requirements_validated": [],
        "warnings": [],
        "recommendations": []
    }
    
    # Check if this is a Minnesota case
    court = case_data.get("court", "").lower()
    property_address = case_data.get("property_address", "").lower()
    
    is_mn_case = any([
        "minnesota" in court,
        "mn" in court,
        "county" in court and "district" in court,
        any(city in property_address for city in ["minneapolis", "st. paul", "duluth", "rochester"])
    ])
    
    if not is_mn_case:
        validation_results["state"] = "unknown"
        return validation_results
    
    # Check notice period requirements
    notice_period = case_data.get("notice_period_days")
    complaint_type = case_data.get("complaint_type", "eviction")
    
    if complaint_type == "eviction" or complaint_type == "rent_nonpayment":
        # Minnesota requires 7-day notice for non-payment
        if notice_period and notice_period < 7:
            validation_results["warnings"].append(
                f"Minnesota requires 7-day notice for non-payment (Minn. Stat. § 504B.285), "
                f"but notice period is {notice_period} days"
            )
            validation_results["recommendations"].append(
                "Verify notice period complies with Minnesota law"
            )
        validation_results["requirements_validated"].append("notice_period_7_day")
        
    elif complaint_type == "lease_violation":
        # Minnesota requires 14-day notice for lease violations
        if notice_period and notice_period < 14:
            validation_results["warnings"].append(
                f"Minnesota requires 14-day notice for lease violations (Minn. Stat. § 504B.285), "
                f"but notice period is {notice_period} days"
            )
        validation_results["requirements_validated"].append("notice_period_14_day")
    
    # Check for proper service requirements
    service_method = case_data.get("service_method", "").lower()
    if service_method:
        valid_methods = ["personal", "substitute", "posting", "mailing", "certified_mail"]
        if service_method not in valid_methods:
            validation_results["warnings"].append(
                f"Service method '{service_method}' may not comply with Minnesota requirements"
            )
            validation_results["recommendations"].append(
                "Use personal service, substitute service, or posting + mailing per Minn. Stat. § 504B.331"
            )
        validation_results["requirements_validated"].append("service_method")
    
    # Check for right to counsel (pilot program in certain counties)
    right_to_counsel_counties = ["hennepin", "ramsey", "dakota", "anoka"]
    if any(county in court for county in right_to_counsel_counties):
        validation_results["requirements_validated"].append("right_to_counsel_notice")
        validation_results["recommendations"].append(
            "Tenant may have right to free legal counsel - verify with county program"
        )
    
    # Check for COVID-19 protections (if applicable)
    if case_data.get("covid_impact", False):
        validation_results["warnings"].append(
            "COVID-19 impact claimed - verify current emergency protections"
        )
        validation_results["recommendations"].append(
            "Check for active emergency tenant protections in Minnesota"
        )
    
    return validation_results


# =============================================================================
# MODELS
# =============================================================================

class CaseCreate(BaseModel):
    case_number: str
    case_type: str = "eviction_defense"
    court: str
    property_address: str
    rent_amount: float = 0
    security_deposit: float = 0
    plaintiff_name: str
    defendant_name: str
    hearing_date: Optional[str] = None
    lease_start: Optional[str] = None
    lease_end: Optional[str] = None
    notes: Optional[str] = None


class TimelineEventCreate(BaseModel):
    date: str
    title: str
    description: str
    category: str  # lease, violation, communication, court, evidence
    importance: str = "medium"  # critical, high, medium, low
    evidence_ids: List[str] = []
    source: Optional[str] = None


class EvidenceCreate(BaseModel):
    title: str
    evidence_type: str  # video, photo, document, text_message, email, witness
    date_obtained: Optional[str] = None
    date_of_event: Optional[str] = None
    description: str
    source: str
    relevance: str
    file_path: Optional[str] = None
    notes: Optional[str] = None


class CounterclaimCreate(BaseModel):
    claim_type: str
    title: str
    facts: List[str]
    damages_sought: Dict[str, float] = {}
    evidence_ids: List[str] = []
    notes: Optional[str] = None


class MotionCreate(BaseModel):
    motion_type: str
    title: str
    deadline: str
    basis: List[str]
    relief_sought: str
    supporting_evidence: List[str] = []
    notes: Optional[str] = None


class DeadlineCreate(BaseModel):
    title: str
    deadline: str
    description: str
    priority: str = "medium"  # critical, high, medium, low
    reminder_days: List[int] = [7, 3, 1]
    notes: Optional[str] = None


class DefenseCreate(BaseModel):
    defense_type: str
    title: str
    legal_basis: str
    facts_supporting: List[str]
    evidence_ids: List[str] = []
    strength: str = "medium"


# =============================================================================
# DATA STORAGE — PostgreSQL via Incident model
# Full case JSON stored in incident_metadata JSONB column.
# Replaces ephemeral local file storage (wiped on Render restart).
# =============================================================================

async def load_case(case_id: str, user_id: str) -> Optional[Dict]:
    """Load case from DB, enforcing user ownership."""
    async with get_db_session() as session:
        row = await session.execute(
            select(Incident).where(
                Incident.incident_id == int(case_id),
                Incident.user_id == user_id,
            )
        )
        incident = row.scalar_one_or_none()
        if not incident:
            return None
        data = dict(incident.incident_metadata or {})
        data["case_id"] = str(incident.incident_id)
        data["user_id"] = incident.user_id
        data["status"] = incident.status
        data["created_at"] = incident.created_at.isoformat()
        data["updated_at"] = incident.updated_at.isoformat()
        return data


async def save_case(case_id: str, case_data: Dict, user_id: str) -> None:
    """Persist full case JSON into incident_metadata."""
    case_data["user_id"] = user_id
    async with get_db_session() as session:
        row = await session.execute(
            select(Incident).where(
                Incident.incident_id == int(case_id),
                Incident.user_id == user_id,
            )
        )
        incident = row.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Case {case_id} not found for user")
        incident.incident_metadata = case_data
        incident.status = case_data.get("status", incident.status)
        incident.title = case_data.get("case_name") or case_data.get("title") or incident.title
        incident.incident_type = case_data.get("case_type") or incident.incident_type
        await session.commit()


async def verify_case_ownership(case_id: str, user_id: str) -> bool:
    """Return True if case exists and belongs to user."""
    async with get_db_session() as session:
        row = await session.execute(
            select(Incident.incident_id).where(
                Incident.incident_id == int(case_id),
                Incident.user_id == user_id,
            )
        )
        return row.scalar_one_or_none() is not None


# =============================================================================
# TEMPLATE DATA - MINNESOTA LAW
# =============================================================================

MN_DEFENSES = {
    "improper_notice": {
        "title": "Improper Notice",
        "legal_basis": "Minn. Stat. § 504B.135",
        "description": "The eviction notice was defective or not properly served",
        "elements": [
            "Notice was not served properly (in person, posted, or mailed)",
            "Notice period was too short (14 days for non-payment, varies for other causes)",
            "Notice lacked required information",
            "Wrong type of notice used"
        ]
    },
    "retaliation": {
        "title": "Retaliatory Eviction",
        "legal_basis": "Minn. Stat. § 504B.441",
        "description": "Eviction is retaliation for exercising legal rights",
        "elements": [
            "You engaged in protected activity (complained to inspector, requested repairs, etc.)",
            "Eviction was filed within 90 days of protected activity",
            "Landlord knew about your protected activity"
        ]
    },
    "habitability": {
        "title": "Breach of Habitability",
        "legal_basis": "Minn. Stat. § 504B.161",
        "description": "Landlord failed to maintain habitable conditions",
        "elements": [
            "Serious defects exist affecting health/safety",
            "You notified landlord of defects (or defects were obvious)",
            "Landlord failed to repair within reasonable time",
            "Defects not caused by you"
        ]
    },
    "discrimination": {
        "title": "Discriminatory Eviction",
        "legal_basis": "Minn. Stat. § 363A.09, Fair Housing Act",
        "description": "Eviction based on protected class status",
        "elements": [
            "You are member of protected class",
            "Eviction is based on protected status",
            "Similarly situated non-protected tenants treated differently"
        ]
    },
    "waiver": {
        "title": "Waiver",
        "legal_basis": "Contract Law",
        "description": "Landlord waived right to evict by accepting rent or delay",
        "elements": [
            "Landlord accepted rent after breach",
            "Landlord knew of breach when accepting rent",
            "Landlord's conduct indicated waiver"
        ]
    },
    "landlord_breach": {
        "title": "Landlord Breach of Lease",
        "legal_basis": "Contract Law",
        "description": "Landlord breached lease first, excusing your performance",
        "elements": [
            "Landlord had obligation under lease",
            "Landlord failed to perform obligation",
            "Failure was material breach"
        ]
    }
}

MN_COUNTERCLAIMS = {
    "breach_of_habitability": {
        "title": "Breach of Warranty of Habitability",
        "legal_basis": "Minn. Stat. § 504B.161",
        "description": "Landlord failed to maintain habitable conditions",
        "elements": [
            "Landlord knew or should have known of defect",
            "Defect substantially affected habitability",
            "Tenant notified landlord or defect was obvious",
            "Reasonable time to repair passed",
            "Defect not caused by tenant"
        ],
        "damages": [
            "Rent reduction/abatement for diminished value",
            "Repair costs if tenant fixed problem",
            "Moving costs if forced to relocate",
            "Property damage",
            "Medical expenses if health affected"
        ]
    },
    "breach_of_quiet_enjoyment": {
        "title": "Breach of Covenant of Quiet Enjoyment",
        "legal_basis": "Minn. Stat. § 504B.375",
        "description": "Landlord substantially interfered with your use of premises",
        "elements": [
            "Landlord's actions substantially interfered with use",
            "Interference was material and ongoing",
            "You did not cause the interference"
        ],
        "damages": [
            "Rent abatement",
            "Emotional distress",
            "Consequential damages"
        ]
    },
    "negligent_maintenance": {
        "title": "Negligent Maintenance",
        "legal_basis": "Common Law Negligence",
        "description": "Landlord's negligence caused injury or damage",
        "elements": [
            "Landlord owed duty of care",
            "Landlord breached that duty",
            "Breach caused injury/damage",
            "Actual damages resulted"
        ],
        "damages": [
            "Property damage",
            "Personal injury costs",
            "Medical expenses",
            "Lost wages"
        ]
    },
    "fraud": {
        "title": "Fraud/Misrepresentation",
        "legal_basis": "Common Law Fraud, Minn. Stat. § 325F.69",
        "description": "Landlord made false statements you relied on",
        "elements": [
            "Landlord made false statement of material fact",
            "Landlord knew it was false (or was reckless)",
            "Landlord intended you to rely on it",
            "You actually relied on it",
            "You suffered damages"
        ],
        "damages": [
            "Out of pocket losses",
            "Benefit of bargain damages",
            "Punitive damages (possible)"
        ]
    },
    "harassment": {
        "title": "Tenant Harassment",
        "legal_basis": "Minn. Stat. § 504B.395",
        "description": "Landlord engaged in harassment to force you out",
        "elements": [
            "Landlord engaged in harassing conduct",
            "Conduct was intentional",
            "Conduct was designed to interfere with tenancy"
        ],
        "damages": [
            "Statutory damages",
            "Actual damages",
            "Attorney fees"
        ]
    },
    "illegal_lockout": {
        "title": "Illegal Lockout/Self-Help Eviction",
        "legal_basis": "Minn. Stat. § 504B.375",
        "description": "Landlord attempted to evict without court process",
        "elements": [
            "Landlord changed locks, removed belongings, or cut utilities",
            "Done without court order",
            "Intent to exclude tenant"
        ],
        "damages": [
            "Up to $500 statutory penalty",
            "Actual damages",
            "Hotel/moving costs",
            "Lost property value"
        ]
    },
    "security_deposit": {
        "title": "Security Deposit Violations",
        "legal_basis": "Minn. Stat. § 504B.178",
        "description": "Landlord improperly withheld security deposit",
        "elements": [
            "You paid security deposit",
            "Tenancy ended",
            "Landlord failed to return within 21 days",
            "Or landlord made improper deductions"
        ],
        "damages": [
            "Return of wrongfully withheld deposit",
            "Bad faith penalty (up to $500)",
            "Interest on deposit"
        ]
    }
}

MOTION_TEMPLATES = {
    "motion_to_compel": {
        "title": "Motion to Compel Discovery",
        "description": "Force opposing party to provide requested documents or information",
        "when_to_use": [
            "Landlord refuses to provide documents you requested",
            "Landlord ignores discovery requests",
            "Need video/security footage before it's deleted",
            "Need financial records or communications"
        ],
        "legal_basis": [
            "Minn. R. Civ. P. 37.01 - Motion to Compel Discovery",
            "Minn. R. Civ. P. 34 - Production of Documents",
            "Minn. R. Civ. P. 33 - Interrogatories"
        ],
        "template": """STATE OF MINNESOTA                          DISTRICT COURT
COUNTY OF {county}                          {judicial_district} JUDICIAL DISTRICT

{plaintiff_name},
    Plaintiff,                              Case No. {case_number}

vs.                                         MOTION TO COMPEL DISCOVERY

{defendant_name},
    Defendant.

TO: THE ABOVE-NAMED COURT AND PLAINTIFF:

    Defendant {defendant_name}, appearing pro se, respectfully moves this Court for an 
order compelling Plaintiff to respond to Defendant's discovery requests, specifically:

    1. {discovery_requests}

GROUNDS:

    This motion is made pursuant to Minnesota Rules of Civil Procedure 37.01 on the 
following grounds:

    1. On {request_date}, Defendant served discovery requests on Plaintiff.
    2. Plaintiff's responses were due by {due_date}.
    3. As of this date, Plaintiff has failed to {failure_description}.
    4. The requested information is relevant to Defendant's defenses and counterclaims.
    5. Defendant requires this information to prepare for the hearing scheduled on {hearing_date}.

RELIEF SOUGHT:

    Defendant respectfully requests that this Court:
    1. Order Plaintiff to fully respond to Defendant's discovery requests within 10 days;
    2. Award Defendant costs and expenses incurred in bringing this motion;
    3. Grant such other relief as the Court deems just.

Dated: {today_date}

                                            _______________________________
                                            {defendant_name}
                                            {defendant_address}
                                            {defendant_phone}
                                            Defendant, Pro Se"""
    },
    "motion_to_dismiss": {
        "title": "Motion to Dismiss",
        "description": "Request dismissal due to legal defects",
        "when_to_use": [
            "Notice was defective (wrong dates, wrong method)",
            "Complaint was not properly served",
            "Complaint fails to state a valid claim",
            "Wrong party named as landlord"
        ],
        "legal_basis": [
            "Minn. R. Civ. P. 12.02 - Defenses and Objections",
            "Minn. Stat. § 504B.135 - Notice Requirements",
            "Minn. Stat. § 504B.321 - Service Requirements"
        ],
        "template": """STATE OF MINNESOTA                          DISTRICT COURT
COUNTY OF {county}                          {judicial_district} JUDICIAL DISTRICT

{plaintiff_name},
    Plaintiff,                              Case No. {case_number}

vs.                                         MOTION TO DISMISS

{defendant_name},
    Defendant.

    Defendant {defendant_name} moves this Court for an order dismissing this action 
pursuant to Minnesota Rule of Civil Procedure 12.02 on the following grounds:

    {grounds}

MEMORANDUM OF LAW:

    {legal_argument}

CONCLUSION:

    For the foregoing reasons, Defendant respectfully requests that this Court dismiss 
Plaintiff's Complaint with prejudice.

Dated: {today_date}

                                            _______________________________
                                            {defendant_name}, Pro Se"""
    },
    "motion_for_continuance": {
        "title": "Motion for Continuance",
        "description": "Request postponement of hearing",
        "when_to_use": [
            "Need more time to gather evidence",
            "Waiting for discovery responses",
            "Scheduling conflict",
            "Need time to find legal assistance"
        ],
        "legal_basis": [
            "Minn. R. Civ. P. 6.02 - Enlargement of Time",
            "Court's inherent scheduling authority"
        ],
        "template": """STATE OF MINNESOTA                          DISTRICT COURT
COUNTY OF {county}                          {judicial_district} JUDICIAL DISTRICT

{plaintiff_name},
    Plaintiff,                              Case No. {case_number}

vs.                                         MOTION FOR CONTINUANCE

{defendant_name},
    Defendant.

    Defendant {defendant_name} respectfully moves this Court for a continuance of the 
hearing currently scheduled for {current_hearing_date}.

GROUNDS:

    1. {reason_for_continuance}
    
    2. This is Defendant's {number} request for continuance.
    
    3. A continuance will not prejudice the Plaintiff.
    
    4. Good cause exists for granting this motion.

PROPOSED NEW DATE:

    Defendant requests the hearing be rescheduled to on or after {proposed_date}.

Dated: {today_date}

                                            _______________________________
                                            {defendant_name}, Pro Se"""
    }
}


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/")
async def case_builder_info():
    """Get Case Builder module information."""
    return {
        "module": "case_builder",
        "version": "1.0.0",
        "description": "Build and manage eviction defense cases and counter-suits",
        "features": [
            "Case creation and management",
            "Timeline tracking",
            "Evidence organization",
            "Counterclaim builder",
            "Motion generator",
            "Deadline reminders",
            "Document generation"
        ]
    }


# -----------------------------------------------------------------------------
# Cases
# -----------------------------------------------------------------------------

@router.get("/cases")
async def list_cases(user: StorageUser = Depends(yellow_access)):
    """List all cases for the authenticated user with computed status and progress."""
    user_id = user.user_id
    cases = []

    async with get_db_session() as session:
        rows = await session.execute(
            select(Incident)
            .where(Incident.user_id == user_id)
            .order_by(Incident.updated_at.desc())
        )
        incidents = rows.scalars().all()

    for incident in incidents:
        case = dict(incident.incident_metadata or {})
        case["case_id"] = str(incident.incident_id)
        case["status"] = incident.status
        case["updated_at"] = incident.updated_at.isoformat()

        status = case.get("status", "draft") or "draft"

        progress = 0
        if case.get("case_number"):    progress += 10
        if case.get("property_address"): progress += 10
        if case.get("plaintiff", {}).get("name"): progress += 10
        if len(case.get("timeline", [])): progress += 15
        if len(case.get("evidence", [])): progress += 20
        if len(case.get("defenses", [])): progress += 15
        if len(case.get("motions", [])):  progress += 20
        progress = min(progress, 100)

        next_deadline = next_deadline_task = None
        urgent = False
        deadlines = case.get("deadlines", [])
        if deadlines:
            today = date.today()
            upcoming = sorted(
                [d for d in deadlines if d.get("deadline") and datetime.fromisoformat(d["deadline"]).date() >= today],
                key=lambda x: x["deadline"]
            )
            if upcoming:
                next_dl = upcoming[0]
                next_deadline = next_dl.get("deadline")
                next_deadline_task = next_dl.get("title", "Deadline")
                urgent = (datetime.fromisoformat(next_deadline).date() - today).days <= 7
        if not next_deadline and case.get("hearing_date"):
            next_deadline = case.get("hearing_date")
            next_deadline_task = "Hearing"
            try:
                urgent = (datetime.fromisoformat(next_deadline).date() - date.today()).days <= 7
            except ValueError:
                pass

        cases.append({
            "id": case["case_id"],
            "case_number": case.get("case_number"),
            "case_type": case.get("case_type"),
            "status": status,
            "court": case.get("court"),
            "property_address": case.get("property_address"),
            "hearing_date": case.get("hearing_date"),
            "plaintiff_name": case.get("plaintiff", {}).get("name"),
            "defendant_name": case.get("defendant", {}).get("name"),
            "progress": progress,
            "next_deadline": next_deadline,
            "next_deadline_task": next_deadline_task,
            "urgent": urgent,
            "defenses": [d.get("defense_type") for d in case.get("defenses", [])],
            "evidence_count": len(case.get("evidence", [])),
            "timeline_events": [
                {"date": e.get("date"), "title": e.get("title")}
                for e in (case.get("timeline", []) or [])[:5]
            ],
            "updated_at": case.get("updated_at"),
        })

    return {"cases": cases, "count": len(cases)}


@router.get("/cases/{case_id}")
async def get_case(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Get a specific case belonging to the authenticated user.

    Includes verified facts from the Context Engine for the case's subject.
    """
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    # Enrich with Context Engine facts (best-effort, never breaks)
    case_type = case.get("case_type", "eviction_defense")
    ctx_subject = _case_type_to_subject(case_type)
    case["context_facts"] = await _get_context_facts(ctx_subject)
    case["context_subject"] = ctx_subject
    return case


@router.get("/cases/{case_id}/context")
async def get_case_context(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Get verified Context Engine facts for a case's subject.

    Returns cached facts with source URLs — no hallucination.
    """
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case_type = case.get("case_type", "eviction_defense")
    ctx_subject = _case_type_to_subject(case_type)
    facts = await _get_context_facts(ctx_subject)
    return {
        "case_id": case_id,
        "subject": ctx_subject,
        "jurisdiction": "MN",
        "count": len(facts),
        "facts": facts,
    }


def _case_type_to_subject(case_type: str) -> str:
    """Map a CaseType value to a Context Engine canonical subject."""
    mapping = {
        "eviction_defense": "eviction",
        "counter_suit": "eviction",
        "habitability": "habitability",
        "security_deposit": "deposit",
        "discrimination": "discrimination",
        "retaliation": "retaliation",
    }
    return mapping.get(case_type, "eviction")


async def _get_context_facts(subject: str, jurisdiction: str = "MN") -> list:
    """Pull verified facts from the Context Engine. Best-effort, never raises."""
    try:
        from app.modules.context_engine import cache as ctx_cache
        facts = await ctx_cache.get_facts(subject, jurisdiction, limit=10)
        return [
            {
                "id": f.id,
                "claim": f.claim,
                "source_url": f.source_url,
                "source_name": f.source_name,
                "citation": f.citation,
                "is_verified": f.is_verified,
            }
            for f in facts
        ]
    except Exception as e:
        logger.debug("Context Engine facts unavailable for %s/%s: %s", subject, jurisdiction, e)
        return []


@router.post("/cases")
async def create_case(case: CaseCreate, user: StorageUser = Depends(yellow_access)):
    """Create a new case for the authenticated user."""
    user_id = user.user_id
    
    # Prepare case data for freshness validation
    case_data = {
        "case_type": case.case_type,
        "court": case.court,
        "property_address": case.property_address,
        "rent_amount": case.rent_amount,
        "security_deposit": case.security_deposit,
        "plaintiff_name": case.plaintiff_name,
        "defendant_name": case.defendant_name,
        "hearing_date": case.hearing_date,
        "lease_start": case.lease_start,
        "lease_end": case.lease_end
    }
    
    # Validate legal data freshness
    freshness_validation = validate_case_freshness(case_data)
    
    # Log freshness warnings for legal compliance
    if freshness_validation.get("warnings"):
        logger.warning(f"⚠️ Legal freshness warnings for case {case.case_number}: {freshness_validation['warnings']}")
    
    # Build complete case data
    complete_case_data = {
        "user_id": user_id,  # Store user ownership
        "case_number": case.case_number,
        "case_type": case.case_type,
        "court": case.court,
        "property_address": case.property_address,
        "rent_amount": case.rent_amount,
        "security_deposit": case.security_deposit,
        "plaintiff": {
            "name": case.plaintiff_name,
            "role": "plaintiff"
        },
        "defendant": {
            "name": case.defendant_name,
            "role": "defendant",
            "is_pro_se": True
        },
        "hearing_date": case.hearing_date,
        "lease_start": case.lease_start,
        "lease_end": case.lease_end,
        "timeline": [],
        "evidence": [],
        "counterclaims": [],
        "motions": [],
        "deadlines": [],
        "defenses": [],
        "notes": [case.notes] if case.notes else [],
        "created_at": utc_now().isoformat(),
        "updated_at": utc_now().isoformat(),
        # Add freshness validation results
        "freshness_validation": freshness_validation,
        "legal_accuracy_score": freshness_validation.get("freshness_score", 100.0)
    }
    
    async with get_db_session() as session:
        incident = Incident(
            user_id=user_id,
            title=case.case_number or "New Case",
            status="draft",
            incident_type=case.case_type,
            incident_metadata=complete_case_data,
        )
        session.add(incident)
        await session.commit()
        await session.refresh(incident)
    complete_case_data["case_id"] = str(incident.incident_id)

    return {
        "success": True,
        "case_id": str(incident.incident_id),
        "case_number": case.case_number,
        "case": complete_case_data,
        "freshness_validation": freshness_validation
    }


@router.post("/validate-freshness")
async def validate_case_legal_accuracy(
    case_data: Dict[str, Any] = Body(...),
    user: StorageUser = Depends(yellow_access)
):
    """
    Validate legal accuracy and freshness of case data.
    
    This endpoint can be called before case creation to ensure
    all legal content is current and accurate.
    """
    if not FRESHNESS_AVAILABLE:
        return {
            "status": "unavailable",
            "message": "Freshness validation not available",
            "recommendations": ["Contact system administrator"]
        }
    
    validation_results = validate_case_freshness(case_data)
    
    # Add user-friendly messaging
    if validation_results["freshness_score"] >= 95:
        status_message = "✅ All legal content is current and accurate"
    elif validation_results["freshness_score"] >= 85:
        status_message = "⚠️ Some legal content may need review"
    else:
        status_message = "🚨 Legal content requires immediate review"
    
    return {
        "status": validation_results["status"],
        "message": status_message,
        "freshness_score": validation_results["freshness_score"],
        "warnings": validation_results["warnings"],
        "recommendations": validation_results["recommendations"],
        "stale_items": validation_results["stale_items"],
        "user_id": user.user_id,
        "validated_at": utc_now().isoformat()
    }


@router.post("/validate-minnesota")
async def validate_minnesota_requirements(
    case_data: Dict[str, Any] = Body(...),
    user: StorageUser = Depends(yellow_access)
):
    """
    Validate Minnesota-specific legal requirements for a case.
    
    This endpoint checks:
    - Notice period compliance (7-day for non-payment, 14-day for violations)
    - Proper service methods (personal, substitute, posting + mailing)
    - Right to counsel eligibility (certain counties)
    - COVID-19 emergency protections (if applicable)
    """
    mn_validation = validate_minnesota_legal_requirements(case_data)
    
    return {
        "state": mn_validation["state"],
        "requirements_validated": mn_validation["requirements_validated"],
        "warnings": mn_validation["warnings"],
        "recommendations": mn_validation["recommendations"],
        "user_id": user.user_id,
        "validated_at": utc_now().isoformat()
    }


@router.post("/validate-court-forms")
async def validate_court_forms(
    case_data: Dict[str, Any] = Body(...),
    user: StorageUser = Depends(yellow_access)
):
    """
    Validate court form requirements for a case.
    
    This endpoint checks:
    - Required forms are current and available
    - Form versions match court requirements
    - E-filing requirements are up to date
    - Case-type specific form requirements
    """
    form_validation = validate_court_forms_freshness(case_data)
    
    return {
        "status": form_validation["status"],
        "forms": form_validation["forms"],
        "warnings": form_validation["warnings"],
        "recommendations": form_validation["recommendations"],
        "user_id": user.user_id,
        "validated_at": utc_now().isoformat()
    }


@router.post("/freshness-recommendations")
async def get_case_freshness_recommendations(
    case_data: Dict[str, Any] = Body(...),
    user: StorageUser = Depends(yellow_access)
):
    """
    Get action recommendations based on case freshness status.
    
    This endpoint analyzes the freshness of legal data for a case
    and returns prioritized action recommendations.
    """
    # Get freshness validation results
    freshness_results = validate_case_freshness(case_data)
    
    # Generate recommendations
    recommendations = get_freshness_action_recommendations(freshness_results)
    
    return {
        "recommendations": recommendations,
        "freshness_score": freshness_results["freshness_score"],
        "status": freshness_results["status"],
        "user_id": user.user_id,
        "generated_at": utc_now().isoformat()
    }


# =============================================================================
# SIMPLE INTAKE - CREATE CASE FROM COMPLAINT DOCUMENT
# =============================================================================

class ComplaintIntake(BaseModel):
    """Simple complaint intake - minimal fields to start a case."""
    case_number: str
    court: str = "Dakota County District Court"
    property_address: str
    plaintiff_name: str  # Landlord/property manager
    defendant_name: str  # You (tenant)
    complaint_type: str = "eviction"  # eviction, unlawful_detainer, rent_nonpayment
    filing_date: Optional[str] = None
    hearing_date: Optional[str] = None
    answer_deadline: Optional[str] = None
    rent_amount: Optional[float] = 0
    amount_claimed: Optional[float] = 0
    document_id: Optional[str] = None  # Link to uploaded document
    notes: Optional[str] = None


@router.post("/intake/complaint")
async def intake_complaint(intake: ComplaintIntake, user: StorageUser = Depends(yellow_access)):
    """
    SIMPLE INTAKE: Create a case from a complaint document.
    
    This is the starting point - upload info from a summons/complaint
    and it creates a full case with auto-calculated deadlines.
    """
    user_id = user.user_id
    
    # Validate deadline rules freshness before calculating deadlines
    deadline_freshness_warning = None
    if FRESHNESS_AVAILABLE:
        deadline_freshness = data_freshness_manager.check_freshness("deadline_rules")
        if deadline_freshness != FreshnessStatus.FRESH:
            deadline_freshness_warning = "Deadline calculation rules may be outdated - verify with current court rules"
            logger.warning(f"Stale deadline rules used for case {intake.case_number}")
    
    # Calculate deadlines
    from datetime import datetime, timedelta
    today = utc_now()
    
    # Parse filing date
    filing_date = None
    if intake.filing_date:
        try:
            filing_date = datetime.fromisoformat(intake.filing_date.replace('Z', '+00:00'))
        except ValueError:
            filing_date = today
    else:
        filing_date = today
    
    # Answer deadline is typically 7 days from service for eviction
    answer_deadline = None
    if intake.answer_deadline:
        answer_deadline = intake.answer_deadline
    else:
        # Default: 7 days from filing for eviction actions
        # NOTE: This should be verified against current rules (see freshness check above)
        answer_date = filing_date + timedelta(days=7)
        answer_deadline = answer_date.strftime("%Y-%m-%d")
    
    # Create the case
    case_data = {
        "user_id": user_id,
        "case_number": intake.case_number,
        "case_type": f"eviction_defense_{intake.complaint_type}",
        "status": "active",
        "court": intake.court,
        "property_address": intake.property_address,
        "rent_amount": intake.rent_amount or 0,
        "amount_claimed": intake.amount_claimed or 0,
        "security_deposit": 0,
        
        "plaintiff": {
            "name": intake.plaintiff_name,
            "role": "plaintiff",
            "type": "landlord"
        },
        "defendant": {
            "name": intake.defendant_name,
            "role": "defendant", 
            "is_pro_se": True,
            "type": "tenant"
        },
        
        "dates": {
            "filing_date": filing_date.strftime("%Y-%m-%d"),
            "answer_deadline": answer_deadline,
            "hearing_date": intake.hearing_date
        },
        "hearing_date": intake.hearing_date,
        
        # Initialize case components
        "timeline": [{
            "id": f"evt_{utc_now().strftime('%Y%m%d%H%M%S')}",
            "date": filing_date.strftime("%Y-%m-%d"),
            "title": "Complaint Filed",
            "description": f"Eviction complaint filed: {intake.complaint_type}",
            "category": "court",
            "importance": "critical",
            "source": "intake"
        }],
        "evidence": [],
        "counterclaims": [],
        "motions": [],
        "defenses": [],
        "documents": [intake.document_id] if intake.document_id else [],
        
        # Auto-calculated deadlines
        "deadlines": [
            {
                "id": "dl_answer",
                "title": "Answer Due",
                "deadline": answer_deadline,
                "description": "File answer to complaint",
                "priority": "critical",
                "status": "pending"
            }
        ],
        
        "notes": [intake.notes] if intake.notes else [],
        "created_at": utc_now().isoformat(),
        "updated_at": utc_now().isoformat(),
        "source": "complaint_intake",
        "freshness_warning": deadline_freshness_warning
    }
    
    # Add hearing deadline if provided
    if intake.hearing_date:
        case_data["deadlines"].append({
            "id": "dl_hearing",
            "title": "Court Hearing",
            "deadline": intake.hearing_date,
            "description": "Appear at court hearing",
            "priority": "critical",
            "status": "pending"
        })
    
    async with get_db_session() as session:
        incident = Incident(
            user_id=user_id,
            title=intake.case_number or "Complaint Intake",
            status="active",
            incident_type=f"eviction_defense_{intake.complaint_type}",
            incident_metadata=case_data,
        )
        session.add(incident)
        await session.commit()
        await session.refresh(incident)
    case_data["case_id"] = str(incident.incident_id)
    
    # Validate Minnesota-specific requirements
    mn_validation = validate_minnesota_legal_requirements(case_data)
    
    logger.info(f"Case created from complaint intake: {intake.case_number} for user {user_id}")
    
    return {
        "success": True,
        "case_number": intake.case_number,
        "message": f"Case created from complaint. Answer due: {answer_deadline}",
        "case": case_data,
        "freshness_warning": deadline_freshness_warning,
        "minnesota_validation": mn_validation,
        "next_steps": [
            f"1. File your ANSWER by {answer_deadline}",
            "2. Gather evidence (photos, texts, emails, receipts)",
            "3. Review potential defenses",
            "4. Consider counterclaims"
        ]
    }


@router.put("/cases/{case_id}")
async def update_case(case_id: str, updates: Dict[str, Any] = Body(...), user: StorageUser = Depends(yellow_access)):
    """Update a case belonging to the authenticated user."""
    user_id = user.user_id
    if not await verify_case_ownership(case_id, user_id):
        raise HTTPException(status_code=404, detail="Case not found")
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    updates.pop("user_id", None)
    case.update(updates)
    await save_case(case_id, case, user_id)
    return {"success": True, "case": case}


@router.delete("/cases/{case_id}")
async def delete_case(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Delete a case belonging to the authenticated user."""
    user_id = user.user_id
    if not await verify_case_ownership(case_id, user_id):
        raise HTTPException(status_code=404, detail="Case not found")
    async with get_db_session() as session:
        await session.execute(
            delete(Incident).where(
                Incident.incident_id == int(case_id),
                Incident.user_id == user_id,
            )
        )
        await session.commit()
    return {"success": True, "message": f"Case {case_id} deleted"}


# -----------------------------------------------------------------------------
# Timeline Events
# -----------------------------------------------------------------------------

@router.get("/cases/{case_id}/timeline")
async def get_timeline(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Get all timeline events for a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    timeline = case.get("timeline", [])
    # Sort by date
    timeline.sort(key=lambda x: x.get("date", ""))
    
    return {"timeline": timeline, "count": len(timeline)}


@router.post("/cases/{case_id}/timeline")
async def add_timeline_event(case_id: str, event: TimelineEventCreate, user: StorageUser = Depends(yellow_access)):
    """Add a timeline event to a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    event_id = f"evt_{utc_now().strftime('%Y%m%d%H%M%S')}"
    event_data = {
        "id": event_id,
        "date": event.date,
        "title": event.title,
        "description": event.description,
        "category": event.category,
        "importance": event.importance,
        "evidence_ids": event.evidence_ids,
        "source": event.source,
        "created_at": utc_now().isoformat()
    }
    
    if "timeline" not in case:
        case["timeline"] = []
    case["timeline"].append(event_data)
    await save_case(case_id, case, user_id)
    
    return {"success": True, "event_id": event_id, "event": event_data}


@router.delete("/cases/{case_id}/timeline/{event_id}")
async def delete_timeline_event(case_id: str, event_id: str, user: StorageUser = Depends(yellow_access)):
    """Delete a timeline event from a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    case["timeline"] = [e for e in case.get("timeline", []) if e.get("id") != event_id]
    await save_case(case_id, case, user_id)
    
    return {"success": True}


# -----------------------------------------------------------------------------
# Evidence
# -----------------------------------------------------------------------------

@router.get("/cases/{case_id}/evidence")
async def get_evidence(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Get all evidence for a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {"evidence": case.get("evidence", []), "count": len(case.get("evidence", []))}


@router.post("/cases/{case_id}/evidence")
async def add_evidence(case_id: str, evidence: EvidenceCreate, user: StorageUser = Depends(yellow_access)):
    """Add evidence to a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    evidence_id = f"evi_{utc_now().strftime('%Y%m%d%H%M%S')}"
    evidence_data = {
        "id": evidence_id,
        "title": evidence.title,
        "evidence_type": evidence.evidence_type,
        "date_obtained": evidence.date_obtained or utc_now().strftime("%Y-%m-%d"),
        "date_of_event": evidence.date_of_event,
        "description": evidence.description,
        "source": evidence.source,
        "relevance": evidence.relevance,
        "file_path": evidence.file_path,
        "notes": evidence.notes,
        "created_at": utc_now().isoformat()
    }
    
    if "evidence" not in case:
        case["evidence"] = []
    case["evidence"].append(evidence_data)
    await save_case(case_id, case, user_id)
    
    return {"success": True, "evidence_id": evidence_id, "evidence": evidence_data}


# -----------------------------------------------------------------------------
# Counterclaims
# -----------------------------------------------------------------------------

@router.get("/cases/{case_id}/counterclaims")
async def get_counterclaims(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Get all counterclaims for a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {"counterclaims": case.get("counterclaims", []), "count": len(case.get("counterclaims", []))}


@router.post("/cases/{case_id}/counterclaims")
async def add_counterclaim(case_id: str, claim: CounterclaimCreate, user: StorageUser = Depends(yellow_access)):
    """Add a counterclaim to a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get template info
    template = MN_COUNTERCLAIMS.get(claim.claim_type, {})
    
    claim_id = f"clm_{utc_now().strftime('%Y%m%d%H%M%S')}"
    claim_data = {
        "id": claim_id,
        "claim_type": claim.claim_type,
        "title": claim.title,
        "legal_basis": template.get("legal_basis", ""),
        "description": template.get("description", ""),
        "elements": template.get("elements", []),
        "potential_damages": template.get("damages", []),
        "facts": claim.facts,
        "damages_sought": claim.damages_sought,
        "evidence_ids": claim.evidence_ids,
        "notes": claim.notes,
        "created_at": utc_now().isoformat()
    }
    
    if "counterclaims" not in case:
        case["counterclaims"] = []
    case["counterclaims"].append(claim_data)
    await save_case(case_id, case, user_id)
    
    return {"success": True, "claim_id": claim_id, "counterclaim": claim_data}


# -----------------------------------------------------------------------------
# Motions
# -----------------------------------------------------------------------------

@router.get("/cases/{case_id}/motions")
async def get_motions(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Get all motions for a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {"motions": case.get("motions", []), "count": len(case.get("motions", []))}


@router.post("/cases/{case_id}/motions")
async def add_motion(case_id: str, motion: MotionCreate, user: StorageUser = Depends(yellow_access)):
    """Add a motion to a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get template info
    template = MOTION_TEMPLATES.get(motion.motion_type, {})
    
    motion_id = f"mot_{utc_now().strftime('%Y%m%d%H%M%S')}"
    motion_data = {
        "id": motion_id,
        "motion_type": motion.motion_type,
        "title": motion.title,
        "deadline": motion.deadline,
        "basis": motion.basis,
        "relief_sought": motion.relief_sought,
        "supporting_evidence": motion.supporting_evidence,
        "legal_basis": template.get("legal_basis", []),
        "when_to_use": template.get("when_to_use", []),
        "template": template.get("template", ""),
        "status": "pending",
        "filed": False,
        "notes": motion.notes,
        "created_at": utc_now().isoformat()
    }
    
    if "motions" not in case:
        case["motions"] = []
    case["motions"].append(motion_data)
    await save_case(case_id, case, user_id)
    
    return {"success": True, "motion_id": motion_id, "motion": motion_data}


# -----------------------------------------------------------------------------
# Deadlines
# -----------------------------------------------------------------------------

@router.get("/cases/{case_id}/deadlines")
async def get_deadlines(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Get all deadlines for a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    deadlines = case.get("deadlines", [])
    
    # Calculate days until each deadline
    today = date.today()
    for d in deadlines:
        if d.get("deadline"):
            try:
                deadline_date = datetime.strptime(d["deadline"], "%Y-%m-%d").date()
                d["days_until"] = (deadline_date - today).days
                if d["days_until"] < 0:
                    d["status"] = "overdue"
                elif d["days_until"] == 0:
                    d["status"] = "today"
                elif d["days_until"] <= 3:
                    d["status"] = "urgent"
                elif d["days_until"] <= 7:
                    d["status"] = "soon"
                else:
                    d["status"] = "upcoming"
            except Exception:
                d["days_until"] = None
                d["status"] = "unknown"
    
    return {"deadlines": deadlines, "count": len(deadlines)}


@router.post("/cases/{case_id}/deadlines")
async def add_deadline(case_id: str, deadline: DeadlineCreate, user: StorageUser = Depends(yellow_access)):
    """Add a deadline to a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    deadline_id = f"ddl_{utc_now().strftime('%Y%m%d%H%M%S')}"
    deadline_data = {
        "id": deadline_id,
        "title": deadline.title,
        "deadline": deadline.deadline,
        "description": deadline.description,
        "priority": deadline.priority,
        "reminder_days": deadline.reminder_days,
        "notes": deadline.notes,
        "completed": False,
        "created_at": utc_now().isoformat()
    }
    
    if "deadlines" not in case:
        case["deadlines"] = []
    case["deadlines"].append(deadline_data)
    await save_case(case_id, case, user_id)
    
    return {"success": True, "deadline_id": deadline_id, "deadline": deadline_data}


@router.put("/cases/{case_id}/deadlines/{deadline_id}/complete")
async def complete_deadline(case_id: str, deadline_id: str, user: StorageUser = Depends(yellow_access)):
    """Mark a deadline as complete for a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    for d in case.get("deadlines", []):
        if d.get("id") == deadline_id:
            d["completed"] = True
            d["completed_at"] = utc_now().isoformat()
    
    await save_case(case_id, case, user_id)
    return {"success": True}


# -----------------------------------------------------------------------------
# Defenses
# -----------------------------------------------------------------------------

@router.get("/cases/{case_id}/defenses")
async def get_defenses(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Get all defenses for a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {"defenses": case.get("defenses", []), "count": len(case.get("defenses", []))}


@router.post("/cases/{case_id}/defenses")
async def add_defense(case_id: str, defense: DefenseCreate, user: StorageUser = Depends(yellow_access)):
    """Add a defense strategy to a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get template info
    template = MN_DEFENSES.get(defense.defense_type, {})
    
    defense_id = f"def_{utc_now().strftime('%Y%m%d%H%M%S')}"
    defense_data = {
        "id": defense_id,
        "defense_type": defense.defense_type,
        "title": defense.title,
        "legal_basis": defense.legal_basis or template.get("legal_basis", ""),
        "description": template.get("description", ""),
        "elements": template.get("elements", []),
        "facts_supporting": defense.facts_supporting,
        "evidence_ids": defense.evidence_ids,
        "strength": defense.strength,
        "created_at": utc_now().isoformat()
    }
    
    if "defenses" not in case:
        case["defenses"] = []
    case["defenses"].append(defense_data)
    await save_case(case_id, case, user_id)
    
    return {"success": True, "defense_id": defense_id, "defense": defense_data}


# -----------------------------------------------------------------------------
# Templates & Reference
# -----------------------------------------------------------------------------

@router.get("/templates/defenses")
async def get_defense_templates():
    """Get all available defense templates."""
    return {"defenses": MN_DEFENSES}


@router.get("/templates/counterclaims")
async def get_counterclaim_templates():
    """Get all available counterclaim templates."""
    return {"counterclaims": MN_COUNTERCLAIMS}


@router.get("/templates/motions")
async def get_motion_templates():
    """Get all available motion templates."""
    return {"motions": MOTION_TEMPLATES}


# -----------------------------------------------------------------------------
# Document Generation
# -----------------------------------------------------------------------------

@router.post("/cases/{case_id}/generate/counterclaim")
async def generate_counterclaim_doc(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Generate the counterclaim document for a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Build the document
    doc_lines = []
    doc_lines.append("STATE OF MINNESOTA                          DISTRICT COURT")
    doc_lines.append(f"COUNTY OF DAKOTA                           FIRST JUDICIAL DISTRICT")
    doc_lines.append("")
    doc_lines.append(f"{case.get('plaintiff', {}).get('name', 'PLAINTIFF')},")
    doc_lines.append(f"    Plaintiff,                              Case No. {case.get('case_number', '')}")
    doc_lines.append("")
    doc_lines.append("vs.                                         AMENDED ANSWER AND COUNTERCLAIM")
    doc_lines.append("")
    doc_lines.append(f"{case.get('defendant', {}).get('name', 'DEFENDANT')},")
    doc_lines.append("    Defendant.")
    doc_lines.append("")
    doc_lines.append("=" * 70)
    doc_lines.append("")
    
    # Defenses section
    defenses = case.get("defenses", [])
    if defenses:
        doc_lines.append("AFFIRMATIVE DEFENSES")
        doc_lines.append("-" * 30)
        for i, defense in enumerate(defenses, 1):
            doc_lines.append(f"\n{i}. {defense.get('title', 'Defense')}")
            doc_lines.append(f"   Legal Basis: {defense.get('legal_basis', '')}")
            for fact in defense.get("facts_supporting", []):
                doc_lines.append(f"   - {fact}")
    
    # Counterclaims section
    counterclaims = case.get("counterclaims", [])
    if counterclaims:
        doc_lines.append("")
        doc_lines.append("=" * 70)
        doc_lines.append("COUNTERCLAIMS")
        doc_lines.append("=" * 70)
        
        for i, claim in enumerate(counterclaims, 1):
            doc_lines.append(f"\nCOUNT {i}: {claim.get('title', 'Counterclaim')}")
            doc_lines.append("-" * 30)
            doc_lines.append(f"Legal Basis: {claim.get('legal_basis', '')}")
            doc_lines.append("")
            doc_lines.append("Facts:")
            for fact in claim.get("facts", []):
                doc_lines.append(f"  - {fact}")
            
            damages = claim.get("damages_sought", {})
            if damages:
                doc_lines.append("")
                doc_lines.append("Damages Sought:")
                for damage_type, amount in damages.items():
                    doc_lines.append(f"  - {damage_type}: ${amount:,.2f}")
    
    # Prayer for relief
    doc_lines.append("")
    doc_lines.append("=" * 70)
    doc_lines.append("PRAYER FOR RELIEF")
    doc_lines.append("=" * 70)
    doc_lines.append("")
    doc_lines.append("WHEREFORE, Defendant respectfully requests that this Court:")
    doc_lines.append("1. Deny Plaintiff's complaint for eviction;")
    doc_lines.append("2. Enter judgment in Defendant's favor on all counterclaims;")
    doc_lines.append("3. Award Defendant actual damages as proven at trial;")
    doc_lines.append("4. Award Defendant statutory penalties as applicable;")
    doc_lines.append("5. Award costs and disbursements;")
    doc_lines.append("6. Grant such other relief as the Court deems just and equitable.")
    doc_lines.append("")
    doc_lines.append("")
    doc_lines.append(f"Dated: {utc_now().strftime('%B %d, %Y')}")
    doc_lines.append("")
    doc_lines.append("")
    doc_lines.append("_______________________________")
    doc_lines.append(case.get("defendant", {}).get("name", "Defendant"))
    doc_lines.append("Defendant, Pro Se")
    
    document_text = "\n".join(doc_lines)
    
    # Save to file
    output_dir = os.path.join(os.getcwd(), "data", "case_outputs")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"COUNTERCLAIM_{case.get('case_number', 'case').replace('-', '_')}.txt")
    
    with open(output_file, 'w') as f:
        f.write(document_text)
    
    return {
        "success": True,
        "document": document_text,
        "file_path": output_file
    }


@router.post("/cases/{case_id}/generate/motion/{motion_type}")
async def generate_motion_doc(case_id: str, motion_type: str, params: Dict[str, Any] = Body(default={}), user: StorageUser = Depends(yellow_access)):
    """Generate a motion document for a case belonging to the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    template = MOTION_TEMPLATES.get(motion_type)
    if not template:
        raise HTTPException(status_code=404, detail="Motion template not found")
    
    # Fill in template
    doc_text = template.get("template", "")
    
    replacements = {
        "{county}": "DAKOTA",
        "{judicial_district}": "FIRST",
        "{plaintiff_name}": case.get("plaintiff", {}).get("name", "PLAINTIFF"),
        "{defendant_name}": case.get("defendant", {}).get("name", "DEFENDANT"),
        "{case_number}": case.get("case_number", ""),
        "{defendant_address}": case.get("property_address", ""),
        "{defendant_phone}": "",
        "{today_date}": utc_now().strftime("%B %d, %Y"),
        "{hearing_date}": case.get("hearing_date", ""),
        "{current_hearing_date}": case.get("hearing_date", ""),
    }
    
    # Add any custom params
    for key, value in params.items():
        replacements[f"{{{key}}}"] = str(value)
    
    for placeholder, value in replacements.items():
        doc_text = doc_text.replace(placeholder, value)
    
    # Save to file
    output_dir = os.path.join(os.getcwd(), "data", "case_outputs")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{motion_type.upper()}_{case.get('case_number', 'case').replace('-', '_')}.txt")
    
    with open(output_file, 'w') as f:
        f.write(doc_text)
    
    return {
        "success": True,
        "document": doc_text,
        "file_path": output_file,
        "motion_type": motion_type,
        "title": template.get("title")
    }


# -----------------------------------------------------------------------------
# Case Summary
# -----------------------------------------------------------------------------

@router.get("/cases/{case_id}/summary")
async def get_case_summary(case_id: str, user: StorageUser = Depends(yellow_access)):
    """Get a complete case summary with reminders for the authenticated user."""
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    today = date.today()
    
    # Calculate hearing days
    hearing_days = None
    if case.get("hearing_date"):
        try:
            hearing_date = datetime.strptime(case["hearing_date"], "%Y-%m-%d").date()
            hearing_days = (hearing_date - today).days
        except ValueError:
            pass
    
    # Get urgent deadlines
    urgent_deadlines = []
    for d in case.get("deadlines", []):
        if d.get("deadline") and not d.get("completed"):
            try:
                deadline_date = datetime.strptime(d["deadline"], "%Y-%m-%d").date()
                days = (deadline_date - today).days
                if days <= 7:
                    urgent_deadlines.append({
                        **d,
                        "days_until": days
                    })
            except ValueError:
                pass
    
    # Build reminders
    reminders = []
    
    if hearing_days is not None:
        if hearing_days <= 0:
            reminders.append({
                "type": "critical",
                "title": "HEARING TODAY!" if hearing_days == 0 else "HEARING PASSED",
                "message": f"Your hearing {'is today' if hearing_days == 0 else 'was ' + str(abs(hearing_days)) + ' days ago'}!"
            })
        elif hearing_days <= 3:
            reminders.append({
                "type": "critical",
                "title": f"Hearing in {hearing_days} days!",
                "message": f"Your court hearing is on {case.get('hearing_date')}. Make sure all documents are prepared."
            })
        elif hearing_days <= 7:
            reminders.append({
                "type": "high",
                "title": f"Hearing in {hearing_days} days",
                "message": "Review your evidence and practice your arguments."
            })
    
    for d in urgent_deadlines:
        reminders.append({
            "type": "high" if d["days_until"] > 3 else "critical",
            "title": f"Deadline: {d.get('title', 'Unknown')}",
            "message": f"Due in {d['days_until']} days on {d.get('deadline')}"
        })
    
    # Next steps
    next_steps = []
    
    if not case.get("defenses"):
        next_steps.append("Add your defense strategies")
    if not case.get("counterclaims"):
        next_steps.append("Consider adding counterclaims against landlord")
    if not case.get("evidence"):
        next_steps.append("Upload and organize your evidence")
    if not case.get("timeline"):
        next_steps.append("Build your case timeline with key events")
    
    if hearing_days and hearing_days <= 14:
        next_steps.append("Prepare copies of all documents for court (3 copies: you, judge, landlord)")
        next_steps.append("Organize evidence in chronological order")
        next_steps.append("Practice your opening statement")
    
    return {
        "case_number": case.get("case_number"),
        "hearing_date": case.get("hearing_date"),
        "days_until_hearing": hearing_days,
        "stats": {
            "timeline_events": len(case.get("timeline", [])),
            "evidence_items": len(case.get("evidence", [])),
            "counterclaims": len(case.get("counterclaims", [])),
            "motions": len(case.get("motions", [])),
            "defenses": len(case.get("defenses", [])),
            "pending_deadlines": len([d for d in case.get("deadlines", []) if not d.get("completed")])
        },
        "reminders": reminders,
        "urgent_deadlines": urgent_deadlines,
        "next_steps": next_steps
    }


# =============================================================================
# DOCUMENT HUB INTEGRATION - Auto-populate from uploaded documents
# =============================================================================

@router.get("/from-documents")
async def get_case_from_documents(user: StorageUser = Depends(yellow_access)):
    """
    Get case data extracted from uploaded documents.
    
    Returns all case-relevant information extracted from documents:
    - Case numbers
    - Parties (tenant, landlord)
    - Key dates (hearing, deadlines)
    - Amounts (rent, claims)
    - Timeline events
    - Action items
    - Law references
    
    Use this to auto-populate a new case or verify existing case data.
    """
    hub = get_document_hub()
    case_data = hub.get_case_data(user.user_id)
    
    return {
        "source": "document_extraction",
        "document_count": case_data.document_count,
        "case_data": case_data.to_dict(),
        "has_data": case_data.document_count > 0,
        "confidence_score": case_data.confidence_score,
    }


@router.post("/auto-create")
async def auto_create_case_from_documents(
    court: str = Query(default="Dakota County District Court", description="Court name"),
    user: StorageUser = Depends(yellow_access),
):
    """
    Auto-create a case using data extracted from uploaded documents.
    
    This endpoint creates a new case pre-populated with all information
    extracted from your uploaded documents:
    - Case number (from complaint/summons)
    - Parties (plaintiff/defendant names)
    - Key dates (hearing date, answer deadline)
    - Rent amount and claims
    - Property address
    - Timeline from document dates
    
    The case is created with "auto-populated" flag set.
    """
    hub = get_document_hub()
    case_data = hub.get_case_data(user.user_id)
    
    if case_data.document_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents found. Upload documents first before auto-creating a case."
        )
    
    if not case_data.primary_case_number:
        raise HTTPException(
            status_code=400,
            detail="Could not extract case number from documents. Please create case manually."
        )
    
    user_id = user.user_id
    
    # Build case from extracted data
    new_case = {
        "user_id": user_id,
        "case_number": case_data.primary_case_number,
        "case_type": "eviction_defense",
        "court": court,
        "property_address": case_data.property_address or "",
        "rent_amount": case_data.rent_amount or 0,
        "security_deposit": case_data.deposit_amount or 0,
        "plaintiff": {
            "name": case_data.landlord_name or "Unknown Landlord",
            "address": case_data.landlord_address,
            "role": "plaintiff"
        },
        "defendant": {
            "name": case_data.tenant_name or user_id,
            "address": case_data.tenant_address,
            "role": "defendant",
            "is_pro_se": True
        },
        "hearing_date": case_data.hearing_date,
        "answer_deadline": case_data.answer_deadline,
        "lease_start": case_data.lease_start,
        "lease_end": case_data.lease_end,
        "amounts_claimed": {
            "rent": case_data.rent_claimed,
            "damages": case_data.damages_claimed,
            "late_fees": case_data.late_fees,
            "total": case_data.total_claimed,
        },
        "timeline": [],
        "evidence": [],
        "counterclaims": [],
        "motions": [],
        "deadlines": [],
        "defenses": [],
        "notes": ["Case auto-created from uploaded documents"],
        "created_at": utc_now().isoformat(),
        "updated_at": utc_now().isoformat(),
        "auto_populated": True,
        "source_documents": case_data.document_count,
        "matched_statutes": case_data.matched_statutes,
    }
    
    # Add deadline from document extraction
    if case_data.answer_deadline:
        new_case["deadlines"].append({
            "id": "auto_deadline_1",
            "title": "Answer Deadline",
            "deadline": case_data.answer_deadline,
            "description": "Deadline to file Answer to Eviction Complaint",
            "priority": "critical",
            "reminder_days": [7, 3, 1],
            "completed": False,
            "source": "document_extraction"
        })
    
    # Add hearing as deadline
    if case_data.hearing_date:
        new_case["deadlines"].append({
            "id": "auto_deadline_2",
            "title": "Court Hearing",
            "deadline": case_data.hearing_date,
            "description": "Eviction Hearing",
            "priority": "critical",
            "reminder_days": [14, 7, 3, 1],
            "completed": False,
            "source": "document_extraction"
        })
    
    # Add timeline events from document extraction
    for i, event in enumerate(case_data.timeline_events[:20]):  # Limit to 20
        new_case["timeline"].append({
            "id": f"auto_timeline_{i}",
            "date": event.get("date", ""),
            "title": event.get("title", "Event"),
            "description": event.get("description", ""),
            "category": event.get("category", "court"),
            "importance": "high" if event.get("is_critical") else "medium",
            "evidence_ids": [],
            "source": "document_extraction"
        })
    
    # Add action items as notes
    for action in case_data.action_items:
        new_case["notes"].append(f"ACTION: {action.get('title', 'Unknown')} - {action.get('description', '')}")
    
    save_case(case_data.primary_case_number, new_case, user_id)
    
    return {
        "success": True,
        "case_number": case_data.primary_case_number,
        "case": new_case,
        "extracted_from": f"{case_data.document_count} documents",
        "fields_populated": [
            k for k, v in new_case.items() 
            if v and k not in ["user_id", "created_at", "updated_at", "auto_populated"]
        ]
    }


@router.post("/cases/{case_id}/populate-from-documents")
async def populate_case_from_documents(
    case_id: str,
    overwrite: bool = Query(default=False, description="Overwrite existing values"),
    user: StorageUser = Depends(yellow_access),
):
    """
    Populate an existing case with data extracted from documents.
    
    This updates an existing case with information from uploaded documents.
    By default, only empty fields are populated. Set overwrite=true to
    replace existing values with document-extracted values.
    
    Fields that can be populated:
    - case_number, property_address
    - plaintiff/defendant names
    - hearing_date, answer_deadline
    - rent_amount, amounts_claimed
    - timeline events
    - deadlines
    """
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    hub = get_document_hub()
    doc_data = hub.get_case_data(user_id)
    
    if doc_data.document_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents found to extract data from."
        )
    
    fields_updated = []
    
    # Update fields
    def update_field(case_key: str, doc_value, nested_key: str = None):
        if doc_value is None:
            return
        
        if nested_key:
            if case_key not in case:
                case[case_key] = {}
            current = case[case_key].get(nested_key)
            if overwrite or not current:
                case[case_key][nested_key] = doc_value
                fields_updated.append(f"{case_key}.{nested_key}")
        else:
            current = case.get(case_key)
            if overwrite or not current:
                case[case_key] = doc_value
                fields_updated.append(case_key)
    
    # Core fields
    update_field("case_number", doc_data.primary_case_number)
    update_field("property_address", doc_data.property_address)
    update_field("hearing_date", doc_data.hearing_date)
    update_field("answer_deadline", doc_data.answer_deadline)
    update_field("lease_start", doc_data.lease_start)
    update_field("lease_end", doc_data.lease_end)
    update_field("rent_amount", doc_data.rent_amount)
    update_field("security_deposit", doc_data.deposit_amount)
    
    # Plaintiff (landlord)
    update_field("plaintiff", doc_data.landlord_name, "name")
    update_field("plaintiff", doc_data.landlord_address, "address")
    
    # Defendant (tenant)
    update_field("defendant", doc_data.tenant_name, "name")
    update_field("defendant", doc_data.tenant_address, "address")
    
    # Add amounts claimed
    if doc_data.rent_claimed or doc_data.total_claimed:
        if "amounts_claimed" not in case or overwrite:
            case["amounts_claimed"] = {
                "rent": doc_data.rent_claimed,
                "damages": doc_data.damages_claimed,
                "late_fees": doc_data.late_fees,
                "total": doc_data.total_claimed,
            }
            fields_updated.append("amounts_claimed")
    
    # Add matched statutes
    if doc_data.matched_statutes:
        case["matched_statutes"] = doc_data.matched_statutes
        fields_updated.append("matched_statutes")
    
    # Add timeline events if empty or overwrite
    if overwrite or not case.get("timeline"):
        existing_ids = {e.get("id") for e in case.get("timeline", [])}
        for i, event in enumerate(doc_data.timeline_events[:20]):
            event_id = f"doc_timeline_{i}"
            if event_id not in existing_ids:
                case.setdefault("timeline", []).append({
                    "id": event_id,
                    "date": event.get("date", ""),
                    "title": event.get("title", "Event"),
                    "description": event.get("description", ""),
                    "category": event.get("category", "court"),
                    "importance": "high" if event.get("is_critical") else "medium",
                    "evidence_ids": [],
                    "source": "document_extraction"
                })
        if doc_data.timeline_events:
            fields_updated.append("timeline")
    
    # Add deadlines
    if doc_data.answer_deadline or doc_data.hearing_date:
        existing_deadlines = {d.get("title") for d in case.get("deadlines", [])}
        
        if doc_data.answer_deadline and "Answer Deadline" not in existing_deadlines:
            case.setdefault("deadlines", []).append({
                "id": "doc_deadline_answer",
                "title": "Answer Deadline",
                "deadline": doc_data.answer_deadline,
                "description": "Deadline to file Answer to Eviction Complaint",
                "priority": "critical",
                "reminder_days": [7, 3, 1],
                "completed": False,
                "source": "document_extraction"
            })
            fields_updated.append("deadlines.answer")
        
        if doc_data.hearing_date and "Court Hearing" not in existing_deadlines:
            case.setdefault("deadlines", []).append({
                "id": "doc_deadline_hearing",
                "title": "Court Hearing",
                "deadline": doc_data.hearing_date,
                "description": "Eviction Hearing",
                "priority": "critical",
                "reminder_days": [14, 7, 3, 1],
                "completed": False,
                "source": "document_extraction"
            })
            fields_updated.append("deadlines.hearing")
    
    case["updated_at"] = utc_now().isoformat()
    case["document_populated"] = True
    case["document_count"] = doc_data.document_count
    
    save_case(case_id, case, user_id)
    
    return {
        "success": True,
        "case_number": case_id,
        "fields_updated": fields_updated,
        "documents_analyzed": doc_data.document_count,
        "case": case
    }


@router.get("/suggested-defenses")
async def get_suggested_defenses(user: StorageUser = Depends(yellow_access)):
    """
    Get defense suggestions based on uploaded documents.
    
    Analyzes uploaded documents and suggests relevant defenses
    based on document types and extracted content.
    """
    hub = get_document_hub()
    case_data = hub.get_case_data(user.user_id)
    
    suggested = []
    
    # Check document types for defense suggestions
    doc_types = case_data.documents_by_type
    
    if doc_types.get("repair_request") or doc_types.get("inspection_report"):
        suggested.append({
            "defense_type": "habitability",
            "reason": "Repair-related documents found",
            "template": MN_DEFENSES.get("habitability", {}),
            "confidence": "high"
        })
    
    if doc_types.get("letter") or doc_types.get("email_communication"):
        suggested.append({
            "defense_type": "retaliation",
            "reason": "Communication records found that may show protected activity",
            "template": MN_DEFENSES.get("retaliation", {}),
            "confidence": "medium"
        })
    
    if doc_types.get("receipt") or doc_types.get("payment_record"):
        suggested.append({
            "defense_type": "waiver",
            "reason": "Payment records found",
            "template": MN_DEFENSES.get("waiver", {}),
            "confidence": "medium"
        })
    
    # Check for notice issues
    if case_data.notice_date and case_data.hearing_date:
        suggested.append({
            "defense_type": "improper_notice",
            "reason": "Notice date found - verify proper notice period",
            "template": MN_DEFENSES.get("improper_notice", {}),
            "confidence": "medium"
        })
    
    return {
        "suggested_defenses": suggested,
        "documents_analyzed": case_data.document_count,
        "all_available_defenses": list(MN_DEFENSES.keys()),
    }


@router.get("/suggested-counterclaims")
async def get_suggested_counterclaims(user: StorageUser = Depends(yellow_access)):
    """
    Get counterclaim suggestions based on uploaded documents.
    
    Analyzes uploaded documents and suggests relevant counterclaims.
    """
    hub = get_document_hub()
    case_data = hub.get_case_data(user.user_id)
    
    suggested = []
    doc_types = case_data.documents_by_type
    
    if case_data.deposit_amount:
        suggested.append({
            "claim_type": "security_deposit",
            "reason": f"Security deposit of ${case_data.deposit_amount} mentioned",
            "template": MN_COUNTERCLAIMS.get("security_deposit", {}),
            "confidence": "high"
        })
    
    if doc_types.get("repair_request") or doc_types.get("inspection_report"):
        suggested.append({
            "claim_type": "breach_of_habitability",
            "reason": "Repair/habitability issues documented",
            "template": MN_COUNTERCLAIMS.get("breach_of_habitability", {}),
            "confidence": "high"
        })
    
    if doc_types.get("photo_evidence"):
        suggested.append({
            "claim_type": "negligent_maintenance",
            "reason": "Photo evidence of property conditions found",
            "template": MN_COUNTERCLAIMS.get("negligent_maintenance", {}),
            "confidence": "medium"
        })
    
    return {
        "suggested_counterclaims": suggested,
        "documents_analyzed": case_data.document_count,
        "all_available_counterclaims": list(MN_COUNTERCLAIMS.keys()),
    }


# =============================================================================
# ATTORNEY INTAKE PACKET EXPORT (Task 6 — scaffold)
# =============================================================================
# Distinct from the court_packet module export (which is court-filing-ready
# with cover sheets, highlights, extractions). This export is a streamlined,
# chronological, evidence-labeled packet optimized for a first-time attorney's
# intake review. Facts and dates only — no editorializing, no recommendations,
# no "next steps". The attorney decides what to do with the facts.
#
# Contract: case_builder_intake_packet_export (see register.py)
# =============================================================================


def _sort_chronological(items: List[Dict[str, Any]], date_key: str) -> List[Dict[str, Any]]:
    """Sort items ascending by a date string field (ISO format). Items with
    missing or unparseable dates sort to the end while preserving input order.
    Non-destructive — returns a new list."""
    def _key(item: Dict[str, Any]):
        raw = item.get(date_key)
        if not raw:
            return (1, "")
        return (0, str(raw))
    return sorted(items, key=_key)


def _build_attorney_intake_packet(case: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble a streamlined, facts-only intake packet from a case dict.

    Output schema (all fields are facts sourced from the case record):
      - case_identification: case_number, court, parties, property_address,
        filing_date, hearing_date
      - timeline: chronological list of {date, title, description, category,
        importance, source}
      - evidence_index: list of {label, title, evidence_type, date_obtained,
        date_of_event, source, relevance, file_path} labeled by category
      - pending_deadlines: chronological list of {deadline, title, description,
        priority, status} excluding completed deadlines
      - generated_at: utc_now() ISO timestamp (when the packet was built)

    No recommendations. No summaries. No editorializing. The attorney reads
    the facts and reaches their own conclusions.
    """
    plaintiff = case.get("plaintiff") or {}
    defendant = case.get("defendant") or {}
    dates = case.get("dates") or {}

    # Chronological timeline (sort by date ascending)
    timeline_raw = list(case.get("timeline") or [])
    timeline_sorted = _sort_chronological(timeline_raw, "date")
    timeline_out = [
        {
            "date": evt.get("date"),
            "title": evt.get("title"),
            "description": evt.get("description"),
            "category": evt.get("category"),
            "importance": evt.get("importance"),
            "source": evt.get("source"),
        }
        for evt in timeline_sorted
    ]

    # Evidence index — labeled by evidence_type, facts only
    evidence_raw = list(case.get("evidence") or [])
    evidence_out = [
        {
            "label": f"EX-{idx + 1:03d}",
            "title": ev.get("title"),
            "evidence_type": ev.get("evidence_type"),
            "date_obtained": ev.get("date_obtained"),
            "date_of_event": ev.get("date_of_event"),
            "source": ev.get("source"),
            "relevance": ev.get("relevance"),
            "file_path": ev.get("file_path"),
        }
        for idx, ev in enumerate(evidence_raw)
    ]

    # Pending deadlines — chronological, completed excluded
    deadlines_raw = list(case.get("deadlines") or [])
    pending = [d for d in deadlines_raw if not d.get("completed")]
    pending_sorted = _sort_chronological(pending, "deadline")
    deadlines_out = [
        {
            "deadline": d.get("deadline"),
            "title": d.get("title"),
            "description": d.get("description"),
            "priority": d.get("priority"),
            "status": d.get("status"),
        }
        for d in pending_sorted
    ]

    return {
        "packet_type": "attorney_intake",
        "packet_version": "0.1.0-scaffold",
        "generated_at": utc_now().isoformat(),
        "case_identification": {
            "case_number": case.get("case_number"),
            "court": case.get("court"),
            "case_type": case.get("case_type"),
            "status": case.get("status"),
            "property_address": case.get("property_address"),
            "filing_date": dates.get("filing_date") or case.get("filing_date"),
            "hearing_date": case.get("hearing_date"),
            "answer_deadline": dates.get("answer_deadline"),
            "plaintiff": {
                "name": plaintiff.get("name"),
                "role": plaintiff.get("role"),
                "type": plaintiff.get("type"),
            },
            "defendant": {
                "name": defendant.get("name"),
                "role": defendant.get("role"),
                "type": defendant.get("type"),
                "is_pro_se": defendant.get("is_pro_se"),
            },
        },
        "timeline": timeline_out,
        "evidence_index": evidence_out,
        "pending_deadlines": deadlines_out,
        "counts": {
            "timeline_events": len(timeline_out),
            "evidence_items": len(evidence_out),
            "pending_deadlines": len(deadlines_out),
        },
    }


@router.get("/cases/{case_id}/intake-packet")
async def export_attorney_intake_packet(
    case_id: str,
    user: StorageUser = Depends(yellow_access),
):
    """Export a streamlined, chronological, evidence-labeled intake packet
    for first-time attorney review. Facts and dates only.

    Distinct from the court_packet module export (court-filing-ready with
    cover sheets, highlights, extractions). This endpoint returns a JSON
    packet — no PDF/ZIP generation in this scaffold. A future task can add
    rendering on top of this canonical data shape.

    Contract: case_builder_intake_packet_export
    """
    user_id = user.user_id
    case = await load_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    packet = _build_attorney_intake_packet(case)
    return {"success": True, "packet": packet}
