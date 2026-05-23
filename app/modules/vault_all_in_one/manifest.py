"""
ALL-IN-ONE Vault Module Manifest

Self-contained SDK module for Unified evidence vault with three-timestamp model.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="vault_all_in_one",
    display_name="ALL-IN-ONE Vault",
    description="Unified evidence vault with three-timestamp model",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.vault_all_in_one.router",
    tags=("ALL-IN-ONE Vault",),
)
