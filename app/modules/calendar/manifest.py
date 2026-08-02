"""
Calendar Module Manifest

Self-contained SDK module for Calendar integration.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


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
