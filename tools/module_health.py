"""
Generic health checks for tools/module_registry.yaml.

Each registry module gets a ``check_<id>()`` callable generated at import time.
The check confirms the module's router is importable, has routes, and enforces
the public/admin route-exposure boundary. Admin-only modules are not allowed to
expose public routes unless those routes carry an admin/capability/elevation
guard.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import yaml
from fastapi import APIRouter

REGISTRY_PATH = Path(__file__).resolve().parent / "module_registry.yaml"

# Public prefixes that are also acceptable for admin-only modules (admin
# authentication is enforced inside the route itself or via module gate).
_ADMIN_PUBLIC_PREFIXES = (
    "/admin/api/",
    "/debug/",
)

# Markers that a route dependency is an admin/capability/elevation guard.
_ADMIN_GUARD_MARKERS = (
    "admin",
    "stealth",
    "elevation",
    "capability",
)


def _load_registry() -> list[dict]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _is_admin_only(entry) -> bool:
    """
    Return True if the manifest entry is intended to be admin-only.

    The authoritative signal is ``requires_role``. A module is admin-only
    only when it explicitly requires the admin role and does not also grant
    access to public-facing roles. Product tier alone is not a reliable
    access-control signal (dev/admin tiers may contain public tools such as
    the vault installer or setup wizard).
    """
    roles = getattr(entry, "requires_role", None) or ()

    return "admin" in roles and not any(r in ("tenant", "user", "advocate", "manager", "legal") for r in roles)


def _collect_dependency_callables(route) -> set:
    """Recursively collect all callables used as FastAPI dependencies."""
    calls: set = set()
    seen: set = set()

    def visit(dependant):
        if dependant is None or id(dependant) in seen:
            return
        seen.add(id(dependant))
        call = getattr(dependant, "call", None)
        if call is not None:
            calls.add(call)
        for dep in getattr(dependant, "dependencies", []) or []:
            visit(dep)

    visit(getattr(route, "dependant", None))

    for dep in getattr(route, "dependencies", []) or []:
        call = getattr(dep, "dependency", None)
        if call is not None:
            calls.add(call)

    return calls


def _has_admin_guard(route) -> bool:
    """Return True if a route has an admin/capability/elevation guard."""
    for call in _collect_dependency_callables(route):
        name = getattr(call, "__name__", "").lower()
        qualname = getattr(call, "__qualname__", name).lower()
        if any(marker in name or marker in qualname for marker in _ADMIN_GUARD_MARKERS):
            return True
    return False


def _full_path(prefix: str, path: str) -> str:
    """Combine a manifest/router prefix with a route path."""
    if not prefix or path.startswith(prefix.rstrip("/") + "/"):
        return path
    if path == "/":
        return prefix.rstrip("/") + "/"
    return prefix.rstrip("/") + path


def _route_pairs(router: APIRouter) -> list[tuple[str, object]]:
    """Return (path, route) pairs for routes that have a resolvable path."""
    pairs: list[tuple[str, object]] = []
    for route in getattr(router, "routes", []) or []:
        path = getattr(route, "path", None)
        if path:
            pairs.append((path, route))
    return pairs


def _check_module(module_path: str) -> tuple[bool, str]:
    """
    Real conformance check for a product-manifest module.

    Returns (ok, message). Checks:
      1. Module imports and its declared router attribute exists.
      2. The router has at least one route.
      3. No duplicate path+method within the module's router.
      4. Admin/dev-only modules do not expose public routes without an
         admin/capability/elevation guard.
    """
    from app.core.product_manifest import MANIFEST
    from app.core.storage_middleware import is_public_path

    entry = MANIFEST.find(module_path)
    if entry is None:
        return False, "no product manifest entry"

    try:
        module = importlib.import_module(module_path)
    except Exception as exc:
        return False, f"import failed: {exc}"

    router_attr = getattr(entry, "router_attr", "router")
    router = getattr(module, router_attr, None)
    if router is None:
        return False, f"router attribute '{router_attr}' missing"

    if not isinstance(router, APIRouter):
        return False, "router attribute is not an APIRouter"

    pairs = _route_pairs(router)
    if not pairs:
        return False, "router has no routes"

    # Resolve full paths using the manifest prefix, if any.
    full_prefix = getattr(entry, "prefix", "") or ""

    # Duplicate detection within the module's own router (same path + methods).
    seen: set[tuple[str, frozenset[str]]] = set()
    duplicates: list[str] = []
    for path, route in pairs:
        methods = frozenset(getattr(route, "methods", {"GET"}) or {"GET"})
        key = (path, methods)
        if key in seen:
            duplicates.append(f"{path} {methods}")
        seen.add(key)
    if duplicates:
        return False, f"duplicate paths: {duplicates}"

    # Route-exposure check for admin-only modules.
    admin_only = _is_admin_only(entry)
    if admin_only:
        exposed: set[str] = set()
        for path, route in pairs:
            full_path = _full_path(full_prefix, path)
            if (
                is_public_path(full_path)
                and not any(full_path.startswith(prefix) for prefix in _ADMIN_PUBLIC_PREFIXES)
                and not _has_admin_guard(route)
            ):
                exposed.add(full_path)
        if exposed:
            return False, f"admin module exposes unguarded public route(s): {sorted(exposed)}"

    return True, f"{len(pairs)} route(s), no exposure issues"


def _build_check(entry: dict):
    """Factory for per-module health check callables."""
    module_path = entry["module_path"]

    def check() -> tuple[bool, str]:
        return _check_module(module_path)

    check.__name__ = f"check_{entry['id']}"
    check.__doc__ = f"Health check for module {entry['id']} ({module_path})"
    return check


# Generate a check_<id>() function for every registry entry that has a module
# path. Callables are resolved by verify_modules.py via dotted names like
# ``tools.module_health.check_health``.
for _entry in _load_registry():
    _id = _entry.get("id")
    _module_path = _entry.get("module_path")
    if not _id or not _module_path:
        continue
    # Sanitize id to a valid Python identifier for the function name.
    _safe_id = re.sub(r"[^a-z0-9_]", "_", _id).lower()
    globals()[f"check_{_safe_id}"] = _build_check(_entry)
