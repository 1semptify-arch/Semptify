"""
Mesh Network Module -- Mesh network infrastructure.

Public API:
    from app.modules.mesh_network import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
