"""
Role UI Module Manifest

Self-contained SDK module for Role-based UI routing.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="role_ui",
    display_name="Role UI",
    description="Role-based UI routing",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.role_ui.router",
    tags=("Role UI",),
)
