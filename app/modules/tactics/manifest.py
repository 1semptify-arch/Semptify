"""
Tactics Module Manifest

Self-contained SDK module for Legal tactics development tools.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="tactics",
    display_name="Tactics",
    description="Legal tactics development tools",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.tactics.router",
    tags=("Tactics",),
)
