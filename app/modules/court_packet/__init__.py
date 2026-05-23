"""
Court Packet Module -- Court packet assembly.

Public API:
    from app.modules.court_packet import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
