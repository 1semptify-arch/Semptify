"""
Tools Module Manifest

Self-contained SDK module for Utility tools API.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="tools_api",
    display_name="Tools",
    description="Utility tools API",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.tools_api.router",
    tags=("Tools",),
)
