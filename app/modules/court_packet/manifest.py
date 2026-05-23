"""
Court Packet Module Manifest

Self-contained SDK module for Court packet assembly.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
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
