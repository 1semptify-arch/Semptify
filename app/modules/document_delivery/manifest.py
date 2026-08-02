"""
Document Delivery Module Manifest

Self-contained SDK module for Secure document delivery.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="document_delivery",
    display_name="Document Delivery",
    description="Secure document delivery",
    version="1.0.0",
    tier=ProductTier.ADVOCATE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.document_delivery.router",
    tags=("Document Delivery",),
)
