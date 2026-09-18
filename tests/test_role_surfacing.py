"""Role landing surfacing — config integrity + href/route validation.

The surfacing block in role_configs/*.json drives landing-page sections and
tools. Every href must resolve to a real registered GET route — a config that
points at a missing path creates a dead end, which is banned.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "app" / "modules" / "onboarding" / "role_configs"

CONFIG_KEYS = [
    "tenant",
    "advocate",
    "multi_client_advocate",
    "legal",
    "manager",
    "admin",
    "agency",
    "developer",
    "researcher",
    "donor_supporter",
]


def _registered_paths() -> set[str]:
    """All registered GET route paths (exact + parameterized patterns)."""
    from app.main import fastapi_app

    paths = set()
    for route in fastapi_app.routes:
        path = getattr(route, "path", None)
        if not path:
            continue
        methods = getattr(route, "methods", set()) or set()
        if "GET" in methods:
            paths.add(path)
    return paths


def _matches(path: str, registered: set[str]) -> bool:
    """Exact match, or matches a parameterized route pattern."""
    if path in registered:
        return True
    if path.rstrip("/") in {p.rstrip("/") for p in registered}:
        return True
    for pattern in registered:
        if "{" not in pattern:
            continue
        regex = "^" + re.sub(r"\{[^}]+\}", r"[^/]+", pattern.rstrip("/")) + "/?$"
        if re.match(regex, path):
            return True
    return False


@pytest.fixture(scope="module")
def registered_paths():
    return _registered_paths()


def test_every_config_has_surfacing():
    for key in CONFIG_KEYS:
        cfg = json.loads((CONFIG_DIR / f"{key}.json").read_text(encoding="utf-8"))
        surfacing = cfg.get("surfacing")
        assert isinstance(surfacing, dict), f"{key}.json missing surfacing block"
        assert surfacing.get("sections") or surfacing.get("tools"), (
            f"{key}.json surfacing has no sections or tools"
        )


def test_surfacing_hrefs_resolve_to_real_routes(registered_paths):
    bad = []
    for key in CONFIG_KEYS:
        cfg = json.loads((CONFIG_DIR / f"{key}.json").read_text(encoding="utf-8"))
        surfacing = cfg.get("surfacing") or {}
        items = list(surfacing.get("sections") or []) + list(surfacing.get("tools") or [])
        for item in items:
            href = item.get("href", "")
            if not _matches(href, registered_paths):
                bad.append(f"{key}: {item.get('title') or item.get('label')} -> {href}")
    assert not bad, "Surfacing hrefs with no registered route:\n" + "\n".join(bad)


def test_surfacing_items_have_required_fields():
    for key in CONFIG_KEYS:
        cfg = json.loads((CONFIG_DIR / f"{key}.json").read_text(encoding="utf-8"))
        surfacing = cfg.get("surfacing") or {}
        for item in surfacing.get("sections") or []:
            assert item.get("title") and item.get("href") and item.get("why"), (
                f"{key} section missing title/href/why: {item}"
            )
        for item in surfacing.get("tools") or []:
            assert item.get("label") and item.get("href") and item.get("why"), (
                f"{key} tool missing label/href/why: {item}"
            )


def test_get_role_surfacing_aliases_and_fallback():
    from app.core.role_surfacing import get_role_surfacing

    assert isinstance(get_role_surfacing("tenant"), dict)
    # Legacy alias resolves to the tenant config
    assert get_role_surfacing("user") == get_role_surfacing("tenant")
    # Unknown / empty roles return None, never raise
    assert get_role_surfacing("not_a_role") is None
    assert get_role_surfacing(None) is None
    assert get_role_surfacing("") is None
