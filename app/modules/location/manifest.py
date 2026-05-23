"""
Location Module Manifest

Self-contained SDK module for Location-based services.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="location",
    display_name="Location",
    description="Location-based services",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.location.router",
    tags=("Location",),
)
