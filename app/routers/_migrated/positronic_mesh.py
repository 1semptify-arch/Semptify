"""
Positronic Mesh API Router
==========================

REST API endpoints for the Positronic Mesh orchestration system.
Allows starting workflows, checking status, and module invocation.
"""

from fastapi import APIRouter, Cookie, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

from app.core.positronic_mesh import (
    positronic_mesh,
    WorkflowType,
    WorkflowStage,
    trigger_eviction_workflow,
    trigger_lease_analysis,
    trigger_court_prep,
    sync_all_modules,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class StartWorkflowRequest(BaseModel):
    workflow_type: str
    initial_context: Dict[str, Any] = {}
    trigger: str = "api_request"


class ProvideInputRequest(BaseModel):
    step_id: str
    user_input: Dict[str, Any]


class InvokeModuleRequest(BaseModel):
    module: str
    action: str
    params: Dict[str, Any] = {}


class WorkflowResponse(BaseModel):
    id: str
    type: str
    stage: str
    current_step: int
    total_steps: int
    waiting_for_input: bool = False
    input_prompt: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_user_id(semptify_uid: Optional[str]) -> str:
    """Get user ID from cookie or return anonymous"""
    return semptify_uid or "anonymous"


# =============================================================================
# MESH STATUS ENDPOINTS
# =============================================================================

@router.get("/mesh/status")
async def get_mesh_status():
    """Get the overall Positronic Mesh status"""
    return positronic_mesh.get_mesh_status()


@router.get("/mesh/workflows/available")
async def get_available_workflows():
    """Get list of available workflow types"""
    return {
        "workflows": positronic_mesh.get_available_workflows(),
        "types": [wt.value for wt in WorkflowType],
    }


@router.get("/mesh/modules")
async def get_connected_modules():
    """Get all modules connected to the mesh"""
    modules = {}
    for module_name in positronic_mesh.actions:
        modules[module_name] = positronic_mesh.get_module_actions(module_name)
    
    return {
        "total_modules": len(modules),
        "modules": modules,
    }


# =============================================================================
# WORKFLOW MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/mesh/workflow/start")
async def start_workflow(
    request: StartWorkflowRequest,
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Start a new workflow"""
    user_id = get_user_id(semptify_uid)
    
    # Validate workflow type
    try:
        workflow_type = WorkflowType(request.workflow_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workflow type. Available: {[wt.value for wt in WorkflowType]}"
        )
    
    # Start the workflow
    workflow = await positronic_mesh.start_workflow(
        workflow_type=workflow_type,
        user_id=user_id,
        trigger=request.trigger,
        initial_context=request.initial_context,
    )
    
    return {
        "success": True,
        "workflow": workflow.to_dict(),
        "message": f"Started {workflow_type.value} workflow",
    }


@router.get("/mesh/workflow/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Get status of a specific workflow"""
    workflow = positronic_mesh.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Check user owns this workflow
    user_id = get_user_id(semptify_uid)
    if workflow.user_id != user_id and user_id != "anonymous":
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = workflow.to_dict()
    
    # Add input prompt if waiting
    if workflow.stage == WorkflowStage.WAITING_INPUT:
        current_step = workflow.steps[workflow.current_step_index]
        response["waiting_for_input"] = True
        response["input_step_id"] = current_step.id
        response["input_prompt"] = current_step.input_prompt
    
    return response


@router.post("/mesh/workflow/{workflow_id}/input")
async def provide_workflow_input(
    workflow_id: str,
    request: ProvideInputRequest,
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Provide input for a workflow step that's waiting"""
    user_id = get_user_id(semptify_uid)
    
    workflow = positronic_mesh.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.user_id != user_id and user_id != "anonymous":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        workflow = await positronic_mesh.provide_workflow_input(
            workflow_id=workflow_id,
            step_id=request.step_id,
            user_input=request.user_input,
        )
        
        return {
            "success": True,
            "workflow": workflow.to_dict(),
            "message": "Input provided, workflow continuing",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mesh/workflows")
async def get_user_workflows(
    active_only: bool = False,
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Get all workflows for the current user"""
    user_id = get_user_id(semptify_uid)
    
    workflows = positronic_mesh.get_user_workflows(user_id, active_only=active_only)
    
    return {
        "user_id": user_id,
        "total": len(workflows),
        "workflows": [w.to_dict() for w in workflows],
    }


# =============================================================================
# QUICK ACTION ENDPOINTS
# =============================================================================

@router.post("/mesh/quick/eviction")
async def quick_start_eviction(
    document_data: Dict[str, Any] = {},
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Quick start an eviction defense workflow"""
    user_id = get_user_id(semptify_uid)
    
    workflow = await trigger_eviction_workflow(user_id, document_data)
    
    return {
        "success": True,
        "workflow_id": workflow.id,
        "message": "Eviction defense workflow started",
        "workflow": workflow.to_dict(),
    }


@router.post("/mesh/quick/lease-analysis")
async def quick_start_lease_analysis(
    lease_data: Dict[str, Any] = {},
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Quick start a lease analysis workflow"""
    user_id = get_user_id(semptify_uid)
    
    workflow = await trigger_lease_analysis(user_id, lease_data)
    
    return {
        "success": True,
        "workflow_id": workflow.id,
        "message": "Lease analysis workflow started",
        "workflow": workflow.to_dict(),
    }


@router.post("/mesh/quick/court-prep")
async def quick_start_court_prep(
    case_data: Dict[str, Any] = {},
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Quick start a court preparation workflow"""
    user_id = get_user_id(semptify_uid)
    
    workflow = await trigger_court_prep(user_id, case_data)
    
    return {
        "success": True,
        "workflow_id": workflow.id,
        "message": "Court preparation workflow started",
        "workflow": workflow.to_dict(),
    }


@router.post("/mesh/quick/sync")
async def quick_sync_modules(
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Quick sync all modules for the user"""
    user_id = get_user_id(semptify_uid)
    
    workflow = await sync_all_modules(user_id)
    
    return {
        "success": True,
        "workflow_id": workflow.id,
        "message": "Full sync workflow started",
        "workflow": workflow.to_dict(),
    }


# =============================================================================
# DIRECT MODULE INVOCATION
# =============================================================================

@router.post("/mesh/invoke")
async def invoke_module_action(
    request: InvokeModuleRequest,
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Directly invoke a module action (without full workflow)"""
    user_id = get_user_id(semptify_uid)
    
    try:
        result = await positronic_mesh.invoke_module(
            module=request.module,
            action=request.action,
            user_id=user_id,
            params=request.params,
        )
        
        return {
            "success": True,
            "module": request.module,
            "action": request.action,
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Module invocation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mesh/module/{module_name}/actions")
async def get_module_actions(module_name: str):
    """Get available actions for a specific module"""
    actions = positronic_mesh.get_module_actions(module_name)
    
    if not actions:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_name}' not found or has no registered actions"
        )
    
    return {
        "module": module_name,
        "actions": actions,
    }
