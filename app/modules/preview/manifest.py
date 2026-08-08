"""
Document Preview Module Manifest

Self-contained SDK module for Multi-format document preview.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="preview",
    display_name="Document Preview",
    description="Multi-format document preview",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.preview.router",
    prefix="/api/preview",
    tags=("Document Preview",),
)
