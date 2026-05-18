"""
Communications Module Manifest

Self-contained SDK module for Advocate communication tools.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="communication",
    display_name="Communications",
    description="Advocate communication tools",
    version="1.0.0",
    tier=ProductTier.ADVOCATE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.communication.router",
    tags=("Communications",),
)
