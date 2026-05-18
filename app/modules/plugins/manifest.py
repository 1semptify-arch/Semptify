"""
Plugin System Module Manifest

Self-contained SDK module for Plugin management and registration.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="plugins",
    display_name="Plugin System",
    description="Plugin management and registration",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.plugins.router",
    tags=("Plugin System",),
)
