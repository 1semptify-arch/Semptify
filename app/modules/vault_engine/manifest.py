"""
Vault Engine Module Manifest

Self-contained SDK module for Vault engine processing.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="vault_engine",
    display_name="Vault Engine",
    description="Vault engine processing",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.vault_engine.router",
    tags=("Vault Engine",),
)
