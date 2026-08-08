"""
Mesh Network Module Manifest

Self-contained SDK module for Mesh network infrastructure.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="mesh_network",
    display_name="Mesh Network",
    description="Mesh network infrastructure",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.mesh_network.router",
    prefix="/api",
    tags=("Mesh Network",),
)
