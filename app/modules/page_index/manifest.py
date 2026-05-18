"""
Page Index Module Manifest

Self-contained SDK module for Page indexing system.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


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
