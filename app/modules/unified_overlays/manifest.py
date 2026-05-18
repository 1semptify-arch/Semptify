"""
Unified Overlays Module Manifest

Self-contained SDK module for Unified overlay system.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="unified_overlays",
    display_name="Unified Overlays",
    description="Unified overlay system",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.unified_overlays.router",
    tags=("Unified Overlays",),
)
