"""
Public Exposure Module Manifest

Self-contained SDK module for Public exposure tracking.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="public_exposure",
    display_name="Public Exposure",
    description="Public exposure tracking",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.public_exposure.router",
    tags=("Public Exposure",),
)
