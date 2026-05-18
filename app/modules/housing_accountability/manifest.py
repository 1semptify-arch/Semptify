"""
Housing Accountability Module Manifest

Self-contained SDK module for Housing accountability tracking.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="housing_accountability",
    display_name="Housing Accountability",
    description="Housing accountability tracking",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.housing_accountability.router",
    tags=("Housing Accountability",),
)
