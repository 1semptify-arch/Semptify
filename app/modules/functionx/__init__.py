"""
FunctionX Module -- Function execution engine.

Public API:
    from app.modules.functionx import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

from .service import *  # noqa: F401,F403

__all__ = ["MANIFEST", "router"]