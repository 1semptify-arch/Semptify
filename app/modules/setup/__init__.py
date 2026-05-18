"""
Setup Wizard Module -- Application setup wizard.

Public API:
    from app.modules.setup import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
