"""
Tenancy Hub Module Manifest

Self-contained SDK module for Tenancy administration hub.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="tenancy_hub",
    display_name="Tenancy Hub",
    description="Tenancy administration hub",
    version="1.0.0",
    tier=ProductTier.ADMIN,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.tenancy_hub.router",
    tags=("Tenancy Hub",),
)
