"""
Batch Operations Module Manifest

Self-contained SDK module for Bulk document management.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="batch",
    display_name="Batch Operations",
    description="Bulk document management",
    version="1.0.0",
    tier=ProductTier.ADMIN,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.batch.router",
    prefix="/api/batch",
    tags=("Batch Operations",),
)
