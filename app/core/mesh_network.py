"""
Mesh Network - True Bidirectional Module Communication
======================================================

Enables:
1. Module-to-Module direct calls (via the mesh)
2. Parallel multi-module requests (fan-out)
3. Collaborative responses (fan-in/merge)
4. Dependency-aware execution (DAG)
5. Real-time module state sharing

Example: Documents module needs info from Calendar + Eviction + Law Library
         to build a complete case summary - all in ONE request.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

logger = logging.getLogger(__name__)


# =============================================================================
# MESH REQUEST/RESPONSE TYPES
# =============================================================================

class RequestType(str, Enum):
    """Types of inter-module requests"""
    QUERY = "query"           # Read-only request
    ACTION = "action"         # State-changing action
    SUBSCRIBE = "subscribe"   # Subscribe to updates
    BROADCAST = "broadcast"   # Notify all modules
    COLLABORATE = "collaborate"  # Multi-module collaboration


class MergeStrategy(str, Enum):
    """How to merge results from multiple modules"""
    COMBINE = "combine"       # Combine all results into one dict
    FIRST = "first"           # Return first successful result
    ALL = "all"               # Return all results as array
    PRIORITY = "priority"     # Use priority ordering
    CHAIN = "chain"           # Pass result to next module


@dataclass
class MeshRequest:
    """A request that can span multiple modules"""
    id: str
    source_module: str            # Who's asking
    target_modules: List[str]     # Who to ask (can be multiple)
    request_type: RequestType
    action: str                   # What action/query
    payload: Dict[str, Any]       # The data
    merge_strategy: MergeStrategy = MergeStrategy.COMBINE
    timeout_seconds: float = 30.0
    require_all: bool = False     # All must succeed?
    priority: int = 5             # 1-10, higher = more urgent
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MeshResponse:
    """Response from one or more modules"""
    request_id: str
    source_modules: List[str]     # Who responded
    success: bool
    data: Dict[str, Any]          # Merged/combined data
    individual_responses: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# MODULE CAPABILITY REGISTRY
# =============================================================================

@dataclass
class ModuleCapability:
    """What a module can do"""
    module_id: str
    name: str
    capabilities: List[str]       # List of actions this module can perform
    provides: List[str]           # Data types this module can provide
    requires: List[str]           # Data types this module needs
    can_collaborate: bool = True  # Can participate in multi-module requests
    priority: int = 5             # Default priority


# =============================================================================
# MESH NETWORK ENGINE
# =============================================================================

class MeshNetwork:
    """
    The neural network connecting all modules.
    
    Enables true bidirectional, multi-module communication:
    - Any module can call any other module(s)
    - Requests can fan-out to multiple modules in parallel
    - Results automatically merge back together
    - Modules can collaborate on complex requests
    """
    
    def __init__(self):
        # Module registry
        self._modules: Dict[str, ModuleCapability] = {}
        self._handlers: Dict[str, Dict[str, Callable]] = {}  # module -> action -> handler
        
        # Request tracking
        self._pending_requests: Dict[str, MeshRequest] = {}
        self._request_history: List[Dict[str, Any]] = []
        
        # Collaboration sessions
        self._collaborations: Dict[str, Dict[str, Any]] = {}
        
        # Event subscribers
        self._subscribers: Dict[str, List[Callable]] = {}  # event_type -> handlers
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "parallel_requests": 0,
            "collaborative_requests": 0,
            "avg_response_time_ms": 0.0
        }
        
        logger.info("🕸️ Mesh Network initialized")
    
    # =========================================================================
    # MODULE REGISTRATION
    # =========================================================================
    
    def register_module(
        self,
        module_id: str,
        name: str,
        capabilities: List[str],
        provides: Optional[List[str]] = None,
        requires: Optional[List[str]] = None
    ) -> None:
        """Register a module with its capabilities."""
        self._modules[module_id] = ModuleCapability(
            module_id=module_id,
            name=name,
            capabilities=capabilities,
            provides=provides or [],
            requires=requires or []
        )
        self._handlers[module_id] = {}
        logger.info(f"🔌 Module '{name}' ({module_id}) registered with {len(capabilities)} capabilities")
    
    def register_handler(
        self,
        module_id: str,
        action: str,
        handler: Callable
    ) -> None:
        """Register an action handler for a module."""
        if module_id not in self._handlers:
            self._handlers[module_id] = {}
        self._handlers[module_id][action] = handler
        logger.debug(f"   → Handler registered: {module_id}.{action}")
    
    # =========================================================================
    # SINGLE MODULE CALLS
    # =========================================================================
    
    async def call(
        self,
        source: str,
        target: str,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> MeshResponse:
        """
        Simple call from one module to another.
        
        Example:
            response = await mesh.call(
                source="documents",
                target="calendar",
                action="get_deadlines",
                payload={"case_id": "123"}
            )
        """
        request = MeshRequest(
            id=f"req_{uuid.uuid4().hex[:12]}",
            source_module=source,
            target_modules=[target],
            request_type=RequestType.QUERY,
            action=action,
            payload=payload or {},
            timeout_seconds=timeout
        )
        
        return await self._execute_request(request)
    
    # =========================================================================
    # PARALLEL MULTI-MODULE CALLS (FAN-OUT)
    # =========================================================================
    
    async def call_many(
        self,
        source: str,
        targets: List[str],
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        merge: MergeStrategy = MergeStrategy.COMBINE,
        require_all: bool = False,
        timeout: float = 30.0
    ) -> MeshResponse:
        """
        Call multiple modules in parallel and merge results.
        
        Example:
            # Get info from 3 modules at once
            response = await mesh.call_many(
                source="copilot",
                targets=["documents", "calendar", "eviction_defense"],
                action="get_case_summary",
                payload={"user_id": "123"},
                merge=MergeStrategy.COMBINE
            )
            # response.data contains merged data from all 3 modules
        """
        request = MeshRequest(
            id=f"req_{uuid.uuid4().hex[:12]}",
            source_module=source,
            target_modules=targets,
            request_type=RequestType.QUERY,
            action=action,
            payload=payload or {},
            merge_strategy=merge,
            require_all=require_all,
            timeout_seconds=timeout
        )
        
        self._stats["parallel_requests"] += 1
        return await self._execute_request(request)
    
    # =========================================================================
    # COLLABORATIVE REQUESTS (MODULES WORK TOGETHER)
    # =========================================================================
    
    async def collaborate(
        self,
        source: str,
        modules: List[str],
        goal: str,
        initial_data: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0
    ) -> MeshResponse:
        """
        Start a collaborative session where modules work together.
        
        The first module processes, passes to next, each adding their piece.
        Like an assembly line, but each module can also call back to others.
        
        Example:
            # Build complete eviction defense - modules collaborate
            response = await mesh.collaborate(
                source="main",
                modules=["documents", "eviction_defense", "calendar", "forms", "copilot"],
                goal="build_eviction_defense",
                initial_data={"document_id": "123", "user_id": "456"}
            )
            # Each module adds their analysis, final result is complete defense package
        """
        collaboration_id = f"collab_{uuid.uuid4().hex[:12]}"
        
        self._collaborations[collaboration_id] = {
            "id": collaboration_id,
            "source": source,
            "modules": modules,
            "goal": goal,
            "stage": "initializing",
            "current_module_index": 0,
            "shared_context": initial_data or {},
            "module_contributions": {},
            "started_at": datetime.utcnow(),
            "completed_at": None
        }
        
        self._stats["collaborative_requests"] += 1
        
        try:
            result = await self._execute_collaboration(collaboration_id, timeout)
            self._collaborations[collaboration_id]["stage"] = "completed"
            self._collaborations[collaboration_id]["completed_at"] = datetime.utcnow()
            return result
        except Exception as e:
            self._collaborations[collaboration_id]["stage"] = "failed"
            logger.error(f"Collaboration {collaboration_id} failed: {e}")
            return MeshResponse(
                request_id=collaboration_id,
                source_modules=modules,
                success=False,
                data={},
                errors={"collaboration": str(e)}
            )
    
    async def _execute_collaboration(
        self,
        collaboration_id: str,
        timeout: float
    ) -> MeshResponse:
        """Execute a collaborative session."""
        collab = self._collaborations[collaboration_id]
        modules = collab["modules"]
        goal = collab["goal"]
        context = collab["shared_context"]
        
        start_time = datetime.utcnow()
        
        # Process through each module in sequence
        # Each module can add to the shared context
        for i, module_id in enumerate(modules):
            collab["current_module_index"] = i
            collab["stage"] = f"processing_{module_id}"
            
            # Check if module has handler for this goal
            handler = self._handlers.get(module_id, {}).get(goal)
            if not handler:
                # Try generic "contribute" handler
                handler = self._handlers.get(module_id, {}).get("contribute")
            
            if handler:
                try:
                    # Call the module with shared context
                    if asyncio.iscoroutinefunction(handler):
                        contribution = await asyncio.wait_for(
                            handler(context, goal),
                            timeout=timeout / len(modules)
                        )
                    else:
                        contribution = handler(context, goal)
                    
                    # Merge contribution into context
                    if isinstance(contribution, dict):
                        context.update(contribution)
                        collab["module_contributions"][module_id] = contribution
                        logger.info(f"   ✓ {module_id} contributed {len(contribution)} fields")
                    
                except asyncio.TimeoutError:
                    logger.warning(f"   ⚠ {module_id} timed out")
                    collab["module_contributions"][module_id] = {"error": "timeout"}
                except Exception as e:
                    logger.error(f"   ✗ {module_id} error: {e}")
                    collab["module_contributions"][module_id] = {"error": str(e)}
            else:
                logger.debug(f"   - {module_id} has no handler for '{goal}'")
        
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return MeshResponse(
            request_id=collaboration_id,
            source_modules=modules,
            success=True,
            data=context,
            individual_responses=collab["module_contributions"],
            execution_time_ms=execution_time
        )
    
    # =========================================================================
    # BROADCAST (NOTIFY ALL MODULES)
    # =========================================================================
    
    async def broadcast(
        self,
        source: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> int:
        """
        Broadcast an event to all modules that care about it.
        
        Example:
            # Notify everyone that a deadline is approaching
            await mesh.broadcast(
                source="calendar",
                event_type="deadline_approaching",
                data={"deadline_id": "123", "days_remaining": 3}
            )
        """
        handlers = self._subscribers.get(event_type, [])
        notified = 0
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(source, data)
                else:
                    handler(source, data)
                notified += 1
            except Exception as e:
                logger.error(f"Broadcast handler error: {e}")
        
        logger.info(f"📢 Broadcast '{event_type}' from {source} → {notified} handlers")
        return notified
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to broadcast events."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    # =========================================================================
    # REQUEST EXECUTION
    # =========================================================================
    
    async def _execute_request(self, request: MeshRequest) -> MeshResponse:
        """Execute a mesh request."""
        self._stats["total_requests"] += 1
        self._pending_requests[request.id] = request
        start_time = datetime.utcnow()
        
        try:
            targets = request.target_modules
            
            if len(targets) == 1:
                # Single target - simple call
                result = await self._call_module(
                    targets[0],
                    request.action,
                    request.payload,
                    request.timeout_seconds
                )
                individual = {targets[0]: result}
                merged = result if isinstance(result, dict) else {"result": result}
                success = not isinstance(result, dict) or "error" not in result
                
            else:
                # Multiple targets - parallel execution
                tasks = [
                    self._call_module(
                        target,
                        request.action,
                        request.payload,
                        request.timeout_seconds
                    )
                    for target in targets
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Build individual responses
                individual = {}
                errors = {}
                for target, result in zip(targets, results):
                    if isinstance(result, Exception):
                        errors[target] = str(result)
                        individual[target] = {"error": str(result)}
                    else:
                        individual[target] = result
                
                # Merge results based on strategy
                merged = self._merge_results(
                    individual,
                    request.merge_strategy,
                    request.require_all
                )
                
                success = len(errors) == 0 or (not request.require_all and len(errors) < len(targets))
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_stats(execution_time, success)
            
            return MeshResponse(
                request_id=request.id,
                source_modules=targets,
                success=success,
                data=merged,
                individual_responses=individual,
                errors=errors if 'errors' in dir() else {},
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._stats["failed_requests"] += 1
            logger.error(f"Request {request.id} failed: {e}")
            return MeshResponse(
                request_id=request.id,
                source_modules=request.target_modules,
                success=False,
                data={},
                errors={"general": str(e)}
            )
        finally:
            del self._pending_requests[request.id]
    
    async def _call_module(
        self,
        module_id: str,
        action: str,
        payload: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """Call a single module's action handler."""
        handler = self._handlers.get(module_id, {}).get(action)
        
        if not handler:
            # Try wildcard handler
            handler = self._handlers.get(module_id, {}).get("*")
        
        if not handler:
            return {"error": f"No handler for {module_id}.{action}"}
        
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(payload),
                    timeout=timeout
                )
            else:
                result = handler(payload)
            
            return result if isinstance(result, dict) else {"result": result}
            
        except asyncio.TimeoutError:
            return {"error": "timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    def _merge_results(
        self,
        results: Dict[str, Any],
        strategy: MergeStrategy,
        require_all: bool
    ) -> Dict[str, Any]:
        """Merge results from multiple modules."""
        
        if strategy == MergeStrategy.ALL:
            return {"modules": results}
        
        elif strategy == MergeStrategy.FIRST:
            for module, result in results.items():
                if isinstance(result, dict) and "error" not in result:
                    return result
            return {"error": "All modules failed"}
        
        elif strategy == MergeStrategy.COMBINE:
            merged = {}
            for module, result in results.items():
                if isinstance(result, dict) and "error" not in result:
                    # Prefix keys with module name if there are conflicts
                    for key, value in result.items():
                        if key in merged:
                            merged[f"{module}_{key}"] = value
                        else:
                            merged[key] = value
            return merged
        
        elif strategy == MergeStrategy.PRIORITY:
            # Results from earlier modules take precedence
            merged = {}
            for module, result in results.items():
                if isinstance(result, dict) and "error" not in result:
                    for key, value in result.items():
                        if key not in merged:
                            merged[key] = value
            return merged
        
        return results
    
    def _update_stats(self, execution_time_ms: float, success: bool) -> None:
        """Update statistics."""
        if success:
            self._stats["successful_requests"] += 1
        else:
            self._stats["failed_requests"] += 1
        
        # Rolling average
        total = self._stats["total_requests"]
        current_avg = self._stats["avg_response_time_ms"]
        self._stats["avg_response_time_ms"] = (
            (current_avg * (total - 1) + execution_time_ms) / total
        )
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    async def ask(
        self,
        question: str,
        from_module: str = "user",
        context: Optional[Dict[str, Any]] = None
    ) -> MeshResponse:
        """
        High-level: Ask the mesh a question, it figures out which modules to ask.
        
        Example:
            response = await mesh.ask(
                "What are my upcoming deadlines?",
                context={"user_id": "123"}
            )
        """
        # Determine which modules can answer this
        relevant_modules = self._find_relevant_modules(question)
        
        if not relevant_modules:
            return MeshResponse(
                request_id=f"ask_{uuid.uuid4().hex[:8]}",
                source_modules=[],
                success=False,
                data={},
                errors={"message": "No modules can answer this question"}
            )
        
        return await self.call_many(
            source=from_module,
            targets=relevant_modules,
            action="answer_question",
            payload={"question": question, **(context or {})},
            merge=MergeStrategy.COMBINE
        )
    
    def _find_relevant_modules(self, question: str) -> List[str]:
        """Find modules that might be able to answer a question."""
        question_lower = question.lower()
        relevant = []
        
        keywords = {
            "documents": ["document", "file", "upload", "pdf", "lease"],
            "calendar": ["deadline", "date", "schedule", "when", "upcoming"],
            "eviction_defense": ["eviction", "defense", "landlord", "tenant", "court"],
            "forms": ["form", "fill", "answer", "response", "motion"],
            "copilot": ["help", "what", "how", "explain", "suggest"],
            "law_library": ["law", "statute", "legal", "rights", "regulation"],
            "timeline": ["timeline", "history", "events", "chronological"],
            "vault": ["secure", "private", "encrypt", "sensitive"],
            "zoom_court": ["zoom", "hearing", "video", "virtual", "court"],
            "context": ["context", "situation", "status", "overview"],
            "ui": ["display", "show", "view", "interface"]
        }
        
        for module, words in keywords.items():
            if module in self._modules:
                if any(word in question_lower for word in words):
                    relevant.append(module)
        
        return relevant or list(self._modules.keys())[:3]  # Default to first 3
    
    # =========================================================================
    # STATUS & DEBUGGING
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get mesh network status."""
        return {
            "modules_connected": len(self._modules),
            "total_handlers": sum(len(h) for h in self._handlers.values()),
            "pending_requests": len(self._pending_requests),
            "active_collaborations": len([
                c for c in self._collaborations.values()
                if c["stage"] not in ["completed", "failed"]
            ]),
            "event_subscribers": sum(len(s) for s in self._subscribers.values()),
            "statistics": self._stats,
            "modules": {
                mid: {
                    "name": m.name,
                    "capabilities": m.capabilities,
                    "handlers": list(self._handlers.get(mid, {}).keys())
                }
                for mid, m in self._modules.items()
            }
        }
    
    def get_module_graph(self) -> Dict[str, Any]:
        """Get a graph of module connections/dependencies."""
        graph = {"nodes": [], "edges": []}
        
        for mid, module in self._modules.items():
            graph["nodes"].append({
                "id": mid,
                "name": module.name,
                "capabilities": len(module.capabilities)
            })
            
            # Add edges based on provides/requires
            for required in module.requires:
                # Find module that provides this
                for other_mid, other_module in self._modules.items():
                    if required in other_module.provides:
                        graph["edges"].append({
                            "from": other_mid,
                            "to": mid,
                            "type": required
                        })
        
        return graph


# =============================================================================
# GLOBAL MESH INSTANCE
# =============================================================================

_mesh_network: Optional[MeshNetwork] = None


def get_mesh_network() -> MeshNetwork:
    """Get the global mesh network instance."""
    global _mesh_network
    if _mesh_network is None:
        _mesh_network = MeshNetwork()
    return _mesh_network


def init_mesh_network() -> MeshNetwork:
    """Initialize a fresh mesh network."""
    global _mesh_network
    _mesh_network = MeshNetwork()
    return _mesh_network


# =============================================================================
# DECORATORS FOR EASY MODULE REGISTRATION
# =============================================================================

def mesh_handler(module_id: str, action: str):
    """
    Decorator to register a function as a mesh handler.
    
    Example:
        @mesh_handler("calendar", "get_deadlines")
        async def handle_get_deadlines(payload: dict) -> dict:
            return {"deadlines": [...]}
    """
    def decorator(func: Callable):
        mesh = get_mesh_network()
        mesh.register_handler(module_id, action, func)
        return func
    return decorator


def mesh_contributor(module_id: str):
    """
    Decorator for collaborative contribution handlers.
    
    Example:
        @mesh_contributor("eviction_defense")
        async def contribute(context: dict, goal: str) -> dict:
            # Add our analysis to the shared context
            return {"defense_analysis": {...}}
    """
    def decorator(func: Callable):
        mesh = get_mesh_network()
        mesh.register_handler(module_id, "contribute", func)
        return func
    return decorator
