"""contract_route_check.py — FunctionGroupContract vs actual route conformance.

Checks that every module with registered FunctionGroupContracts:
  1. Has a valid tier (T0–T3).
  2. Declares allowed_prefixes that cover the product manifest prefix.
  3. Has every actual FastAPI route path in its allowed_routes.
  4. Does not expose a T1/T2/T3 route under a PUBLIC_PREFIXES path.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

# Guardrail plugins live in tools/checks/; app/ is two directories up.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from guardrail_engine import CheckResult  # noqa: E402

_VALID_TIERS = {"T0", "T1", "T2", "T3"}


def _full_path(prefix: str, path: str) -> str:
    """Combine manifest prefix with router path."""
    if not prefix:
        return path or "/"
    if path == "/":
        return prefix + "/"
    return prefix.rstrip("/") + "/" + path.lstrip("/")


def run(repo_root: Path) -> CheckResult:
    """Run the contract-vs-route conformance guardrail."""
    from app.core.contract_loader import load_all_contracts
    from app.core.module_contracts import contract_registry
    from app.core.product_manifest import MANIFEST
    from app.core.storage_middleware import is_public_path

    result = load_all_contracts()
    if result["failed"]:
        return CheckResult(
            name="contract_route_check",
            passed=False,
            summary=f"Contract loader failed: {result['failed']} module(s) failed to load.",
            details=str(result),
        )

    contracts = contract_registry.list_contracts()
    if not contracts:
        return CheckResult(
            name="contract_route_check",
            passed=True,
            summary="No FunctionGroupContracts registered — nothing to check.",
        )

    # Group contracts by module
    module_contracts: dict[str, list[Any]] = {}
    for contract in contracts:
        module_contracts.setdefault(contract.module, []).append(contract)

    failures: list[str] = []

    for module, mcs in module_contracts.items():
        allowed_routes: set[str] = set()
        allowed_prefixes: set[str] = set()
        tiers: set[str] = set()
        for c in mcs:
            allowed_routes.update(c.allowed_routes)
            allowed_prefixes.update(c.allowed_prefixes)
            if c.tier:
                tiers.add(c.tier)

        # Only enforce the new route-conformance contract fields for modules that
        # have opted in by setting allowed_routes, allowed_prefixes, or tier.
        # This prevents breaking 100+ existing modules that predate the extension.
        if not allowed_routes and not allowed_prefixes and not tiers:
            continue

        # Manifest entries may point at router.py, routes.py, or another
        # module inside the package (e.g. vault_installer uses routes.py).
        module_path = f"app.modules.{module}.router"
        entry = MANIFEST.find(module_path)
        if entry is None:
            package_prefix = f"app.modules.{module}."
            candidates = [
                e for e in MANIFEST.all()
                if e.module_path.startswith(package_prefix)
            ]
            entry = next(
                (e for e in candidates if e.module_path.endswith(".router")),
                candidates[0] if candidates else None,
            )
            if entry is not None:
                module_path = entry.module_path
        if entry is None:
            failures.append(f"{module}: contract registered but no product manifest entry")
            continue

        prefix = getattr(entry, "prefix", "") or ""

        # Tier validation
        invalid_tiers = tiers - _VALID_TIERS
        if invalid_tiers:
            failures.append(f"{module}: invalid tier(s) {sorted(invalid_tiers)}")

        # Prefix validation
        if prefix and not any(prefix == p or prefix.startswith(p.rstrip("/") + "/") for p in allowed_prefixes):
            failures.append(
                f"{module}: manifest prefix {prefix!r} not covered by allowed_prefixes {sorted(allowed_prefixes)}"
            )

        # Import router and get actual route paths
        try:
            mod = importlib.import_module(module_path)
        except Exception as exc:
            failures.append(f"{module}: could not import router: {exc}")
            continue

        router = getattr(mod, "router", None)
        if router is None:
            failures.append(f"{module}: router attribute missing on {module_path}")
            continue

        actual_routes: set[str] = set()
        # Routes under PUBLIC_PREFIXES that enforce their own auth via
        # Depends(get_current_user / require_admin / ...) are not truly public —
        # the middleware defers to the endpoint. Track which paths do this so
        # the public-exposure rule below only flags genuinely open routes.
        self_authed_paths: set[str] = set()
        for route in getattr(router, "routes", []) or []:
            path = getattr(route, "path", None)
            if not path:
                continue
            full = _full_path(prefix, path)
            actual_routes.add(full)

            dep_names = {
                getattr(getattr(dep, "call", None), "__name__", "")
                for dep in getattr(getattr(route, "dependant", None), "dependencies", [])
            }
            if any(
                name and ("current_user" in name or "require_admin" in name or "auth" in name)
                for name in dep_names
            ):
                self_authed_paths.add(full)

        if not actual_routes:
            failures.append(f"{module}: router has no routes")
            continue

        # Every actual route must be declared in the contract
        for route in actual_routes:
            if route not in allowed_routes:
                failures.append(f"{module}: actual route {route!r} not in allowed_routes")

            # Public exposure: only T0 routes may live under public prefixes/paths.
            # Routes that enforce their own auth dependency are exempt — the
            # path is middleware-public but the endpoint is not.
            if (
                is_public_path(route)
                and route not in self_authed_paths
                and not all(t == "T0" for t in tiers)
            ):
                failures.append(
                    f"{module}: non-T0 route {route!r} is under a public prefix/path (tier={sorted(tiers)})"
                )

        # Every declared allowed_route should start with an allowed prefix
        for route in allowed_routes:
            if not any(route.startswith(p) for p in allowed_prefixes):
                failures.append(
                    f"{module}: allowed_route {route!r} does not start with any allowed_prefix "
                    f"{sorted(allowed_prefixes)}"
                )

    if failures:
        return CheckResult(
            name="contract_route_check",
            passed=False,
            summary=f"{len(failures)} contract/route conformance failure(s).",
            details="\n".join(failures),
        )

    return CheckResult(
        name="contract_route_check",
        passed=True,
        summary="FunctionGroupContract allowed_routes/prefixes/tiers match actual routes.",
    )
