"""
Litigation Intelligence Module Manifest

Self-contained SDK module for Justice-grade legal intelligence.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="litigation_intelligence",
    display_name="Litigation Intelligence",
    description="Justice-grade legal intelligence",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.litigation_intelligence.router",
    tags=("Litigation Intelligence",),
)
