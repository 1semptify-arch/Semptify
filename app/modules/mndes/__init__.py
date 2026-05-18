"""
MNDES Module - Court Exhibit System (MN Supreme Court Order ADM09-8010 compliance).

Public API:
    from app.modules.mndes import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

from .service import *  # noqa: F401,F403

__all__ = ["MANIFEST", "router"]