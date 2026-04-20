"""Mesh Action Deferral System

Queues actions that were skipped in lean mode for potential
re-execution when mesh switches to full mode.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DeferredAction:
    """Record of an action that was deferred."""
    module: str
    action: str
    user_id: str
    params: Dict[str, Any]
    context: Dict[str, Any]
    deferred_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 3


class ActionDeferralQueue:
    """Queue for actions deferred due to lean mesh mode."""
    
    def __init__(self):
        self._deferred: List[DeferredAction] = []
        self._lock = asyncio.Lock()
    
    async def defer(
        self,
        module: str,
        action: str,
        user_id: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        """Record a deferred action."""
        async with self._lock:
            deferred = DeferredAction(
                module=module,
                action=action,
                user_id=user_id,
                params=params,
                context=context,
            )
            self._deferred.append(deferred)
            logger.info(f"📥 Deferred: {module}.{action} for user {user_id[:8]}...")
    
    async def get_pending(self) -> List[DeferredAction]:
        """Get all pending deferred actions."""
        async with self._lock:
            return list(self._deferred)
    
    async def remove(self, deferred: DeferredAction) -> None:
        """Remove a deferred action from queue (after successful execution)."""
        async with self._lock:
            if deferred in self._deferred:
                self._deferred.remove(deferred)
    
    async def retry_all(self, mesh) -> Dict[str, Any]:
        """Retry all deferred actions through the mesh.
        
        Returns summary of results.
        """
        from app.core.mesh_config import FULL_MESH_CONFIG
        
        async with self._lock:
            pending = list(self._deferred)
            if not pending:
                return {"attempted": 0, "succeeded": 0, "failed": 0}
            
            results = {"attempted": 0, "succeeded": 0, "failed": 0, "still_deferred": []}
            
            for action in pending:
                # Only retry if we've switched to full mode
                from app.core.mesh_config import get_mesh_config
                if get_mesh_config().mode != "full":
                    results["still_deferred"].append(f"{action.module}.{action.action}")
                    continue
                
                results["attempted"] += 1
                try:
                    await mesh.invoke_module(
                        action.module,
                        action.action,
                        action.user_id,
                        action.params,
                    )
                    self._deferred.remove(action)
                    results["succeeded"] += 1
                    logger.info(f"✅ Retried deferred action succeeded: {action.module}.{action.action}")
                except Exception as e:
                    action.retry_count += 1
                    if action.retry_count >= action.max_retries:
                        self._deferred.remove(action)
                        logger.error(f"❌ Deferred action exhausted retries: {action.module}.{action.action}: {e}")
                    else:
                        results["still_deferred"].append(f"{action.module}.{action.action}")
                    results["failed"] += 1
            
            return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get current deferral queue status."""
        by_module: Dict[str, int] = {}
        for d in self._deferred:
            by_module[d.module] = by_module.get(d.module, 0) + 1
        
        return {
            "total_deferred": len(self._deferred),
            "by_module": by_module,
            "oldest_deferred": self._deferred[0].deferred_at.isoformat() if self._deferred else None,
        }


# Global deferral queue instance
deferral_queue = ActionDeferralQueue()


async def defer_action(
    module: str,
    action: str,
    user_id: str,
    params: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience function to defer an action."""
    await deferral_queue.defer(
        module=module,
        action=action,
        user_id=user_id,
        params=params or {},
        context=context or {},
    )
