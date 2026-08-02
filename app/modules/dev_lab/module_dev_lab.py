from app.core.semptify_internal_sdk import (
    ModuleCapability,
    ModuleManifest,
    ProductTier,
    register_module,
)


def register_dev_lab_module(app):
    manifest = ModuleManifest(
        name="dev_lab",
        display_name="Dev Lab",
        description="Incubator hub for internal + external dev modules",
        version="0.1.0",
        tier=ProductTier.DEV,
        capabilities=(ModuleCapability.ROUTER,),
        router_module="app.modules.dev_lab.router",
        prefix="/dev/lab",
        tags=("Dev Lab", "Dev"),
    )
    register_module(app, manifest)
