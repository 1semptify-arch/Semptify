"""
HUD Funding Guide Module -- HUD funding guide.

Public API:
    from app.modules.hud_funding import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router
from .service import *  # noqa: F401,F403

__all__ = ["MANIFEST", "router"]
