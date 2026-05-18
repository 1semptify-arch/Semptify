"""
Preamble Module Manifest

Self-contained SDK module for Preamble entry point routing.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="preamble",
    display_name="Preamble",
    description="Preamble entry point routing",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.preamble.router",
    tags=("Preamble",),
)
