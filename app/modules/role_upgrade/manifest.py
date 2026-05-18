"""
Role Management Module Manifest

Self-contained SDK module for User role management.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="role_upgrade",
    display_name="Role Management",
    description="User role management",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.role_upgrade.router",
    tags=("Role Management",),
)
