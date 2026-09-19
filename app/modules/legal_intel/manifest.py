"""Legal Intel Module Manifest

Entity/attorney/shell-LLC intelligence — "who owns this LLC" lookups and
cross-entity court-pattern analysis. Ported from app-legal-intel
(models + intel lookups + pattern engine; crawlers not ported).
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="legal_intel",
    display_name="Legal Intel",
    description="Entity/attorney/shell-LLC lookups and cross-entity court-pattern analysis",
    version="0.1.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.legal_intel.router",
    tags=("Legal Intel", "Accountability", "Research"),
)
