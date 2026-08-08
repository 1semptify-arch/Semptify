"""
Fraud Exposure Module Manifest

Self-contained SDK module for Fraud exposure detection.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="fraud_exposure",
    display_name="Fraud Exposure",
    description="Fraud exposure detection",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.fraud_exposure.router",
    tags=("Fraud Exposure",),
)
