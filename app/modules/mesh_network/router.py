"""
Mesh Network API Router
=======================

Exposes the mesh network capabilities via REST API:
- Module-to-module calls
- Parallel multi-module requests
- Collaborative sessions
- Broadcasts
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging

from app.core.mesh_network import (
    get_mesh_network,
    MergeStrategy,
    RequestType
)

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST MODELS
# =============================================================================

class SingleCallRequest(BaseModel):
    """Call a single module."""
    source: str = Field(default="api", description="Calling module")
    target: str = Field(..., description="Target module")
    action: str = Field(..., description="Action to perform")
    payload: Dict[str, Any] = Field(default_factory=dict)
    timeout: float = Field(default=30.0)


class MultiCallRequest(BaseModel):
    """Call multiple modules in parallel."""
    source: str = Field(default="api", description="Calling module")
    targets: List[str] = Field(..., description="Target modules")
    action: str = Field(..., description="Action to perform")
    payload: Dict[str, Any] = Field(default_factory=dict)
    merge_strategy: str = Field(default="combine", description="combine|first|all|priority")
    require_all: bool = Field(default=False)
    timeout: float = Field(default=30.0)


class CollaborateRequest(BaseModel):
    """Start a collaborative session."""
    source: str = Field(default="api")
    modules: List[str] = Field(..., description="Modules to collaborate")
    goal: str = Field(..., description="The goal/task")
    initial_data: Dict[str, Any] = Field(default_factory=dict)
    timeout: float = Field(default=60.0)


class BroadcastRequest(BaseModel):
    """Broadcast to all modules."""
    source: str = Field(default="api")
    event_type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(default_factory=dict)


class AskRequest(BaseModel):
    """Ask the mesh a question."""
    question: str = Field(..., description="Natural language question")
    from_module: str = Field(default="user")
    context: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/network/status")
async def get_network_status():
    """Get mesh network status including all modules and statistics."""
    mesh = get_mesh_network()
    status = mesh.get_status()
    return {
        "status": "online",
        "network": status
    }


@router.get("/network/graph")
async def get_network_graph():
    """Get the module dependency graph for visualization."""
    mesh = get_mesh_network()
    return mesh.get_module_graph()


@router.get("/network/modules")
async def list_network_modules():
    """List all connected modules and their capabilities."""
    mesh = get_mesh_network()
    status = mesh.get_status()
    return {
        "total": status["modules_connected"],
        "modules": status["modules"]
    }


@router.post("/network/call")
async def call_module(request: SingleCallRequest):
    """
    Call a single module.
    
    Example:
    ```json
    {
        "target": "calendar",
        "action": "get_deadlines",
        "payload": {"user_id": "123"}
    }
    ```
    """
    mesh = get_mesh_network()
    
    response = await mesh.call(
        source=request.source,
        target=request.target,
        action=request.action,
        payload=request.payload,
        timeout=request.timeout
    )
    
    return {
        "success": response.success,
        "request_id": response.request_id,
        "data": response.data,
        "execution_time_ms": response.execution_time_ms
    }


@router.post("/network/call-many")
async def call_many_modules(request: MultiCallRequest):
    """
    Call multiple modules in parallel and merge results.
    
    Example - Get case summary from 3 modules at once:
    ```json
    {
        "targets": ["documents", "calendar", "eviction_defense"],
        "action": "get_case_info",
        "payload": {"case_id": "123"},
        "merge_strategy": "combine"
    }
    ```
    """
    mesh = get_mesh_network()
    
    # Map string to enum
    strategy_map = {
        "combine": MergeStrategy.COMBINE,
        "first": MergeStrategy.FIRST,
        "all": MergeStrategy.ALL,
        "priority": MergeStrategy.PRIORITY,
        "chain": MergeStrategy.CHAIN
    }
    strategy = strategy_map.get(request.merge_strategy, MergeStrategy.COMBINE)
    
    response = await mesh.call_many(
        source=request.source,
        targets=request.targets,
        action=request.action,
        payload=request.payload,
        merge=strategy,
        require_all=request.require_all,
        timeout=request.timeout
    )
    
    return {
        "success": response.success,
        "request_id": response.request_id,
        "modules_called": response.source_modules,
        "merged_data": response.data,
        "individual_responses": response.individual_responses,
        "errors": response.errors,
        "execution_time_ms": response.execution_time_ms
    }


@router.post("/network/collaborate")
async def start_collaboration(request: CollaborateRequest):
    """
    Start a collaborative session where modules work together.
    
    Modules process in sequence, each adding to shared context.
    Like an assembly line - each module contributes their piece.
    
    Example - Build complete eviction defense:
    ```json
    {
        "modules": ["documents", "eviction_defense", "calendar", "forms", "copilot"],
        "goal": "build_eviction_defense",
        "initial_data": {"document_id": "123", "user_id": "456"}
    }
    ```
    """
    mesh = get_mesh_network()
    
    response = await mesh.collaborate(
        source=request.source,
        modules=request.modules,
        goal=request.goal,
        initial_data=request.initial_data,
        timeout=request.timeout
    )
    
    return {
        "success": response.success,
        "collaboration_id": response.request_id,
        "modules_participated": response.source_modules,
        "final_data": response.data,
        "module_contributions": response.individual_responses,
        "errors": response.errors,
        "execution_time_ms": response.execution_time_ms
    }


@router.post("/network/broadcast")
async def broadcast_event(request: BroadcastRequest):
    """
    Broadcast an event to all interested modules.
    
    Example - Notify about approaching deadline:
    ```json
    {
        "event_type": "deadline_approaching",
        "data": {"deadline_id": "123", "days_remaining": 3}
    }
    ```
    """
    mesh = get_mesh_network()
    
    notified = await mesh.broadcast(
        source=request.source,
        event_type=request.event_type,
        data=request.data
    )
    
    return {
        "success": True,
        "event_type": request.event_type,
        "modules_notified": notified
    }


@router.post("/network/ask")
async def ask_mesh(request: AskRequest):
    """
    Ask the mesh a natural language question.
    It figures out which modules to query.
    
    Example:
    ```json
    {
        "question": "What are my upcoming deadlines?",
        "context": {"user_id": "123"}
    }
    ```
    """
    mesh = get_mesh_network()
    
    response = await mesh.ask(
        question=request.question,
        from_module=request.from_module,
        context=request.context
    )
    
    return {
        "success": response.success,
        "question": request.question,
        "modules_consulted": response.source_modules,
        "answer": response.data,
        "execution_time_ms": response.execution_time_ms
    }


# =============================================================================
# PRE-BUILT COLLABORATION WORKFLOWS
# =============================================================================

@router.post("/network/quick/case-summary")
async def quick_case_summary(
    user_id: str,
    case_id: Optional[str] = None
):
    """
    Quick endpoint: Get a complete case summary from all relevant modules.
    
    Calls documents, calendar, eviction_defense, timeline in parallel.
    """
    mesh = get_mesh_network()
    
    response = await mesh.call_many(
        source="api",
        targets=["documents", "calendar", "eviction_defense", "timeline"],
        action="get_case_summary",
        payload={"user_id": user_id, "case_id": case_id},
        merge=MergeStrategy.COMBINE
    )
    
    return {
        "success": response.success,
        "case_summary": response.data,
        "sources": response.source_modules,
        "execution_time_ms": response.execution_time_ms
    }


@router.post("/network/quick/deadline-check")
async def quick_deadline_check(user_id: str):
    """
    Quick endpoint: Check all deadlines across all modules.
    """
    mesh = get_mesh_network()
    
    response = await mesh.call_many(
        source="api",
        targets=["calendar", "eviction_defense", "forms"],
        action="get_deadlines",
        payload={"user_id": user_id},
        merge=MergeStrategy.COMBINE
    )
    
    return {
        "success": response.success,
        "deadlines": response.data,
        "sources": response.source_modules
    }


@router.post("/network/quick/build-defense")
async def quick_build_defense(
    user_id: str,
    document_id: Optional[str] = None,
    eviction_type: str = "nonpayment"
):
    """
    Quick endpoint: Collaborative defense building.
    
    All modules work together to build a complete defense package.
    """
    mesh = get_mesh_network()
    
    response = await mesh.collaborate(
        source="api",
        modules=["documents", "eviction_defense", "law_library", "calendar", "forms", "copilot"],
        goal="build_defense",
        initial_data={
            "user_id": user_id,
            "document_id": document_id,
            "eviction_type": eviction_type
        },
        timeout=90.0
    )
    
    return {
        "success": response.success,
        "defense_package": response.data,
        "module_contributions": response.individual_responses,
        "execution_time_ms": response.execution_time_ms
    }
