"""
Funding & Tax Credit Search Module -- Funding and tax credit search.

Public API:
    from app.modules.funding_search import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
