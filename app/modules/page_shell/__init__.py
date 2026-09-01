"""
Semptify Page Shell — Pillar-Mixer Backbone (spec: temp/semptify_pillar_mixer_backbone.md)

Renders the four-skeleton page shell (RECORD / KNOW / ACT / GOVERN) from a
data-driven page config. This module is the SHELL + RENDERING ENGINE only.
It does NOT pick blends, compute intensity, or gather case data — those are
the context engine's job. Feed it a validated PageConfig, get back rendered
HTML for the shell.

Lifecycle: dev_only (admin-only until promoted via Forge).
"""

# Load sample PageContracts so the in-memory registry is populated in dev.
# This is safe to ship because these demo contracts are not linked from
# navigation and do not affect any existing tenant-facing route.
from app.modules.page_shell import sample_contracts  # noqa: F401
