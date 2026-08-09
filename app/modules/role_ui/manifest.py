"""
Role UI Module Manifest

Self-contained SDK module for Role-based UI routing.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="role_ui",
    display_name="Role UI",
    description="Role-based UI routing",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.role_ui.router",
    tags=("Role UI",),
)
