"""
Court Forms Module Manifest

Self-contained SDK module for Court form generation.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="court_forms",
    display_name="Court Forms",
    description="Court form generation",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.court_forms.router",
    tags=("Court Forms",),
)
