"""
Funding & Tax Credit Search Module Manifest

Self-contained SDK module for Funding and tax credit search.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="funding_search",
    display_name="Funding & Tax Credit Search",
    description="Funding and tax credit search",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.funding_search.router",
    tags=("Funding & Tax Credit Search",),
)
