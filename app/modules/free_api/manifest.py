"""
Free API Module Manifest

Self-contained SDK module for public data lookups.
- Property parcel/address lookup
- Landlord business/owner lookup
- Court eviction/federal case search
- City/environmental violations
- HUD/local inspections
- MN statute lookup
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="free_api",
    display_name="Free API Pack",
    description="Public data lookups: property, landlord, courts, violations, inspections, statutes",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.free_api.router",
    tags=("Free APIs",),
)
