"""Judge module registration helper. Deprecated — merged into Legal sub-role."""

from app.core.product_manifest import ModuleEntry, ProductTier


MODULE = ModuleEntry(
    module_path="app.modules.judge.router",
    tier=ProductTier.DEV,
    origin="internal",
    lifecycle="deprecated",
    requires_role=("admin",),
    tags=("Judge", "Deprecated", "Merged Into Legal"),
    dev_notes=(
        "Judge role is DEPRECATED as of 2026-06-23. Merged into Legal as "
        "sub_role='judge'. This stub remains for backward compat with services "
        "that reference UserRole.JUDGE. New judge functionality goes in Legal module."
    ),
)
