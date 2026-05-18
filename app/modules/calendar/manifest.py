"""
Calendar Module Manifest

Self-contained SDK module for Calendar integration.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="calendar",
    display_name="Calendar",
    description="Calendar integration",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.calendar.router",
    tags=("Calendar",),
)
