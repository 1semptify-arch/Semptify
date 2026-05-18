"""
Tactics Module Manifest

Self-contained SDK module for Legal tactics development tools.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="tactics",
    display_name="Tactics",
    description="Legal tactics development tools",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.tactics.router",
    tags=("Tactics",),
)
