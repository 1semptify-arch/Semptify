"""
Context Loop Module Manifest

Self-contained SDK module for Context loop debugging.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="context_loop",
    display_name="Context Loop",
    description="Context loop debugging",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.context_loop.router",
    tags=("Context Loop",),
)
