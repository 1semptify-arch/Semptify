"""
Modular Components Module Manifest

Self-contained SDK module for Modular component system integration.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="components",
    display_name="Modular Components",
    description="Modular component system integration",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.components.router",
    tags=("Modular Components",),
)
