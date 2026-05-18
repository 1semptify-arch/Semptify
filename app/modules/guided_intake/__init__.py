"""
Guided Intake Module -- Guided document intake.

Public API:
    from app.modules.guided_intake import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
