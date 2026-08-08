"""
Guided Intake Module Manifest

Self-contained SDK module for Guided document intake.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="guided_intake",
    display_name="Guided Intake",
    description="Guided document intake",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.guided_intake.router",
    tags=("Guided Intake",),
)
