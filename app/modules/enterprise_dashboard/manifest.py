"""
Enterprise Dashboard Module Manifest

Self-contained SDK module for Enterprise analytics dashboard.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="enterprise_dashboard",
    display_name="Enterprise Dashboard",
    description="Enterprise analytics dashboard",
    version="1.0.0",
    tier=ProductTier.ADMIN,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.enterprise_dashboard.router",
    tags=("Enterprise Dashboard",),
)
