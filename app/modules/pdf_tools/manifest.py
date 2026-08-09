"""
PDF Tools Module Manifest

Self-contained SDK module for PDF manipulation and generation tools.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="pdf_tools",
    display_name="PDF Tools",
    description="PDF manipulation and generation tools",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.pdf_tools.router",
    tags=("PDF Tools",),
)
