"""Accountability Ledger Module — subject registry, patterns, political alignments.

Public API:
    from app.modules.accountability_ledger import MANIFEST, router

Design doc: handoffs/accountability-platform-design-2026-09-14.md
"""

from .manifest import MANIFEST
from .router import accountability_ledger_router as router

__all__ = ["MANIFEST", "router"]
