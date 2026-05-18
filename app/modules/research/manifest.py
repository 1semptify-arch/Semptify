"""
Research Module Module Manifest

Self-contained SDK module for Legal research tools.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="research",
    display_name="Research Module",
    description="Legal research tools",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.research.router",
    tags=("Research Module",),
)
