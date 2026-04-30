"""
🧠 Positronic Brain - Module Integrations
=========================================
Connects all Semptify modules to the brain.
"""

import logging
from typing import Optional
from datetime import datetime

from app.services.positronic_brain import (
    get_brain,
    BrainEvent,
    EventType,
    ModuleType
)

logger = logging.getLogger(__name__)


async def initialize_brain_connections():
    """
    Initialize all module connections to the brain.
    Call this during app startup.
    """
    brain = get_brain()
    
    # Register all modules
    brain.register_module(
        ModuleType.DOCUMENTS,
        "Document Manager",
        capabilities=["upload", "analyze", "classify", "store"]
    )
    
    brain.register_module(
        ModuleType.TIMELINE,
        "Timeline Engine",
        capabilities=["track_events", "build_history", "evidence_chain"]
    )
    
    brain.register_module(
        ModuleType.CALENDAR,
        "Calendar & Deadlines",
        capabilities=["schedule", "reminders", "deadline_tracking"]
    )
    
    brain.register_module(
        ModuleType.EVICTION,
        "Eviction Defense",
        capabilities=["answer", "counterclaim", "motions", "defenses"]
    )
    
    brain.register_module(
        ModuleType.COPILOT,
        "AI Copilot",
        capabilities=["analyze", "suggest", "classify", "generate"]
    )
    
    brain.register_module(
        ModuleType.VAULT,
        "Secure Vault",
        capabilities=["store", "certify", "retrieve", "audit"]
    )
    
    brain.register_module(
        ModuleType.CONTEXT,
        "Context Engine",
        capabilities=["state", "intensity", "predictions"]
    )
    
    brain.register_module(
        ModuleType.UI,
        "Adaptive UI",
        capabilities=["widgets", "suggestions", "display"]
    )
    
    brain.register_module(
        ModuleType.FORMS,
        "Form Generator",
        capabilities=["generate", "fill", "validate", "submit"]
    )
    
    brain.register_module(
        ModuleType.LAW_LIBRARY,
        "Law Library",
        capabilities=["search", "cite", "explain"]
    )
    
    brain.register_module(
        ModuleType.ZOOM_COURT,
        "Zoom Court Helper",
        capabilities=["prepare", "checklist", "tips"]
    )
    
    # Set up event handlers
    _setup_event_handlers(brain)
    
    logger.info("🧠 Positronic Brain fully initialized with all modules")
    
    return brain


def _setup_event_handlers(brain):
    """Set up cross-module event handlers."""
    
    # When document uploaded -> analyze and classify
    async def on_document_uploaded(event: BrainEvent):
        logger.info(f"🧠 Brain processing: {event.event_type.value}")
        
        # Update shared state
        docs = brain.get_state("documents") or []
        docs.append({
            "id": event.data.get("document_id"),
            "uploaded_at": datetime.utcnow().isoformat(),
            **event.data
        })
        await brain.update_state("documents", docs, ModuleType.DOCUMENTS)
    
    brain.subscribe(EventType.DOCUMENT_UPLOADED, on_document_uploaded)
    
    # When document classified -> add to timeline if eviction-related
    async def on_document_classified(event: BrainEvent):
        doc_type = event.data.get("type", "")
        if doc_type in ["eviction_notice", "summons", "complaint", "court_order"]:
            # Add to timeline
            timeline = brain.get_state("timeline") or []
            timeline.append({
                "event_type": doc_type,
                "title": f"Document: {doc_type.replace('_', ' ').title()}",
                "document_id": event.data.get("document_id"),
                "date": datetime.utcnow().isoformat()
            })
            await brain.update_state("timeline", timeline, ModuleType.TIMELINE)
    
    brain.subscribe(EventType.DOCUMENT_CLASSIFIED, on_document_classified)
    
    # When defense identified -> update defenses list
    async def on_defense_identified(event: BrainEvent):
        defenses = brain.get_state("defenses") or []
        new_defenses = event.data.get("defenses", [])
        for d in new_defenses:
            if d not in defenses:
                defenses.append(d)
        await brain.update_state("defenses", defenses, ModuleType.EVICTION)
    
    brain.subscribe(EventType.DEFENSE_IDENTIFIED, on_defense_identified)
    
    # When deadline approaching -> increase intensity
    async def on_deadline_approaching(event: BrainEvent):
        days_until = event.data.get("days_until", 30)
        
        # Calculate intensity based on deadline proximity
        if days_until <= 1:
            intensity = 1.0
        elif days_until <= 3:
            intensity = 0.9
        elif days_until <= 7:
            intensity = 0.7
        elif days_until <= 14:
            intensity = 0.5
        else:
            intensity = 0.3
        
        current_intensity = brain.get_state("intensity") or 0
        if intensity > current_intensity:
            await brain.update_state("intensity", intensity, ModuleType.CALENDAR)
            
            # Also emit intensity change event
            await brain.emit(BrainEvent(
                event_type=EventType.INTENSITY_CHANGED,
                source_module=ModuleType.CONTEXT,
                data={"old": current_intensity, "new": intensity, "reason": "deadline"}
            ))
    
    brain.subscribe(EventType.DEADLINE_APPROACHING, on_deadline_approaching)
    
    # When context updated -> notify UI
    async def on_context_updated(event: BrainEvent):
        # This will automatically broadcast to all WebSocket clients
        pass
    
    brain.subscribe(EventType.CONTEXT_UPDATED, on_context_updated)


# =============================================================================
# Helper Functions for Other Modules
# =============================================================================

async def brain_document_uploaded(
    document_id: str,
    filename: str,
    document_type: str = None,
    analysis: dict = None,
    user_id: str = None
):
    """Call this when a document is uploaded."""
    brain = get_brain()
    
    await brain.emit(BrainEvent(
        event_type=EventType.DOCUMENT_UPLOADED,
        source_module=ModuleType.DOCUMENTS,
        data={
            "document_id": document_id,
            "filename": filename,
            "document_type": document_type,
            "analysis": analysis
        },
        user_id=user_id
    ))
    
    # Trigger full document intake workflow
    await brain.trigger_workflow("document_intake", {
        "document_id": document_id,
        "filename": filename,
        "document_type": document_type,
        "analysis": analysis
    }, user_id)


async def brain_timeline_event(
    event_type: str,
    title: str,
    description: str = None,
    event_date: str = None,
    document_id: str = None,
    user_id: str = None
):
    """Call this when a timeline event is created."""
    brain = get_brain()
    
    await brain.emit(BrainEvent(
        event_type=EventType.TIMELINE_EVENT_ADDED,
        source_module=ModuleType.TIMELINE,
        data={
            "event_type": event_type,
            "title": title,
            "description": description,
            "event_date": event_date,
            "document_id": document_id
        },
        user_id=user_id
    ))


async def brain_calendar_event(
    title: str,
    event_type: str,
    start_datetime: str,
    is_critical: bool = False,
    user_id: str = None
):
    """Call this when a calendar event is created."""
    brain = get_brain()
    
    # Calculate days until
    from datetime import datetime
    event_date = datetime.fromisoformat(start_datetime.replace("Z", ""))
    days_until = (event_date - datetime.utcnow()).days
    
    if days_until <= 14:
        await brain.emit(BrainEvent(
            event_type=EventType.DEADLINE_APPROACHING,
            source_module=ModuleType.CALENDAR,
            data={
                "title": title,
                "event_type": event_type,
                "start_datetime": start_datetime,
                "days_until": days_until,
                "is_critical": is_critical or days_until <= 3
            },
            user_id=user_id
        ))
    
    if event_type == "hearing":
        await brain.emit(BrainEvent(
            event_type=EventType.HEARING_SCHEDULED,
            source_module=ModuleType.CALENDAR,
            data={
                "title": title,
                "start_datetime": start_datetime,
                "days_until": days_until
            },
            user_id=user_id
        ))


async def brain_eviction_step_completed(
    flow_name: str,
    step: int,
    data: dict = None,
    user_id: str = None
):
    """Call this when an eviction flow step is completed."""
    brain = get_brain()
    
    await brain.emit(BrainEvent(
        event_type=EventType.EVICTION_STEP_COMPLETED,
        source_module=ModuleType.EVICTION,
        data={
            "flow": flow_name,
            "step": step,
            **data
        },
        user_id=user_id
    ))


async def brain_ai_analysis(
    document_id: str,
    analysis: dict,
    suggestions: list = None,
    user_id: str = None
):
    """Call this when AI completes analysis."""
    brain = get_brain()
    
    await brain.emit(BrainEvent(
        event_type=EventType.AI_ANALYSIS_COMPLETE,
        source_module=ModuleType.COPILOT,
        data={
            "document_id": document_id,
            "analysis": analysis,
            "suggestions": suggestions or []
        },
        user_id=user_id
    ))
    
    # If defenses found, emit defense event
    defenses = analysis.get("defenses", [])
    if defenses:
        await brain.emit(BrainEvent(
            event_type=EventType.DEFENSE_IDENTIFIED,
            source_module=ModuleType.COPILOT,
            data={"defenses": defenses, "source": "ai_analysis"},
            user_id=user_id
        ))


async def brain_form_generated(
    form_type: str,
    filename: str,
    user_id: str = None
):
    """Call this when a form is generated."""
    brain = get_brain()
    
    await brain.emit(BrainEvent(
        event_type=EventType.FORM_GENERATED,
        source_module=ModuleType.FORMS,
        data={
            "form_type": form_type,
            "filename": filename,
            "generated_at": datetime.utcnow().isoformat()
        },
        user_id=user_id
    ))
