"""
Modular Components Module Manifest

Self-contained SDK module for Modular component system integration.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="components",
    display_name="Modular Components",
    description="Modular component system integration",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.components.router",
    tags=("Modular Components",),
)
