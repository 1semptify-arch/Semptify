"""
Analytics Module Manifest

Self-contained SDK module for Usage and performance analytics.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="analytics",
    display_name="Analytics",
    description="Usage and performance analytics",
    version="1.0.0",
    tier=ProductTier.ADMIN,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.analytics.router",
    prefix="/api/analytics",
    tags=("Analytics",),
)
