"""
Eviction Defense Module Manifest

Self-contained SDK module for eviction defense toolkit.
Motions, forms, procedures, counterclaims, trial prep, and court etiquette.

Capabilities:
- Defense analysis and recommendation
- Court form templates
- Motion generation
- Procedure guides
- Counterclaim templates
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="eviction_defense",
    display_name="Eviction Defense Toolkit",
    description="Complete eviction defense: motions, forms, procedures, counterclaims, trial prep",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER, ModuleCapability.CONTRACT),
    router_module="app.modules.eviction_defense.router",
    prefix="/api/eviction-defense",
    tags=("Eviction Defense Toolkit",),
)
