"""
Zoom Courtroom Module Manifest

Self-contained SDK module for Zoom court video integration.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="zoom_court",
    display_name="Zoom Courtroom",
    description="Zoom court video integration",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.zoom_court.router",
    tags=("Zoom Courtroom",),
)
