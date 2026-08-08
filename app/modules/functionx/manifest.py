"""
FunctionX Module Manifest

Self-contained SDK module for Function execution engine.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="functionx",
    display_name="FunctionX",
    description="Function execution engine",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.functionx.router",
    tags=("FunctionX",),
)
