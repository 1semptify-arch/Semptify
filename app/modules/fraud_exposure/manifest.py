"""
Fraud Exposure Module Manifest

Self-contained SDK module for Fraud exposure detection.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


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
