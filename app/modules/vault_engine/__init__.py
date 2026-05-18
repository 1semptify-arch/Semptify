"""
Vault Engine Module - Vault engine processing.

Public API:
    from app.modules.vault_engine import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

from .service import *  # noqa: F401,F403

__all__ = ["MANIFEST", "router"]