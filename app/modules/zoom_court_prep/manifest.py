"""
Zoom Court Prep Module Manifest

Self-contained SDK module for Zoom court preparation tools.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="zoom_court_prep",
    display_name="Zoom Court Prep",
    description="Zoom court preparation tools",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.zoom_court_prep.router",
    tags=("Zoom Court Prep",),
)
