"""
RISC Module Manifest

Self-contained SDK module for RISC assessment routing.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="risc",
    display_name="RISC",
    description="RISC assessment routing",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.risc.router",
    tags=("RISC",),
)
