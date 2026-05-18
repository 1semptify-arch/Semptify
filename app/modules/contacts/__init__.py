"""
Contacts Module — Case-related contact management.

Public API:
    from app.modules.contacts import MANIFEST, router
    register_module(app, MANIFEST)

Endpoints (all under /api/contacts):
    GET    /              — List contacts
    POST   /              — Create contact
    GET    /{id}          — Get contact
    PUT    /{id}          — Update contact
    DELETE /{id}          — Delete contact
    POST   /{id}/interactions — Log interaction
    GET    /{id}/interactions — List interactions
    POST   /extract       — Import from extracted form data
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
