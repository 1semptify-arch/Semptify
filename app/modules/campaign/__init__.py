"""
Campaign Orchestration Module -- Campaign management and orchestration.

Public API:
    from app.modules.campaign import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
