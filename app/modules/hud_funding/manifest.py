"""
HUD Funding Guide Module Manifest

Self-contained SDK module for HUD funding guide.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="hud_funding",
    display_name="HUD Funding Guide",
    description="HUD funding guide",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.hud_funding.router",
    tags=("HUD Funding Guide",),
)
