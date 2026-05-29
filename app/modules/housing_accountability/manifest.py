"""
Housing Accountability Module Manifest

Self-contained SDK module for Housing accountability tracking.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="housing_accountability",
    display_name="Housing Accountability",
    description="Housing accountability tracking with optional pattern persistence",
    version="1.1.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.housing_accountability.router",
    tags=("Housing Accountability", "Pattern Analysis", "Trends"),
)
