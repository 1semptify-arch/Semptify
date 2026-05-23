"""
Invite Codes Module Manifest

Self-contained SDK module for Invite code management.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="invite_codes",
    display_name="Invite Codes",
    description="Invite code management",
    version="1.0.0",
    tier=ProductTier.ADVOCATE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.invite_codes.router",
    tags=("Invite Codes",),
)
