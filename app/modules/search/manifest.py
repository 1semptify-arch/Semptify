"""
Global Search Module Manifest

Self-contained SDK module for Global search across all data.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="search",
    display_name="Global Search",
    description="Global search across all data",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.search.router",
    prefix="/api/search",
    tags=("Global Search",),
)
