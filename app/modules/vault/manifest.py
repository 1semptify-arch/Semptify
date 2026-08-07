"""
Document Vault Module Manifest

Self-contained SDK module for Document vault management.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="vault",
    display_name="Document Vault",
    description="Document vault management",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.vault.router",
    prefix="/api/vault",
    tags=("Document Vault",),
)
