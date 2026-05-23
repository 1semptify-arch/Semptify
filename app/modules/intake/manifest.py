"""
Document Intake Module Manifest

Self-contained SDK module for Document intake processing.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="intake",
    display_name="Document Intake",
    description="Document intake processing",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.intake.router",
    tags=("Document Intake",),
)
