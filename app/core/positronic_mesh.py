"""
Positronic Mesh - Module Orchestration System
=============================================

The central nervous system that allows:
1. Main app to initialize and trigger module workflows
2. Modules to communicate bidirectionally with each other
3. Workflows to span multiple modules automatically
4. Real-time state synchronization across all modules

This is the "mesh" that connects everything - the Positronic Brain's neural pathways.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# WORKFLOW DEFINITIONS
# =============================================================================

class WorkflowType(str, Enum):
    """Pre-defined cross-module workflows"""
    # Document-triggered workflows
    EVICTION_DEFENSE = "eviction_defense"  # Document → Eviction → Calendar → Forms → Copilot
    LEASE_ANALYSIS = "lease_analysis"  # Document → Analysis → Timeline → Calendar
    COURT_PREP = "court_prep"  # Multiple docs → Case Builder → Forms → Zoom Court
    
    # User-initiated workflows
    DEADLINE_ALERT = "deadline_alert"  # Calendar → UI → Copilot
    CASE_STATUS = "case_status"  # All modules → Summary → UI
    DOCUMENT_REQUEST = "document_request"  # Copilot → Documents → User
    
    # System workflows
    FULL_SYNC = "full_sync"  # Sync all module states
    CONTEXT_UPDATE = "context_update"  # Update user context across modules
    EMERGENCY_MODE = "emergency_mode"  # Activate urgent response mode


class WorkflowStage(str, Enum):
    """Stages a workflow goes through"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    id: str
    module: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    requires_input: bool = False
    input_prompt: Optional[str] = None
    timeout_seconds: int = 30
    on_success: Optional[str] = None  # Next step ID
    on_failure: Optional[str] = None  # Fallback step ID
    
    # Runtime state
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Workflow:
    """A complete workflow spanning multiple modules"""
    id: str
    type: WorkflowType
    user_id: str
    trigger: str  # What triggered this workflow
    steps: List[WorkflowStep] = field(default_factory=list)
    current_step_index: int = 0
    stage: WorkflowStage = WorkflowStage.PENDING
    context: Dict[str, Any] = field(default_factory=dict)  # Shared across steps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "user_id": self.user_id,
            "trigger": self.trigger,
            "stage": self.stage.value,
            "current_step": self.current_step_index,
            "total_steps": len(self.steps),
            "steps": [
                {
                    "id": s.id,
                    "module": s.module,
                    "action": s.action,
                    "status": s.status,
                    "requires_input": s.requires_input,
                }
                for s in self.steps
            ],
            "context_keys": list(self.context.keys()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# =============================================================================
# MODULE ACTION HANDLERS
# =============================================================================

@dataclass
class ModuleAction:
    """Defines an action a module can perform"""
    module: str
    action: str
    handler: Callable
    description: str
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)  # Context keys this action produces


# =============================================================================
# POSITRONIC MESH - THE NEURAL NETWORK
# =============================================================================

class PositronicMesh:
    """
    The Positronic Mesh - Central orchestration for all modules.
    
    Think of this as the brain's neural pathways:
    - Modules are neurons
    - Workflows are neural pathways
    - Context is shared memory
    - Actions are synaptic signals
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Always initialize _initialized before checking it
        if not hasattr(self, "_initialized"):
            self._initialized = False
        if self._initialized:
            return

        self._initialized = True
        
        # Module action registry
        self.actions: Dict[str, Dict[str, ModuleAction]] = {}  # module -> action -> handler
        
        # Active workflows
        self.workflows: Dict[str, Workflow] = {}  # workflow_id -> Workflow
        self.user_workflows: Dict[str, List[str]] = {}  # user_id -> [workflow_ids]
        
        # Workflow templates
        self.workflow_templates: Dict[WorkflowType, List[Dict]] = {}
        
        # Event subscribers for real-time updates
        self.subscribers: Dict[str, Set[Callable]] = {}  # event_type -> callbacks
        
        # Module state cache
        self.module_states: Dict[str, Dict[str, Any]] = {}
        
        # Initialize workflow templates
        self._init_workflow_templates()
        
        logger.info("🧠 Positronic Mesh initialized - Neural pathways active")
    
    def _init_workflow_templates(self):
        """Define the standard workflow templates"""
        
        # Eviction Defense Workflow
        self.workflow_templates[WorkflowType.EVICTION_DEFENSE] = [
            {
                "module": "documents",
                "action": "extract_eviction_data",
                "produces": ["eviction_date", "landlord", "reason", "court_info"],
            },
            {
                "module": "calendar",
                "action": "calculate_deadlines",
                "produces": ["answer_deadline", "hearing_date", "critical_dates"],
            },
            {
                "module": "eviction_defense",
                "action": "analyze_defenses",
                "produces": ["available_defenses", "recommended_strategy"],
            },
            {
                "module": "forms",
                "action": "prepare_answer_form",
                "requires_input": True,
                "input_prompt": "Please confirm the information for your Answer form",
                "produces": ["answer_form_draft"],
            },
            {
                "module": "copilot",
                "action": "generate_guidance",
                "produces": ["next_steps", "recommendations"],
            },
            {
                "module": "ui",
                "action": "update_dashboard",
                "produces": ["ui_state"],
            },
        ]
        
        # Lease Analysis Workflow
        self.workflow_templates[WorkflowType.LEASE_ANALYSIS] = [
            {
                "module": "documents",
                "action": "extract_lease_terms",
                "produces": ["rent_amount", "lease_dates", "terms", "landlord_info"],
            },
            {
                "module": "law_library",
                "action": "check_lease_violations",
                "produces": ["violations", "tenant_rights"],
            },
            {
                "module": "timeline",
                "action": "create_lease_timeline",
                "produces": ["lease_events"],
            },
            {
                "module": "calendar",
                "action": "set_lease_reminders",
                "produces": ["reminders"],
            },
        ]
        
        # Court Preparation Workflow
        self.workflow_templates[WorkflowType.COURT_PREP] = [
            {
                "module": "eviction_defense",
                "action": "compile_case_info",
                "produces": ["case_summary", "evidence_list"],
            },
            {
                "module": "documents",
                "action": "gather_evidence",
                "produces": ["evidence_documents"],
            },
            {
                "module": "timeline",
                "action": "build_case_timeline",
                "produces": ["case_timeline"],
            },
            {
                "module": "forms",
                "action": "prepare_court_packet",
                "produces": ["court_packet"],
            },
            {
                "module": "zoom_court",
                "action": "prepare_virtual_hearing",
                "produces": ["hearing_prep"],
            },
            {
                "module": "copilot",
                "action": "generate_talking_points",
                "produces": ["talking_points", "objection_responses"],
            },
        ]
        
        # Full Context Sync Workflow
        self.workflow_templates[WorkflowType.FULL_SYNC] = [
            {"module": "documents", "action": "get_state", "produces": ["documents_state"]},
            {"module": "timeline", "action": "get_state", "produces": ["timeline_state"]},
            {"module": "calendar", "action": "get_state", "produces": ["calendar_state"]},
            {"module": "eviction_defense", "action": "get_state", "produces": ["eviction_state"]},
            {"module": "context", "action": "merge_states", "produces": ["unified_context"]},
            {"module": "ui", "action": "refresh", "produces": ["ui_refreshed"]},
        ]
        
        # Deadline Alert Workflow
        self.workflow_templates[WorkflowType.DEADLINE_ALERT] = [
            {
                "module": "calendar",
                "action": "get_urgent_deadlines",
                "produces": ["urgent_deadlines"],
            },
            {
                "module": "copilot",
                "action": "explain_deadline",
                "produces": ["deadline_explanation", "required_actions"],
            },
            {
                "module": "ui",
                "action": "show_alert",
                "produces": ["alert_shown"],
            },
        ]
        
        logger.info(f"📋 Loaded {len(self.workflow_templates)} workflow templates")
    
    # =========================================================================
    # MODULE ACTION REGISTRATION
    # =========================================================================
    
    def register_action(
        self,
        module: str,
        action: str,
        handler: Callable,
        description: str = "",
        required_params: List[str] = None,
        optional_params: List[str] = None,
        produces: List[str] = None,
    ):
        """Register an action handler for a module"""
        if module not in self.actions:
            self.actions[module] = {}
        
        self.actions[module][action] = ModuleAction(
            module=module,
            action=action,
            handler=handler,
            description=description,
            required_params=required_params or [],
            optional_params=optional_params or [],
            produces=produces or [],
        )
        
        logger.debug(f"⚡ Registered action: {module}.{action}")
    
    def get_module_actions(self, module: str) -> List[Dict[str, Any]]:
        """Get all registered actions for a module"""
        if module not in self.actions:
            return []
        
        return [
            {
                "action": a.action,
                "description": a.description,
                "required_params": a.required_params,
                "optional_params": a.optional_params,
                "produces": a.produces,
            }
            for a in self.actions[module].values()
        ]
    
    # =========================================================================
    # WORKFLOW MANAGEMENT
    # =========================================================================
    
    async def start_workflow(
        self,
        workflow_type: WorkflowType,
        user_id: str,
        trigger: str,
        initial_context: Dict[str, Any] = None,
    ) -> Workflow:
        """Start a new workflow for a user"""
        
        if workflow_type not in self.workflow_templates:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        # Create workflow from template
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        template = self.workflow_templates[workflow_type]
        
        steps = []
        for i, step_def in enumerate(template):
            step = WorkflowStep(
                id=f"step_{i}",
                module=step_def["module"],
                action=step_def["action"],
                params=step_def.get("params", {}),
                requires_input=step_def.get("requires_input", False),
                input_prompt=step_def.get("input_prompt"),
                on_success=f"step_{i+1}" if i < len(template) - 1 else None,
            )
            steps.append(step)
        
        workflow = Workflow(
            id=workflow_id,
            type=workflow_type,
            user_id=user_id,
            trigger=trigger,
            steps=steps,
            context=initial_context or {},
        )
        
        # Store workflow
        self.workflows[workflow_id] = workflow
        if user_id not in self.user_workflows:
            self.user_workflows[user_id] = []
        self.user_workflows[user_id].append(workflow_id)
        
        logger.info(f"🚀 Started workflow {workflow_type.value} for user {user_id[:8]}...")
        
        # Start executing
        asyncio.create_task(self._execute_workflow(workflow))
        
        # Notify subscribers
        await self._emit_event("workflow_started", {
            "workflow_id": workflow_id,
            "type": workflow_type.value,
            "user_id": user_id,
        })
        
        return workflow
    
    async def _execute_workflow(self, workflow: Workflow):
        """Execute a workflow step by step"""
        workflow.stage = WorkflowStage.RUNNING
        workflow.updated_at = datetime.utcnow()
        
        while workflow.current_step_index < len(workflow.steps):
            step = workflow.steps[workflow.current_step_index]
            
            # Check if step requires user input
            if step.requires_input and step.status == "pending":
                workflow.stage = WorkflowStage.WAITING_INPUT
                await self._emit_event("workflow_waiting_input", {
                    "workflow_id": workflow.id,
                    "step_id": step.id,
                    "prompt": step.input_prompt,
                    "module": step.module,
                    "action": step.action,
                })
                return  # Wait for input
            
            # Execute step
            step.status = "running"
            step.started_at = datetime.utcnow()
            
            try:
                result = await self._execute_step(workflow, step)
                
                step.status = "completed"
                step.result = result
                step.completed_at = datetime.utcnow()
                
                # Merge result into workflow context
                if result:
                    workflow.context.update(result)
                
                # Emit step completion
                await self._emit_event("workflow_step_completed", {
                    "workflow_id": workflow.id,
                    "step_id": step.id,
                    "module": step.module,
                    "action": step.action,
                    "result_keys": list(result.keys()) if result else [],
                })
                
                # Move to next step
                workflow.current_step_index += 1
                workflow.updated_at = datetime.utcnow()
                
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                step.completed_at = datetime.utcnow()
                
                logger.error(f"Step {step.id} failed: {e}")
                
                # Check for fallback
                if step.on_failure:
                    # Find fallback step index
                    for i, s in enumerate(workflow.steps):
                        if s.id == step.on_failure:
                            workflow.current_step_index = i
                            break
                else:
                    # No fallback, workflow failed
                    workflow.stage = WorkflowStage.FAILED
                    await self._emit_event("workflow_failed", {
                        "workflow_id": workflow.id,
                        "step_id": step.id,
                        "error": str(e),
                    })
                    return
        
        # All steps completed
        workflow.stage = WorkflowStage.COMPLETED
        workflow.completed_at = datetime.utcnow()
        
        logger.info(f"✅ Workflow {workflow.id} completed successfully")
        
        await self._emit_event("workflow_completed", {
            "workflow_id": workflow.id,
            "type": workflow.type.value,
            "user_id": workflow.user_id,
            "context_keys": list(workflow.context.keys()),
        })
    
    async def _execute_step(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Execute a single workflow step"""
        
        # Get action handler
        if step.module not in self.actions:
            logger.warning(f"Module {step.module} not registered, using default handler")
            return await self._default_step_handler(workflow, step)
        
        if step.action not in self.actions[step.module]:
            logger.warning(f"Action {step.action} not registered for {step.module}")
            return await self._default_step_handler(workflow, step)
        
        action = self.actions[step.module][step.action]
        
        # Prepare params from workflow context
        params = {**step.params}
        for key in action.required_params:
            if key in workflow.context:
                params[key] = workflow.context[key]
        
        # Execute handler
        if asyncio.iscoroutinefunction(action.handler):
            result = await action.handler(workflow.user_id, params, workflow.context)
        else:
            result = action.handler(workflow.user_id, params, workflow.context)
        
        return result or {}
    
    async def _default_step_handler(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Default handler when module/action not registered"""
        logger.info(f"Default handler for {step.module}.{step.action}")
        
        # Return empty result - step still completes
        return {
            f"{step.module}_{step.action}_status": "completed_default",
            f"{step.module}_available": False,
        }
    
    async def provide_workflow_input(
        self,
        workflow_id: str,
        step_id: str,
        user_input: Dict[str, Any],
    ) -> Workflow:
        """Provide user input for a waiting workflow step"""
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        
        if workflow.stage != WorkflowStage.WAITING_INPUT:
            raise ValueError(f"Workflow not waiting for input")
        
        # Find the step
        step = None
        for s in workflow.steps:
            if s.id == step_id:
                step = s
                break
        
        if not step:
            raise ValueError(f"Step not found: {step_id}")
        
        # Add input to context
        workflow.context.update(user_input)
        
        # Mark step as no longer requiring input
        step.requires_input = False
        
        # Resume workflow
        workflow.stage = WorkflowStage.RUNNING
        asyncio.create_task(self._execute_workflow(workflow))
        
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        return self.workflows.get(workflow_id)
    
    def get_user_workflows(self, user_id: str, active_only: bool = False) -> List[Workflow]:
        """Get all workflows for a user"""
        workflow_ids = self.user_workflows.get(user_id, [])
        workflows = [self.workflows[wid] for wid in workflow_ids if wid in self.workflows]
        
        if active_only:
            workflows = [
                w for w in workflows
                if w.stage in [WorkflowStage.RUNNING, WorkflowStage.WAITING_INPUT]
            ]
        
        return workflows
    
    # =========================================================================
    # DIRECT MODULE INVOCATION
    # =========================================================================
    
    async def invoke_module(
        self,
        module: str,
        action: str,
        user_id: str,
        params: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Directly invoke a module action without a full workflow"""
        
        if module not in self.actions or action not in self.actions[module]:
            raise ValueError(f"Action not found: {module}.{action}")
        
        action_def = self.actions[module][action]
        
        # Execute
        if asyncio.iscoroutinefunction(action_def.handler):
            result = await action_def.handler(user_id, params or {}, {})
        else:
            result = action_def.handler(user_id, params or {}, {})
        
        logger.info(f"⚡ Invoked {module}.{action} for user {user_id[:8]}...")
        
        await self._emit_event("module_invoked", {
            "module": module,
            "action": action,
            "user_id": user_id,
        })
        
        return result or {}
    
    # =========================================================================
    # EVENT SYSTEM
    # =========================================================================
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to mesh events"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()
        self.subscribers[event_type].add(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from mesh events"""
        if event_type in self.subscribers:
            self.subscribers[event_type].discard(callback)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to all subscribers"""
        if event_type not in self.subscribers:
            return
        
        for callback in self.subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")
    
    # =========================================================================
    # STATUS & INTROSPECTION
    # =========================================================================
    
    def get_mesh_status(self) -> Dict[str, Any]:
        """Get the overall mesh status"""
        active_workflows = sum(
            1 for w in self.workflows.values()
            if w.stage in [WorkflowStage.RUNNING, WorkflowStage.WAITING_INPUT]
        )
        
        return {
            "modules_connected": len(self.actions),
            "total_actions": sum(len(actions) for actions in self.actions.values()),
            "workflow_templates": len(self.workflow_templates),
            "active_workflows": active_workflows,
            "total_workflows": len(self.workflows),
            "users_with_workflows": len(self.user_workflows),
            "event_subscribers": sum(len(subs) for subs in self.subscribers.values()),
            "modules": list(self.actions.keys()),
        }
    
    def get_available_workflows(self) -> List[Dict[str, Any]]:
        """Get list of available workflow types"""
        return [
            {
                "type": wt.value,
                "steps": len(self.workflow_templates[wt]),
                "modules_involved": list(set(
                    step["module"] for step in self.workflow_templates[wt]
                )),
            }
            for wt in self.workflow_templates
        ]


# Global mesh instance
positronic_mesh = PositronicMesh()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def trigger_eviction_workflow(user_id: str, document_data: Dict[str, Any]) -> Workflow:
    """Convenience function to start eviction defense workflow"""
    return await positronic_mesh.start_workflow(
        WorkflowType.EVICTION_DEFENSE,
        user_id,
        trigger="document_upload",
        initial_context=document_data,
    )


async def trigger_lease_analysis(user_id: str, lease_data: Dict[str, Any]) -> Workflow:
    """Convenience function to start lease analysis workflow"""
    return await positronic_mesh.start_workflow(
        WorkflowType.LEASE_ANALYSIS,
        user_id,
        trigger="lease_upload",
        initial_context=lease_data,
    )


async def trigger_court_prep(user_id: str, case_data: Dict[str, Any]) -> Workflow:
    """Convenience function to start court prep workflow"""
    return await positronic_mesh.start_workflow(
        WorkflowType.COURT_PREP,
        user_id,
        trigger="user_request",
        initial_context=case_data,
    )


async def sync_all_modules(user_id: str) -> Workflow:
    """Sync all module states for a user"""
    return await positronic_mesh.start_workflow(
        WorkflowType.FULL_SYNC,
        user_id,
        trigger="sync_request",
    )
