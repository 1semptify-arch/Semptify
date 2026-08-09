"""
Law Library Module Manifest

Self-contained SDK module for Law library search and reference.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="law_library",
    display_name="Law Library",
    description="Law library search and reference",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.law_library.router",
    tags=("Law Library",),
)
