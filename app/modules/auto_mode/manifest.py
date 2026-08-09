"""
Auto Mode Module Manifest

Self-contained SDK module for Automated analysis mode.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="auto_mode",
    display_name="Auto Mode",
    description="Automated analysis mode",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.auto_mode.router",
    tags=("Auto Mode",),
)
