"""
Module Registration Service
===========================

Registers all Semptify modules with the Module Hub on startup.
Each module gets registered with:
- What document types it handles
- What pack types it accepts
- Callback handlers for receiving packs and updates
"""

import asyncio
import logging
from typing import Optional

from app.core.module_hub import (
    module_hub,
    ModuleType,
    DocumentCategory,
    PackType,
    InfoPack,
    ModuleUpdate,
)
from app.core.event_bus import event_bus, EventType

logger = logging.getLogger(__name__)


# =============================================================================
# EVICTION DEFENSE MODULE HANDLERS
# =============================================================================

async def on_eviction_pack_received(pack: InfoPack):
    """
    Handle info pack received by Eviction Defense module.
    
    When an eviction notice, court summons, or related document is uploaded,
    this function receives the extracted data and initializes the case.
    """
    logger.info(f"📦 Eviction Defense received pack: {pack.pack_type.value}")
    
    # Get the case builder service
    try:
        from app.services.eviction.case_builder import get_case_builder
        case_builder = get_case_builder()
        
        # Initialize or update the eviction case with the pack data
        case = case_builder.get_or_create_case(pack.user_id)
        
        # Apply data from the pack
        if pack.data.get("landlord_name"):
            case.landlord_name = pack.data["landlord_name"]
        
        if pack.data.get("tenant_name"):
            case.tenant_name = pack.data["tenant_name"]
        
        if pack.data.get("property_address"):
            case.property_address = pack.data["property_address"]
        
        if pack.data.get("case_number"):
            case.case_number = pack.data["case_number"]
        
        if pack.data.get("hearing_date"):
            case.hearing_date = pack.data["hearing_date"]
        
        if pack.data.get("hearing_time"):
            case.hearing_time = pack.data["hearing_time"]
        
        if pack.data.get("court_location"):
            case.court_location = pack.data["court_location"]
        
        if pack.data.get("amount_claimed"):
            case.amount_claimed = pack.data["amount_claimed"]
        
        if pack.data.get("reason"):
            case.eviction_reason = pack.data["reason"]
        
        # Link the source document
        if pack.source_document_id:
            case.documents.append({
                "id": pack.source_document_id,
                "type": pack.data.get("document_type"),
                "added_at": pack.created_at.isoformat(),
            })
        
        # Calculate deadlines based on document type
        from datetime import datetime, timedelta
        if pack.pack_type == PackType.COURT_CASE and pack.data.get("hearing_date"):
            # Answer is typically due before hearing
            hearing = datetime.fromisoformat(pack.data["hearing_date"])
            case.answer_deadline = (hearing - timedelta(days=3)).isoformat()
        
        # Notify user that case was initialized
        await event_bus.publish(
            EventType.NOTIFICATION,
            {
                "title": "Eviction Case Detected",
                "message": f"We've started building your defense based on the uploaded document.",
                "level": "info",
                "action": {
                    "label": "Review Case",
                    "url": "/eviction/case",
                },
            },
            source="eviction_defense",
            user_id=pack.user_id,
        )
        
        logger.info(f"✅ Eviction case initialized for user {pack.user_id}")
        
    except Exception as e:
        logger.error(f"Failed to process eviction pack: {e}")


async def on_eviction_update_received(update: ModuleUpdate):
    """Handle updates from other modules relevant to eviction defense"""
    logger.info(f"📬 Eviction Defense received update: {update.update_type}")
    
    # Handle timeline events that might be relevant
    if update.update_type == "timeline_event_added":
        # Check if it's an eviction-related event
        event_type = update.data.get("event_type", "")
        if "eviction" in event_type.lower() or "court" in event_type.lower():
            # Add to case timeline
            try:
                from app.services.eviction.case_builder import get_case_builder
                case_builder = get_case_builder()
                case = case_builder.get_case(update.user_id)
                if case:
                    case.timeline.append(update.data)
            except Exception as e:
                logger.error(f"Failed to add timeline event to case: {e}")


# =============================================================================
# TIMELINE MODULE HANDLERS
# =============================================================================

async def on_timeline_pack_received(pack: InfoPack):
    """Handle info pack received by Timeline module"""
    logger.info(f"📦 Timeline received pack: {pack.pack_type.value}")
    
    # Add events to timeline
    try:
        from app.services.document_pipeline import get_document_pipeline
        pipeline = get_document_pipeline()
        
        # The timeline is built from document analysis
        # This pack might contain additional dates to add
        
    except Exception as e:
        logger.error(f"Failed to process timeline pack: {e}")


async def on_timeline_update_received(update: ModuleUpdate):
    """Handle updates from other modules for timeline"""
    logger.info(f"📬 Timeline received update: {update.update_type}")


# =============================================================================
# CALENDAR MODULE HANDLERS
# =============================================================================

async def on_calendar_pack_received(pack: InfoPack):
    """Handle info pack received by Calendar module"""
    logger.info(f"📦 Calendar received pack: {pack.pack_type.value}")
    
    # Add deadlines to calendar
    if pack.pack_type == PackType.CALENDAR_DEADLINES:
        # Process deadlines
        pass


async def on_calendar_update_received(update: ModuleUpdate):
    """Handle updates from other modules for calendar"""
    logger.info(f"📬 Calendar received update: {update.update_type}")
    
    if update.update_type == "deadline_added":
        # Add to calendar
        try:
            # Calendar will handle the deadline
            await event_bus.publish(
                EventType.DEADLINE_ADDED,
                update.data,
                source="module_hub",
                user_id=update.user_id,
            )
        except Exception as e:
            logger.error(f"Failed to add deadline to calendar: {e}")


# =============================================================================
# DOCUMENT/VAULT MODULE HANDLERS
# =============================================================================

async def on_documents_pack_received(pack: InfoPack):
    """Handle info pack received by Documents module"""
    logger.info(f"📦 Documents received pack: {pack.pack_type.value}")


async def on_documents_update_received(update: ModuleUpdate):
    """Handle updates for documents module"""
    logger.info(f"📬 Documents received update: {update.update_type}")


# =============================================================================
# REGISTRATION FUNCTION
# =============================================================================

def register_all_modules():
    """
    Register all modules with the Module Hub.
    Called during application startup.
    """
    logger.info("🔌 Registering modules with Module Hub...")
    
    # Eviction Defense Module
    module_hub.register_module(
        module_type=ModuleType.EVICTION_DEFENSE,
        name="Eviction Defense",
        description="Court-ready eviction defense tools - answers, counterclaims, motions",
        handles_documents=[
            DocumentCategory.EVICTION_NOTICE,
            DocumentCategory.COURT_SUMMONS,
            DocumentCategory.NOTICE_TO_QUIT,
            DocumentCategory.PAY_OR_QUIT,
            DocumentCategory.LEASE_VIOLATION,
        ],
        accepts_packs=[
            PackType.EVICTION_CASE,
            PackType.COURT_CASE,
            PackType.LEASE_INFO,
        ],
        on_pack_received=on_eviction_pack_received,
        on_update_received=on_eviction_update_received,
    )
    
    # Timeline Module
    module_hub.register_module(
        module_type=ModuleType.TIMELINE,
        name="Timeline Engine",
        description="Chronological event tracking and evidence organization",
        handles_documents=[
            DocumentCategory.RENT_RECEIPT,
            DocumentCategory.COMMUNICATION,
            DocumentCategory.PHOTO_EVIDENCE,
        ],
        accepts_packs=[
            PackType.TIMELINE_EVENTS,
            PackType.PAYMENT_HISTORY,
        ],
        on_pack_received=on_timeline_pack_received,
        on_update_received=on_timeline_update_received,
    )
    
    # Calendar Module
    module_hub.register_module(
        module_type=ModuleType.CALENDAR,
        name="Calendar & Deadlines",
        description="Deadline tracking, court dates, and important reminders",
        handles_documents=[],
        accepts_packs=[
            PackType.CALENDAR_DEADLINES,
            PackType.COURT_CASE,
        ],
        on_pack_received=on_calendar_pack_received,
        on_update_received=on_calendar_update_received,
    )
    
    # Documents/Vault Module
    module_hub.register_module(
        module_type=ModuleType.DOCUMENTS,
        name="Document Manager",
        description="Secure document storage and organization",
        handles_documents=[
            DocumentCategory.LEASE,
            DocumentCategory.REPAIR_REQUEST,
            DocumentCategory.FINANCIAL,
            DocumentCategory.OTHER,
        ],
        accepts_packs=[
            PackType.LEASE_INFO,
            PackType.DOCUMENT_ANALYSIS,
        ],
        on_pack_received=on_documents_pack_received,
        on_update_received=on_documents_update_received,
    )
    
    # Vault Module (separate from documents for secure storage)
    module_hub.register_module(
        module_type=ModuleType.VAULT,
        name="Secure Vault",
        description="Encrypted document storage with chain of custody",
        handles_documents=[],
        accepts_packs=[],
    )
    
    # AI Copilot Module
    module_hub.register_module(
        module_type=ModuleType.COPILOT,
        name="AI Copilot",
        description="AI-powered legal assistance and guidance",
        handles_documents=[],
        accepts_packs=[],
    )
    
    # Forms Module
    module_hub.register_module(
        module_type=ModuleType.FORMS,
        name="Form Generator",
        description="Court form generation and filing assistance",
        handles_documents=[],
        accepts_packs=[
            PackType.EVICTION_CASE,
            PackType.COURT_CASE,
        ],
    )
    
    # Law Library Module
    module_hub.register_module(
        module_type=ModuleType.LAW_LIBRARY,
        name="Law Library",
        description="Minnesota tenant rights and legal reference",
        handles_documents=[
            DocumentCategory.LEGAL_DOCUMENT,
        ],
        accepts_packs=[],
    )
    
    # Zoom Court Module
    module_hub.register_module(
        module_type=ModuleType.ZOOM_COURT,
        name="Zoom Court Helper",
        description="Virtual court preparation and guidance",
        handles_documents=[],
        accepts_packs=[
            PackType.COURT_CASE,
        ],
    )
    
    # Context Engine Module
    module_hub.register_module(
        module_type=ModuleType.CONTEXT_ENGINE,
        name="Context Engine",
        description="Central intelligence hub - intensity and risk analysis",
        handles_documents=[],
        accepts_packs=[],
    )
    
    # Adaptive UI Module
    module_hub.register_module(
        module_type=ModuleType.ADAPTIVE_UI,
        name="Adaptive UI",
        description="Self-building interface based on user context",
        handles_documents=[],
        accepts_packs=[],
    )
    
    status = module_hub.get_hub_status()
    logger.info(f"✅ Module Hub ready: {status['modules_registered']} modules registered")
    
    return status


# =============================================================================
# STARTUP HOOK
# =============================================================================

async def initialize_module_hub():
    """
    Initialize the module hub during application startup.
    """
    # Register all modules
    register_all_modules()
    
    # Log the hub status
    status = module_hub.get_hub_status()
    logger.info(f"🔄 Module Hub Status:")
    logger.info(f"   Modules: {status['modules_registered']}")
    for module in status['modules']:
        logger.info(f"   - {module['name']} ({module['type']})")
