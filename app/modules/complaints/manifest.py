"""
Complaint Wizard Module Manifest

Self-contained SDK module for Regulatory complaint filing.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="complaints",
    display_name="Complaint Wizard",
    description="Regulatory complaint filing",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.complaints.router",
    tags=("Complaint Wizard",),
)
