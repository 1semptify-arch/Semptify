"""Portal module — public guest portal + services catalog for semptify.org.

The portal is the front door of the organization. It serves three functions:
1. Information hub for renters (educational content)
2. Services catalog (modular, additive — new services added without rewriting)
3. Guest portal / branch separator (routes visitors to the correct branch)

Design:
- One endpoint: GET /api/portal/services — returns active services from the registry
- One endpoint: GET /api/portal/sitemap — returns sitemap entries for SEO
- The registry is the SSOT for portal services. Add a new entry, it appears.
- Entries are toggleable via the module flag system (visible field).
- The root route (/) renders the portal via Jinja2 with the services catalog.
"""

from .router import router, seo_router

__all__ = ["router", "seo_router"]
