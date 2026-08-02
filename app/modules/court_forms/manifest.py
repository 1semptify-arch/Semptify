"""
Court Forms Module Manifest

Self-contained SDK module for Court form generation.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="court_forms",
    display_name="Court Forms",
    description="Court form generation",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.court_forms.router",
    tags=("Court Forms",),
)
