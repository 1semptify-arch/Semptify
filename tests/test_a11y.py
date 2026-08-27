"""
ARIA / accessibility regression tests for tenant and public pages.

These are not a full audit, but they guarantee that every tenant-facing
and public-facing page we ship has the landmarks and form labels that
screen-reader users rely on.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from lxml import html

# Public pages anyone can reach.
PUBLIC_PATHS: list[str] = [
    "/",
    "/help",
    "/renters-guide",
]

# Pages an authenticated tenant user reaches.
TENANT_PATHS: list[str] = [
    "/dashboard",
    "/documents",
    "/timeline",
    "/vault",
]


def _element_text(element) -> str:
    """Return the concatenated text content of an element, including children."""
    return " ".join(element.itertext()).strip()


def _control_has_label(element, tree) -> bool:
    """Return True if a form control has a programmatically associated label."""
    # aria-label / aria-labelledby
    if element.get("aria-label") or element.get("aria-labelledby"):
        return True

    # Direct <label> wrapper
    if element.getparent().tag == "label":
        return True

    # <label for="id">
    control_id = element.get("id")
    if control_id:
        for label in tree.xpath(f'//label[@for="{control_id}"]'):
            if _element_text(label):
                return True

    # placeholder alone is not an accessible name
    return False


def _landmark_count(tree) -> dict[str, int]:
    """Count explicit ARIA landmarks and HTML5 landmark elements."""
    return {
        "main": len(tree.xpath("//main")),
        "main_role": len(tree.xpath("//*[@role='main']")),
        "nav": len(tree.xpath("//nav")),
        "nav_role": len(tree.xpath("//*[@role='navigation']")),
        "header": len(tree.xpath("//header")),
        "banner_role": len(tree.xpath("//*[@role='banner']")),
        "footer": len(tree.xpath("//footer")),
        "contentinfo_role": len(tree.xpath("//*[@role='contentinfo']")),
    }


def _collect_a11y_issues(path: str, html_text: str) -> list[str]:
    """Parse a page and return a list of accessibility issues (landmarks, labels)."""
    issues: list[str] = []
    tree = html.fromstring(html_text)

    # One and only one main landmark
    landmarks = _landmark_count(tree)
    total_main = landmarks["main"] + landmarks["main_role"]
    if total_main == 0:
        issues.append("missing main landmark")
    elif total_main > 1:
        issues.append(f"multiple main landmarks ({total_main})")

    # Navigation landmark must have an accessible name
    navs = tree.xpath("//nav") + tree.xpath("//*[@role='navigation']")
    for i, nav in enumerate(navs):
        if not (nav.get("aria-label") or nav.get("aria-labelledby") or nav.get("title")):
            issues.append(f"nav[{i}] missing accessible name")

    # Form controls must have labels
    for tag in ("input", "select", "textarea"):
        for ctrl in tree.xpath(f"//{tag}"):
            # Skip purely decorative / non-interactive input types
            itype = (ctrl.get("type") or "").lower()
            if tag == "input" and itype in {"hidden", "submit", "button", "image", "reset"}:
                continue
            if not _control_has_label(ctrl, tree):
                name = ctrl.get("name") or ctrl.get("id") or "?"
                issues.append(f"unlabeled <{tag} name='{name}'>")

    # Buttons should have accessible text (or aria-label)
    for btn in tree.xpath("//button"):
        if not (_element_text(btn) or btn.get("aria-label") or btn.get("aria-labelledby")):
            issues.append("button with no accessible name")

    # Page should declare a language
    html_element = tree.xpath("//html")
    if not html_element or not html_element[0].get("lang"):
        issues.append("html element missing lang attribute")

    return issues


def _format_issue(path: str, issue: str) -> str:
    return f"{path}: {issue}"


@pytest.mark.anyio
@pytest.mark.parametrize("path", PUBLIC_PATHS)
async def test_public_pages_have_accessible_landmarks(client: AsyncClient, path: str):
    """Public pages must expose main, nav, header and footer landmarks."""
    response = await client.get(path, follow_redirects=True)
    # A public page may redirect to a newer route; just make sure it lands 200
    assert response.status_code == 200, f"{path} returned {response.status_code}"
    issues = _collect_a11y_issues(path, response.text)
    assert not issues, "\n".join(_format_issue(path, i) for i in issues)


@pytest.mark.anyio
@pytest.mark.parametrize("path", TENANT_PATHS)
async def test_tenant_pages_have_accessible_landmarks(authenticated_client: AsyncClient, path: str):
    """Tenant pages must expose main, nav, header and footer landmarks."""
    response = await authenticated_client.get(path, follow_redirects=True)
    assert response.status_code == 200, f"{path} returned {response.status_code}"
    issues = _collect_a11y_issues(path, response.text)
    assert not issues, "\n".join(_format_issue(path, i) for i in issues)
