"""
WebSocket Manager - Real-time Communication System
===============================================

Manages WebSocket connections for real-time notifications and updates.
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
from app.core.id_gen import make_id
import weakref

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types of notifications."""
    JOB_STATUS = "job_status"
    DOCUMENT_UPLOAD = "document_upload"
    SYSTEM_ALERT = "system_alert"
    USER_MESSAGE = "user_message"
    STORAGE_EVENT = "storage_event"
    SECURITY_EVENT = "security_event"

@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    type: str
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id
        }

@dataclass
class ConnectionInfo:
    """WebSocket connection information."""
    websocket: Any
    user_id: str
    session_id: str
    connected_at: datetime
    last_ping: datetime
    subscriptions: Set[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "subscriptions": list(self.subscriptions)
        }

class WebSocketManager:
    """Manages WebSocket connections and real-time messaging."""
    
    def __init__(self):
        # Active connections
        self.connections: Dict[str, ConnectionInfo] = {}
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)  # user_id -> connection_ids
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # subscription -> connection_ids
        
        # Message queues
        self.message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        # Background tasks
        self.broadcast_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_failed": 0,
            "subscriptions_active": 0
        }
        
        # Shutdown flag
        self.shutdown_event = asyncio.Event()
    
    async def connect(self, websocket: Any, user_id: str, session_id: str = None) -> str:
        """Register a new WebSocket connection."""
        if session_id is None:
            session_id = make_id("sess")
        
        connection_id = make_id("ws")
        
        # Create connection info
        connection_info = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            session_id=session_id,
            connected_at=datetime.now(timezone.utc),
            last_ping=datetime.now(timezone.utc),
            subscriptions=set()
        )
        
        # Store connection
        self.connections[connection_id] = connection_info
        self.user_connections[user_id].add(connection_id)
        
        # Update statistics
        self.stats["total_connections"] += 1
        self.stats["active_connections"] += 1
        
        # Start background tasks if not running
        await self._ensure_background_tasks()
        
        logger.info(f"WebSocket connected: user={user_id}, session={session_id}, conn_id={connection_id}")
        
        # Send welcome message
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="connection_established",
            data={
                "connection_id": connection_id,
                "session_id": session_id,
                "server_time": datetime.now(timezone.utc).isoformat()
            },
            timestamp=datetime.now(timezone.utc),
            user_id=user_id
        ))
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection."""
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        user_id = connection_info.user_id
        
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from subscriptions
        for subscription in connection_info.subscriptions:
            if subscription in self.subscriptions:
                self.subscriptions[subscription].discard(connection_id)
                if not self.subscriptions[subscription]:
                    del self.subscriptions[subscription]
        
        # Remove connection
        del self.connections[connection_id]
        
        # Update statistics
        self.stats["active_connections"] -= 1
        
        logger.info(f"WebSocket disconnected: user={user_id}, conn_id={connection_id}")
    
    async def subscribe(self, connection_id: str, subscription: str):
        """Subscribe a connection to a topic."""
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        connection_info.subscriptions.add(subscription)
        self.subscriptions[subscription].add(connection_id)
        
        # Update statistics
        self.stats["subscriptions_active"] = len(self.subscriptions)
        
        logger.info(f"Connection {connection_id} subscribed to {subscription}")
        return True
    
    async def unsubscribe(self, connection_id: str, subscription: str):
        """Unsubscribe a connection from a topic."""
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        connection_info.subscriptions.discard(subscription)
        
        if subscription in self.subscriptions:
            self.subscriptions[subscription].discard(connection_id)
            if not self.subscriptions[subscription]:
                del self.subscriptions[subscription]
        
        # Update statistics
        self.stats["subscriptions_active"] = len(self.subscriptions)
        
        logger.info(f"Connection {connection_id} unsubscribed from {subscription}")
        return True
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send a message to a specific connection."""
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        try:
            await connection_info.websocket.send_text(json.dumps(message.to_dict()))
            self.stats["messages_sent"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to connection {connection_id}: {e}")
            self.stats["messages_failed"] += 1
            
            # Remove dead connection
            await self.disconnect(connection_id)
            return False
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """Send a message to all connections for a user."""
        if user_id not in self.user_connections:
            return False
        
        connection_ids = list(self.user_connections[user_id])
        success_count = 0
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                success_count += 1
        
        return success_count > 0
    
    async def broadcast_to_subscription(self, subscription: str, message: WebSocketMessage):
        """Broadcast a message to all subscribers."""
        if subscription not in self.subscriptions:
            return False
        
        connection_ids = list(self.subscriptions[subscription])
        success_count = 0
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                success_count += 1
        
        return success_count > 0
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast a message to all active connections."""
        connection_ids = list(self.connections.keys())
        success_count = 0
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                success_count += 1
        
        return success_count > 0
    
    async def queue_message(self, message: WebSocketMessage, target: str = None, target_type: str = "all"):
        """Queue a message for background processing."""
        await self.message_queue.put({
            "message": message,
            "target": target,
            "target_type": target_type
        })
    
    async def send_job_status_update(self, user_id: str, job_id: str, status: str, progress: float = None, result: Dict[str, Any] = None):
        """Send job status update to user."""
        message = WebSocketMessage(
            type=NotificationType.JOB_STATUS.value,
            data={
                "job_id": job_id,
                "status": status,
                "progress": progress,
                "result": result
            },
            timestamp=datetime.now(timezone.utc),
            user_id=user_id
        )
        
        await self.send_to_user(user_id, message)
    
    async def send_document_upload_notification(self, user_id: str, document_id: str, filename: str, status: str):
        """Send document upload notification."""
        message = WebSocketMessage(
            type=NotificationType.DOCUMENT_UPLOAD.value,
            data={
                "document_id": document_id,
                "filename": filename,
                "status": status
            },
            timestamp=datetime.now(timezone.utc),
            user_id=user_id
        )
        
        await self.send_to_user(user_id, message)
    
    async def send_system_alert(self, message: str, severity: str = "info", target_users: List[str] = None):
        """Send system alert."""
        alert_message = WebSocketMessage(
            type=NotificationType.SYSTEM_ALERT.value,
            data={
                "message": message,
                "severity": severity
            },
            timestamp=datetime.now(timezone.utc)
        )
        
        if target_users:
            for user_id in target_users:
                await self.send_to_user(user_id, alert_message)
        else:
            await self.broadcast_to_all(alert_message)
    
    async def send_security_event(self, user_id: str, event_type: str, details: Dict[str, Any]):
        """Send security event notification."""
        message = WebSocketMessage(
            type=NotificationType.SECURITY_EVENT.value,
            data={
                "event_type": event_type,
                "details": details
            },
            timestamp=datetime.now(timezone.utc),
            user_id=user_id
        )
        
        await self.send_to_user(user_id, message)
    
    async def _ensure_background_tasks(self):
        """Ensure background tasks are running."""
        if self.broadcast_task is None or self.broadcast_task.done():
            self.broadcast_task = asyncio.create_task(self._broadcast_loop())
        
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _broadcast_loop(self):
        """Background task for processing message queue."""
        while not self.shutdown_event.is_set():
            try:
                # Get message from queue
                item = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                message = item["message"]
                target = item["target"]
                target_type = item["target_type"]
                
                # Send based on target type
                if target_type == "user":
                    await self.send_to_user(target, message)
                elif target_type == "subscription":
                    await self.broadcast_to_subscription(target, message)
                elif target_type == "all":
                    await self.broadcast_to_all(message)
                
            except asyncio.TimeoutError:
                # No message in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                await asyncio.sleep(1)
    
    async def _cleanup_loop(self):
        """Background task for cleaning up dead connections."""
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                
                current_time = datetime.now(timezone.utc())
                dead_connections = []
                
                # Check for dead connections (no ping for 5 minutes)
                for connection_id, connection_info in self.connections.items():
                    if (current_time - connection_info.last_ping).seconds > 300:
                        dead_connections.append(connection_id)
                
                # Clean up dead connections
                for connection_id in dead_connections:
                    await self.disconnect(connection_id)
                
                if dead_connections:
                    logger.info(f"Cleaned up {len(dead_connections)} dead connections")
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def ping_connections(self):
        """Ping all connections to check they're alive."""
        ping_message = WebSocketMessage(
            type="ping",
            data={"timestamp": datetime.now(timezone.utc).isoformat()},
            timestamp=datetime.now(timezone.utc)
        )
        
        dead_connections = []
        
        for connection_id, connection_info in self.connections.items():
            try:
                await connection_info.websocket.send_text(json.dumps(ping_message.to_dict()))
                connection_info.last_ping = datetime.now(timezone.utc)
            except Exception:
                dead_connections.append(connection_id)
        
        # Clean up dead connections
        for connection_id in dead_connections:
            await self.disconnect(connection_id)
        
        return len(dead_connections)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "active_connections": len(self.connections),
            "total_users": len(self.user_connections),
            "total_subscriptions": len(self.subscriptions),
            "messages_sent": self.stats["messages_sent"],
            "messages_failed": self.stats["messages_failed"],
            "total_connections": self.stats["total_connections"]
        }
    
    def get_user_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all connections for a user."""
        if user_id not in self.user_connections:
            return []
        
        user_conns = []
        for connection_id in self.user_connections[user_id]:
            if connection_id in self.connections:
                user_conns.append(self.connections[connection_id].to_dict())
        
        return user_conns
    
    async def shutdown(self):
        """Shutdown the WebSocket manager."""
        self.shutdown_event.set()
        
        # Cancel background tasks
        if self.broadcast_task:
            self.broadcast_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Close all connections
        for connection_id in list(self.connections.keys()):
            await self.disconnect(connection_id)
        
        logger.info("WebSocket manager shutdown complete")

# Global WebSocket manager instance
_websocket_manager: Optional[WebSocketManager] = None

def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global _websocket_manager
    
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    
    return _websocket_manager

# Helper functions
async def send_job_notification(user_id: str, job_id: str, status: str, progress: float = None):
    """Send job status notification."""
    manager = get_websocket_manager()
    await manager.send_job_status_update(user_id, job_id, status, progress)

async def send_upload_notification(user_id: str, document_id: str, filename: str, status: str):
    """Send upload notification."""
    manager = get_websocket_manager()
    await manager.send_document_upload_notification(user_id, document_id, filename, status)

async def send_system_alert(message: str, severity: str = "info", target_users: List[str] = None):
    """Send system alert."""
    manager = get_websocket_manager()
    await manager.send_system_alert(message, severity, target_users)

async def send_security_notification(user_id: str, event_type: str, details: Dict[str, Any]):
    """Send security notification."""
    manager = get_websocket_manager()
    await manager.send_security_event(user_id, event_type, details)

def get_websocket_stats() -> Dict[str, Any]:
    """Get WebSocket statistics."""
    manager = get_websocket_manager()
    return manager.get_connection_stats()

# Cleanup on shutdown
import atexit
atexit.register(lambda: asyncio.run(get_websocket_manager().shutdown()))
