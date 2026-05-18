"""
Unified Dashboard Module Manifest

Self-contained SDK module for Unified admin dashboard.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="dashboard",
    display_name="Unified Dashboard",
    description="Unified admin dashboard",
    version="1.0.0",
    tier=ProductTier.ADMIN,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.dashboard.router",
    tags=("Unified Dashboard",),
)
