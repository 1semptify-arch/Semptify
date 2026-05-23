"""
Workflow Module Manifest

Self-contained SDK module for Workflow management and execution.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier
import logging
logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="workflow",
    display_name="Workflow",
    description="Workflow management and execution",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.workflow.router",
    tags=("Workflow",),
)
