"""
Crawler Module Manifest

Self-contained SDK module for Web crawler for legal data.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="crawler",
    display_name="Crawler",
    description="Web crawler for legal data",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.crawler.router",
    tags=("Crawler",),
)
