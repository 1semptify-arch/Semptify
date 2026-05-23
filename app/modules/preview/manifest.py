"""
Document Preview Module Manifest

Self-contained SDK module for Multi-format document preview.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
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
