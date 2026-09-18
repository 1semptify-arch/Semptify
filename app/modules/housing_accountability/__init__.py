"""
Housing Accountability Module -- Housing accountability tracking.

Public API:
    from app.modules.housing_accountability import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

import os

from .manifest import MANIFEST
from .router import accountability_router as router

# Only import pattern_history (and the pattern vault store) when persistence
# is explicitly enabled — pattern records are PATTERN_RECORD overlays under
# Vault/derived/ in the tenant's own cloud, not the server database.
if os.getenv("ENABLE_PATTERN_PERSISTENCE", "false").lower() == "true":
    from .pattern_history import pattern_history_router
else:
    from fastapi import APIRouter as _APIRouter

    pattern_history_router = _APIRouter()

__all__ = ["MANIFEST", "router", "pattern_history_router"]
