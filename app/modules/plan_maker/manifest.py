"""
Plan Maker Module Manifest

Self-contained SDK module for Action plan generation.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="plan_maker",
    display_name="Plan Maker",
    description="Action plan generation",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.plan_maker.router",
    tags=("Plan Maker",),
)
