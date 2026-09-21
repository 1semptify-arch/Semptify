"""Info Donation Module Manifest

Post-resolution, opt-in, anonymized info donation — "help the next tenant."
Gated on the issue-resolved event; versioned informed consent for the
server-side aggregate; per-item opt-in; revocable.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="info_donation",
    display_name="Info Donation",
    description="Post-resolution opt-in info donation — anonymized, consented, aggregate-only",
    version="0.1.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.info_donation.router",
    tags=("Info Donation",),
)
