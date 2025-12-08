"""
Distributed Mesh Network - Peer-to-Peer Module Communication
============================================================

Replaces the centralized brain bottleneck with a distributed architecture:
- Modules communicate directly with each other (peer-to-peer)
- No single point of failure
- Horizontal scaling support
- Local-first processing with optional sync
- Event sourcing for state reconstruction

Architecture:
┌─────────┐     ┌─────────┐     ┌─────────┐
│ Legal   │◄───►│Documents│◄───►│Timeline │
│ Analysis│     │ Engine  │     │ Service │
└────┬────┘     └────┬────┘     └────┬────┘
     │               │               │
     └───────────────┼───────────────┘
                     │
              ┌──────▼──────┐
              │  Mesh Index │  (Discovery only, not routing)
              │  (Optional) │
              └─────────────┘
"""

import asyncio
import logging
import uuid
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Generic
from dataclasses import dataclass, field
from collections import defaultdict
from weakref import WeakSet
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# MESH NODE IDENTITY
# =============================================================================

@dataclass
class NodeIdentity:
    """Unique identity for each mesh node/module"""
    node_id: str
    node_type: str  # e.g., "legal_analysis", "documents", "timeline"
    capabilities: Set[str] = field(default_factory=set)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Network info
    direct_peers: Set[str] = field(default_factory=set)  # Node IDs of direct connections
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "capabilities": list(self.capabilities),
            "version": self.version,
            "direct_peers": list(self.direct_peers),
        }


# =============================================================================
# MESH MESSAGE PROTOCOL
# =============================================================================

class MessageType(str, Enum):
    """Types of messages in the mesh"""
    # Discovery
    ANNOUNCE = "announce"  # Node announcing itself
    DISCOVER = "discover"  # Looking for nodes with capability
    
    # Communication
    REQUEST = "request"  # Request to another node
    RESPONSE = "response"  # Response to a request
    EVENT = "event"  # Fire-and-forget event
    STREAM = "stream"  # Streaming data
    
    # Coordination
    SYNC = "sync"  # State synchronization
    HEARTBEAT = "heartbeat"  # Keep-alive
    
    # Workflow
    WORKFLOW_START = "workflow_start"
    WORKFLOW_STEP = "workflow_step"
    WORKFLOW_COMPLETE = "workflow_complete"


@dataclass
class MeshMessage:
    """Message passed between mesh nodes"""
    id: str
    type: MessageType
    source_node: str
    target_node: Optional[str]  # None = broadcast
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None  # For request/response matching
    ttl: int = 5  # Hops before message dies
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "ttl": self.ttl,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeshMessage":
        return cls(
            id=data["id"],
            type=MessageType(data["type"]),
            source_node=data["source_node"],
            target_node=data.get("target_node"),
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            ttl=data.get("ttl", 5),
        )


# =============================================================================
# LOCAL MESSAGE QUEUE (Per-Node)
# =============================================================================

class LocalMessageQueue:
    """In-memory message queue for a single node"""
    
    def __init__(self, max_size: int = 10000):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self._processing = False
    
    async def enqueue(self, message: MeshMessage):
        """Add message to queue"""
        await self.queue.put(message)
    
    async def dequeue(self, timeout: float = 1.0) -> Optional[MeshMessage]:
        """Get message from queue"""
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def register_response_handler(self, correlation_id: str) -> asyncio.Future:
        """Register a future to receive a response"""
        future = asyncio.get_event_loop().create_future()
        self.pending_responses[correlation_id] = future
        return future
    
    def resolve_response(self, correlation_id: str, response: MeshMessage):
        """Resolve a pending response future"""
        if correlation_id in self.pending_responses:
            future = self.pending_responses.pop(correlation_id)
            if not future.done():
                future.set_result(response)


# =============================================================================
# MESH NODE - The Core Unit
# =============================================================================

class MeshNode:
    """
    A single node in the distributed mesh.
    
    Each module/service becomes a MeshNode that can:
    - Communicate directly with other nodes
    - Handle requests without going through central hub
    - Publish events that interested nodes receive
    - Participate in distributed workflows
    """
    
    def __init__(
        self,
        node_type: str,
        capabilities: Optional[Set[str]] = None,
        node_id: Optional[str] = None,
    ):
        self.identity = NodeIdentity(
            node_id=node_id or f"{node_type}_{uuid.uuid4().hex[:8]}",
            node_type=node_type,
            capabilities=capabilities or set(),
        )
        
        # Message handling
        self.message_queue = LocalMessageQueue()
        self._handlers: Dict[str, Callable] = {}  # capability -> handler
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Peer connections (direct references to other nodes)
        self._peers: Dict[str, "MeshNode"] = {}  # node_id -> MeshNode
        
        # Capability index (which peer has what capability)
        self._capability_index: Dict[str, Set[str]] = defaultdict(set)  # capability -> node_ids
        
        # State
        self._running = False
        self._message_processor_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "requests_handled": 0,
            "avg_response_time_ms": 0,
        }
        
        logger.info(f"🔷 MeshNode created: {self.identity.node_id} ({node_type})")
    
    # =========================================================================
    # PEER MANAGEMENT (Direct Connections)
    # =========================================================================
    
    def connect_peer(self, peer: "MeshNode"):
        """Establish direct connection to another node"""
        if peer.identity.node_id == self.identity.node_id:
            return  # Don't connect to self
        
        self._peers[peer.identity.node_id] = peer
        self.identity.direct_peers.add(peer.identity.node_id)
        
        # Index peer's capabilities
        for cap in peer.identity.capabilities:
            self._capability_index[cap].add(peer.identity.node_id)
        
        # Reciprocal connection
        if self.identity.node_id not in peer._peers:
            peer.connect_peer(self)
        
        logger.debug(f"🔗 {self.identity.node_id} connected to {peer.identity.node_id}")
    
    def disconnect_peer(self, peer_id: str):
        """Disconnect from a peer"""
        if peer_id in self._peers:
            peer = self._peers.pop(peer_id)
            self.identity.direct_peers.discard(peer_id)
            
            # Remove from capability index
            for cap in peer.identity.capabilities:
                self._capability_index[cap].discard(peer_id)
    
    def find_peers_with_capability(self, capability: str) -> List["MeshNode"]:
        """Find all connected peers with a specific capability"""
        peer_ids = self._capability_index.get(capability, set())
        return [self._peers[pid] for pid in peer_ids if pid in self._peers]
    
    # =========================================================================
    # HANDLER REGISTRATION
    # =========================================================================
    
    def register_handler(self, capability: str, handler: Callable):
        """Register a handler for a capability"""
        self._handlers[capability] = handler
        self.identity.capabilities.add(capability)
        logger.debug(f"⚡ {self.identity.node_id} registered handler: {capability}")
    
    def on_event(self, event_type: str, handler: Callable):
        """Subscribe to events of a specific type"""
        self._event_handlers[event_type].append(handler)
    
    # =========================================================================
    # MESSAGE SENDING (Peer-to-Peer)
    # =========================================================================
    
    async def send_to_peer(self, peer_id: str, message: MeshMessage):
        """Send message directly to a specific peer"""
        if peer_id not in self._peers:
            raise ValueError(f"Peer not connected: {peer_id}")
        
        peer = self._peers[peer_id]
        message.ttl -= 1
        
        if message.ttl <= 0:
            logger.warning(f"Message TTL expired: {message.id}")
            return
        
        await peer.receive_message(message)
        self.metrics["messages_sent"] += 1
    
    async def broadcast(self, message: MeshMessage):
        """Broadcast message to all connected peers"""
        tasks = []
        for peer in self._peers.values():
            msg_copy = MeshMessage(
                id=message.id,
                type=message.type,
                source_node=message.source_node,
                target_node=None,
                payload=message.payload,
                correlation_id=message.correlation_id,
                ttl=message.ttl - 1,
            )
            if msg_copy.ttl > 0:
                tasks.append(peer.receive_message(msg_copy))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.metrics["messages_sent"] += len(tasks)
    
    async def request(
        self,
        capability: str,
        payload: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Send a request to any peer with the capability and wait for response.
        This is the main P2P communication method.
        """
        peers = self.find_peers_with_capability(capability)
        
        if not peers:
            raise ValueError(f"No peers with capability: {capability}")
        
        # Round-robin or first available
        peer = peers[0]
        
        correlation_id = f"req_{uuid.uuid4().hex[:12]}"
        message = MeshMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            type=MessageType.REQUEST,
            source_node=self.identity.node_id,
            target_node=peer.identity.node_id,
            payload={"capability": capability, **payload},
            correlation_id=correlation_id,
        )
        
        # Register response handler
        response_future = self.message_queue.register_response_handler(correlation_id)
        
        # Send request
        start_time = time.time()
        await self.send_to_peer(peer.identity.node_id, message)
        
        # Wait for response
        try:
            response = await asyncio.wait_for(response_future, timeout=timeout)
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            self.metrics["avg_response_time_ms"] = int(
                self.metrics["avg_response_time_ms"] * 0.9 + elapsed_ms * 0.1
            )
            
            return response.payload
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request to {capability} timed out after {timeout}s")
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to all interested peers"""
        message = MeshMessage(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            type=MessageType.EVENT,
            source_node=self.identity.node_id,
            target_node=None,
            payload={"event_type": event_type, "data": data},
        )
        await self.broadcast(message)
    
    # =========================================================================
    # MESSAGE RECEIVING
    # =========================================================================
    
    async def receive_message(self, message: MeshMessage):
        """Receive a message from another node"""
        self.metrics["messages_received"] += 1
        await self.message_queue.enqueue(message)
    
    async def _process_messages(self):
        """Background task to process incoming messages"""
        while self._running:
            message = await self.message_queue.dequeue()
            if message is None:
                continue
            
            try:
                await self._handle_message(message)
            except Exception as e:
                logger.error(f"Error processing message {message.id}: {e}")
    
    async def _handle_message(self, message: MeshMessage):
        """Handle a single message based on its type"""
        
        if message.type == MessageType.REQUEST:
            await self._handle_request(message)
        
        elif message.type == MessageType.RESPONSE:
            # Resolve pending response future
            if message.correlation_id:
                self.message_queue.resolve_response(message.correlation_id, message)
        
        elif message.type == MessageType.EVENT:
            await self._handle_event(message)
        
        elif message.type == MessageType.ANNOUNCE:
            # Peer announced - update capability index
            peer_id = message.source_node
            if peer_id in self._peers:
                caps = message.payload.get("capabilities", [])
                for cap in caps:
                    self._capability_index[cap].add(peer_id)
        
        elif message.type == MessageType.HEARTBEAT:
            # Just acknowledge
            pass
    
    async def _handle_request(self, message: MeshMessage):
        """Handle an incoming request"""
        capability = message.payload.get("capability")
        
        if capability not in self._handlers:
            # Send error response
            response = MeshMessage(
                id=f"msg_{uuid.uuid4().hex[:12]}",
                type=MessageType.RESPONSE,
                source_node=self.identity.node_id,
                target_node=message.source_node,
                payload={"error": f"No handler for capability: {capability}"},
                correlation_id=message.correlation_id,
            )
        else:
            # Execute handler
            handler = self._handlers[capability]
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(message.payload)
                else:
                    result = handler(message.payload)
                
                response = MeshMessage(
                    id=f"msg_{uuid.uuid4().hex[:12]}",
                    type=MessageType.RESPONSE,
                    source_node=self.identity.node_id,
                    target_node=message.source_node,
                    payload=result or {},
                    correlation_id=message.correlation_id,
                )
                self.metrics["requests_handled"] += 1
            except Exception as e:
                response = MeshMessage(
                    id=f"msg_{uuid.uuid4().hex[:12]}",
                    type=MessageType.RESPONSE,
                    source_node=self.identity.node_id,
                    target_node=message.source_node,
                    payload={"error": str(e)},
                    correlation_id=message.correlation_id,
                )
        
        # Send response back
        if message.source_node in self._peers:
            await self.send_to_peer(message.source_node, response)
    
    async def _handle_event(self, message: MeshMessage):
        """Handle an incoming event"""
        event_type = message.payload.get("event_type")
        data = message.payload.get("data", {})
        
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_type, data, message.source_node)
                    else:
                        handler(event_type, data, message.source_node)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
    
    # =========================================================================
    # LIFECYCLE
    # =========================================================================
    
    async def start(self):
        """Start the node's message processor"""
        if self._running:
            return
        
        self._running = True
        self._message_processor_task = asyncio.create_task(self._process_messages())
        logger.info(f"🟢 MeshNode started: {self.identity.node_id}")
    
    async def stop(self):
        """Stop the node"""
        self._running = False
        if self._message_processor_task:
            self._message_processor_task.cancel()
            try:
                await self._message_processor_task
            except asyncio.CancelledError:
                pass
        logger.info(f"🔴 MeshNode stopped: {self.identity.node_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get node status"""
        return {
            "identity": self.identity.to_dict(),
            "peers_connected": len(self._peers),
            "capabilities": list(self.identity.capabilities),
            "metrics": self.metrics,
            "running": self._running,
        }


# =============================================================================
# MESH COORDINATOR (Optional - for discovery only)
# =============================================================================

class MeshCoordinator:
    """
    Optional coordinator for node discovery.
    NOT a central router - just helps nodes find each other.
    Nodes still communicate directly peer-to-peer.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        
        self._initialized = True
        self._nodes: Dict[str, MeshNode] = {}  # node_id -> MeshNode
        self._capability_registry: Dict[str, Set[str]] = defaultdict(set)  # capability -> node_ids
        self._websocket_observers: Set[Any] = WeakSet()  # For UI visualization
        
        logger.info("🌐 MeshCoordinator initialized (discovery service)")
    
    def register_node(self, node: MeshNode):
        """Register a node for discovery"""
        self._nodes[node.identity.node_id] = node
        
        for cap in node.identity.capabilities:
            self._capability_registry[cap].add(node.identity.node_id)
        
        # Auto-connect to all existing nodes (full mesh)
        for existing_node in self._nodes.values():
            if existing_node.identity.node_id != node.identity.node_id:
                node.connect_peer(existing_node)
        
        logger.info(f"📍 Node registered: {node.identity.node_id}")
    
    def unregister_node(self, node_id: str):
        """Unregister a node"""
        if node_id in self._nodes:
            node = self._nodes.pop(node_id)
            for cap in node.identity.capabilities:
                self._capability_registry[cap].discard(node_id)
    
    def find_nodes_with_capability(self, capability: str) -> List[MeshNode]:
        """Find nodes that have a specific capability"""
        node_ids = self._capability_registry.get(capability, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]
    
    def get_all_nodes(self) -> List[MeshNode]:
        """Get all registered nodes"""
        return list(self._nodes.values())
    
    def get_mesh_topology(self) -> Dict[str, Any]:
        """Get the mesh topology for visualization"""
        nodes = []
        edges = []
        
        for node in self._nodes.values():
            nodes.append({
                "id": node.identity.node_id,
                "type": node.identity.node_type,
                "capabilities": list(node.identity.capabilities),
                "metrics": node.metrics,
            })
            
            for peer_id in node.identity.direct_peers:
                # Avoid duplicate edges
                edge_id = tuple(sorted([node.identity.node_id, peer_id]))
                edge = {"source": edge_id[0], "target": edge_id[1]}
                if edge not in edges:
                    edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_connections": len(edges),
        }
    
    def add_websocket_observer(self, ws):
        """Add a WebSocket for mesh visualization"""
        self._websocket_observers.add(ws)
    
    async def broadcast_mesh_update(self):
        """Broadcast mesh topology to all observers"""
        topology = self.get_mesh_topology()
        message = json.dumps({"type": "mesh_update", "data": topology})
        
        for ws in list(self._websocket_observers):
            try:
                await ws.send_text(message)
            except Exception:
                self._websocket_observers.discard(ws)


# Global coordinator instance
mesh_coordinator = MeshCoordinator()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_mesh_node(
    node_type: str,
    capabilities: Optional[Set[str]] = None,
    auto_register: bool = True,
) -> MeshNode:
    """Create and optionally register a new mesh node"""
    node = MeshNode(node_type, capabilities)
    
    if auto_register:
        mesh_coordinator.register_node(node)
    
    return node


async def mesh_request(
    capability: str,
    payload: Dict[str, Any],
    source_node: Optional[MeshNode] = None,
) -> Dict[str, Any]:
    """
    Make a request to any node with the capability.
    If no source_node provided, finds one automatically.
    """
    nodes = mesh_coordinator.find_nodes_with_capability(capability)
    
    if not nodes:
        raise ValueError(f"No nodes with capability: {capability}")
    
    target = nodes[0]
    
    if source_node:
        return await source_node.request(capability, payload)
    else:
        # Direct invocation for convenience
        handler = target._handlers.get(capability)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(payload)
            return handler(payload)
        raise ValueError(f"Handler not found for: {capability}")


def get_mesh_status() -> Dict[str, Any]:
    """Get overall mesh status"""
    topology = mesh_coordinator.get_mesh_topology()
    
    total_messages = sum(n.metrics["messages_sent"] for n in mesh_coordinator.get_all_nodes())
    total_requests = sum(n.metrics["requests_handled"] for n in mesh_coordinator.get_all_nodes())
    
    return {
        **topology,
        "total_messages_sent": total_messages,
        "total_requests_handled": total_requests,
        "capabilities_available": list(mesh_coordinator._capability_registry.keys()),
    }
