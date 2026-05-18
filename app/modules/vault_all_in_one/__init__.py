"""
ALL-IN-ONE Vault Module -- Unified evidence vault with three-timestamp model.

Public API:
    from app.modules.vault_all_in_one import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

from .service import *  # noqa: F401,F403

__all__ = ["MANIFEST", "router"]