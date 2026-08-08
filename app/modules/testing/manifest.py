"""
Automated Testing Module Manifest

Self-contained SDK module for Automated testing framework.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="testing",
    display_name="Automated Testing",
    description="Automated testing framework",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.testing.router",
    prefix="/api/testing",
    tags=("Automated Testing",),
)
