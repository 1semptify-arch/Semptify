"""
Case Builder Module Manifest

Self-contained SDK module for building eviction defense cases.
- Case creation and management
- Timeline and evidence tracking
- Counterclaims and motions
- Court document generation
- Deadline management
- Defense strategy analysis
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="case_builder",
    display_name="Case Builder",
    description="Build eviction defense cases: timelines, evidence, counterclaims, motions",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER, ModuleCapability.CONTRACT),
    router_module="app.modules.case_builder.router",
    prefix="/api/case-builder",
    tags=("Case Builder",),
)
