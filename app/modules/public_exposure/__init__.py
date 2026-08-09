"""
Public Exposure Module -- Public exposure tracking.

Public API:
    from app.modules.public_exposure import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router
from .service import *  # noqa: F401,F403

__all__ = ["MANIFEST", "router"]
