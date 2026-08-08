"""Portal service — builds the services catalog for the guest portal.

Reads from the PortalRegistry (SSOT) and returns the data needed to render
the portal page. No hallucination — all services are defined in the registry.
"""

from __future__ import annotations

import logging

from app.modules.portal.pages import PortalPage, portal_pages
from app.modules.portal.registry import PortalService, portal

logger = logging.getLogger(__name__)


def get_portal_catalog() -> dict:
    """Build the complete portal catalog for rendering.

    Returns a dict with:
    - services: list of visible services, grouped by category
    - categories: active categories with metadata
    - total_services: count of visible services
    """
    data = portal.to_dict()
    logger.debug("Portal catalog built: %s services", data["total_services"])
    return data


def get_services_for_category(category: str) -> list[PortalService]:
    """Get visible services for a specific category."""
    return portal.get_services_by_category(category)


def get_service(service_id: str) -> PortalService | None:
    """Get a single service by ID."""
    return portal.get_service(service_id)


def get_footer_pages() -> list[PortalPage]:
    """Return pages that should appear in the footer."""
    return portal_pages.get_footer_pages()


def get_sitemap_pages() -> list[PortalPage]:
    """Return pages that should appear in the sitemap."""
    return portal_pages.get_sitemap_pages()


def get_page(page_id: str) -> PortalPage | None:
    """Get a single portal page by ID."""
    return portal_pages.get_page(page_id)


def get_page_by_path(path: str) -> PortalPage | None:
    """Get a single portal page by URL path."""
    return portal_pages.get_page_by_path(path)


def get_sitemap_entries() -> list[dict[str, str]]:
    """Return sitemap entries for SEO.

    Combines the root page, all registered portal pages, and the service
    detail pages. Each entry is a URL + priority + changefreq.
    """
    entries: list[dict[str, str]] = [
        {"path": "/", "priority": "1.0", "changefreq": "weekly"},
    ]
    # Add all registered portal pages
    for page in portal_pages.get_sitemap_pages():
        entries.append(
            {
                "path": page.path,
                "priority": "0.8" if page.id in ("services", "renters_guide") else "0.6",
                "changefreq": "weekly" if page.id in ("services", "tools") else "monthly",
            }
        )
    return entries
