"""
Example Module - Payment Tracking
=================================

This is a COMPLETE EXAMPLE of how to create a new module
that integrates with the Semptify Positronic Mesh.

Copy this file and modify it for your own module!
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from app.sdk import (
    ModuleSDK,
    ModuleDefinition,
    ModuleCategory,
    DocumentType,
    PackType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# STEP 1: DEFINE YOUR MODULE
# =============================================================================

module_definition = ModuleDefinition(
    # Unique identifier (snake_case, no spaces)
    name="payment_tracking",
    
    # Human-readable name
    display_name="Payment Tracking",
    
    # Description of what this module does
    description="Tracks rent payments and generates payment history for court",
    
    # Version following semver
    version="1.0.0",
    
    # Category for organization
    category=ModuleCategory.DOCUMENT,
    
    # What document types can this module process?
    handles_documents=[
        DocumentType.PAYMENT_RECORD,
    ],
    
    # What info packs can this module receive?
    accepts_packs=[
        PackType.EVICTION_DATA,  # Receives eviction info
        PackType.LEASE_DATA,     # Receives lease info
    ],
    
    # What info packs does this module produce?
    produces_packs=[
        PackType.CASE_DATA,      # Produces payment history for case
    ],
    
    # What other modules does this depend on?
    depends_on=[
        "documents",  # Needs document storage
        "calendar",   # Needs deadline calculations
    ],
    
    # Does this module have a UI component?
    has_ui=True,
    
    # Does it run background tasks?
    has_background_tasks=False,
    
    # Does it require user authentication?
    requires_auth=True,
)


# =============================================================================
# STEP 2: CREATE SDK INSTANCE
# =============================================================================

sdk = ModuleSDK(module_definition)


# =============================================================================
# STEP 3: DEFINE YOUR ACTIONS
# =============================================================================

@sdk.action(
    "record_payment",
    description="Record a rent payment",
    required_params=["amount", "date"],
    optional_params=["method", "note"],
    produces=["payment_recorded"],
)
async def record_payment(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Record a rent payment to the user's history"""
    logger.info(f"💰 Recording payment for user {user_id[:8]}...")
    
    amount = params.get("amount", 0)
    date = params.get("date", datetime.utcnow().isoformat())
    method = params.get("method", "unknown")
    note = params.get("note", "")
    
    # In production, this would save to database
    payment = {
        "id": f"pay_{datetime.utcnow().timestamp()}",
        "amount": amount,
        "date": date,
        "method": method,
        "note": note,
        "recorded_at": datetime.utcnow().isoformat(),
    }
    
    return {
        "payment_recorded": payment,
        "success": True,
    }


@sdk.action(
    "get_payment_history",
    description="Get payment history for a user",
    optional_params=["start_date", "end_date"],
    produces=["payment_history", "total_paid"],
)
async def get_payment_history(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Retrieve payment history for court documentation"""
    logger.info(f"📊 Getting payment history for user {user_id[:8]}...")
    
    # In production, fetch from database
    # For now, return mock data
    history = [
        {"date": "2024-01-01", "amount": 800, "method": "check"},
        {"date": "2024-02-01", "amount": 800, "method": "check"},
        {"date": "2024-03-01", "amount": 800, "method": "bank_transfer"},
    ]
    
    total = sum(p["amount"] for p in history)
    
    return {
        "payment_history": history,
        "total_paid": total,
        "payment_count": len(history),
    }


@sdk.action(
    "analyze_payment_pattern",
    description="Analyze payment patterns for defense",
    requires_context=["eviction_date", "rent_amount"],
    produces=["payment_analysis", "defense_points"],
)
async def analyze_payment_pattern(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Analyze payment patterns to find potential defense points.
    This is called as part of the eviction defense workflow.
    """
    logger.info(f"🔍 Analyzing payment patterns for user {user_id[:8]}...")
    
    # Get context from workflow
    rent_amount = context.get("rent_amount", 0)
    eviction_date = context.get("eviction_date", "")
    
    # Get payment history (we can call our own action!)
    history_result = await get_payment_history(user_id, {}, context)
    history = history_result.get("payment_history", [])
    total_paid = history_result.get("total_paid", 0)
    
    # Analyze patterns
    analysis = {
        "consistent_payer": len(history) >= 3,
        "total_paid": total_paid,
        "average_payment": total_paid / len(history) if history else 0,
        "on_time_percentage": 85,  # Would calculate from dates
    }
    
    # Generate defense points based on analysis
    defense_points = []
    
    if analysis["consistent_payer"]:
        defense_points.append({
            "type": "payment_history",
            "strength": "strong",
            "description": "Consistent payment history demonstrates good faith",
        })
    
    if analysis["on_time_percentage"] > 80:
        defense_points.append({
            "type": "timeliness",
            "strength": "medium",
            "description": f"Payments were on-time {analysis['on_time_percentage']}% of the time",
        })
    
    return {
        "payment_analysis": analysis,
        "defense_points": defense_points,
    }


@sdk.action(
    "generate_payment_summary",
    description="Generate a court-ready payment summary document",
    produces=["payment_summary_doc"],
)
async def generate_payment_summary(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate a formatted payment summary for court"""
    logger.info(f"📄 Generating payment summary for user {user_id[:8]}...")
    
    history_result = await get_payment_history(user_id, {}, context)
    
    summary = {
        "title": "Payment History Summary",
        "generated_at": datetime.utcnow().isoformat(),
        "payments": history_result.get("payment_history", []),
        "total_paid": history_result.get("total_paid", 0),
        "format": "pdf_ready",
    }
    
    return {
        "payment_summary_doc": summary,
    }


@sdk.action(
    "get_state",
    description="Get current module state",
    produces=["payment_tracking_state"],
)
async def get_state(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Return module state for sync operations"""
    return {
        "payment_tracking_state": {
            "active": True,
            "user_id": user_id,
            "last_payment_date": None,
        }
    }


# =============================================================================
# STEP 4: EVENT HANDLERS (Optional)
# =============================================================================

@sdk.on_event("workflow_started")
async def on_workflow_started(event_type: str, data: Dict[str, Any]):
    """React when a workflow starts"""
    workflow_type = data.get("type", "")
    if workflow_type == "eviction_defense":
        logger.info("💰 Payment tracking: Eviction workflow started, preparing data...")


@sdk.on_event("document_uploaded")
async def on_document_uploaded(event_type: str, data: Dict[str, Any]):
    """React when a document is uploaded"""
    doc_type = data.get("document_type", "")
    if doc_type == "payment_record":
        logger.info("💰 Payment tracking: New payment record uploaded!")
        # Could trigger automatic extraction here


# =============================================================================
# STEP 5: INITIALIZATION FUNCTION
# =============================================================================

def initialize():
    """
    Initialize this module.
    Call this from main.py on application startup.
    """
    sdk.initialize()
    logger.info(f"✅ {module_definition.display_name} module ready")


# =============================================================================
# STEP 6: EXPORT FOR EASY IMPORTING
# =============================================================================

__all__ = [
    "sdk",
    "module_definition", 
    "initialize",
    # Export actions if needed elsewhere
    "record_payment",
    "get_payment_history",
    "analyze_payment_pattern",
    "generate_payment_summary",
]


# =============================================================================
# OPTIONAL: FastAPI Router (if module has its own API endpoints)
# =============================================================================

from fastapi import APIRouter, Cookie, HTTPException
from typing import Optional

router = APIRouter()

@router.get("/payments")
async def api_get_payments(
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """API endpoint to get payment history"""
    user_id = semptify_uid or "anonymous"
    result = await get_payment_history(user_id, {}, {})
    return result

@router.post("/payments")
async def api_record_payment(
    amount: float,
    date: str = None,
    method: str = "other",
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """API endpoint to record a payment"""
    user_id = semptify_uid or "anonymous"
    result = await record_payment(
        user_id,
        {"amount": amount, "date": date, "method": method},
        {},
    )
    return result
