"""
Positronic Mesh Module -- Positronic mesh integration.

Public API:
    from app.modules.positronic_mesh import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
