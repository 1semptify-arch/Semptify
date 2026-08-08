"""
Development Tools Module Manifest

Self-contained SDK module for Internal development tools.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="development",
    display_name="Development Tools",
    description="Internal development tools",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.development.router",
    tags=("Development Tools",),
)
