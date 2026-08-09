"""
Document Converter Module Manifest

Self-contained SDK module for Document format conversion.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="document_converter",
    display_name="Document Converter",
    description="Document format conversion",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.document_converter.router",
    tags=("Document Converter",),
)
