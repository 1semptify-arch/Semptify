"""
Mesh Integration - Bridges existing services to the distributed mesh
====================================================================

This module:
1. Creates mesh nodes for each service
2. Registers capabilities (what each service can do)
3. Connects nodes in a peer-to-peer mesh
4. Provides migration path from centralized to distributed
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Callable
from functools import wraps

from app.core.distributed_mesh import (
    MeshNode,
    MeshCoordinator,
    mesh_coordinator,
    create_mesh_node,
    MessageType,
    MeshMessage,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SERVICE MESH NODES
# =============================================================================

class ServiceMeshRegistry:
    """
    Registry that creates and manages mesh nodes for all services.
    Each service gets its own node that can communicate directly with others.
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
        self._service_nodes: Dict[str, MeshNode] = {}
        self._started = False
        
        # Create nodes for all core services
        self._create_service_nodes()
        
        logger.info("📦 ServiceMeshRegistry initialized")
    
    def _create_service_nodes(self):
        """Create mesh nodes for each service"""
        
        # Legal Analysis Engine
        self._service_nodes["legal_analysis"] = create_mesh_node(
            node_type="legal_analysis",
            capabilities={
                "classify_evidence",
                "detect_hearsay",
                "analyze_timeline",
                "assess_merit",
                "find_defenses",
                "quick_case_check",
            }
        )
        
        # Document Engine
        self._service_nodes["documents"] = create_mesh_node(
            node_type="documents",
            capabilities={
                "upload_document",
                "extract_text",
                "extract_events",
                "classify_document",
                "search_documents",
                "get_document",
            }
        )
        
        # Timeline Service
        self._service_nodes["timeline"] = create_mesh_node(
            node_type="timeline",
            capabilities={
                "add_event",
                "get_timeline",
                "analyze_gaps",
                "find_conflicts",
                "build_narrative",
            }
        )
        
        # Calendar Service
        self._service_nodes["calendar"] = create_mesh_node(
            node_type="calendar",
            capabilities={
                "add_deadline",
                "get_deadlines",
                "calculate_deadline",
                "set_reminder",
            }
        )
        
        # Eviction Defense
        self._service_nodes["eviction"] = create_mesh_node(
            node_type="eviction",
            capabilities={
                "analyze_notice",
                "find_violations",
                "generate_defenses",
                "calculate_deadlines",
            }
        )
        
        # Court Learning - Bidirectional learning from court outcomes
        self._service_nodes["court_learning"] = create_mesh_node(
            node_type="court_learning",
            capabilities={
                "get_procedures",
                "learn_from_outcome",
                "suggest_strategy",
                "get_defense_rates",
                "get_judge_patterns",
                "get_landlord_patterns",
                "get_learning_stats",
                "seed_historical_data",
                "record_case_outcome",
                "recommend_strategy",
            }
        )
        
        # Forms Engine
        self._service_nodes["forms"] = create_mesh_node(
            node_type="forms",
            capabilities={
                "fill_form",
                "validate_form",
                "get_form_template",
            }
        )
        
        # Tenancy Hub
        self._service_nodes["tenancy"] = create_mesh_node(
            node_type="tenancy",
            capabilities={
                "store_info",
                "get_tenancy_data",
                "cross_reference",
                "extract_from_document",
            }
        )
        
        # Copilot/AI Assistant
        self._service_nodes["copilot"] = create_mesh_node(
            node_type="copilot",
            capabilities={
                "explain",
                "suggest_action",
                "answer_question",
                "generate_text",
            }
        )
        
        # UI/Notification Service
        self._service_nodes["ui"] = create_mesh_node(
            node_type="ui",
            capabilities={
                "notify",
                "update_dashboard",
                "show_alert",
            }
        )
        
        logger.info(f"🔷 Created {len(self._service_nodes)} service mesh nodes")
    
    def get_node(self, service_name: str) -> Optional[MeshNode]:
        """Get the mesh node for a service"""
        return self._service_nodes.get(service_name)
    
    def register_handler(
        self,
        service_name: str,
        capability: str,
        handler: Callable,
    ):
        """Register a handler for a service capability"""
        node = self._service_nodes.get(service_name)
        if node:
            node.register_handler(capability, handler)
        else:
            logger.warning(f"Service node not found: {service_name}")
    
    async def start_all(self):
        """Start all service nodes"""
        if self._started:
            return
        
        for node in self._service_nodes.values():
            await node.start()
        
        self._started = True
        logger.info("🟢 All service mesh nodes started")
    
    async def stop_all(self):
        """Stop all service nodes"""
        for node in self._service_nodes.values():
            await node.stop()
        
        self._started = False
        logger.info("🔴 All service mesh nodes stopped")
    
    def get_all_nodes(self) -> Dict[str, MeshNode]:
        """Get all service nodes"""
        return self._service_nodes.copy()


# Global registry instance
service_mesh = ServiceMeshRegistry()


# =============================================================================
# DECORATOR FOR MESH-ENABLED FUNCTIONS
# =============================================================================

def mesh_handler(service: str, capability: str):
    """
    Decorator to automatically register a function as a mesh handler.
    
    Usage:
        @mesh_handler("legal_analysis", "detect_hearsay")
        async def detect_hearsay(payload: Dict) -> Dict:
            # ... implementation
            return {"hearsay_found": True}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Register with mesh
        service_mesh.register_handler(service, capability, wrapper)
        
        return wrapper
    return decorator


def mesh_event(service: str, event_type: str):
    """
    Decorator to emit an event after function execution.
    
    Usage:
        @mesh_event("legal_analysis", "hearsay_detected")
        async def detect_hearsay(...):
            # ... 
            return result  # This will be emitted as event data
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Emit event to mesh
            node = service_mesh.get_node(service)
            if node:
                await node.emit_event(event_type, result or {})
            
            return result
        return wrapper
    return decorator


# =============================================================================
# BRIDGE FROM OLD BRAIN TO NEW MESH
# =============================================================================

class BrainMeshBridge:
    """
    Bridges the old PositronicBrain events to the new distributed mesh.
    Allows gradual migration without breaking existing code.
    """
    
    def __init__(self):
        self._brain = None
        self._forwarding_enabled = True
    
    def connect_brain(self, brain):
        """Connect to the old brain for event forwarding"""
        self._brain = brain
        logger.info("🌉 BrainMeshBridge connected to PositronicBrain")
    
    async def forward_brain_event_to_mesh(self, event_type: str, data: Dict[str, Any]):
        """Forward a brain event to the mesh"""
        if not self._forwarding_enabled:
            return
        
        # Determine which service this event came from
        service_map = {
            "legal.": "legal_analysis",
            "document.": "documents",
            "timeline.": "timeline",
            "calendar.": "calendar",
            "eviction.": "eviction",
            "court.": "court_learning",
        }
        
        service = "system"
        for prefix, svc in service_map.items():
            if event_type.startswith(prefix):
                service = svc
                break
        
        node = service_mesh.get_node(service)
        if node:
            await node.emit_event(event_type, data)
    
    async def forward_mesh_event_to_brain(
        self,
        event_type: str,
        data: Dict[str, Any],
        source_node: str,
    ):
        """Forward a mesh event to the brain for UI updates"""
        if self._brain and self._forwarding_enabled:
            try:
                await self._brain.emit_event(event_type, data)
            except Exception as e:
                logger.error(f"Failed to forward to brain: {e}")


# Global bridge instance
brain_mesh_bridge = BrainMeshBridge()


# =============================================================================
# STARTUP/SHUTDOWN
# =============================================================================

async def start_mesh_network():
    """Start the distributed mesh network"""
    await service_mesh.start_all()
    logger.info("🌐 Distributed mesh network started")


async def stop_mesh_network():
    """Stop the distributed mesh network"""
    await service_mesh.stop_all()
    logger.info("🌐 Distributed mesh network stopped")


# =============================================================================
# HELPER FUNCTIONS FOR SERVICES
# =============================================================================

async def mesh_call(capability: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a call to any service with the capability.
    The mesh will route to the appropriate node.
    """
    from app.core.distributed_mesh import mesh_request
    return await mesh_request(capability, payload)


def get_service_node(service_name: str) -> Optional[MeshNode]:
    """Get a specific service's mesh node"""
    return service_mesh.get_node(service_name)
