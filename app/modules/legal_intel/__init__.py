"""Legal Intel Module — entity/attorney/shell-LLC intelligence.

Public API:
    from app.modules.legal_intel import MANIFEST, router

Ported from app-legal-intel (workflow only — Playwright crawlers are a
separate decision; records arrive via the ingest endpoints).
"""

from .manifest import MANIFEST
from .router import legal_intel_router as router

__all__ = ["MANIFEST", "router"]
