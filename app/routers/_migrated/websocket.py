"""
WebSocket Router for Real-Time Events
Pushes events to browser for live UI updates.
Enhanced with advanced WebSocket management and job notifications.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Optional
import logging
import json

from app.core.event_bus import event_bus, EventType
from app.core.websocket_manager import get_websocket_manager, WebSocketMessage
from app.core.job_processor import get_job_processor

logger = logging.getLogger(__name__)
router = APIRouter()


def get_user_id_from_websocket(websocket: WebSocket) -> str:
    """Get user_id from WebSocket cookies (secure approach)."""
    user_id = websocket.cookies.get("semptify_uid", "broadcast")
    return user_id if user_id else "broadcast"


@router.websocket("/events")
async def websocket_events(websocket: WebSocket):
    """
    Enhanced WebSocket endpoint for real-time events and job notifications.
    
    Connect: ws://localhost:8000/ws/events
    (User ID is automatically read from cookies)
    
    Receives all events published to the EventBus and job status updates.
    """
    # Get user_id from cookies (not query params - security!)
    user_id = get_user_id_from_websocket(websocket)
    
    await websocket.accept()
    logger.info(f"Enhanced WebSocket connected: {user_id}")
    
    # Get WebSocket manager
    ws_manager = get_websocket_manager()
    connection_id = await ws_manager.connect(websocket, user_id)
    
    # Register with event bus (legacy support)
    event_bus.register_websocket(websocket, user_id)
    
    try:
        # Send welcome message with enhanced features
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Semptify Enhanced Event Stream",
            "user_id": user_id,
            "connection_id": connection_id,
            "features": ["job_notifications", "real_time_updates", "system_alerts"]
        })
        
        # Subscribe to job notifications for this user
        await ws_manager.subscribe(connection_id, f"user_jobs:{user_id}")
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (for ping/pong and commands)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message.get("type") == "subscribe":
                    # Client can subscribe to specific event types
                    event_types = message.get("events", [])
                    await websocket.send_json({
                        "type": "subscribed",
                        "events": event_types,
                    })
                    
                    # Subscribe to WebSocket manager topics
                    for event_type in event_types:
                        await ws_manager.subscribe(connection_id, event_type)
                
                elif message.get("type") == "get_history":
                    # Client requests recent events
                    event_type = message.get("event_type")
                    limit = message.get("limit", 50)
                    
                    history = event_bus.get_history(
                        event_type=EventType(event_type) if event_type else None,
                        user_id=user_id if user_id != "broadcast" else None,
                        limit=limit,
                    )
                    
                    await websocket.send_json({
                        "type": "history",
                        "events": [e.to_dict() for e in history],
                    })
                
                elif message.get("type") == "get_jobs":
                    # Client requests user's job status
                    job_processor = get_job_processor()
                    user_jobs = job_processor.get_user_jobs(user_id)
                    
                    await websocket.send_json({
                        "type": "jobs",
                        "jobs": user_jobs
                    })
                
                elif message.get("type") == "get_job_status":
                    # Client requests specific job status
                    job_id = message.get("job_id")
                    job_processor = get_job_processor()
                    job_status = job_processor.get_job_status(job_id)
                    
                    await websocket.send_json({
                        "type": "job_status",
                        "job_id": job_id,
                        "status": job_status
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
                
    except WebSocketDisconnect:
        logger.info(f"Enhanced WebSocket disconnected: {user_id}")
    except Exception as e:
        logger.error(f"Enhanced WebSocket error: {e}")
    finally:
        # Unregister from event bus
        event_bus.unregister_websocket(websocket, user_id)
        # Disconnect from WebSocket manager
        await ws_manager.disconnect(connection_id)


@router.get("/status")
async def get_websocket_status():
    """Get enhanced WebSocket connection status"""
    ws_manager = get_websocket_manager()
    job_processor = get_job_processor()
    
    return {
        "status": "active",
        "event_types": [e.value for e in EventType],
        "connect_url": "/ws/events",
        "usage": "Connect via WebSocket to receive real-time events and job notifications",
        "features": {
            "job_notifications": True,
            "real_time_updates": True,
            "system_alerts": True,
            "document_updates": True
        },
        "stats": ws_manager.get_connection_stats(),
        "job_queue_stats": job_processor.get_queue_stats()
    }

@router.get("/connections/{user_id}")
async def get_user_connections(user_id: str):
    """Get WebSocket connections for a specific user"""
    ws_manager = get_websocket_manager()
    connections = ws_manager.get_user_connections(user_id)
    
    return {
        "user_id": user_id,
        "connections": connections,
        "connection_count": len(connections)
    }

@router.post("/notify/{user_id}")
async def send_notification_to_user(user_id: str, notification: dict):
    """Send a notification to a specific user via WebSocket"""
    ws_manager = get_websocket_manager()
    
    message_type = notification.get("type", "notification")
    message_data = notification.get("data", {})
    
    from datetime import datetime, timezone
    from app.core.websocket_manager import WebSocketMessage
    
    message = WebSocketMessage(
        type=message_type,
        data=message_data,
        timestamp=datetime.now(timezone.utc),
        user_id=user_id
    )
    
    success = await ws_manager.send_to_user(user_id, message)
    
    return {
        "success": success,
        "user_id": user_id,
        "message": "Notification sent" if success else "Failed to send notification"
    }

@router.post("/broadcast")
async def broadcast_notification(notification: dict):
    """Broadcast a notification to all connected users"""
    ws_manager = get_websocket_manager()
    
    message_type = notification.get("type", "broadcast")
    message_data = notification.get("data", {})
    
    from datetime import datetime, timezone
    from app.core.websocket_manager import WebSocketMessage
    
    message = WebSocketMessage(
        type=message_type,
        data=message_data,
        timestamp=datetime.now(timezone.utc)
    )
    
    success = await ws_manager.broadcast_to_all(message)
    
    return {
        "success": success,
        "message": "Broadcast sent" if success else "Failed to broadcast"
    }
