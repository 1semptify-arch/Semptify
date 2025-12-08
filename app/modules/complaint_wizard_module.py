"""
Complaint Wizard Module
=======================

Guides users through filing complaints with regulatory agencies.
Integrated with Semptify Positronic Mesh for workflow orchestration.

Features:
- Agency recommendation based on complaint type
- Draft management with evidence attachment
- Auto-population from case data
- Filing tracking and follow-up reminders
- Integration with Timeline and Calendar modules
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.sdk.module_sdk import (
    ModuleSDK,
    ModuleDefinition,
    ModuleCategory,
    DocumentType,
    PackType,
)
from app.services.complaint_wizard import (
    complaint_wizard,
    ComplaintStatus,
    AgencyType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MODULE DEFINITION
# =============================================================================

module_definition = ModuleDefinition(
    name="complaint_wizard",
    display_name="Complaint Filing Wizard",
    description="Guides users through filing complaints with regulatory agencies like MN AG, HUD, and more",
    version="2.0.0",
    category=ModuleCategory.LEGAL,
    
    # Document types this module can process
    handles_documents=[
        DocumentType.COMMUNICATION,
        DocumentType.LEASE,
        DocumentType.EVICTION_NOTICE,
        DocumentType.PAYMENT_RECORD,
        DocumentType.PHOTO,
    ],
    
    # Info pack types this module accepts
    accepts_packs=[
        PackType.EVICTION_DATA,
        PackType.LEASE_DATA,
        PackType.CASE_DATA,
        PackType.USER_DATA,
    ],
    
    # Info pack types this module produces
    produces_packs=[
        PackType.FORM_DATA,
        PackType.DEADLINE_DATA,
    ],
    
    # Dependencies
    depends_on=[
        "documents",
        "calendar",
        "timeline",
        "location",
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
# ACTION HANDLERS
# =============================================================================

@sdk.action(
    "get_agencies",
    description="Get list of complaint agencies, optionally filtered by type or state",
    optional_params=["agency_type", "state_code"],
    produces=["agencies"],
)
async def get_agencies(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get agencies based on type or user location."""
    agency_type = params.get("agency_type")
    state_code = params.get("state_code")
    
    if agency_type:
        try:
            atype = AgencyType(agency_type)
            agencies = complaint_wizard.get_agencies_by_type(atype)
        except ValueError:
            agencies = list(complaint_wizard.agencies.values())
    elif state_code:
        agencies = complaint_wizard.get_all_agencies(state_code.upper())
    else:
        agencies = complaint_wizard.get_agencies_for_user(user_id)
    
    return {
        "agencies": [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type.value,
                "description": a.description,
                "jurisdiction": a.jurisdiction,
                "website": a.website,
                "filing_url": a.filing_url,
                "phone": a.phone,
                "complaint_types": a.complaint_types,
                "typical_response_days": a.typical_response_days,
            }
            for a in agencies
        ]
    }


@sdk.action(
    "recommend_agencies",
    description="Recommend agencies based on complaint keywords",
    required_params=["keywords"],
    produces=["recommendations", "strategy"],
)
async def recommend_agencies(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get AI-powered agency recommendations."""
    keywords = params.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",")]
    
    agencies = complaint_wizard.get_recommended_agencies(keywords)
    
    # Build strategic recommendations
    recommendations = []
    for i, agency in enumerate(agencies[:5]):
        priority = "Primary" if i == 0 else "Secondary" if i < 3 else "Additional"
        recommendations.append({
            "agency_id": agency.id,
            "agency_name": agency.name,
            "priority": priority,
            "matching_types": [
                ct for ct in agency.complaint_types
                if any(kw.lower() in ct.lower() for kw in keywords)
            ][:3],
            "response_time": f"~{agency.typical_response_days} days",
            "filing_url": agency.filing_url,
        })
    
    # Build strategy narrative
    strategy = _build_filing_strategy(recommendations, keywords)
    
    return {
        "recommendations": recommendations,
        "strategy": strategy,
        "keywords_analyzed": keywords,
    }


@sdk.action(
    "create_complaint",
    description="Create a new complaint draft",
    required_params=["agency_id"],
    optional_params=["subject", "auto_populate"],
    produces=["draft_id", "draft"],
)
async def create_complaint(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a complaint draft, optionally auto-populating from context."""
    agency_id = params["agency_id"]
    subject = params.get("subject", "")
    auto_populate = params.get("auto_populate", True)
    
    # Create the draft
    draft = complaint_wizard.create_draft(
        user_id=user_id,
        agency_id=agency_id,
        subject=subject,
    )
    
    # Auto-populate from context if available
    if auto_populate and context:
        updates = {}
        
        # From eviction data
        if "eviction_data" in context:
            ev = context["eviction_data"]
            updates["respondent_name"] = ev.get("landlord_name", "")
            updates["respondent_company"] = ev.get("property_management", "")
            updates["respondent_address"] = ev.get("property_address", "")
        
        # From case data
        if "case_data" in context:
            case = context["case_data"]
            if not updates.get("respondent_name"):
                updates["respondent_name"] = case.get("opposing_party", "")
        
        # From lease data
        if "lease_data" in context:
            lease = context["lease_data"]
            if not updates.get("respondent_address"):
                updates["respondent_address"] = lease.get("property_address", "")
        
        if updates:
            draft = complaint_wizard.update_draft(draft.id, **updates)
    
    return {
        "draft_id": draft.id,
        "draft": draft.model_dump(),
    }


@sdk.action(
    "update_complaint",
    description="Update complaint draft details",
    required_params=["draft_id"],
    optional_params=[
        "subject", "description", "incident_dates", "damages_claimed",
        "relief_sought", "respondent_name", "respondent_company",
        "respondent_address", "respondent_phone", "notes"
    ],
    produces=["draft"],
)
async def update_complaint(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Update a complaint draft."""
    draft_id = params.pop("draft_id")
    
    # Remove None values
    updates = {k: v for k, v in params.items() if v is not None}
    
    draft = complaint_wizard.update_draft(draft_id, **updates)
    if not draft:
        return {"error": "Draft not found"}
    
    return {"draft": draft.model_dump()}


@sdk.action(
    "attach_evidence",
    description="Attach documents as evidence to complaint",
    required_params=["draft_id", "document_ids"],
    produces=["draft", "attached_count"],
)
async def attach_evidence(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Attach evidence documents to a complaint."""
    draft_id = params["draft_id"]
    document_ids = params["document_ids"]
    
    if isinstance(document_ids, str):
        document_ids = [document_ids]
    
    draft = complaint_wizard.attach_documents(draft_id, document_ids)
    if not draft:
        return {"error": "Draft not found"}
    
    return {
        "draft": draft.model_dump(),
        "attached_count": len(draft.attached_document_ids),
    }


@sdk.action(
    "preview_complaint",
    description="Preview formatted complaint text",
    required_params=["draft_id"],
    produces=["complaint_text", "ready_to_file", "checklist"],
)
async def preview_complaint(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate preview of formatted complaint."""
    draft_id = params["draft_id"]
    
    draft = complaint_wizard.get_draft(draft_id)
    if not draft:
        return {"error": "Draft not found"}
    
    text = complaint_wizard.generate_complaint_text(draft)
    agency = complaint_wizard.get_agency(draft.agency_id)
    checklist = complaint_wizard.get_filing_checklist(draft.agency_id)
    
    # Check readiness
    missing = []
    if not draft.subject:
        missing.append("subject")
    if not draft.description:
        missing.append("description")
    if not draft.respondent_name:
        missing.append("respondent_name")
    if not draft.incident_dates:
        missing.append("incident_dates")
    
    return {
        "complaint_text": text,
        "ready_to_file": len(missing) == 0,
        "missing_fields": missing,
        "agency_name": agency.name if agency else "Unknown",
        "filing_url": agency.filing_url if agency else None,
        "checklist": checklist,
    }


@sdk.action(
    "file_complaint",
    description="Mark complaint as filed and schedule follow-up",
    required_params=["draft_id"],
    optional_params=["confirmation_number", "filed_date"],
    produces=["draft", "follow_up_date", "calendar_event_id"],
)
async def file_complaint(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Mark complaint as filed and create follow-up reminder."""
    draft_id = params["draft_id"]
    confirmation = params.get("confirmation_number")
    
    draft = complaint_wizard.mark_as_filed(draft_id, confirmation)
    if not draft:
        return {"error": "Draft not found"}
    
    agency = complaint_wizard.get_agency(draft.agency_id)
    response_days = agency.typical_response_days if agency else 30
    follow_up_date = datetime.utcnow() + timedelta(days=response_days)
    
    # Create calendar event via mesh if available
    calendar_event_id = None
    if sdk._mesh:
        try:
            result = await sdk.invoke_action(
                module="calendar",
                action="create_event",
                user_id=user_id,
                params={
                    "title": f"Follow up: {agency.name if agency else 'Complaint'} filing",
                    "date": follow_up_date.isoformat(),
                    "type": "deadline",
                    "notes": f"Confirmation: {confirmation or 'N/A'}",
                }
            )
            calendar_event_id = result.get("event_id")
        except Exception as e:
            logger.warning(f"Could not create calendar event: {e}")
    
    # Create timeline event
    if sdk._mesh:
        try:
            await sdk.invoke_action(
                module="timeline",
                action="add_event",
                user_id=user_id,
                params={
                    "title": f"Filed complaint with {agency.name if agency else 'agency'}",
                    "date": datetime.utcnow().isoformat(),
                    "type": "complaint_filed",
                    "details": {
                        "agency_id": draft.agency_id,
                        "confirmation": confirmation,
                    }
                }
            )
        except Exception as e:
            logger.debug(f"Could not add timeline event: {e}")
    
    return {
        "draft": draft.model_dump(),
        "follow_up_date": follow_up_date.isoformat(),
        "calendar_event_id": calendar_event_id,
        "status": "filed",
    }


@sdk.action(
    "get_user_complaints",
    description="Get all complaints for a user",
    optional_params=["status"],
    produces=["complaints", "stats"],
)
async def get_user_complaints(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get user's complaint drafts with statistics."""
    status_filter = params.get("status")
    
    drafts = complaint_wizard.get_user_drafts(user_id)
    
    if status_filter:
        try:
            status = ComplaintStatus(status_filter)
            drafts = [d for d in drafts if d.status == status]
        except ValueError:
            pass
    
    # Build stats
    stats = {
        "total": len(drafts),
        "by_status": {},
        "by_agency": {},
    }
    
    for draft in complaint_wizard.get_user_drafts(user_id):
        stats["by_status"][draft.status.value] = stats["by_status"].get(draft.status.value, 0) + 1
        agency = complaint_wizard.get_agency(draft.agency_id)
        if agency:
            stats["by_agency"][agency.name] = stats["by_agency"].get(agency.name, 0) + 1
    
    return {
        "complaints": [d.model_dump() for d in drafts],
        "stats": stats,
    }


@sdk.action(
    "get_filing_guide",
    description="Get comprehensive filing guide for an agency",
    required_params=["agency_id"],
    produces=["guide"],
)
async def get_filing_guide(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get detailed filing guide for an agency."""
    agency_id = params["agency_id"]
    agency = complaint_wizard.get_agency(agency_id)
    
    if not agency:
        return {"error": "Agency not found"}
    
    guide = {
        "agency": {
            "name": agency.name,
            "type": agency.type.value,
            "description": agency.description,
            "jurisdiction": agency.jurisdiction,
        },
        "contact": {
            "website": agency.website,
            "filing_url": agency.filing_url,
            "phone": agency.phone,
            "email": agency.email,
            "address": agency.address,
        },
        "filing_info": {
            "fee": agency.filing_fee,
            "typical_response_days": agency.typical_response_days,
        },
        "what_they_handle": agency.complaint_types,
        "required_documents": agency.required_documents,
        "tips": agency.tips,
        "step_by_step": _get_filing_steps(agency),
    }
    
    return {"guide": guide}


@sdk.action(
    "get_state",
    description="Get complaint wizard module state for sync",
    produces=["complaint_wizard_state"],
)
async def get_state(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Return module state for sync operations."""
    drafts = complaint_wizard.get_user_drafts(user_id)
    
    return {
        "complaint_wizard_state": {
            "status": "active",
            "user_id": user_id,
            "draft_count": len(drafts),
            "pending_filings": len([d for d in drafts if d.status == ComplaintStatus.READY]),
            "filed_count": len([d for d in drafts if d.status == ComplaintStatus.FILED]),
        }
    }


# =============================================================================
# EVENT HANDLERS
# =============================================================================

@sdk.on_event("document_uploaded")
async def on_document_uploaded(event_type: str, data: Dict[str, Any]):
    """Handle new document uploads - suggest for evidence."""
    logger.debug(f"complaint_wizard: Document uploaded - {data.get('document_id')}")
    # Could trigger suggestion to attach to open complaints


@sdk.on_event("eviction_notice_detected")
async def on_eviction_notice(event_type: str, data: Dict[str, Any]):
    """When eviction notice is detected, suggest filing complaints."""
    logger.info(f"complaint_wizard: Eviction notice detected - may recommend complaint filing")
    # Could create info pack suggesting complaint agencies


@sdk.on_event("workflow_completed")
async def on_workflow_completed(event_type: str, data: Dict[str, Any]):
    """Track workflow completions for complaint context."""
    workflow_type = data.get("workflow_type")
    if workflow_type == "document_analysis":
        logger.debug("complaint_wizard: Document analysis complete - evidence may be available")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _build_filing_strategy(recommendations: List[Dict], keywords: List[str]) -> str:
    """Build a strategic narrative for complaint filing."""
    if not recommendations:
        return "No matching agencies found. Consider consulting Legal Aid for guidance."
    
    lines = ["📋 **Recommended Filing Strategy:**\n"]
    
    # Primary recommendation
    primary = recommendations[0]
    lines.append(f"**Start with {primary['agency_name']}** - This agency is best positioned to handle your complaint.")
    
    # Multi-agency approach
    if len(recommendations) > 1:
        lines.append("\n**Multi-Agency Approach:** Filing with multiple agencies creates pressure from multiple directions:")
        for rec in recommendations[1:3]:
            lines.append(f"  • {rec['agency_name']} ({rec['response_time']})")
    
    # Timing advice
    lines.append("\n**Timing Tips:**")
    lines.append("  • File all complaints within the same week for maximum impact")
    lines.append("  • Keep copies of all confirmation numbers")
    lines.append("  • Set calendar reminders for follow-up dates")
    
    return "\n".join(lines)


def _get_filing_steps(agency) -> List[Dict[str, str]]:
    """Get step-by-step filing instructions for an agency."""
    base_steps = [
        {
            "step": "1",
            "title": "Gather Documentation",
            "description": f"Collect: {', '.join(agency.required_documents[:3])}..."
        },
        {
            "step": "2", 
            "title": "Write Your Statement",
            "description": "Clearly describe what happened, when, and who was involved."
        },
        {
            "step": "3",
            "title": "Complete the Form",
            "description": f"Go to {agency.filing_url or agency.website} and fill out the complaint form."
        },
        {
            "step": "4",
            "title": "Attach Evidence",
            "description": "Upload or attach copies of all supporting documents."
        },
        {
            "step": "5",
            "title": "Submit & Save Confirmation",
            "description": "Submit your complaint and save the confirmation number."
        },
        {
            "step": "6",
            "title": "Schedule Follow-Up",
            "description": f"Mark your calendar to follow up in ~{agency.typical_response_days} days."
        },
    ]
    
    return base_steps


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize():
    """Initialize the complaint wizard module with the Positronic Mesh."""
    sdk.initialize()
    logger.info(f"✅ {module_definition.display_name} module ready (v{module_definition.version})")


# Auto-initialize when imported in main app
def register_with_mesh():
    """Register this module with the Positronic Mesh."""
    initialize()


# Export for importing
__all__ = ["sdk", "module_definition", "initialize", "register_with_mesh"]
