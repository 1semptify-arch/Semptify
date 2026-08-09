"""
Document Recognition Module Manifest

Self-contained SDK module for AI document recognition.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="recognition",
    display_name="Document Recognition",
    description="AI document recognition",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.recognition.router",
    tags=("Document Recognition",),
)
