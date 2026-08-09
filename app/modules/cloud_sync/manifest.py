"""
Cloud Sync Module Manifest

Self-contained SDK module for User-controlled data persistence.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="cloud_sync",
    display_name="Cloud Sync",
    description="User-controlled data persistence",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.cloud_sync.router",
    tags=("Cloud Sync",),
)
