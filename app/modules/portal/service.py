"""Portal service — builds the services catalog for the guest portal.

Reads from the PortalRegistry (SSOT) and returns the data needed to render
the portal page. No hallucination — all services are defined in the registry.
"""

from __future__ import annotations

import logging
import re

from app.modules.portal.pages import PortalPage, portal_pages
from app.modules.portal.registry import PortalService, portal

logger = logging.getLogger(__name__)

_BILL_ACT_NAME = "MINNESOTA RENT ASSURANCE"
_BILL_NOTES_HEAD = "Locked clauses"


def bill_statute_view(draft_html: str) -> str | None:
    """Derive the clean statute view from the published working-draft partial.

    The case-side publish pipeline regenerates ``public/bill_draft.html``
    with drafting shorthand inline — ``*(Locked ...)*``, ``*(NEEDS BRAD
    ...)*``, ``---`` separators, markdown ``**bold**``. This returns the
    same file's statute body (act name through Title IV) with that
    shorthand removed, so /bill/live can show a clean reading copy while
    the marked-up file stays intact on the notes tab. Nothing is copied
    into a second source file — the view is derived at render time, so
    the two tabs can never drift apart.

    Returns None when the expected markers are missing (e.g. the publish
    format changed), so the template can fall back to the raw include.
    """
    act = draft_html.find(_BILL_ACT_NAME)
    notes = draft_html.find(_BILL_NOTES_HEAD)
    if act == -1 or notes == -1 or notes <= act:
        return None
    start = draft_html.rfind("<h3", 0, act)
    end = draft_html.rfind("<h3", 0, notes)
    if start == -1 or end == -1:
        return None
    body = draft_html[start:end]

    # Drafting annotations *( ... )* — may span </p><p> boundaries in the
    # published markup; stripping them can leave empty paragraphs.
    body = re.sub(r"\*\(.*?\)\*", "", body, flags=re.S)
    # Clause run-ins (**I-1. Title.**) at paragraph start -> clause heads.
    body = re.sub(
        r"<p>\s*\*\*([IVX]+-\d+\.[^*]*?)\*\*",
        r'<h4 class="clause-head">\1</h4><p>',
        body,
    )
    # Remaining **bold** -> <strong>; the publish pipeline wraps lines
    # across paragraph boundaries, so merge the split inside the match.
    body = re.sub(
        r"\*\*(.+?)\*\*",
        lambda m: "<strong>" + re.sub(r"</p>\s*<p>", " ", m.group(1)) + "</strong>",
        body,
        flags=re.S,
    )
    # Single-star italic notes -> <em>, same paragraph-merge treatment.
    body = re.sub(
        r"\*([^*]+)\*",
        lambda m: "<em>" + re.sub(r"</p>\s*<p>", " ", m.group(1)) + "</em>",
        body,
        flags=re.S,
    )
    # Drafting separators -> rules; drop paragraphs emptied by stripping.
    body = re.sub(r'<p>\s*-{2,}\s*</p>', '<hr class="bill-rule">', body)
    while True:
        collapsed = re.sub(r"<p>\s*</p>", "", body)
        if collapsed == body:
            break
        body = collapsed
    return body.strip()


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
                "priority": "0.8" if page.id == "services" else "0.6",
                "changefreq": "weekly" if page.id in ("services", "tools") else "monthly",
            }
        )
    return entries
