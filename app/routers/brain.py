"""
🧠 Positronic Brain - API Router
================================
REST API and WebSocket endpoints for the brain.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import json
import logging

from app.services.positronic_brain import (
    get_brain, 
    PositronicBrain, 
    BrainEvent, 
    EventType, 
    ModuleType
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Positronic Brain"])


# =============================================================================
# Schemas
# =============================================================================

class WorkflowRequest(BaseModel):
    """Request to trigger a workflow."""
    workflow_name: str
    data: dict = {}


class EventRequest(BaseModel):
    """Request to emit an event."""
    event_type: str
    source_module: str
    data: dict = {}


class StateUpdateRequest(BaseModel):
    """Request to update shared state."""
    key: str
    value: dict | list | str | int | float | bool


class ThinkRequest(BaseModel):
    """Request for brain to analyze context."""
    context: dict = {}


# =============================================================================
# REST Endpoints
# =============================================================================

@router.get("/status")
async def get_brain_status(brain: PositronicBrain = Depends(get_brain)):
    """
    🧠 Get full brain status.
    
    Returns information about:
    - Connected modules
    - Active workflows
    - WebSocket clients
    - Event history size
    """
    return brain.get_system_status()


@router.get("/modules")
async def list_modules(brain: PositronicBrain = Depends(get_brain)):
    """
    🔌 List all connected modules.
    """
    return {
        "modules": brain.list_modules(),
        "count": len(brain.modules)
    }


@router.get("/state")
async def get_state(
    key: Optional[str] = None,
    brain: PositronicBrain = Depends(get_brain)
):
    """
    📊 Get shared state.
    
    Optionally filter by key.
    """
    if key:
        value = brain.get_state(key)
        return {key: value}
    return brain.get_state()


@router.put("/state")
async def update_state(
    request: StateUpdateRequest,
    brain: PositronicBrain = Depends(get_brain)
):
    """
    ✏️ Update shared state.
    
    This will notify all connected modules.
    """
    await brain.update_state(request.key, request.value, ModuleType.CONTEXT)
    return {"success": True, "key": request.key}


@router.get("/events")
async def get_recent_events(
    limit: int = 50,
    brain: PositronicBrain = Depends(get_brain)
):
    """
    📜 Get recent brain events.
    """
    return {
        "events": brain.get_recent_events(limit),
        "total": len(brain.event_history)
    }


@router.post("/events")
async def emit_event(
    request: EventRequest,
    brain: PositronicBrain = Depends(get_brain)
):
    """
    📤 Emit an event to the brain.
    """
    try:
        event_type = EventType(request.event_type)
        source_module = ModuleType(request.source_module)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid event/module type: {e}")
    
    event = BrainEvent(
        event_type=event_type,
        source_module=source_module,
        data=request.data
    )
    
    await brain.emit(event)
    return {"success": True, "event": event.to_dict()}


@router.post("/workflow")
async def trigger_workflow(
    request: WorkflowRequest,
    brain: PositronicBrain = Depends(get_brain)
):
    """
    ⚡ Trigger a cross-module workflow.
    
    Available workflows:
    - document_intake: Process uploaded document through all modules
    - eviction_defense: Start eviction defense workflow
    - deadline_check: Check all deadlines
    - full_sync: Synchronize all modules
    """
    workflow_id = await brain.trigger_workflow(
        request.workflow_name,
        request.data
    )
    
    return {
        "workflow_id": workflow_id,
        "name": request.workflow_name,
        "status": "started"
    }


@router.get("/workflows")
async def list_workflows(brain: PositronicBrain = Depends(get_brain)):
    """
    📋 List active and recent workflows.
    """
    return {
        "active": brain.active_workflows,
        "count": len(brain.active_workflows)
    }


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    brain: PositronicBrain = Depends(get_brain)
):
    """
    🔍 Get workflow status.
    """
    workflow = brain.active_workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.post("/think")
async def brain_think(
    request: ThinkRequest,
    brain: PositronicBrain = Depends(get_brain)
):
    """
    🤔 Ask the brain to think and suggest actions.
    
    The brain analyzes current context and provides:
    - Priority suggestions
    - Next actions
    - System status
    """
    result = await brain.think(request.context)
    return result


@router.post("/sync")
async def sync_all(brain: PositronicBrain = Depends(get_brain)):
    """
    🔄 Force full synchronization of all modules.
    """
    workflow_id = await brain.trigger_workflow("full_sync", {})
    return {
        "success": True,
        "workflow_id": workflow_id,
        "message": "Full sync initiated"
    }


# =============================================================================
# WebSocket for Real-Time Updates
# =============================================================================

@router.websocket("/ws")
async def brain_websocket(
    websocket: WebSocket,
    brain: PositronicBrain = Depends(get_brain)
):
    """
    🔌 WebSocket connection to the brain.
    
    Clients receive:
    - All brain events in real-time
    - State change notifications
    - Workflow updates
    
    Clients can send:
    - Events to emit
    - State updates
    - Workflow triggers
    """
    await websocket.accept()
    brain.websocket_clients.add(websocket)
    
    logger.info(f"🧠 Brain WebSocket connected (total: {len(brain.websocket_clients)})")
    
    # Send initial state
    await websocket.send_json({
        "type": "connected",
        "state": brain.get_state(),
        "modules": brain.list_modules()
    })
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            msg_type = data.get("type")
            
            if msg_type == "emit_event":
                # Client wants to emit an event
                try:
                    event = BrainEvent(
                        event_type=EventType(data["event_type"]),
                        source_module=ModuleType(data.get("source", "ui")),
                        data=data.get("data", {})
                    )
                    await brain.emit(event)
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})
            
            elif msg_type == "update_state":
                # Client wants to update state
                await brain.update_state(
                    data["key"],
                    data["value"],
                    ModuleType.UI
                )
            
            elif msg_type == "trigger_workflow":
                # Client wants to trigger workflow
                workflow_id = await brain.trigger_workflow(
                    data["workflow_name"],
                    data.get("data", {})
                )
                await websocket.send_json({
                    "type": "workflow_started",
                    "workflow_id": workflow_id
                })
            
            elif msg_type == "get_state":
                # Client requests current state
                await websocket.send_json({
                    "type": "state",
                    "state": brain.get_state()
                })
            
            elif msg_type == "ping":
                # Keep-alive
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        pass
    finally:
        brain.websocket_clients.discard(websocket)
        logger.info(f"🧠 Brain WebSocket disconnected (total: {len(brain.websocket_clients)})")
