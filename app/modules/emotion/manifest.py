"""
Emotion Engine Module Manifest

Self-contained SDK module for Emotional intelligence analysis.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="emotion",
    display_name="Emotion Engine",
    description="Emotional intelligence analysis",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.emotion.router",
    tags=("Emotion Engine",),
)
