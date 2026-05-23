"""
Preamble Module - Preamble entry point routing.

Public API:
    from app.modules.preamble import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
