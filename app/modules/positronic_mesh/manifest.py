"""
Positronic Mesh Module Manifest

Self-contained SDK module for Positronic mesh integration.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="positronic_mesh",
    display_name="Positronic Mesh",
    description="Positronic mesh integration",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.positronic_mesh.router",
    prefix="/api",
    tags=("Positronic Mesh",),
)
