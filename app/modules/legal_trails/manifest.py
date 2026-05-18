"""
Legal Trails Module Manifest

Self-contained SDK module for Legal case trails and precedents.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="legal_trails",
    display_name="Legal Trails",
    description="Legal case trails and precedents",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.legal_trails.router",
    tags=("Legal Trails",),
)
