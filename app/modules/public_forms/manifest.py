"""
Public Forms Module Manifest

Self-contained SDK module for Public court form access.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="public_forms",
    display_name="Public Forms",
    description="Public court form access",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.public_forms.router",
    tags=("Public Forms",),
)
