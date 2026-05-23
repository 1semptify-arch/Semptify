"""
Form Field Extraction Module Manifest

Self-contained SDK module for Form field extraction AI.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="extraction",
    display_name="Form Field Extraction",
    description="Form field extraction AI",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.extraction.router",
    tags=("Form Field Extraction",),
)
