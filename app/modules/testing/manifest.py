"""
Automated Testing Module Manifest

Self-contained SDK module for Automated testing framework.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="testing",
    display_name="Automated Testing",
    description="Automated testing framework",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.testing.router",
    prefix="/api/testing",
    tags=("Automated Testing",),
)
