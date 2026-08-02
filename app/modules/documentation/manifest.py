"""
Documentation Module Manifest

Self-contained SDK module for API and system documentation.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="documentation",
    display_name="Documentation",
    description="API and system documentation",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.documentation.router",
    tags=("Documentation",),
)
