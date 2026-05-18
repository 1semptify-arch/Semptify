"""
Public Forms Module Manifest

Self-contained SDK module for Public court form access.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="public_forms",
    display_name="Public Forms",
    description="Public court form access",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.public_forms.router",
    tags=("Public Forms",),
)
