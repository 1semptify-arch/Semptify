"""
State Laws Module Manifest

Self-contained SDK module for State law lookup and reference.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="state_laws",
    display_name="State Laws",
    description="State law lookup and reference",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.state_laws.router",
    tags=("State Laws",),
)
