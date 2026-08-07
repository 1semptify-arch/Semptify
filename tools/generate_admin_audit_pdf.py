#!/usr/bin/env python3
"""Generate a comprehensive Semptify admin audit PDF.

This script introspects the running FastAPI application to enumerate all
admin-protected routes, then combines them with manually-curated sections for
authentication, authorization, dashboard capabilities, standalone tools, and
limitations. The output is written to docs/reports/Semptify_Admin_Audit.pdf.
"""

import html
import os
import sys
from collections import defaultdict
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

# Ensure the repo root is on sys.path and admin env vars are present so the
# app can be imported without raising on missing configuration.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "dummy")

from fastapi import params  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.user_context import UserRole  # noqa: E402
from app.main import fastapi_app  # noqa: E402

OUTPUT_DIR = REPO / "docs" / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PDF = OUTPUT_DIR / "Semptify_Admin_Audit.pdf"

# ---------------------------------------------------------------------------
# Route introspection helpers
# ---------------------------------------------------------------------------


def _closure_vars(fn):
    """Return a dict of closure variables for a function."""
    result = {}
    if not getattr(fn, "__closure__", None):
        return result
    freevars = fn.__code__.co_freevars
    for name, cell in zip(freevars, fn.__closure__, strict=False):
        with suppress(ValueError):
            result[name] = cell.cell_contents
    return result


def _collect_dependant_calls(dependant, seen=None):
    """Recursively collect callables from a FastAPI Dependant tree."""
    calls = []
    if seen is None:
        seen = set()
    dep_id = id(dependant)
    if dep_id in seen:
        return calls
    seen.add(dep_id)
    if dependant.call is not None:
        calls.append(dependant.call)
    for sub in getattr(dependant, "dependencies", []):
        calls.extend(_collect_dependant_calls(sub, seen))
    return calls


def _route_callables(route):
    """Return all callables that protect a route (dependencies + dependant tree)."""
    calls = []
    for dep in getattr(route, "dependencies", []):
        if isinstance(dep, params.Depends) and dep.dependency is not None:
            calls.append(dep.dependency)
    if hasattr(route, "dependant"):
        calls.extend(_collect_dependant_calls(route.dependant))
    return calls


def _guard_kind(fn):
    """Classify a dependency callable as an admin guard and return metadata."""
    name = getattr(fn, "__name__", str(fn))
    closure = _closure_vars(fn)

    if name == "require_admin":
        return "admin role"
    if name == "_require_elevation":
        return "admin elevation"
    if name == "_stealth_admin":
        return "stealth admin"
    if name == "require_role":
        roles = closure.get("roles", ())
        try:
            role_names = [r.value if isinstance(r, UserRole) else str(r) for r in roles]
        except TypeError:
            role_names = [str(roles)]
        if "admin" in role_names:
            return "admin role"
        return None
    if name == "_gate":
        module_name = closure.get("module_name", "")
        if isinstance(module_name, str) and (
            module_name.startswith("admin") or "admin_" in module_name or module_name == "admin_console"
        ):
            return f"capability:{module_name}"
        return None
    return None


def _is_auth_flow(route):
    """Return True for the public admin login/logout endpoints."""
    if not hasattr(route, "path"):
        return False
    return route.path in {
        "/admin/login",
        "/admin/api/login-step1",
        "/admin/api/login-step2",
        "/admin/logout",
    }


def _extract_admin_routes():
    """Introspect fastapi_app and return admin-protected routes grouped by tag."""
    admin_routes = []
    auth_routes = []

    for route in fastapi_app.routes:
        if not hasattr(route, "path") or not hasattr(route, "methods"):
            continue

        calls = _route_callables(route)
        guards = []
        for fn in calls:
            kind = _guard_kind(fn)
            if kind:
                guards.append(kind)

        # Also consider explicit admin path prefixes / tags.
        tags = getattr(route, "tags", []) or []
        path = route.path
        is_admin_path = path.startswith("/admin") or path.startswith("/admin-console")
        is_admin_tag = any("admin" in (t or "").lower() for t in tags)

        if not guards and not (is_admin_path or is_admin_tag):
            continue

        # If it has no guards but is an admin path, it may be a static page
        # served under /admin that is gated elsewhere; still list it.
        if not guards and is_admin_path:
            guards = ["admin access"]

        endpoint = getattr(route, "endpoint", None)
        doc = (getattr(endpoint, "__doc__", "") or "").strip().split("\n")[0].strip()

        entry = {
            "path": path,
            "methods": ", ".join(sorted(route.methods or [])),
            "tags": ", ".join(tags) if tags else "admin",
            "guards": ", ".join(sorted(set(guards))) if guards else "",
            "description": doc,
        }

        if _is_auth_flow(route):
            auth_routes.append(entry)
        else:
            admin_routes.append(entry)

    # Group remaining admin routes by a derived module name.
    groups = defaultdict(list)
    for r in admin_routes:
        tag = (r["tags"].split(",")[0] or "Admin").strip()
        groups[tag].append(r)

    # Sort groups and routes within groups for stable output.
    sorted_groups = {k: sorted(v, key=lambda x: x["path"]) for k, v in sorted(groups.items())}

    return auth_routes, sorted_groups


# ---------------------------------------------------------------------------
# PDF building helpers
# ---------------------------------------------------------------------------


def _styles():
    """Return the report styles."""
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading1Custom",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            spaceBefore=18,
            spaceAfter=10,
            textColor=colors.HexColor("#0c4a6e"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading2Custom",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#075985"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading3Custom",
            parent=styles["Heading3"],
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallCustom",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeCustom",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            fontName="Courier",
        )
    )
    return styles


def _p(text, style="BodyCustom", bold=False):
    """Return a Paragraph with HTML-escaped text and optional bold wrapper."""
    safe = html.escape(str(text))
    if bold:
        safe = f"<b>{safe}</b>"
    return Paragraph(safe, styles[style])


def _bullet(text, style="BodyCustom"):
    """Return a ListItem wrapping a Paragraph."""
    return ListItem(_p(text, style=style))


def _bullets(items, style="BodyCustom"):
    """Return a ListFlowable of bullets."""
    return ListFlowable([_bullet(i, style) for i in items], bulletType="bullet")


def _table(headers, rows, col_widths, header_style=True):
    """Build a reportlab Table with wrapped Paragraph cells."""
    data = [[_p(h, style="SmallCustom", bold=True) for h in headers]]
    for row in rows:
        data.append([_p(cell, style="SmallCustom") for cell in row])

    table = Table(data, colWidths=col_widths, repeatRows=1 if header_style else 0)
    style_commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]
    if header_style:
        style_commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0c4a6e")),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#94a3b8")),
            ]
        )
    style_commands.append(("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")))
    table.setStyle(TableStyle(style_commands))
    return table


styles = _styles()


# ---------------------------------------------------------------------------
# Static report content
# ---------------------------------------------------------------------------


def _add_auth_section(story):
    story.append(_p("1. Authentication & Authorization", style="Heading1Custom"))

    story.append(_p("Admin login URL", style="Heading2Custom"))
    story.append(_p("/admin/login"))
    story.append(
        _bullets(
            [
                "Requires an existing OAuth session before elevation.",
                "Step 1: validates ADMIN_USERNAME / ADMIN_PASSWORD environment variables.",
                "Step 2: validates a 6-digit TOTP code if ADMIN_TOTP_SECRET is configured (60-second drift window).",
                "If TOTP is not configured, the bypass code 000000 is accepted.",
                "On success, issues the semptify_admin_elev cookie and redirects to /admin/dashboard.",
            ]
        )
    )

    story.append(_p("Elevation cookie", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "Name: semptify_admin_elev",
                "TTL: 2 hours (7200 seconds)",
                "Format: base64(payload JSON).HMAC-SHA256",
                "Payload fields: issued_at, expires_at, uid",
                "Signed with SECRET_KEY + ':admin_elevation'",
                "Attributes: HttpOnly, Secure, SameSite=Strict, Path=/",
                "Requires a valid OAuth session OR a valid elevation cookie for admin API access.",
            ]
        )
    )

    story.append(_p("Logout", style="Heading2Custom"))
    story.append(_p("GET /admin/logout clears the elevation cookie but does not clear the OAuth session."))


def _add_gating_section(story):
    story.append(_p("2. Admin Network Gating", style="Heading1Custom"))
    story.append(
        _p(
            "Admin endpoints are protected by a stealth middleware in app/core/admin_gating.py. "
            "If the client IP is not in an allowed range, the server returns HTTP 404 (Not Found) instead of 403, "
            "hiding the existence of admin routes."
        )
    )
    story.append(_p("Default allowed ranges", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "100.64.0.0/10  (Tailscale CGNAT)",
                "10.0.0.0/8     (RFC1918 private)",
                "172.16.0.0/12  (RFC1918 private)",
                "192.168.0.0/16 (RFC1918 private)",
                "127.0.0.0/8    (localhost)",
                "::1/128        (IPv6 localhost)",
            ]
        )
    )
    story.append(_p("Override via the ADMIN_IP_RANGES environment variable (comma-separated CIDR ranges)."))


def _add_roles_section(story):
    story.append(_p("3. Roles & Capabilities", style="Heading1Custom"))
    story.append(_p("UserRole values", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "admin    - Full system access",
                "manager  - Multi-client coordination",
                "tenant   - Standard housing-case user",
                "user     - Legacy alias for tenant (deprecated)",
                "advocate - Tenant advocate: helps multiple users",
                "legal    - Attorneys, judges, clerks, paralegals",
                "judge    - DEPRECATED, merged into legal",
            ]
        )
    )
    story.append(_p("Permission guards", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "require_admin            - Direct ADMIN role dependency (app.core.security).",
                "require_role(UserRole.*) - Require one or more specific roles.",
                "require_capability(name) - Require a module capability. Admins have the __all__ sentinel and bypass capability checks.",
                "_stealth_admin           - Returns 404 (not 403) on failure; also accepts an X-Admin-Token header or admin_token query param with rate limiting.",
                "_require_elevation       - Validates the admin elevation cookie used for /admin pages and API endpoints registered in app/main.py.",
            ]
        )
    )
    story.append(_p("Role-to-admin-module matrix", style="Heading2Custom"))
    matrix = [
        ["Role", "admin_console", "admin_funding", "admin_batch_ops", "admin_analytics", "Other admin paths"],
        ["ADMIN", "Yes", "Yes", "Yes", "Yes", "Yes"],
        ["MANAGER", "No", "No", "No", "No", "Invite-code create/list only"],
        ["ADVOCATE", "No", "No", "No", "No", "No"],
        ["LEGAL", "No", "No", "No", "No", "No"],
        ["TENANT", "No", "No", "No", "No", "No"],
    ]
    story.append(
        _table(matrix[0], matrix[1:], [1.0 * inch, 1.1 * inch, 1.1 * inch, 1.2 * inch, 1.2 * inch, 1.9 * inch])
    )


def _add_dashboard_section(story):
    story.append(_p("4. Admin GUI Dashboard Capabilities", style="Heading1Custom"))
    story.append(_p("Location: /admin/dashboard.html"))
    story.append(
        _p("The dashboard is the central hub for system monitoring, user management, and quick access to admin tools.")
    )

    story.append(_p("Dashboard cards & widgets", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "System Overview Hero - Total users, active cases, documents in vaults, pending signatures, 30-day uptime, security incidents, rate-limit violations, blockchain timestamps.",
                "User Breakdown Card - Distribution by tenant, advocate, legal professional, property manager.",
                "Recent Activity Feed - Real-time log of user signups, document signatures, uploads, advocate onboarding, maintenance events.",
                "Security Card - Uptime, incidents, rate limits, blockchain verification status.",
                "MNDES System Compliance Card - Minnesota District E-Filing System compliance status and file-type enforcement.",
                "Quick Actions Panel - Jump to Function Browser, Contract Browser, Theme Preview, Page Editor, Review Checklist, Component Inventory, Navigation Structure, MNDES Compliance.",
                "User Search Widget - Search by user ID, email, or name. Actions: Impersonate (all actions logged), Reset onboarding gates (storage_connected / vault_initialized), View vault summary.",
                "Audit Log Viewer - Recent admin actions with a Refresh button.",
                "System Configuration Card - Active tier count, loaded module count, active feature-flag count.",
                "API Keys Status Card - Count of configured vs. missing environment/API key variables.",
            ]
        )
    )

    story.append(_p("Linked admin tools", style="Heading2Custom"))
    tools = [
        ("/admin/function-browser.html", "Interactive function documentation"),
        ("/admin/contract-browser.html", "Page/module contracts and health"),
        ("/admin/page-editor.html", "Edit static and Jinja2 template files"),
        ("/admin/review-checklist.html", "Automated verification tests (contracts, routes, SSOT, footer, security)"),
        ("/admin/module-flags.html", "Runtime feature flags and module toggles"),
        ("/admin/forge.html", "Semptify Forge / Dev Lab (experimental features)"),
        ("/admin/agent_orchestrator.html", "AI task/agent queue"),
        ("/admin/api-workbook.html", "API testing workbook"),
        ("/admin/manual.html", "Admin manual"),
        ("/admin/overlay-viewer.html", "Overlay viewer"),
        ("/admin/page_shell_demo.html", "Page shell demo"),
    ]
    rows = [[url, desc] for url, desc in tools]
    story.append(_table(["URL", "Purpose"], rows, [2.4 * inch, 4.6 * inch]))


def _add_modules_section(story):
    story.append(_p("5. Admin-Only Modules", style="Heading1Custom"))
    modules = [
        (
            "funding_mgmt",
            "/admin/funding/*",
            "admin_funding",
            "Track funding sources, applications, budgets, and the ID System prospectus.",
        ),
        (
            "invite_codes",
            "/api/invite-codes/*",
            "MANAGER/ADMIN",
            "Validate/redeem (public), create/list/deactivate (manager or admin).",
        ),
        (
            "batch",
            "/batch/*",
            "admin_batch_ops",
            "Bulk document upload, deletion, export/import, tagging, and analysis.",
        ),
        (
            "analytics",
            "/analytics/*",
            "admin_analytics",
            "Usage metrics, realtime metrics, event listing, and data export.",
        ),
        (
            "admin_console",
            "/admin-console/*",
            "admin_console",
            "User management, system configuration, content (help articles / law library / letter templates), audit log, feature flags, tiers, modules, error queue.",
        ),
        (
            "agent_orchestrator",
            "/api/agent-orchestrator/*",
            "stealth admin",
            "Queue parallel agent tasks, assign models, track progress, batch tasks, copy-paste prompts.",
        ),
        (
            "module_flags",
            "/admin/api/module-flags/*",
            "admin_module_flags",
            "Runtime module overrides, reload, preview-as-user.",
        ),
        ("dev_lab", "/dev/lab*", "admin dev lab", "Experimental development tools and ideas router."),
        ("page_shell", "/api/page-shell/*", "admin page shell", "Admin-only page shell API."),
        ("document_center", "/api/dc/*", "admin", "Admin-only document center operations (stable)."),
        ("fems", "/api/fems/*", "admin", "Forensic Evidence Management System endpoints."),
    ]
    rows = [[m[1], m[0], m[2], m[3]] for m in modules]
    story.append(
        _table(
            ["Route prefix", "Module", "Capability/guard", "Description"],
            rows,
            [1.7 * inch, 1.3 * inch, 1.4 * inch, 2.6 * inch],
        )
    )


def _add_standalone_section(story):
    story.append(_p("6. Standalone Admin Tools", style="Heading1Custom"))
    story.append(_p("Funding Forge", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "Location: funding_forge/",
                "Entry: funding_forge/main.py; start script: funding_forge/start_funding_forge.ps1",
                "Default port: 8001 (APP_HOST / APP_PORT)",
                "Auth: self-contained admin gate with signed funding_forge_admin cookie; credentials from FUNDING_FORGE_ADMIN_* or ADMIN_* env vars; optional TOTP.",
                "Features: funders, contacts, opportunities, application steps, interactions, tasks, documents, emails, optional Cloudflare R2 storage, 33 pre-seeded funding entities.",
            ]
        )
    )
    story.append(_p("Legal Intel Engine", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "Location: legal_intel/",
                "Entry: legal_intel/app/main.py",
                "Features: crawls Minnesota court records (MCRO), MN SOS, CourtListener, PlainSite; pattern detection; shell-LLC clustering.",
                "GUI: legal_intel/gui.py (Tkinter) for attorney/entity crawl and pattern viewing.",
                "No separate admin auth detected; intended as an internal service.",
            ]
        )
    )
    story.append(_p("Dakota County Eviction Defense", style="Heading2Custom"))
    story.append(
        _p(
            "Location: semptify_dakota_eviction/. Optional standalone FastAPI app with eviction defense flows, court forms, and multi-language support. Not an admin tool; listed for completeness."
        )
    )


def _add_env_section(story):
    story.append(_p("7. Environment Variables & Configuration", style="Heading1Custom"))
    story.append(_p("Admin credentials", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "ADMIN_USERNAME - Admin login username (default: admin).",
                "ADMIN_PASSWORD - Admin login password. Required in production; no default.",
                "ADMIN_TOTP_SECRET - Base32 TOTP secret for two-factor authentication (optional).",
                "ADMIN_PIN - Optional elevated-access PIN.",
            ]
        )
    )
    story.append(_p("Network / security", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "ADMIN_IP_RANGES - Comma-separated CIDR list overriding default allowed admin networks.",
                "SECRET_KEY - Used to sign the elevation cookie and other security tokens.",
                "SECURITY_MODE - 'open' (dev) or 'enforced' (production).",
            ]
        )
    )
    story.append(_p("Standalone tools", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "FUNDING_FORGE_ADMIN_USERNAME / FUNDING_FORGE_ADMIN_PASSWORD / FUNDING_FORGE_ADMIN_TOTP_SECRET",
                "FUNDING_FORGE_RESEND_API_KEY, FUNDING_FORGE_SMTP_*",
                "FUNDING_FORGE_R2_* (optional Cloudflare R2 document storage).",
            ]
        )
    )


def _add_limits_section(story):
    story.append(_p("8. Limitations, Security Considerations & Operational Notes", style="Heading1Custom"))
    story.append(_p("What admin cannot do", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "Direct SQL/database access - only API endpoints are available.",
                "View or modify user OAuth tokens.",
                "Access storage-provider credentials on behalf of users.",
                "Force-logout users or revoke elevation cookies before expiry.",
                "Hot-reload modules without a server restart.",
                "Rotate SECRET_KEY or other secrets without a restart.",
            ]
        )
    )
    story.append(_p("Security considerations", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "Elevation cookie theft grants up to 2 hours of admin access.",
                "TOTP secret stored in environment; if leaked, 2FA is bypassable.",
                "IP gating relies on trusted proxy headers; a compromised proxy can bypass it.",
                "Stealth 404 responses may still be logged by load balancers.",
                "Admin-token rate limiting is in-memory only; resets on server restart.",
                "Impersonation is logged but has no real-time alert hook.",
                "/admin-console/api/env-update can change environment variables at runtime (high privilege).",
            ]
        )
    )
    story.append(_p("Operational notes", style="Heading2Custom"))
    story.append(
        _bullets(
            [
                "Python version is strictly 3.11.9.",
                "SECRET_KEY auto-generates in dev with a warning; must be set in production.",
                "Session storage is in-memory by default; Redis recommended for production.",
                "Log retention default is 90 days (LOG_RETENTION_DAYS).",
                "Feature flags are runtime-toggled and persisted in the database.",
            ]
        )
    )


def _add_route_inventory(story, auth_routes, admin_groups):
    story.append(PageBreak())
    story.append(_p("9. Full Admin Route Inventory", style="Heading1Custom"))
    story.append(
        _p(
            "The following tables list routes that are protected by admin guards or that live under an /admin path. "
            "The 'Guard' column shows the protection mechanism found by introspection."
        )
    )

    if auth_routes:
        story.append(_p("9.1 Public admin authentication routes", style="Heading2Custom"))
        rows = [[r["methods"], r["path"], r["guards"], r["description"]] for r in auth_routes]
        story.append(
            _table(["Methods", "Path", "Guard", "Description"], rows, [0.7 * inch, 2.4 * inch, 1.4 * inch, 2.5 * inch])
        )

    for tag, routes in admin_groups.items():
        story.append(_p(f"9.{tag.replace(' ', '_')}", style="Heading2Custom"))
        # Limit the tag name to a safe header string
        display_tag = html.escape(tag)
        story[-1] = _p(f"Module / tag: {display_tag}", style="Heading2Custom")
        rows = [[r["methods"], r["path"], r["guards"], r["description"]] for r in routes]
        # If a group is very large, split into multiple tables to keep the PDF readable.
        chunk_size = 40
        for idx in range(0, len(rows), chunk_size):
            chunk = rows[idx : idx + chunk_size]
            story.append(
                _table(
                    ["Methods", "Path", "Guard", "Description"], chunk, [0.7 * inch, 2.4 * inch, 1.4 * inch, 2.5 * inch]
                )
            )
            if idx + chunk_size < len(rows):
                story.append(Spacer(1, 0.1 * inch))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_pdf():
    auth_routes, admin_groups = _extract_admin_routes()

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story = []

    story.append(_p("Semptify Administrator Audit Report", style="ReportTitle", bold=True))
    story.append(_p(f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}", style="BodyCustom"))
    story.append(_p(f"Repository: {REPO}", style="BodyCustom"))
    story.append(Spacer(1, 0.25 * inch))

    _add_auth_section(story)
    _add_gating_section(story)
    _add_roles_section(story)
    _add_dashboard_section(story)
    _add_modules_section(story)
    _add_standalone_section(story)
    _add_env_section(story)
    _add_limits_section(story)
    _add_route_inventory(story, auth_routes, admin_groups)

    doc.build(story)
    print(f"PDF written to: {OUTPUT_PDF}")
    print(f"Admin routes found: {sum(len(v) for v in admin_groups.values())}")


if __name__ == "__main__":
    build_pdf()
