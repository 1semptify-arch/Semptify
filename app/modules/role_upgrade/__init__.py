"""
Role Management Module -- User role management.

Public API:
    from app.modules.role_upgrade import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
