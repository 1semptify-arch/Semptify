"""
Research Module Module Manifest

Self-contained SDK module for Legal research tools.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="research",
    display_name="Research Module",
    description="Legal research tools",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.research.router",
    tags=("Research Module",),
)
