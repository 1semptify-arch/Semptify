"""
Legal Analysis Module Manifest

Self-contained SDK module for Legal document analysis and insights.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="legal_analysis",
    display_name="Legal Analysis",
    description="Legal document analysis and insights",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.legal_analysis.router",
    tags=("Legal Analysis",),
)
