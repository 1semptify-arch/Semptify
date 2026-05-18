"""
Progress Tracker Module Manifest

Self-contained SDK module for Case progress tracking.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


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
