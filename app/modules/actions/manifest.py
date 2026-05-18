"""
Smart Actions Module Manifest

Self-contained SDK module for Smart action automation.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="actions",
    display_name="Smart Actions",
    description="Smart action automation",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.actions.router",
    tags=("Smart Actions",),
)
