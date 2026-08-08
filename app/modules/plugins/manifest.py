"""
Plugin System Module Manifest

Self-contained SDK module for Plugin management and registration.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="plugins",
    display_name="Plugin System",
    description="Plugin management and registration",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.plugins.router",
    tags=("Plugin System",),
)
