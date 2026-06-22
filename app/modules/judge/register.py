"""Judge module registration helper."""

from app.core.product_manifest import ModuleEntry, ProductTier, ModuleOrigin


MODULE = ModuleEntry(
    module_path="app.modules.judge.router",
    tier=ProductTier.DEV,
    origin=ModuleOrigin.INTERNAL,
    lifecycle="dev_only",
    requires_role=("admin",),
    tags=("Judge", "Dev Only", "Placeholder"),
    dev_notes="Phase 4.6 — Judge role is dev_only. Placeholder module, not built out. Read-only role by design.",
)
