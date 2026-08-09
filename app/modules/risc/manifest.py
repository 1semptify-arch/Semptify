"""
RISC Module Manifest

Self-contained SDK module for RISC assessment routing.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="risc",
    display_name="RISC",
    description="RISC assessment routing",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.risc.router",
    tags=("RISC",),
)
