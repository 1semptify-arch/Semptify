"""
FunctionX Module Manifest

Self-contained SDK module for Function execution engine.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="functionx",
    display_name="FunctionX",
    description="Function execution engine",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.functionx.router",
    tags=("FunctionX",),
)
