from app.core.semptify_internal_sdk import (
    ModuleCapability,
    ModuleManifest,
    ProductTier,
    register_module,
)


def register_admin_console_module(app):
    manifest = ModuleManifest(
        name="admin_console",
        display_name="Admin Console",
        description="System maintenance, AI tools, and diagnostics",
        version="1.0.0",
        tier=ProductTier.ADMIN,
        capabilities=(ModuleCapability.ROUTER, ModuleCapability.WIDGET),
        router_module="app.modules.admin_console.router",
        prefix="/admin-console",
        tags=("Admin Console",),
    )
    register_module(app, manifest)
