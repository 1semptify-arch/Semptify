"""Portal API router.

Endpoints:
- GET /api/portal/services — list all visible portal services
- GET /api/portal/services/{service_id} — get a single service
- GET /api/portal/pages — list all public pages
- GET /api/portal/sitemap — return sitemap entries for SEO (JSON)
- GET /sitemap.xml — XML sitemap for search engines
- GET /robots.txt — robots.txt for search engines
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.core.utc import utc_now
from app.modules.portal.service import (
    get_portal_catalog,
    get_service,
    get_sitemap_entries,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portal", tags=["Portal"])

# Separate router for SEO files at root (no /api/portal prefix)
seo_router = APIRouter(tags=["SEO"])


@router.get("/services")
async def list_portal_services():
    """List all visible portal services, grouped by category.

    Public endpoint — no auth required. Used by the portal page
    to render the services catalog.
    """
    catalog = get_portal_catalog()
    return catalog


@router.get("/services/{service_id}")
async def get_portal_service(service_id: str):
    """Get a single portal service by ID.

    Public endpoint — no auth required.
    """
    service = get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service_id}")
    return {
        "id": service.id,
        "name": service.name,
        "short_description": service.short_description,
        "cta_label": service.cta_label,
        "cta_path": service.cta_path,
        "icon": service.icon,
        "category": service.category,
        "order": service.order,
        "requires_auth": service.requires_auth,
        "description_long": service.description_long,
    }


@router.get("/pages")
async def list_portal_pages():
    """List all public portal pages.

    Public endpoint — no auth required. Used to build navigation
    and footer links.
    """
    from app.modules.portal.pages import portal_pages

    return portal_pages.to_dict()


@router.get("/sitemap")
async def get_portal_sitemap():
    """Return sitemap entries for SEO (JSON).

    Public endpoint — no auth required.
    """
    entries = get_sitemap_entries()
    return {"entries": entries, "count": len(entries)}


@seo_router.get("/sitemap.xml")
async def get_sitemap_xml(request: Request):
    """XML sitemap for search engines.

    Public endpoint — no auth required. Returns a valid sitemap.xml
    built from the portal pages registry.
    """
    base_url = str(request.base_url).rstrip("/")
    entries = get_sitemap_entries()
    lastmod = utc_now().strftime("%Y-%m-%d")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for entry in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{base_url}{entry['path']}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{entry['changefreq']}</changefreq>")
        lines.append(f"    <priority>{entry['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")

    content = "\n".join(lines)
    return Response(content=content, media_type="application/xml")


@seo_router.get("/robots.txt")
async def get_robots_txt(request: Request):
    """robots.txt for search engines.

    Public endpoint — no auth required. Allows all crawlers, points
    to the sitemap.
    """
    base_url = str(request.base_url).rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /api/",
        "Disallow: /onboarding/",
        "Disallow: /storage/",
        "Disallow: /tenant/",
        "Disallow: /advocate/",
        "Disallow: /legal/",
        "Disallow: /manager/",
        "Disallow: /admin/",
        "Disallow: /vault/",
        "Disallow: /documents/",
        "Disallow: /static/",
        "",
        f"Sitemap: {base_url}/sitemap.xml",
    ]
    content = "\n".join(lines)
    return Response(content=content, media_type="text/plain")
