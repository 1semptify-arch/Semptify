"""
Court Packet Module -- Court packet assembly.

Public API:
    from app.modules.court_packet import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
