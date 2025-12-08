"""
Module Hub - Bidirectional Communication System for All Modules
==============================================================

This is the CENTRAL NERVOUS SYSTEM that connects all modules:
- Document Intake → Creates Info Packs → Routes to appropriate modules
- Modules can REQUEST data from the hub
- Modules can SEND updates back to the hub
- All communication is logged and traceable

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                         MODULE HUB                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Info Packs  │ ←→ │  Data Store  │ ←→ │  Event Bus   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         ↓                   ↕                   ↓               │
│  ┌──────────────────────────────────────────────────────┐      │
│  │                 MODULE REGISTRY                       │      │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │      │
│  │  │Eviction │ │Timeline │ │Calendar │ │  Vault  │    │      │
│  │  │ Defense │ │  Engine │ │ Tracker │ │ Storage │    │      │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
"""

import asyncio
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
from uuid import uuid4
import json

from app.core.event_bus import event_bus, EventType as BusEventType

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class ModuleType(str, Enum):
    """All registered module types"""
    EVICTION_DEFENSE = "eviction_defense"
    TIMELINE = "timeline"
    CALENDAR = "calendar"
    DOCUMENTS = "documents"
    VAULT = "vault"
    COPILOT = "copilot"
    FORMS = "forms"
    LAW_LIBRARY = "law_library"
    ZOOM_COURT = "zoom_court"
    CONTEXT_ENGINE = "context"
    ADAPTIVE_UI = "ui"
    COMPLAINT_WIZARD = "complaint_wizard"
    LOCATION = "location"
    HUD_FUNDING = "hud_funding"
    FRAUD_EXPOSURE = "fraud_exposure"
    PUBLIC_EXPOSURE = "public_exposure"
    RESEARCH = "research"
    LEGAL_TRAILS = "legal_trails"
    CUSTOM = "custom"  # For unknown/plugin modules


class DocumentCategory(str, Enum):
    """Document categories that trigger module routing"""
    EVICTION_NOTICE = "eviction_notice"
    LEASE = "lease"
    RENT_RECEIPT = "rent_receipt"
    REPAIR_REQUEST = "repair_request"
    COURT_SUMMONS = "court_summons"
    NOTICE_TO_QUIT = "notice_to_quit"
    PAY_OR_QUIT = "pay_or_quit"
    LEASE_VIOLATION = "lease_violation"
    COMMUNICATION = "communication"
    PHOTO_EVIDENCE = "photo_evidence"
    LEGAL_DOCUMENT = "legal_document"
    FINANCIAL = "financial"
    OTHER = "other"


class PackType(str, Enum):
    """Types of info packs"""
    EVICTION_CASE = "eviction_case"
    LEASE_INFO = "lease_info"
    PAYMENT_HISTORY = "payment_history"
    REPAIR_ISSUE = "repair_issue"
    COURT_CASE = "court_case"
    TIMELINE_EVENTS = "timeline_events"
    CALENDAR_DEADLINES = "calendar_deadlines"
    DOCUMENT_ANALYSIS = "document_analysis"
    COMPLAINT_FILING = "complaint_filing"
    LOCATION_DATA = "location_data"
    HUD_FUNDING_INFO = "hud_funding_info"
    CASE_CONTEXT = "case_context"
    FRAUD_ANALYSIS = "fraud_analysis"


class RequestType(str, Enum):
    """Types of data requests modules can make"""
    GET_USER_DOCUMENTS = "get_user_documents"
    GET_DOCUMENT_BY_TYPE = "get_document_by_type"
    GET_TIMELINE_EVENTS = "get_timeline_events"
    GET_CALENDAR_DEADLINES = "get_calendar_deadlines"
    GET_CASE_INFO = "get_case_info"
    GET_LEASE_DATA = "get_lease_data"
    GET_PAYMENT_HISTORY = "get_payment_history"
    GET_LANDLORD_INFO = "get_landlord_info"
    GET_PROPERTY_INFO = "get_property_info"
    GET_APPLICABLE_LAWS = "get_applicable_laws"
    GET_USER_CONTEXT = "get_user_context"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class InfoPack:
    """
    An Info Pack - Pre-filled data bundle sent to modules.
    
    Created when document intake recognizes a document type
    and needs to initialize a module with relevant data.
    """
    id: str
    pack_type: PackType
    user_id: str
    source_document_id: Optional[str] = None
    target_module: Optional[ModuleType] = None
    
    # The actual data payload
    data: Dict[str, Any] = field(default_factory=dict)
    
    # What data is available vs what user needs to provide
    auto_filled: Dict[str, Any] = field(default_factory=dict)
    user_required: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    
    # Status tracking
    status: str = "pending"  # pending, sent, received, processed, failed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    
    # Confidence scores for auto-filled data
    confidence: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pack_type": self.pack_type.value,
            "user_id": self.user_id,
            "source_document_id": self.source_document_id,
            "target_module": self.target_module.value if self.target_module else None,
            "data": self.data,
            "auto_filled": self.auto_filled,
            "user_required": self.user_required,
            "optional_fields": self.optional_fields,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "InfoPack":
        data["pack_type"] = PackType(data["pack_type"])
        if data.get("target_module"):
            data["target_module"] = ModuleType(data["target_module"])
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("processed_at") and isinstance(data["processed_at"], str):
            data["processed_at"] = datetime.fromisoformat(data["processed_at"])
        return cls(**data)


@dataclass
class DataRequest:
    """
    A data request from a module to the hub.
    
    Modules use this to request data they need from the central system.
    """
    id: str
    request_type: RequestType
    requesting_module: ModuleType
    user_id: str
    
    # Request parameters
    params: Dict[str, Any] = field(default_factory=dict)
    
    # Response
    response_data: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_type": self.request_type.value,
            "requesting_module": self.requesting_module.value,
            "user_id": self.user_id,
            "params": self.params,
            "response_data": self.response_data,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ModuleUpdate:
    """
    An update from a module back to the hub.
    
    Modules send these when they have new data to share
    with other modules or the main application.
    """
    id: str
    source_module: ModuleType
    user_id: str
    update_type: str
    
    # The update data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Optional: which modules should receive this update
    target_modules: List[ModuleType] = field(default_factory=list)
    
    # Broadcast to all modules?
    broadcast: bool = False
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_module": self.source_module.value,
            "user_id": self.user_id,
            "update_type": self.update_type,
            "data": self.data,
            "target_modules": [m.value for m in self.target_modules],
            "broadcast": self.broadcast,
            "created_at": self.created_at.isoformat(),
        }


@dataclass 
class RegisteredModule:
    """A registered module in the hub"""
    module_type: ModuleType
    name: str
    description: str
    
    # What document types this module handles
    handles_documents: List[DocumentCategory] = field(default_factory=list)
    
    # What pack types this module accepts
    accepts_packs: List[PackType] = field(default_factory=list)
    
    # Callbacks
    on_pack_received: Optional[Callable] = None
    on_data_request: Optional[Callable] = None
    on_update_received: Optional[Callable] = None
    
    # Status
    active: bool = True
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# DOCUMENT ROUTING RULES
# =============================================================================

# Map document types to target modules and pack types
DOCUMENT_ROUTING = {
    DocumentCategory.EVICTION_NOTICE: {
        "target_module": ModuleType.EVICTION_DEFENSE,
        "pack_type": PackType.EVICTION_CASE,
        "priority": "critical",
        "auto_extract": [
            "landlord_name", "tenant_name", "property_address",
            "notice_date", "deadline_date", "reason", "amount_claimed"
        ],
        "user_required": [
            "county", "case_number"  # Often not on notice
        ],
    },
    DocumentCategory.COURT_SUMMONS: {
        "target_module": ModuleType.EVICTION_DEFENSE,
        "pack_type": PackType.COURT_CASE,
        "priority": "critical",
        "auto_extract": [
            "case_number", "hearing_date", "hearing_time", "court_location",
            "judge_name", "plaintiff", "defendant"
        ],
        "user_required": [],
    },
    DocumentCategory.NOTICE_TO_QUIT: {
        "target_module": ModuleType.EVICTION_DEFENSE,
        "pack_type": PackType.EVICTION_CASE,
        "priority": "critical",
        "auto_extract": [
            "landlord_name", "notice_date", "quit_date", "reason"
        ],
        "user_required": ["property_address"],
    },
    DocumentCategory.PAY_OR_QUIT: {
        "target_module": ModuleType.EVICTION_DEFENSE,
        "pack_type": PackType.EVICTION_CASE,
        "priority": "high",
        "auto_extract": [
            "amount_due", "due_date", "landlord_name"
        ],
        "user_required": ["property_address"],
    },
    DocumentCategory.LEASE: {
        "target_module": ModuleType.DOCUMENTS,  # Goes to vault, but extracts lease info
        "pack_type": PackType.LEASE_INFO,
        "priority": "medium",
        "auto_extract": [
            "landlord_name", "tenant_name", "property_address",
            "lease_start", "lease_end", "rent_amount", "security_deposit"
        ],
        "user_required": [],
    },
    DocumentCategory.RENT_RECEIPT: {
        "target_module": ModuleType.TIMELINE,
        "pack_type": PackType.PAYMENT_HISTORY,
        "priority": "low",
        "auto_extract": [
            "payment_date", "amount", "period_covered"
        ],
        "user_required": [],
    },
    DocumentCategory.REPAIR_REQUEST: {
        "target_module": ModuleType.TIMELINE,
        "pack_type": PackType.REPAIR_ISSUE,
        "priority": "medium",
        "auto_extract": [
            "issue_description", "request_date", "landlord_response"
        ],
        "user_required": ["issue_resolved"],
    },
}


# =============================================================================
# MODULE HUB
# =============================================================================

class ModuleHub:
    """
    The Module Hub - Central communication system for all modules.
    
    Responsibilities:
    1. Route documents to appropriate modules via Info Packs
    2. Handle data requests from modules
    3. Distribute updates between modules
    4. Maintain central data store for shared information
    5. Log all communications for debugging/auditing
    """
    
    _instance: Optional["ModuleHub"] = None
    
    def __new__(cls) -> "ModuleHub":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Always initialize _initialized before checking it
        if not hasattr(self, "_initialized"):
            self._initialized = False
        if self._initialized:
            return

        self._initialized = True
        
        # Module registry
        self._modules: Dict[ModuleType, RegisteredModule] = {}
        
        # Data stores (per user)
        self._user_data: Dict[str, Dict[str, Any]] = {}
        
        # Info pack storage
        self._info_packs: Dict[str, InfoPack] = {}
        
        # Request/update history
        self._requests: List[DataRequest] = []
        self._updates: List[ModuleUpdate] = []
        
        # Communication log
        self._comm_log: List[Dict] = []
        
        logger.info("🔄 Module Hub initialized")
    
    # =========================================================================
    # MODULE REGISTRATION
    # =========================================================================
    
    def register_module(
        self,
        module_type: Union[ModuleType, str],
        name: str,
        description: str = "",
        handles_documents: List[Union[DocumentCategory, str]] = [],
        accepts_packs: List[Union[PackType, str]] = [],
        on_pack_received: Callable = None,
        on_data_request: Callable = None,
        on_update_received: Callable = None,
    ) -> RegisteredModule:
        """Register a module with the hub"""
        # Convert string to enum if needed
        if isinstance(module_type, str):
            try:
                module_type = ModuleType(module_type)
            except ValueError:
                # Try to find by name
                module_type_lower = module_type.lower()
                for mt in ModuleType:
                    if mt.value == module_type_lower or mt.name.lower() == module_type_lower:
                        module_type = mt
                        break
                else:
                    # Create a pseudo-module type for unknown modules
                    logger.warning(f"Unknown module type: {module_type}, using CUSTOM")
                    module_type = ModuleType.CUSTOM
        
        # Convert document categories
        doc_categories = []
        for doc in (handles_documents or []):
            if isinstance(doc, str):
                try:
                    doc_categories.append(DocumentCategory(doc))
                except ValueError:
                    logger.warning(f"Unknown document category: {doc}")
            else:
                doc_categories.append(doc)
        
        # Convert pack types
        pack_types = []
        for pack in (accepts_packs or []):
            if isinstance(pack, str):
                try:
                    pack_types.append(PackType(pack))
                except ValueError:
                    logger.warning(f"Unknown pack type: {pack}")
            else:
                pack_types.append(pack)
        
        module = RegisteredModule(
            module_type=module_type,
            name=name,
            description=description,
            handles_documents=doc_categories,
            accepts_packs=pack_types,
            on_pack_received=on_pack_received,
            on_data_request=on_data_request,
            on_update_received=on_update_received,
        )

        self._modules[module_type] = module
        self._log_comm("register", module_type.value, {"name": name})
        logger.info(f"📦 Module registered: {name} ({module_type.value})")
        return module
    
    def get_module(self, module_type: ModuleType) -> Optional[RegisteredModule]:
        """Get a registered module"""
        return self._modules.get(module_type)
    
    def list_modules(self) -> List[Dict]:
        """List all registered modules"""
        return [
            {
                "type": m.module_type.value,
                "name": m.name,
                "active": m.active,
                "handles_documents": [d.value for d in m.handles_documents],
                "accepts_packs": [p.value for p in m.accepts_packs],
            }
            for m in self._modules.values()
        ]
    
    # =========================================================================
    # DOCUMENT ROUTING & INFO PACK CREATION
    # =========================================================================
    
    async def route_document(
        self,
        user_id: str,
        document_id: str,
        document_type: str,
        extracted_data: Dict[str, Any],
        confidence_scores: Dict[str, float] = None,
    ) -> Optional[InfoPack]:
        """
        Route a document to the appropriate module.
        
        Called by document pipeline after classification.
        Creates an Info Pack and sends it to the target module.
        """
        # Normalize document type
        try:
            doc_category = DocumentCategory(document_type.lower().replace(" ", "_"))
        except ValueError:
            doc_category = DocumentCategory.OTHER
        
        # Get routing rules
        routing = DOCUMENT_ROUTING.get(doc_category)
        if not routing:
            logger.info(f"No routing rule for document type: {doc_category}")
            return None
        
        # Create Info Pack
        pack = self._create_info_pack(
            user_id=user_id,
            document_id=document_id,
            doc_category=doc_category,
            routing=routing,
            extracted_data=extracted_data,
            confidence_scores=confidence_scores or {},
        )
        
        # Store pack
        self._info_packs[pack.id] = pack
        
        # Send to target module
        await self._send_pack_to_module(pack)
        
        # Log
        self._log_comm(
            "route_document",
            routing["target_module"].value,
            {
                "document_id": document_id,
                "pack_id": pack.id,
                "pack_type": pack.pack_type.value,
            },
            user_id=user_id,
        )
        
        logger.info(
            f"📨 Document routed: {doc_category.value} → "
            f"{routing['target_module'].value} (pack: {pack.id})"
        )
        
        return pack
    
    def _create_info_pack(
        self,
        user_id: str,
        document_id: str,
        doc_category: DocumentCategory,
        routing: Dict,
        extracted_data: Dict[str, Any],
        confidence_scores: Dict[str, float],
    ) -> InfoPack:
        """Create an Info Pack from extracted document data"""
        
        pack_id = f"pack_{uuid4().hex[:12]}"
        
        # Separate auto-filled from user-required
        auto_filled = {}
        for field in routing.get("auto_extract", []):
            if field in extracted_data:
                auto_filled[field] = extracted_data[field]
        
        # Get existing user data if available
        user_store = self._get_user_store(user_id)
        
        # Merge with existing data (don't overwrite if already have good data)
        for field, value in auto_filled.items():
            existing = user_store.get(field)
            existing_conf = user_store.get(f"{field}_confidence", 0)
            new_conf = confidence_scores.get(field, 0.5)
            
            if not existing or new_conf > existing_conf:
                user_store[field] = value
                user_store[f"{field}_confidence"] = new_conf
        
        # Build complete data package
        pack_data = {
            **auto_filled,
            "document_id": document_id,
            "document_type": doc_category.value,
            "priority": routing.get("priority", "medium"),
        }
        
        # Add any additional context from user store
        context_fields = [
            "landlord_name", "tenant_name", "property_address",
            "lease_start", "lease_end", "rent_amount"
        ]
        for field in context_fields:
            if field not in pack_data and field in user_store:
                pack_data[field] = user_store[field]
        
        return InfoPack(
            id=pack_id,
            pack_type=routing["pack_type"],
            user_id=user_id,
            source_document_id=document_id,
            target_module=routing["target_module"],
            data=pack_data,
            auto_filled=auto_filled,
            user_required=routing.get("user_required", []),
            optional_fields=routing.get("optional_fields", []),
            confidence=confidence_scores,
        )
    
    async def _send_pack_to_module(self, pack: InfoPack):
        """Send an Info Pack to its target module"""
        if not pack.target_module:
            return
        
        module = self._modules.get(pack.target_module)
        if not module:
            logger.warning(f"Target module not registered: {pack.target_module}")
            pack.status = "failed"
            return
        
        pack.status = "sent"
        
        # Call module's pack handler if registered
        if module.on_pack_received:
            try:
                if asyncio.iscoroutinefunction(module.on_pack_received):
                    await module.on_pack_received(pack)
                else:
                    module.on_pack_received(pack)
                pack.status = "received"
            except Exception as e:
                logger.error(f"Error sending pack to {pack.target_module}: {e}")
                pack.status = "failed"
        
        # Also publish to event bus
        await event_bus.publish(
            BusEventType.NOTIFICATION,
            {
                "type": "info_pack",
                "pack_id": pack.id,
                "pack_type": pack.pack_type.value,
                "target_module": pack.target_module.value,
                "priority": pack.data.get("priority", "medium"),
            },
            source="module_hub",
            user_id=pack.user_id,
        )
    
    # =========================================================================
    # DATA REQUESTS (Module → Hub)
    # =========================================================================
    
    async def request_data(
        self,
        requesting_module: ModuleType,
        request_type: RequestType,
        user_id: str,
        params: Dict[str, Any] = None,
    ) -> DataRequest:
        """
        Handle a data request from a module.
        
        Modules call this to get data they need from the hub.
        """
        request = DataRequest(
            id=f"req_{uuid4().hex[:12]}",
            request_type=request_type,
            requesting_module=requesting_module,
            user_id=user_id,
            params=params or {},
        )
        
        self._requests.append(request)
        
        # Process the request
        try:
            request.status = "processing"
            response = await self._process_request(request)
            request.response_data = response
            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            request.status = "failed"
            request.error = str(e)
            logger.error(f"Request failed: {e}")
        
        self._log_comm(
            "data_request",
            requesting_module.value,
            {
                "request_type": request_type.value,
                "status": request.status,
            },
            user_id=user_id,
        )
        
        return request
    
    async def _process_request(self, request: DataRequest) -> Dict[str, Any]:
        """Process a data request and return response data"""
        user_store = self._get_user_store(request.user_id)
        params = request.params
        
        handlers = {
            RequestType.GET_USER_DOCUMENTS: self._get_user_documents,
            RequestType.GET_DOCUMENT_BY_TYPE: self._get_document_by_type,
            RequestType.GET_TIMELINE_EVENTS: self._get_timeline_events,
            RequestType.GET_CALENDAR_DEADLINES: self._get_calendar_deadlines,
            RequestType.GET_CASE_INFO: self._get_case_info,
            RequestType.GET_LEASE_DATA: self._get_lease_data,
            RequestType.GET_PAYMENT_HISTORY: self._get_payment_history,
            RequestType.GET_LANDLORD_INFO: self._get_landlord_info,
            RequestType.GET_PROPERTY_INFO: self._get_property_info,
            RequestType.GET_APPLICABLE_LAWS: self._get_applicable_laws,
            RequestType.GET_USER_CONTEXT: self._get_user_context,
        }
        
        handler = handlers.get(request.request_type)
        if handler:
            return await handler(request.user_id, params)
        
        return {"error": f"Unknown request type: {request.request_type}"}
    
    async def _get_user_documents(self, user_id: str, params: Dict) -> Dict:
        """Get all documents for a user"""
        try:
            from app.services.document_pipeline import get_document_pipeline
            pipeline = get_document_pipeline()
            docs = pipeline.get_user_documents(user_id)
            return {
                "documents": [d.to_dict() for d in docs],
                "count": len(docs),
            }
        except Exception as e:
            return {"documents": [], "error": str(e)}
    
    async def _get_document_by_type(self, user_id: str, params: Dict) -> Dict:
        """Get documents filtered by type"""
        doc_type = params.get("type")
        try:
            from app.services.document_pipeline import get_document_pipeline
            from app.services.azure_ai import DocumentType
            pipeline = get_document_pipeline()
            docs = pipeline.get_user_documents_by_type(user_id, DocumentType(doc_type))
            return {
                "documents": [d.to_dict() for d in docs],
                "count": len(docs),
            }
        except Exception as e:
            return {"documents": [], "error": str(e)}
    
    async def _get_timeline_events(self, user_id: str, params: Dict) -> Dict:
        """Get timeline events for a user"""
        try:
            from app.services.document_pipeline import get_document_pipeline
            pipeline = get_document_pipeline()
            timeline = pipeline.get_timeline(user_id)
            return {
                "events": timeline,
                "count": len(timeline),
            }
        except Exception as e:
            return {"events": [], "error": str(e)}
    
    async def _get_calendar_deadlines(self, user_id: str, params: Dict) -> Dict:
        """Get calendar deadlines for a user"""
        user_store = self._get_user_store(user_id)
        deadlines = user_store.get("deadlines", [])
        return {
            "deadlines": deadlines,
            "count": len(deadlines),
        }
    
    async def _get_case_info(self, user_id: str, params: Dict) -> Dict:
        """Get eviction case info for a user"""
        user_store = self._get_user_store(user_id)
        case_fields = [
            "case_number", "hearing_date", "hearing_time", "court_location",
            "judge_name", "answer_deadline", "case_type", "filing_date"
        ]
        case_info = {k: user_store.get(k) for k in case_fields if k in user_store}
        return case_info
    
    async def _get_lease_data(self, user_id: str, params: Dict) -> Dict:
        """Get lease information for a user"""
        user_store = self._get_user_store(user_id)
        lease_fields = [
            "lease_start", "lease_end", "rent_amount", "security_deposit",
            "landlord_name", "property_address", "lease_terms"
        ]
        lease_data = {k: user_store.get(k) for k in lease_fields if k in user_store}
        return lease_data
    
    async def _get_payment_history(self, user_id: str, params: Dict) -> Dict:
        """Get payment history for a user"""
        user_store = self._get_user_store(user_id)
        return {
            "payments": user_store.get("payment_history", []),
        }
    
    async def _get_landlord_info(self, user_id: str, params: Dict) -> Dict:
        """Get landlord information"""
        user_store = self._get_user_store(user_id)
        landlord_fields = [
            "landlord_name", "landlord_address", "landlord_phone",
            "landlord_email", "property_manager"
        ]
        return {k: user_store.get(k) for k in landlord_fields if k in user_store}
    
    async def _get_property_info(self, user_id: str, params: Dict) -> Dict:
        """Get property information"""
        user_store = self._get_user_store(user_id)
        property_fields = [
            "property_address", "unit_number", "property_type",
            "move_in_date", "move_out_date"
        ]
        return {k: user_store.get(k) for k in property_fields if k in user_store}
    
    async def _get_applicable_laws(self, user_id: str, params: Dict) -> Dict:
        """Get applicable laws for user's situation"""
        user_store = self._get_user_store(user_id)
        try:
            from app.services.law_engine import get_law_engine
            law_engine = get_law_engine()
            
            # Get laws based on document types and issues
            context = {
                "document_types": user_store.get("document_types", []),
                "issues": user_store.get("active_issues", []),
                "county": user_store.get("county", "Dakota"),
            }
            
            # TODO: Query law engine
            return {"laws": [], "context": context}
        except Exception as e:
            return {"laws": [], "error": str(e)}
    
    async def _get_user_context(self, user_id: str, params: Dict) -> Dict:
        """Get full user context from context loop"""
        try:
            from app.services.context_loop import context_loop
            return context_loop.get_state(user_id)
        except Exception as e:
            return {"error": str(e)}
    
    # =========================================================================
    # MODULE UPDATES (Module → Hub → Other Modules)
    # =========================================================================
    
    async def send_update(
        self,
        source_module: ModuleType,
        user_id: str,
        update_type: str,
        data: Dict[str, Any],
        target_modules: List[ModuleType] = None,
        broadcast: bool = False,
    ) -> ModuleUpdate:
        """
        Send an update from a module to other modules.
        
        Modules call this to share new data or state changes.
        """
        update = ModuleUpdate(
            id=f"upd_{uuid4().hex[:12]}",
            source_module=source_module,
            user_id=user_id,
            update_type=update_type,
            data=data,
            target_modules=target_modules or [],
            broadcast=broadcast,
        )
        
        self._updates.append(update)
        
        # Update user store if applicable
        self._apply_update_to_store(user_id, update)
        
        # Route to target modules
        await self._route_update(update)
        
        self._log_comm(
            "module_update",
            source_module.value,
            {
                "update_type": update_type,
                "targets": [m.value for m in (target_modules or [])],
                "broadcast": broadcast,
            },
            user_id=user_id,
        )
        
        return update
    
    def _apply_update_to_store(self, user_id: str, update: ModuleUpdate):
        """Apply an update to the user's data store"""
        user_store = self._get_user_store(user_id)
        
        # Merge data into user store
        for key, value in update.data.items():
            if key.endswith("_list"):
                # Append to list
                base_key = key.replace("_list", "")
                if base_key not in user_store:
                    user_store[base_key] = []
                if isinstance(value, list):
                    user_store[base_key].extend(value)
                else:
                    user_store[base_key].append(value)
            else:
                # Overwrite value
                user_store[key] = value
    
    async def _route_update(self, update: ModuleUpdate):
        """Route an update to target modules"""
        targets = update.target_modules if not update.broadcast else list(self._modules.keys())
        
        for module_type in targets:
            if module_type == update.source_module:
                continue  # Don't send back to source
            
            module = self._modules.get(module_type)
            if module and module.on_update_received:
                try:
                    if asyncio.iscoroutinefunction(module.on_update_received):
                        await module.on_update_received(update)
                    else:
                        module.on_update_received(update)
                except Exception as e:
                    logger.error(f"Error routing update to {module_type}: {e}")
    
    # =========================================================================
    # USER DATA STORE
    # =========================================================================
    
    def _get_user_store(self, user_id: str) -> Dict[str, Any]:
        """Get or create user data store"""
        if user_id not in self._user_data:
            self._user_data[user_id] = {}
        return self._user_data[user_id]
    
    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Public method to get user data"""
        return self._get_user_store(user_id).copy()
    
    def set_user_data(self, user_id: str, key: str, value: Any):
        """Set a value in user data store"""
        user_store = self._get_user_store(user_id)
        user_store[key] = value
    
    def update_user_data(self, user_id: str, data: Dict[str, Any]):
        """Update multiple values in user data store"""
        user_store = self._get_user_store(user_id)
        user_store.update(data)
    
    # =========================================================================
    # INFO PACK MANAGEMENT
    # =========================================================================
    
    def get_info_pack(self, pack_id: str) -> Optional[InfoPack]:
        """Get an info pack by ID"""
        return self._info_packs.get(pack_id)
    
    def get_user_packs(self, user_id: str) -> List[InfoPack]:
        """Get all info packs for a user"""
        return [p for p in self._info_packs.values() if p.user_id == user_id]
    
    def get_pending_packs(self, user_id: str) -> List[InfoPack]:
        """Get pending info packs requiring user input"""
        return [
            p for p in self._info_packs.values()
            if p.user_id == user_id and p.user_required and p.status != "processed"
        ]
    
    async def complete_pack(
        self,
        pack_id: str,
        user_provided_data: Dict[str, Any],
    ) -> Optional[InfoPack]:
        """
        Complete an info pack with user-provided data.
        
        Called when user fills in required fields.
        """
        pack = self._info_packs.get(pack_id)
        if not pack:
            return None
        
        # Merge user data
        pack.data.update(user_provided_data)
        
        # Update user store
        user_store = self._get_user_store(pack.user_id)
        user_store.update(user_provided_data)
        
        # Mark as processed
        pack.status = "processed"
        pack.processed_at = datetime.now(timezone.utc)
        
        # Notify target module
        await self._send_pack_to_module(pack)
        
        logger.info(f"✅ Info pack completed: {pack_id}")
        
        return pack
    
    # =========================================================================
    # LOGGING & DEBUGGING
    # =========================================================================
    
    def _log_comm(
        self,
        action: str,
        module: str,
        details: Dict,
        user_id: str = None,
    ):
        """Log a communication event"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "module": module,
            "details": details,
            "user_id": user_id,
        }
        self._comm_log.append(entry)
        
        # Keep last 1000 entries
        if len(self._comm_log) > 1000:
            self._comm_log = self._comm_log[-1000:]
    
    def get_comm_log(
        self,
        user_id: str = None,
        module: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get communication log"""
        log = self._comm_log
        
        if user_id:
            log = [e for e in log if e.get("user_id") == user_id]
        
        if module:
            log = [e for e in log if e.get("module") == module]
        
        return log[-limit:]
    
    def get_hub_status(self) -> Dict:
        """Get hub status and statistics"""
        return {
            "modules_registered": len(self._modules),
            "modules": self.list_modules(),
            "users_tracked": len(self._user_data),
            "info_packs_total": len(self._info_packs),
            "info_packs_pending": len([p for p in self._info_packs.values() if p.status == "pending"]),
            "requests_total": len(self._requests),
            "updates_total": len(self._updates),
            "comm_log_entries": len(self._comm_log),
        }


# =============================================================================
# GLOBAL INSTANCE & CONVENIENCE FUNCTIONS
# =============================================================================

# Global singleton
module_hub = ModuleHub()


def get_module_hub() -> ModuleHub:
    """Get the module hub instance"""
    return module_hub


async def route_document_to_module(
    user_id: str,
    document_id: str,
    document_type: str,
    extracted_data: Dict[str, Any],
    confidence_scores: Dict[str, float] = None,
) -> Optional[InfoPack]:
    """Convenience function to route a document"""
    return await module_hub.route_document(
        user_id, document_id, document_type, extracted_data, confidence_scores
    )


async def request_module_data(
    requesting_module: ModuleType,
    request_type: RequestType,
    user_id: str,
    params: Dict[str, Any] = None,
) -> DataRequest:
    """Convenience function to request data"""
    return await module_hub.request_data(
        requesting_module, request_type, user_id, params
    )


async def send_module_update(
    source_module: ModuleType,
    user_id: str,
    update_type: str,
    data: Dict[str, Any],
    target_modules: List[ModuleType] = None,
    broadcast: bool = False,
) -> ModuleUpdate:
    """Convenience function to send an update"""
    return await module_hub.send_update(
        source_module, user_id, update_type, data, target_modules, broadcast
    )
