"""
Module Template — Registration Helper

Call `register_template_module(app)` from main.py to register this module.
Replace 'template' with your module name.
"""
from app.core.semptify_internal_sdk import (
    ModuleCapability,
    ModuleManifest,
    ProductTier,
    register_module,
)


def register_template_module(app):
    manifest = ModuleManifest(
        name="template",
        display_name="Template Module",
        description="Dev module scaffold — replace with your module",
        version="0.1.0",
        tier=ProductTier.DEV,
        capabilities=(ModuleCapability.ROUTER,),
        router_module="app.modules._template.router",
        prefix="/template",
        tags=("Template", "Dev"),
    )
    register_module(app, manifest)
