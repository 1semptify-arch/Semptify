"""
Admin Module Manifest

Self-contained SDK module for Workflow validation and admin tools.
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="workflow_validator",
    display_name="Admin",
    description="Workflow validation and admin tools",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.workflow_validator.router",
    tags=("Admin",),
)
