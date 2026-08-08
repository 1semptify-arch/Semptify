"""
Progress Tracker Module Manifest

Self-contained SDK module for Case progress tracking.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="progress",
    display_name="Progress Tracker",
    description="Case progress tracking",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.progress.router",
    tags=("Progress Tracker",),
)
