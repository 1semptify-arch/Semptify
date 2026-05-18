"""
Mesh Network API Router
=======================

Endpoints to:
- View mesh topology
- Monitor node health
- Make direct mesh calls
- WebSocket for real-time mesh visualization
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from typing import Any, Dict, Optional
import asyncio
import json
import logging

from app.core.distributed_mesh import (
    mesh_coordinator,
    get_mesh_status,
    MeshNode,
)
from app.core.mesh_integration import (
    service_mesh,
    mesh_call,
    get_service_node,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mesh", tags=["Distributed Mesh"])


# =============================================================================
# MESH TOPOLOGY & STATUS
# =============================================================================

@router.get("/status")
async def get_status():
    """Get overall mesh network status"""
    return {
        "status": "healthy",
        "mesh": get_mesh_status(),
    }


@router.get("/topology")
async def get_topology():
    """Get the mesh topology for visualization"""
    return mesh_coordinator.get_mesh_topology()


@router.get("/nodes")
async def list_nodes():
    """List all nodes in the mesh"""
    nodes = []
    for node in mesh_coordinator.get_all_nodes():
        nodes.append(node.get_status())
    return {"nodes": nodes, "count": len(nodes)}


@router.get("/nodes/{node_type}")
async def get_node(node_type: str):
    """Get a specific node by type"""
    node = service_mesh.get_node(node_type)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_type}")
    return node.get_status()


@router.get("/capabilities")
async def list_capabilities():
    """List all available capabilities in the mesh"""
    caps = {}
    for node in mesh_coordinator.get_all_nodes():
        for cap in node.identity.capabilities:
            if cap not in caps:
                caps[cap] = []
            caps[cap].append(node.identity.node_type)
    
    return {
        "capabilities": caps,
        "total": len(caps),
    }


# =============================================================================
# MESH INVOCATION
# =============================================================================

@router.post("/call/{capability}")
async def call_capability(capability: str, payload: Dict[str, Any] = {}):
    """
    Make a direct call to any capability in the mesh.
    The mesh will route to the appropriate node.
    """
    try:
        result = await mesh_call(capability, payload)
        return {
            "success": True,
            "capability": capability,
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        logger.error(f"Mesh call error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nodes/{node_type}/call/{capability}")
async def call_specific_node(node_type: str, capability: str, payload: Dict[str, Any] = {}):
    """Call a specific capability on a specific node"""
    node = service_mesh.get_node(node_type)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_type}")
    
    if capability not in node.identity.capabilities:
        raise HTTPException(
            status_code=400,
            detail=f"Node {node_type} doesn't have capability: {capability}"
        )
    
    # Find a peer to make the request (or handle locally)
    handler = node._handlers.get(capability)
    if handler:
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(payload)
            else:
                result = handler(payload)
            return {"success": True, "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    raise HTTPException(status_code=501, detail="Handler not implemented")


@router.post("/broadcast/{event_type}")
async def broadcast_event(event_type: str, data: Dict[str, Any] = {}):
    """Broadcast an event to all nodes in the mesh"""
    # Pick any node to broadcast from
    nodes = mesh_coordinator.get_all_nodes()
    if not nodes:
        raise HTTPException(status_code=503, detail="No nodes available")
    
    await nodes[0].emit_event(event_type, data)
    
    return {
        "success": True,
        "event_type": event_type,
        "broadcast_from": nodes[0].identity.node_id,
    }


# =============================================================================
# MESH METRICS
# =============================================================================

@router.get("/metrics")
async def get_metrics():
    """Get aggregated metrics from all nodes"""
    metrics = {
        "total_messages_sent": 0,
        "total_messages_received": 0,
        "total_requests_handled": 0,
        "avg_response_time_ms": 0,
        "by_node": {},
    }
    
    nodes = mesh_coordinator.get_all_nodes()
    response_times = []
    
    for node in nodes:
        nm = node.metrics
        metrics["total_messages_sent"] += nm["messages_sent"]
        metrics["total_messages_received"] += nm["messages_received"]
        metrics["total_requests_handled"] += nm["requests_handled"]
        response_times.append(nm["avg_response_time_ms"])
        
        metrics["by_node"][node.identity.node_type] = nm
    
    if response_times:
        metrics["avg_response_time_ms"] = sum(response_times) / len(response_times)
    
    return metrics


# =============================================================================
# WEBSOCKET FOR REAL-TIME MESH VISUALIZATION
# =============================================================================

@router.websocket("/ws")
async def mesh_websocket(websocket: WebSocket):
    """WebSocket for real-time mesh topology updates"""
    await websocket.accept()
    
    # Register for updates
    mesh_coordinator.add_websocket_observer(websocket)
    
    # Send initial topology
    topology = mesh_coordinator.get_mesh_topology()
    await websocket.send_json({
        "type": "mesh_topology",
        "data": topology,
    })
    
    try:
        while True:
            # Receive messages (for commands)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif data.get("type") == "get_node_status":
                    node_type = data.get("node_type")
                    node = service_mesh.get_node(node_type)
                    if node:
                        await websocket.send_json({
                            "type": "node_status",
                            "data": node.get_status(),
                        })
                
                elif data.get("type") == "get_metrics":
                    metrics = {
                        "by_node": {
                            n.identity.node_type: n.metrics
                            for n in mesh_coordinator.get_all_nodes()
                        }
                    }
                    await websocket.send_json({
                        "type": "metrics",
                        "data": metrics,
                    })
            
            except asyncio.TimeoutError:
                # Send periodic topology updates
                topology = mesh_coordinator.get_mesh_topology()
                await websocket.send_json({
                    "type": "mesh_update",
                    "data": topology,
                })
    
    except WebSocketDisconnect:
        logger.info("Mesh WebSocket disconnected")
    except Exception as e:
        logger.error(f"Mesh WebSocket error: {e}")


# =============================================================================
# HEALTH & DIAGNOSTICS
# =============================================================================

@router.get("/health")
async def mesh_health():
    """Check health of all mesh nodes"""
    nodes = mesh_coordinator.get_all_nodes()
    
    health = {
        "status": "healthy",
        "nodes_total": len(nodes),
        "nodes_running": 0,
        "nodes_stopped": 0,
        "details": [],
    }
    
    for node in nodes:
        status = node.get_status()
        if status["running"]:
            health["nodes_running"] += 1
        else:
            health["nodes_stopped"] += 1
        
        health["details"].append({
            "node_type": node.identity.node_type,
            "running": status["running"],
            "peers": status["peers_connected"],
            "capabilities": len(status["capabilities"]),
        })
    
    if health["nodes_stopped"] > 0:
        health["status"] = "degraded"
    
    if health["nodes_running"] == 0:
        health["status"] = "unhealthy"
    
    return health


@router.post("/restart/{node_type}")
async def restart_node(node_type: str):
    """Restart a specific node"""
    node = service_mesh.get_node(node_type)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_type}")
    
    await node.stop()
    await node.start()
    
    return {"success": True, "node_type": node_type, "status": "restarted"}
