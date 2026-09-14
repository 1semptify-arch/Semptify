"""Accountability Ledger Module Manifest.

Self-contained SDK module for the accountability subject registry, pattern
ledger, and political alignment tracker. This is the foundation data model
for the accountability platform — see
``handoffs/accountability-platform-design-2026-09-14.md``.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="accountability_ledger",
    display_name="Accountability Ledger",
    description="Subject registry, documented patterns, and political alignments for housing accountability",
    version="0.1.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.accountability_ledger.router",
    tags=("Accountability", "Political Tracker", "Research"),
)
