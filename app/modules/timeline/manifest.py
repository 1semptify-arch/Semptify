"""
Timeline Module Manifest

Self-contained SDK module for unified chronological event tracking.
Aggregates documents, timeline events, calendar events, and vault items.

Capabilities:
- Multi-axis date sorting (event_time, record_time, entry_time)
- Date range filtering
- Evidence highlighting
- Real-time updates
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="timeline",
    display_name="Unified Timeline",
    description="Chronological event tracking aggregating documents, events, calendar, and vault",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.timeline.router",
    prefix="/api/timeline",
    tags=("Unified Timeline",),
)
