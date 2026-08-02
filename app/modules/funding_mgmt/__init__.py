"""
Semptify Funding Management Module

Administrator tool for managing funding sources, applications, budgets,
and tracking progress toward funding goals.

This module is restricted to admin users only.
"""

from .router import router


def register_funding_module(app):
    """Register funding management module with the app."""
    app.include_router(router)
    return True


__all__ = ["router", "register_funding_module"]
