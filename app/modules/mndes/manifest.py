"""
MNDES Module Manifest

Self-contained SDK module for Court Exhibit System (MN Supreme Court Order ADM09-8010 compliance).
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="mndes",
    display_name="MNDES",
    description="Court Exhibit System (MN Supreme Court Order ADM09-8010 compliance)",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.mndes.router",
    tags=("MNDES",),
)
