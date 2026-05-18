"""
Page Editor Module Manifest

Self-contained SDK module for Interactive page editor for templates.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="page_editor",
    display_name="Page Editor",
    description="Interactive page editor for templates",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.page_editor.router",
    tags=("Page Editor",),
)
