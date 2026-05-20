"""
External Mappings Module Manifest

Self-contained SDK module for external system ID mappings.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="external_mappings",
    display_name="External Mappings",
    description="Bridge between Semptify and external systems (court cases, properties, agencies)",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.external_mappings.router",
    tags=("External Mappings", "Court Cases", "Properties", "Agencies"),
)
