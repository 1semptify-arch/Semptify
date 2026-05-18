"""
Core System Module Manifest

Self-contained SDK module for Core system infrastructure.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="core_system",
    display_name="Core System",
    description="Core system infrastructure",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.core_system.router",
    tags=("Core System",),
)
