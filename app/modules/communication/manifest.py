"""
Communications Module Manifest

Self-contained SDK module for Advocate communication tools.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="communication",
    display_name="Communications",
    description="Advocate communication tools",
    version="1.0.0",
    tier=ProductTier.ADVOCATE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.communication.router",
    tags=("Communications",),
)
