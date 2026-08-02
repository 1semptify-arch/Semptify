"""
Advanced Security Module Manifest

Self-contained SDK module for 2FA and session management.
"""

import logging

from app.core.semptify_internal_sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)
MANIFEST = ModuleManifest(
    name="security",
    display_name="Advanced Security",
    description="2FA and session management",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.security.router",
    prefix="/api/security",
    tags=("Advanced Security",),
)
