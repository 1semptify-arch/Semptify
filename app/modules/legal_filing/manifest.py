"""
Legal Filing Module Manifest

Self-contained SDK module for Legal filing management.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="legal_filing",
    display_name="Legal Filing",
    description="Legal filing management",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.legal_filing.router",
    tags=("Legal Filing",),
)
