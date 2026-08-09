"""
Document Registry Module Manifest

Self-contained SDK module for Document registry management.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="registry",
    display_name="Document Registry",
    description="Document registry management",
    version="1.0.0",
    tier=ProductTier.ADMIN,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.registry.router",
    tags=("Document Registry",),
)
