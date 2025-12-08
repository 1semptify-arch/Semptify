"""
🧠 POSITRONIC BRAIN - Central Intelligence Hub
==============================================
The neural core that connects ALL Semptify modules together.

This creates a mesh network of interconnected services that can:
- Communicate with each other in real-time
- Share state automatically
- Trigger cross-module workflows
- Maintain full awareness of the system state

Inspired by Isaac Asimov's positronic brain concept.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class ModuleType(str, Enum):
    """Types of modules that can connect to the brain."""
    DOCUMENTS = "documents"
    TIMELINE = "timeline"
    CALENDAR = "calendar"
    EVICTION = "eviction"
    COPILOT = "copilot"
    VAULT = "vault"
    AUTH = "auth"
    CONTEXT = "context"
    UI = "ui"
    FORMS = "forms"
    LAW_LIBRARY = "law_library"
    ZOOM_COURT = "zoom_court"
    NOTIFICATIONS = "notifications"
    LOCATION = "location"  # Location detection and state-specific resources
    LEGAL_ANALYSIS = "legal_analysis"  # Legal merit, evidence, consistency analysis
    TENANCY_HUB = "tenancy_hub"  # Central tenancy documentation hub
    LEGAL_TRAILS = "legal_trails"  # Track violations, claims, filing deadlines, broker oversight
    COURT_FORMS = "court_forms"  # Auto-generate Minnesota court forms
    ZOOM_COURT_PREP = "zoom_court_prep"  # Zoom hearing preparation and tech checks
    DOCUMENT_FLOW = "document_flow"  # Document pipeline orchestration
    OCR_SERVICE = "ocr_service"  # OCR text extraction from scans
    CONTACTS = "contacts"  # Contact management for parties


class EventType(str, Enum):
    """Types of events that flow through the brain."""
    # Document events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_ANALYZED = "document.analyzed"
    DOCUMENT_CLASSIFIED = "document.classified"
    
    # Timeline events
    TIMELINE_EVENT_ADDED = "timeline.event_added"
    TIMELINE_UPDATED = "timeline.updated"
    
    # Calendar events
    DEADLINE_APPROACHING = "calendar.deadline_approaching"
    HEARING_SCHEDULED = "calendar.hearing_scheduled"
    REMINDER_DUE = "calendar.reminder_due"
    
    # Eviction flow events
    EVICTION_FLOW_STARTED = "eviction.flow_started"
    EVICTION_STEP_COMPLETED = "eviction.step_completed"
    DEFENSE_IDENTIFIED = "eviction.defense_identified"
    FORM_GENERATED = "eviction.form_generated"
    
    # AI/Copilot events
    AI_ANALYSIS_COMPLETE = "ai.analysis_complete"
    AI_SUGGESTION_READY = "ai.suggestion_ready"

    # Legal Analysis events
    LEGAL_QUICK_CHECK = "legal.quick_check"
    LEGAL_MERIT_ASSESSED = "legal.merit_assessed"
    LEGAL_HEARSAY_DETECTED = "legal.hearsay_detected"
    LEGAL_DEFENSE_FOUND = "legal.defense_found"
    LEGAL_TIMELINE_ANALYZED = "legal.timeline_analyzed"
    
    # Context events
    CONTEXT_UPDATED = "context.updated"
    INTENSITY_CHANGED = "context.intensity_changed"
    LOCATION_CHANGED = "location.changed"  # User location updated

    # User events
    USER_ACTION = "user.action"
    SESSION_STARTED = "user.session_started"
    
    # System events
    MODULE_REGISTERED = "system.module_registered"
    BRAIN_SYNC = "system.brain_sync"
    ERROR_OCCURRED = "system.error"

    # Court Form events
    COURT_FORM_GENERATED = "forms.generated"
    COURT_FORM_BATCH = "forms.batch_generated"

    # Zoom Court Prep events
    ZOOM_PREP_STARTED = "zoom_prep.started"
    ZOOM_PREP_TECH_CHECK = "zoom_prep.tech_check"
    ZOOM_PREP_COMPLETED = "zoom_prep.completed"

    # Document Flow events
    DOCUMENT_FLOW_STARTED = "document_flow.started"
    DOCUMENT_FLOW_COMPLETED = "document_flow.completed"
    OCR_COMPLETED = "ocr.completed"
    OCR_FAILED = "ocr.failed"

    # Contact events
    CONTACT_ADDED = "contacts.added"
    CONTACT_UPDATED = "contacts.updated"


@dataclass
class BrainEvent:
    """An event that flows through the positronic brain."""
    event_type: EventType
    source_module: ModuleType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "source_module": self.source_module.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "correlation_id": self.correlation_id
        }


@dataclass
class ModuleConnection:
    """A connected module in the brain network."""
    module_type: ModuleType
    name: str
    version: str = "1.0.0"
    capabilities: List[str] = field(default_factory=list)
    subscriptions: Set[EventType] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    handler: Optional[Callable] = None
    is_active: bool = True


class PositronicBrain:
    """
    🧠 The Positronic Brain - Central Intelligence Hub
    
    This is the neural core of Semptify that:
    1. Maintains awareness of all connected modules
    2. Routes events between modules
    3. Manages shared state
    4. Orchestrates complex cross-module workflows
    5. Provides real-time synchronization
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern - only one brain per application."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Core systems
        self.modules: Dict[ModuleType, ModuleConnection] = {}
        self.event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_history: List[BrainEvent] = []
        self.max_history = 1000
        
        # Shared state (synchronized across all modules)
        self.shared_state: Dict[str, Any] = {
            "user": None,
            "case": {},
            "documents": [],
            "timeline": [],
            "calendar": [],
            "defenses": [],
            "intensity": 0.0,
            "context": {},
            "notifications": [],
        }
        
        # WebSocket connections for real-time updates
        self.websocket_clients: Set[Any] = set()
        
        # Workflow orchestration
        self.active_workflows: Dict[str, dict] = {}
        
        # Module dependency graph
        self.dependencies: Dict[ModuleType, Set[ModuleType]] = {
            ModuleType.EVICTION: {ModuleType.DOCUMENTS, ModuleType.TIMELINE, ModuleType.CALENDAR},
            ModuleType.COPILOT: {ModuleType.DOCUMENTS, ModuleType.CONTEXT},
            ModuleType.FORMS: {ModuleType.EVICTION, ModuleType.DOCUMENTS},
            ModuleType.NOTIFICATIONS: {ModuleType.CALENDAR, ModuleType.TIMELINE},
            ModuleType.COURT_FORMS: {ModuleType.DOCUMENTS, ModuleType.EVICTION, ModuleType.CONTACTS},
            ModuleType.ZOOM_COURT_PREP: {ModuleType.CALENDAR, ModuleType.DOCUMENTS},
            ModuleType.DOCUMENT_FLOW: {ModuleType.DOCUMENTS, ModuleType.TIMELINE, ModuleType.VAULT},
            ModuleType.OCR_SERVICE: {ModuleType.DOCUMENTS},
            ModuleType.CONTACTS: {ModuleType.DOCUMENTS},
        }
        
        logger.info("🧠 Positronic Brain initialized")
    
    # =========================================================================
    # Module Management
    # =========================================================================
    
    def register_module(
        self,
        module_type: ModuleType,
        name: str,
        capabilities: List[str] = None,
        handler: Callable = None
    ) -> ModuleConnection:
        """Register a module with the brain."""
        connection = ModuleConnection(
            module_type=module_type,
            name=name,
            capabilities=capabilities or [],
            handler=handler
        )
        self.modules[module_type] = connection
        
        logger.info(f"🔌 Module registered: {name} ({module_type.value})")
        
        # Emit registration event
        asyncio.create_task(self.emit(BrainEvent(
            event_type=EventType.MODULE_REGISTERED,
            source_module=module_type,
            data={"name": name, "capabilities": capabilities}
        )))
        
        return connection
    
    def get_module(self, module_type: ModuleType) -> Optional[ModuleConnection]:
        """Get a connected module."""
        return self.modules.get(module_type)
    
    def list_modules(self) -> List[dict]:
        """List all connected modules."""
        return [
            {
                "type": m.module_type.value,
                "name": m.name,
                "capabilities": m.capabilities,
                "active": m.is_active,
                "connected_at": m.connected_at.isoformat()
            }
            for m in self.modules.values()
        ]
    
    # =========================================================================
    # Event System (Pub/Sub)
    # =========================================================================
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to an event type."""
        self.event_handlers[event_type].append(handler)
        logger.debug(f"📡 Subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from an event type."""
        if handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    async def emit(self, event: BrainEvent):
        """Emit an event to all subscribers."""
        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        # Call all handlers for this event type
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
        
        # Broadcast to WebSocket clients
        await self._broadcast_to_websockets(event)
        
        logger.debug(f"📤 Event emitted: {event.event_type.value} from {event.source_module.value}")
    
    async def _broadcast_to_websockets(self, event: BrainEvent):
        """Send event to all connected WebSocket clients."""
        if not self.websocket_clients:
            return
            
        message = json.dumps({
            "type": "brain_event",
            "event": event.to_dict()
        })
        
        dead_clients = set()
        for client in self.websocket_clients:
            try:
                await client.send_text(message)
            except:
                dead_clients.add(client)
        
        # Clean up disconnected clients
        self.websocket_clients -= dead_clients
    
    # =========================================================================
    # Shared State Management
    # =========================================================================
    
    def get_state(self, key: str = None) -> Any:
        """Get shared state (or specific key)."""
        if key:
            return self.shared_state.get(key)
        return self.shared_state.copy()
    
    async def update_state(self, key: str, value: Any, source: ModuleType = None):
        """Update shared state and notify all modules."""
        old_value = self.shared_state.get(key)
        self.shared_state[key] = value
        
        # Emit state change event
        await self.emit(BrainEvent(
            event_type=EventType.CONTEXT_UPDATED,
            source_module=source or ModuleType.CONTEXT,
            data={
                "key": key,
                "old_value": old_value,
                "new_value": value
            }
        ))
    
    async def merge_state(self, updates: Dict[str, Any], source: ModuleType = None):
        """Merge multiple state updates at once."""
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(self.shared_state.get(key), dict):
                self.shared_state[key].update(value)
            elif isinstance(value, list) and isinstance(self.shared_state.get(key), list):
                self.shared_state[key].extend(value)
            else:
                self.shared_state[key] = value
        
        await self.emit(BrainEvent(
            event_type=EventType.BRAIN_SYNC,
            source_module=source or ModuleType.CONTEXT,
            data={"updates": list(updates.keys())}
        ))
    
    # =========================================================================
    # Cross-Module Workflows
    # =========================================================================
    
    async def trigger_workflow(self, workflow_name: str, data: dict, user_id: str = None) -> str:
        """Trigger a cross-module workflow."""
        import uuid
        workflow_id = str(uuid.uuid4())[:8]
        
        self.active_workflows[workflow_id] = {
            "name": workflow_name,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "data": data,
            "steps_completed": []
        }
        
        # Execute workflow based on type
        if workflow_name == "document_intake":
            await self._workflow_document_intake(workflow_id, data, user_id)
        elif workflow_name == "eviction_defense":
            await self._workflow_eviction_defense(workflow_id, data, user_id)
        elif workflow_name == "deadline_check":
            await self._workflow_deadline_check(workflow_id, data, user_id)
        elif workflow_name == "full_sync":
            await self._workflow_full_sync(workflow_id, data, user_id)
        
        return workflow_id
    
    async def _workflow_document_intake(self, workflow_id: str, data: dict, user_id: str):
        """
        Document Intake Workflow:
        1. Extract text from document
        2. Analyze with AI
        3. Classify document type
        4. Add to timeline if relevant
        5. Check for deadlines
        6. Suggest defenses
        """
        workflow = self.active_workflows[workflow_id]
        
        try:
            # Step 1: Document uploaded event
            await self.emit(BrainEvent(
                event_type=EventType.DOCUMENT_UPLOADED,
                source_module=ModuleType.DOCUMENTS,
                data=data,
                user_id=user_id,
                correlation_id=workflow_id
            ))
            workflow["steps_completed"].append("document_uploaded")
            
            # Step 2: AI Analysis
            await self.emit(BrainEvent(
                event_type=EventType.AI_ANALYSIS_COMPLETE,
                source_module=ModuleType.COPILOT,
                data={"document_id": data.get("document_id"), "analysis": data.get("analysis", {})},
                user_id=user_id,
                correlation_id=workflow_id
            ))
            workflow["steps_completed"].append("ai_analyzed")
            
            # Step 3: Classification
            doc_type = data.get("document_type", "unknown")
            await self.emit(BrainEvent(
                event_type=EventType.DOCUMENT_CLASSIFIED,
                source_module=ModuleType.DOCUMENTS,
                data={"document_id": data.get("document_id"), "type": doc_type},
                user_id=user_id,
                correlation_id=workflow_id
            ))
            workflow["steps_completed"].append("classified")
            
            # Step 4: Add to timeline
            if doc_type in ["eviction_notice", "summons", "complaint", "court_order"]:
                await self.emit(BrainEvent(
                    event_type=EventType.TIMELINE_EVENT_ADDED,
                    source_module=ModuleType.TIMELINE,
                    data={
                        "event_type": doc_type,
                        "title": f"Received: {doc_type.replace('_', ' ').title()}",
                        "document_id": data.get("document_id")
                    },
                    user_id=user_id,
                    correlation_id=workflow_id
                ))
                workflow["steps_completed"].append("timeline_updated")
            
            # Step 5: Check deadlines
            if data.get("dates"):
                for date_info in data["dates"]:
                    await self.emit(BrainEvent(
                        event_type=EventType.DEADLINE_APPROACHING,
                        source_module=ModuleType.CALENDAR,
                        data=date_info,
                        user_id=user_id,
                        correlation_id=workflow_id
                    ))
                workflow["steps_completed"].append("deadlines_checked")
            
            # Step 6: Suggest defenses
            if data.get("defenses"):
                await self.emit(BrainEvent(
                    event_type=EventType.DEFENSE_IDENTIFIED,
                    source_module=ModuleType.EVICTION,
                    data={"defenses": data["defenses"]},
                    user_id=user_id,
                    correlation_id=workflow_id
                ))
                workflow["steps_completed"].append("defenses_suggested")
            
            workflow["status"] = "completed"
            
        except Exception as e:
            workflow["status"] = "failed"
            workflow["error"] = str(e)
            logger.error(f"Workflow {workflow_id} failed: {e}")
    
    async def _workflow_eviction_defense(self, workflow_id: str, data: dict, user_id: str):
        """
        Eviction Defense Workflow:
        1. Gather all case documents
        2. Build timeline
        3. Identify defenses
        4. Calculate deadlines
        5. Prepare forms
        """
        workflow = self.active_workflows[workflow_id]
        
        await self.emit(BrainEvent(
            event_type=EventType.EVICTION_FLOW_STARTED,
            source_module=ModuleType.EVICTION,
            data=data,
            user_id=user_id,
            correlation_id=workflow_id
        ))
        
        # Sync state
        await self.merge_state({
            "case": data.get("case", {}),
            "defenses": data.get("defenses", [])
        }, ModuleType.EVICTION)
        
        workflow["status"] = "completed"
    
    async def _workflow_deadline_check(self, workflow_id: str, data: dict, user_id: str):
        """Check all deadlines and send notifications."""
        workflow = self.active_workflows[workflow_id]
        
        # Get calendar events
        calendar_events = self.shared_state.get("calendar", [])
        
        from datetime import timedelta
        now = datetime.utcnow()
        
        for event in calendar_events:
            event_date = datetime.fromisoformat(event.get("start_datetime", "").replace("Z", ""))
            days_until = (event_date - now).days
            
            if 0 <= days_until <= 7:
                await self.emit(BrainEvent(
                    event_type=EventType.DEADLINE_APPROACHING,
                    source_module=ModuleType.CALENDAR,
                    data={
                        "event": event,
                        "days_until": days_until,
                        "is_critical": days_until <= 3
                    },
                    user_id=user_id,
                    correlation_id=workflow_id
                ))
        
        workflow["status"] = "completed"
    
    async def _workflow_full_sync(self, workflow_id: str, data: dict, user_id: str):
        """Synchronize all modules with current state."""
        workflow = self.active_workflows[workflow_id]
        
        await self.emit(BrainEvent(
            event_type=EventType.BRAIN_SYNC,
            source_module=ModuleType.CONTEXT,
            data={"full_state": self.shared_state},
            user_id=user_id,
            correlation_id=workflow_id
        ))
        
        workflow["status"] = "completed"
    
    # =========================================================================
    # Intelligence Features
    # =========================================================================
    
    def get_system_status(self) -> dict:
        """Get full brain status."""
        return {
            "brain_active": True,
            "modules_connected": len(self.modules),
            "modules": self.list_modules(),
            "websocket_clients": len(self.websocket_clients),
            "active_workflows": len(self.active_workflows),
            "event_history_size": len(self.event_history),
            "state_keys": list(self.shared_state.keys()),
            "intensity": self.shared_state.get("intensity", 0)
        }
    
    def get_recent_events(self, limit: int = 50) -> List[dict]:
        """Get recent brain events."""
        return [e.to_dict() for e in self.event_history[-limit:]]
    
    async def think(self, context: dict) -> dict:
        """
        The brain "thinks" about the current context and suggests actions.
        This is the AI decision-making core.
        """
        suggestions = []
        
        # Check for missing critical items
        if not self.shared_state.get("documents"):
            suggestions.append({
                "priority": "high",
                "action": "upload_documents",
                "message": "Upload your eviction documents to get started"
            })
        
        # Check for approaching deadlines
        intensity = self.shared_state.get("intensity", 0)
        if intensity > 0.7:
            suggestions.append({
                "priority": "critical",
                "action": "check_deadlines",
                "message": "You have critical deadlines approaching!"
            })
        
        # Suggest defenses if case data exists
        case = self.shared_state.get("case", {})
        if case and not self.shared_state.get("defenses"):
            suggestions.append({
                "priority": "medium",
                "action": "analyze_defenses",
                "message": "Let's identify your legal defenses"
            })
        
        return {
            "suggestions": suggestions,
            "intensity": intensity,
            "modules_ready": len(self.modules),
            "context": context
        }


# Global brain instance
brain = PositronicBrain()


def get_brain() -> PositronicBrain:
    """Get the singleton brain instance."""
    return brain
