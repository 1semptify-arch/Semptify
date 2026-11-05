"""route_audit_check.py — build-time twin of app/core/route_audit.py.

contract_route_check.py only inspects module routers discovered through the
product manifest, so routes registered directly on the FastAPI app object
(the /debug/* class of ad-hoc additions) are invisible to it. The runtime
audit in app/core/route_audit.py already walks fastapi_app.routes after
mounting, but it only logs warnings — an uncovered public route can ship
past it unnoticed.

This check builds the app via create_app() and runs the same scan inside
the guardrail engine so an uncovered public route fails the commit, not
just a log line. Scanning logic is deliberately NOT duplicated here —
scan_public_routes() is the single source of truth for what counts as
public, actionable, and contract-covered.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# Guardrail plugins live in tools/checks/; app/ is two directories up.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from guardrail_engine import CheckResult  # noqa: E402

# Same environment tests/conftest.py pins before importing the app:
# SECURITY_MODE=open mounts the widest surface (diagnostic routes only exist
# in open mode) and SEMPTIFY_ENV=development registers every contract tier.
# get_settings() is lru_cached and defaults to open, but pinning keeps this
# check deterministic if a later default ever tightens.
_ENV_PINS = {
    "SECURITY_MODE": "open",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "TESTING": "true",
    "INVITE_CODES": "ROUTE-AUDIT-INVITE",
    "ADMIN_PIN": "route-audit-pin",
    "SEMPTIFY_ENV": "development",
}


def run(repo_root: Path) -> CheckResult:
    """Build the app and flag uncovered actionable public routes."""
    # Snapshot and restore so the pins cannot leak into checks that run
    # after this one inside the same guardrail-engine process.
    saved_env = {key: os.environ.get(key) for key in _ENV_PINS}
    os.environ.update(_ENV_PINS)
    try:
        # Importing app.main runs create_app(): every router mounts, module
        # contracts load, and the runtime audit itself executes (its warnings
        # are log-only). This is the real mounted surface — ad-hoc routes
        # registered directly on fastapi_app are included.
        from app.main import app
    except Exception:
        return CheckResult(
            name="route_audit_check",
            passed=False,
            summary="create_app() failed — the app cannot be built in this "
            "environment, so the public-route surface cannot be audited.",
            details=traceback.format_exc(),
        )
    finally:
        for key, old_value in saved_env.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value

    from app.core.route_audit import scan_public_routes

    flagged = scan_public_routes(app)

    if flagged:
        listing = "\n".join(sorted(f"{item['method']} {item['path']}" for item in flagged))
        return CheckResult(
            name="route_audit_check",
            passed=False,
            summary=f"{len(flagged)} uncovered public route(s) mounted on the app.",
            details=(
                listing
                + "\n\nEach route above is public (matches storage_middleware "
                "PUBLIC_PATHS/PUBLIC_PREFIXES) and has no FunctionGroupContract "
                "coverage. Fix: declare it in the owning module's contract "
                "(allowed_routes/allowed_prefixes) or put it behind an auth "
                "gate. Runtime twin: app/core/route_audit.py "
                "(scan_public_routes)."
            ),
        )

    return CheckResult(
        name="route_audit_check",
        passed=True,
        summary="All actionable public routes have contract coverage.",
    )
