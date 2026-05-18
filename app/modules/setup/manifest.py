"""
Setup Wizard Module Manifest

Self-contained SDK module for Application setup wizard.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="setup",
    display_name="Setup Wizard",
    description="Application setup wizard",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.setup.router",
    prefix="/api/setup",
    tags=("Setup Wizard",),
)
