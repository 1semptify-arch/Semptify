"""
Campaign Orchestration Module Manifest

Self-contained SDK module for Campaign management and orchestration.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="campaign",
    display_name="Campaign Orchestration",
    description="Campaign management and orchestration",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.campaign.router",
    tags=("Campaign Orchestration",),
)
