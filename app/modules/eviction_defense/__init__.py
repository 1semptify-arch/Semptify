"""
Eviction Defense Module — Complete eviction defense toolkit.

Public API:
    from app.modules.eviction_defense import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)

Endpoints (under /api/eviction-defense):
    GET /defenses        — List applicable defenses
    GET /forms           — Court form templates
    GET /motions         — Motion templates
    GET /procedures      — Court procedure guides
    GET /counterclaims   — Counterclaim templates
    GET /timeline        — Case timeline events
    GET /prep            — Trial preparation checklist
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
