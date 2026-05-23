"""
Form Data Hub Module Manifest

Self-contained SDK module for Centralized form data hub.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="form_data",
    display_name="Form Data Hub",
    description="Centralized form data hub",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.form_data.router",
    prefix="/api/form-data",
    tags=("Form Data Hub",),
)
