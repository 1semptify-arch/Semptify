"""
Document Registry Module Manifest

Self-contained SDK module for Document registry management.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="registry",
    display_name="Document Registry",
    description="Document registry management",
    version="1.0.0",
    tier=ProductTier.ADMIN,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.registry.router",
    tags=("Document Registry",),
)
