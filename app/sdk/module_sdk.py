"""
Semptify Module SDK
===================

This SDK provides everything a new module needs to integrate with
the Semptify Positronic Mesh (Workflow Orchestration Engine).

REQUIREMENTS FOR NEW MODULES:
-----------------------------
1. Import this SDK
2. Create a ModuleDefinition
3. Register actions the module can perform
4. Handle incoming requests from the mesh

EXAMPLE USAGE:
--------------
```python
from app.sdk.module_sdk import (
    ModuleSDK,
    ModuleDefinition,
    ActionDefinition,
    ModuleCategory,
)

# 1. Define your module
my_module = ModuleDefinition(
    name="my_new_module",
    display_name="My New Module",
    description="Does amazing things",
    version="1.0.0",
    category=ModuleCategory.UTILITY,
)

# 2. Create SDK instance
sdk = ModuleSDK(my_module)

# 3. Register actions
@sdk.action("do_something", produces=["result_data"])
async def do_something(user_id: str, params: dict, context: dict):
    # Your logic here
    return {"result_data": "success"}

# 4. Initialize (call on startup)
sdk.initialize()
```
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union
import asyncio
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# MODULE CATEGORIES
# =============================================================================

class ModuleCategory(str, Enum):
    """Categories for organizing modules"""
    DOCUMENT = "document"          # Document processing
    LEGAL = "legal"                # Legal analysis/forms
    CALENDAR = "calendar"          # Scheduling/deadlines
    COMMUNICATION = "communication"  # User communication
    ANALYSIS = "analysis"          # Data analysis
    STORAGE = "storage"            # File/data storage
    UI = "ui"                      # User interface
    UTILITY = "utility"            # General utilities
    AI = "ai"                      # AI/ML features
    INTEGRATION = "integration"    # External integrations


class DocumentType(str, Enum):
    """Document types a module can handle"""
    EVICTION_NOTICE = "eviction_notice"
    LEASE = "lease"
    COURT_FILING = "court_filing"
    PAYMENT_RECORD = "payment_record"
    COMMUNICATION = "communication"
    PHOTO = "photo"
    LEGAL_FORM = "legal_form"
    ID_DOCUMENT = "id_document"
    UNKNOWN = "unknown"


class PackType(str, Enum):
    """Info pack types for module communication"""
    EVICTION_DATA = "eviction_data"
    LEASE_DATA = "lease_data"
    DEADLINE_DATA = "deadline_data"
    CASE_DATA = "case_data"
    USER_DATA = "user_data"
    FORM_DATA = "form_data"
    ANALYSIS_RESULT = "analysis_result"
    CUSTOM = "custom"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ActionDefinition:
    """Defines an action a module can perform"""
    name: str
    handler: Callable
    description: str = ""
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)  # Context keys this produces
    requires_context: List[str] = field(default_factory=list)  # Context keys needed
    is_async: bool = True
    timeout_seconds: int = 30


@dataclass
class ModuleDefinition:
    """Defines a module's identity and capabilities"""
    name: str                      # Unique identifier (snake_case)
    display_name: str              # Human-readable name
    description: str               # What this module does
    version: str = "1.0.0"
    category: ModuleCategory = ModuleCategory.UTILITY
    
    # Document handling capabilities
    handles_documents: List[DocumentType] = field(default_factory=list)
    
    # Info pack capabilities
    accepts_packs: List[PackType] = field(default_factory=list)
    produces_packs: List[PackType] = field(default_factory=list)
    
    # Dependencies on other modules
    depends_on: List[str] = field(default_factory=list)
    
    # Optional capabilities
    has_ui: bool = False
    has_background_tasks: bool = False
    requires_auth: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "category": self.category.value,
            "handles_documents": [d.value for d in self.handles_documents],
            "accepts_packs": [p.value for p in self.accepts_packs],
            "produces_packs": [p.value for p in self.produces_packs],
            "depends_on": self.depends_on,
            "has_ui": self.has_ui,
            "has_background_tasks": self.has_background_tasks,
            "requires_auth": self.requires_auth,
        }


@dataclass
class InfoPack:
    """Data package for inter-module communication"""
    id: str
    pack_type: PackType
    source_module: str
    target_module: Optional[str]  # None = broadcast
    user_id: str
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    priority: int = 5  # 1-10, higher = more urgent
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pack_type": self.pack_type.value,
            "source_module": self.source_module,
            "target_module": self.target_module,
            "user_id": self.user_id,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "priority": self.priority,
        }


@dataclass
class ModuleRequest:
    """Request from one module to another"""
    id: str
    from_module: str
    to_module: str
    action: str
    params: Dict[str, Any]
    user_id: str
    callback: Optional[str] = None  # Action to call with response
    timeout_seconds: int = 30
    created_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# MODULE SDK - THE MAIN CLASS NEW MODULES USE
# =============================================================================

class ModuleSDK:
    """
    SDK for integrating a module with the Semptify Positronic Mesh.
    
    This is the ONLY thing new modules need to import to integrate
    with the entire Semptify ecosystem.
    """
    
    def __init__(self, definition: ModuleDefinition):
        self.definition = definition
        self.actions: Dict[str, ActionDefinition] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self._initialized = False
        self._mesh = None
        self._hub = None
        
        logger.info(f"📦 ModuleSDK created for: {definition.name}")
    
    # =========================================================================
    # ACTION REGISTRATION (Decorator-based)
    # =========================================================================
    
    def action(
        self,
        name: str,
        description: str = "",
        required_params: List[str] = None,
        optional_params: List[str] = None,
        produces: List[str] = None,
        requires_context: List[str] = None,
        timeout_seconds: int = 30,
    ):
        """
        Decorator to register an action handler.
        
        Usage:
            @sdk.action("my_action", produces=["output_key"])
            async def my_action(user_id, params, context):
                return {"output_key": "value"}
        """
        def decorator(func: Callable):
            # Wrap sync functions to be async
            if not asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                handler = async_wrapper
            else:
                handler = func
            
            action_def = ActionDefinition(
                name=name,
                handler=handler,
                description=description or func.__doc__ or "",
                required_params=required_params or [],
                optional_params=optional_params or [],
                produces=produces or [],
                requires_context=requires_context or [],
                is_async=True,
                timeout_seconds=timeout_seconds,
            )
            
            self.actions[name] = action_def
            logger.debug(f"   ⚡ Registered action: {self.definition.name}.{name}")
            
            return handler
        
        return decorator
    
    def register_action(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        produces: List[str] = None,
    ):
        """
        Programmatically register an action (alternative to decorator).
        """
        self.action(name, description, produces=produces)(handler)
    
    # =========================================================================
    # EVENT HANDLING
    # =========================================================================
    
    def on_event(self, event_type: str):
        """
        Decorator to handle mesh events.
        
        Usage:
            @sdk.on_event("workflow_started")
            async def handle_workflow(event_type, data):
                print(f"Workflow started: {data}")
        """
        def decorator(func: Callable):
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
            self.event_handlers[event_type].append(func)
            return func
        return decorator
    
    # =========================================================================
    # INFO PACK OPERATIONS
    # =========================================================================
    
    def create_pack(
        self,
        pack_type: PackType,
        user_id: str,
        data: Dict[str, Any],
        target_module: Optional[str] = None,
        priority: int = 5,
    ) -> InfoPack:
        """Create and send an info pack to another module or broadcast"""
        pack = InfoPack(
            id=f"pack_{uuid.uuid4().hex[:12]}",
            pack_type=pack_type,
            source_module=self.definition.name,
            target_module=target_module,
            user_id=user_id,
            data=data,
            priority=priority,
        )
        
        # Send to hub if initialized
        if self._hub:
            self._hub.create_info_pack(
                source_module=self.definition.name,
                pack_type=pack_type.value,
                data=data,
                user_id=user_id,
                target_module=target_module,
            )
        
        logger.info(f"📤 {self.definition.name} created pack: {pack_type.value}")
        return pack
    
    async def request_data(
        self,
        from_module: str,
        data_keys: List[str],
        user_id: str,
    ) -> Dict[str, Any]:
        """Request specific data from another module"""
        if self._hub:
            return self._hub.request_data(
                requesting_module=self.definition.name,
                target_module=from_module,
                data_keys=data_keys,
                user_id=user_id,
            )
        return {}
    
    # =========================================================================
    # WORKFLOW TRIGGERS
    # =========================================================================
    
    async def trigger_workflow(
        self,
        workflow_type: str,
        user_id: str,
        initial_context: Dict[str, Any] = None,
    ):
        """Trigger a workflow from this module"""
        if self._mesh:
            from app.core.positronic_mesh import WorkflowType
            try:
                wf_type = WorkflowType(workflow_type)
                return await self._mesh.start_workflow(
                    workflow_type=wf_type,
                    user_id=user_id,
                    trigger=f"module:{self.definition.name}",
                    initial_context=initial_context or {},
                )
            except ValueError:
                logger.error(f"Unknown workflow type: {workflow_type}")
        return None
    
    async def invoke_action(
        self,
        module: str,
        action: str,
        user_id: str,
        params: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Invoke an action on another module"""
        if self._mesh:
            return await self._mesh.invoke_module(
                module=module,
                action=action,
                user_id=user_id,
                params=params or {},
            )
        return {}
    
    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    
    def initialize(self):
        """
        Initialize the module and register with the Positronic Mesh.
        Call this on application startup.
        """
        if self._initialized:
            logger.warning(f"Module {self.definition.name} already initialized")
            return
        
        # Import the core systems
        try:
            from app.core.positronic_mesh import positronic_mesh
            from app.core.module_hub import module_hub
            
            self._mesh = positronic_mesh
            self._hub = module_hub
        except ImportError as e:
            logger.warning(f"Could not import core systems: {e}")
        
        # Register module with hub
        if self._hub:
            self._hub.register_module(
                module_type=self.definition.name,
                name=self.definition.display_name,
                description=self.definition.description,
                handles_documents=[d.value for d in self.definition.handles_documents],
                accepts_packs=[p.value for p in self.definition.accepts_packs],
            )
        
        # Register actions with mesh
        if self._mesh:
            for action_name, action_def in self.actions.items():
                self._mesh.register_action(
                    module=self.definition.name,
                    action=action_name,
                    handler=action_def.handler,
                    description=action_def.description,
                    required_params=action_def.required_params,
                    optional_params=action_def.optional_params,
                    produces=action_def.produces,
                )
        
        # Register event handlers
        if self._mesh:
            for event_type, handlers in self.event_handlers.items():
                for handler in handlers:
                    self._mesh.subscribe(event_type, handler)
        
        self._initialized = True
        logger.info(f"✅ Module initialized: {self.definition.name} ({len(self.actions)} actions)")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current module status"""
        return {
            "name": self.definition.name,
            "display_name": self.definition.display_name,
            "version": self.definition.version,
            "initialized": self._initialized,
            "actions": list(self.actions.keys()),
            "event_handlers": list(self.event_handlers.keys()),
            "connected_to_mesh": self._mesh is not None,
            "connected_to_hub": self._hub is not None,
        }


# =============================================================================
# BASE MODULE CLASS (Alternative approach using inheritance)
# =============================================================================

class BaseModule(ABC):
    """
    Abstract base class for modules preferring inheritance over SDK.
    
    Usage:
        class MyModule(BaseModule):
            def __init__(self):
                super().__init__(
                    name="my_module",
                    display_name="My Module",
                    description="Does things",
                )
            
            def register_actions(self):
                self.sdk.register_action("do_thing", self.do_thing)
            
            async def do_thing(self, user_id, params, context):
                return {"result": "done"}
    """
    
    def __init__(
        self,
        name: str,
        display_name: str,
        description: str,
        version: str = "1.0.0",
        category: ModuleCategory = ModuleCategory.UTILITY,
        **kwargs,
    ):
        self.definition = ModuleDefinition(
            name=name,
            display_name=display_name,
            description=description,
            version=version,
            category=category,
            **kwargs,
        )
        self.sdk = ModuleSDK(self.definition)
    
    @abstractmethod
    def register_actions(self):
        """Override to register module actions"""
        pass
    
    def initialize(self):
        """Initialize the module"""
        self.register_actions()
        self.sdk.initialize()
    
    def get_sdk(self) -> ModuleSDK:
        """Get the underlying SDK instance"""
        return self.sdk


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_module(
    name: str,
    display_name: str,
    description: str,
    category: ModuleCategory = ModuleCategory.UTILITY,
    handles_documents: List[DocumentType] = None,
    accepts_packs: List[PackType] = None,
    **kwargs,
) -> ModuleSDK:
    """
    Quick helper to create a module SDK instance.
    
    Usage:
        sdk = create_module(
            "my_module",
            "My Module",
            "Does amazing things",
            handles_documents=[DocumentType.LEASE],
        )
    """
    definition = ModuleDefinition(
        name=name,
        display_name=display_name,
        description=description,
        category=category,
        handles_documents=handles_documents or [],
        accepts_packs=accepts_packs or [],
        **kwargs,
    )
    return ModuleSDK(definition)


# =============================================================================
# MODULE TEMPLATE GENERATOR
# =============================================================================

def generate_module_template(
    module_name: str,
    display_name: str,
    description: str,
    output_dir: str = None,
) -> str:
    """
    Generate a template file for a new module.
    Returns the template as a string (also writes to file if output_dir provided).
    """
    template = f'''"""
{display_name} Module
{"=" * (len(display_name) + 7)}

{description}

This module integrates with the Semptify Positronic Mesh for
workflow orchestration and inter-module communication.
"""

import logging
from typing import Any, Dict

from app.sdk.module_sdk import (
    ModuleSDK,
    ModuleDefinition,
    ModuleCategory,
    DocumentType,
    PackType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MODULE DEFINITION
# =============================================================================

module_definition = ModuleDefinition(
    name="{module_name}",
    display_name="{display_name}",
    description="{description}",
    version="1.0.0",
    category=ModuleCategory.UTILITY,  # Change as needed
    
    # Document types this module can process
    handles_documents=[
        # DocumentType.LEASE,
        # DocumentType.EVICTION_NOTICE,
    ],
    
    # Info pack types this module accepts
    accepts_packs=[
        # PackType.EVICTION_DATA,
        # PackType.USER_DATA,
    ],
    
    # Info pack types this module produces
    produces_packs=[
        # PackType.ANALYSIS_RESULT,
    ],
    
    # Other modules this depends on
    depends_on=[
        # "documents",
        # "calendar",
    ],
    
    has_ui=False,
    has_background_tasks=False,
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
    "example_action",
    description="An example action that does something",
    required_params=["input_data"],
    produces=["output_data"],
)
async def example_action(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Example action handler.
    
    Args:
        user_id: The user making the request
        params: Parameters passed to this action
        context: Shared workflow context
    
    Returns:
        Dictionary with output data (keys should match 'produces')
    """
    logger.info(f"{{module_definition.name}}: Processing for user {{user_id[:8]}}...")
    
    input_data = params.get("input_data", "")
    
    # Your logic here
    result = f"Processed: {{input_data}}"
    
    return {{
        "output_data": result,
        "processed_at": "now",
    }}


@sdk.action(
    "get_state",
    description="Get the current state of this module",
    produces=["{module_name}_state"],
)
async def get_state(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Return the current module state for sync operations"""
    return {{
        "{module_name}_state": {{
            "status": "active",
            "user_id": user_id,
        }}
    }}


# =============================================================================
# EVENT HANDLERS (Optional)
# =============================================================================

@sdk.on_event("workflow_started")
async def on_workflow_started(event_type: str, data: Dict[str, Any]):
    """Handle workflow started events"""
    logger.debug(f"{{module_definition.name}}: Workflow started - {{data.get('workflow_id')}}")


@sdk.on_event("workflow_completed")
async def on_workflow_completed(event_type: str, data: Dict[str, Any]):
    """Handle workflow completed events"""
    logger.debug(f"{{module_definition.name}}: Workflow completed - {{data.get('workflow_id')}}")


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize():
    """Initialize this module - call on application startup"""
    sdk.initialize()
    logger.info(f"✅ {{module_definition.display_name}} module ready")


# Export for easy importing
__all__ = ["sdk", "module_definition", "initialize"]
'''
    
    if output_dir:
        import os
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"{module_name}.py")
        with open(filepath, "w") as f:
            f.write(template)
        logger.info(f"📄 Generated module template: {filepath}")
    
    return template
