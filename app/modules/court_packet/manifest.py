"""
Court Packet Module Manifest

Self-contained SDK module for Court packet assembly.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="court_packet",
    display_name="Court Packet",
    description="Court packet assembly",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.court_packet.router",
    tags=("Court Packet",),
)
