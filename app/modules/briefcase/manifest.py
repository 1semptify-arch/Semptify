"""
Briefcase Module Manifest

Self-contained SDK module for Briefcase document organization.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="briefcase",
    display_name="Briefcase",
    description="Briefcase document organization",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.briefcase.router",
    tags=("Briefcase",),
)
