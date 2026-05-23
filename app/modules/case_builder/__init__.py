"""
Case Builder Module — Eviction defense case building.

Public API:
    from app.modules.case_builder import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)

Endpoints (under /api/case-builder):
    POST /cases              — Create case
    GET  /cases              — List cases
    GET  /cases/{id}         — Get case
    POST /timeline           — Add timeline event
    POST /evidence           — Add evidence
    POST /counterclaims      — Add counterclaim
    POST /motions            — Add motion
    POST /deadlines          — Add deadline
    GET  /defenses           — Defense strategies
    POST /documents          — Generate court document
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
