"""
Admin Module - Workflow validation and admin tools.

Public API:
    from app.modules.workflow_validator import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
