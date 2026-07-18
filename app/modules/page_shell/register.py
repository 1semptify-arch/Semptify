"""Page Shell module registration helper.

This module is registered via `_register()` in `app/core/product_manifest.py`
(DEV tier, dev_only lifecycle). This file documents the registration for
module authors — the actual registration line lives in the manifest so
all modules are declared in one SSOT location.

Registration line (added to the DEV tier block in product_manifest.py):

    _register("app.modules.page_shell.router", prefix="/api/page-shell",
              tags=("Page Shell", "Pillar Mixer"), tier=ProductTier.DEV,
              lifecycle="dev_only", requires_role=("admin",),
              dev_notes="Shell + rendering engine for the pillar-mixer backbone. "
                        "Renders four skeletons (RECORD/KNOW/ACT/GOVERN) from a "
                        "validated page config. Does not pick blends or compute "
                        "intensity. Spec: temp/semptify_pillar_mixer_backbone.md",
              log_message="Page Shell router active — /api/page-shell (admin-only)")
"""

from __future__ import annotations
