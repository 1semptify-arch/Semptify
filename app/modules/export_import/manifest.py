"""
Data Export/Import Module Manifest

Self-contained SDK module for GDPR-compliant data export/import.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="export_import",
    display_name="Data Export/Import",
    description="GDPR-compliant data export/import",
    version="1.0.0",
    tier=ProductTier.DEV,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.export_import.router",
    prefix="/api/export-import",
    tags=("Data Export/Import",),
)
