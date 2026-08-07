"""
Page Editor Module Manifest

Self-contained SDK module for Interactive page editor for templates.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


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
