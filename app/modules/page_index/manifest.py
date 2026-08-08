"""
Page Index Module Manifest

Self-contained SDK module for Page indexing system.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="page_index",
    display_name="Page Index",
    description="Page indexing system",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.page_index.router",
    tags=("Page Index",),
)
