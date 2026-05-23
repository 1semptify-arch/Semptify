"""
Module Hub Module Manifest

Self-contained SDK module for Central module hub.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="module_hub",
    display_name="Module Hub",
    description="Central module hub",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.module_hub.router",
    prefix="/api",
    tags=("Module Hub",),
)
