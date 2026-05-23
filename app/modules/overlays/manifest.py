"""
Document Overlays Module Manifest

Self-contained SDK module for Non-destructive document annotation.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="overlays",
    display_name="Document Overlays",
    description="Non-destructive document annotation",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.overlays.router",
    tags=("Document Overlays",),
)
