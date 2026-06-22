"""
Dev Lab Router — Phase 3.1a

Endpoints:
  GET  /dev/lab                    — List all dev_only modules (internal + external)
  GET  /dev/lab/{module_path}      — Sandbox page for a specific dev module
  GET  /dev/lab/{module_path}/status    — Show module's maturity checklist
  POST /dev/lab/{module_path}/promote   — Request promotion to next lifecycle stage
  POST /dev/lab/{module_path}/test      — Run module's test suite
  GET  /dev/lab/ideas              — List submitted ideas
  POST /dev/lab/ideas              — Submit a new idea
  POST /dev/lab/ideas/{idea_id}/promote — Promote idea to dev module

All endpoints require admin auth (dev_lab is admin-only by design).
"""
import importlib
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.product_manifest import MANIFEST, ModuleEntry
from app.core.module_overrides import set_override
from app.core.module_resolver import invalidate_all_caches
from app.core.utc import utc_now
from app.modules.dev_lab.maturity import (
    MATURITY_CHECKLIST,
    LIFECYCLE_ORDER,
    get_checklist,
    get_next_lifecycle,
    can_promote,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dev Lab"])


# =============================================================================
# Auth — reuse stealth admin from admin_console
# =============================================================================

async def _stealth_admin(request: Request):
    """Stealth admin guard — returns 404 to non-admins."""
    from app.modules.admin_console.router import _stealth_admin as _admin
    return await _admin(request)


# =============================================================================
# Request models
# =============================================================================

class PromoteRequest(BaseModel):
    """Request to promote a module to the next lifecycle stage."""
    target_lifecycle: str = Field(..., description="Target lifecycle: experimental|beta|stable")
    notes: str = Field(default="", description="Admin notes about this promotion")


class RunTestsRequest(BaseModel):
    """Request to run a module's test suite."""
    test_path: Optional[str] = Field(
        default=None,
        description="Specific test path (defaults to module's tests/ directory)",
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("")
async def list_dev_modules(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """List all dev_only and preview modules (the incubator).

    Returns modules grouped by origin (internal/external) with their
    lifecycle, tier, dev_notes, and maturity checklist progress.
    """
    dev_modules = []
    for entry in MANIFEST.all():
        if entry.lifecycle not in ("dev_only", "preview", "experimental"):
            continue
        dev_modules.append({
            "module_path": entry.module_path,
            "tier": entry.tier.value,
            "lifecycle": entry.lifecycle,
            "origin": entry.origin,
            "prefix": entry.prefix,
            "tags": list(entry.tags),
            "requires_role": list(entry.requires_role),
            "requires_gate": entry.requires_gate,
            "feature_flag": entry.feature_flag,
            "dev_notes": entry.dev_notes,
            "visibility_label": entry.visibility_label,
            "next_lifecycle": get_next_lifecycle(entry.lifecycle),
            "checklist": get_checklist(entry.lifecycle),
        })

    # Sort by lifecycle (dev_only first), then module_path
    lc_order = {"dev_only": 0, "preview": 1, "experimental": 2}
    dev_modules.sort(key=lambda m: (lc_order.get(m["lifecycle"], 99), m["module_path"]))

    return {
        "modules": dev_modules,
        "total": len(dev_modules),
        "lifecycle_order": LIFECYCLE_ORDER,
        "maturity_checklist": MATURITY_CHECKLIST,
        "generated_at": utc_now().isoformat(),
    }


@router.get("/{module_path:path}")
async def get_dev_module(
    module_path: str,
    request: Request,
    _admin=Depends(_stealth_admin),
) -> dict:
    """Get detailed info about a specific dev module."""
    entry = MANIFEST.find(module_path)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_path}' not found in manifest",
        )

    # Check if module has tests directory
    module_file = entry.module_path.replace(".", "/")
    # Try to find the module's directory
    tests_dir = None
    try:
        mod = importlib.import_module(entry.module_path)
        if hasattr(mod, "__file__") and mod.__file__:
            module_dir = Path(mod.__file__).parent
            tests_dir = str(module_dir / "tests") if (module_dir / "tests").exists() else None
    except Exception as e:
        logger.warning("DevLab: could not import %s: %s", module_path, e)

    return {
        "module_path": entry.module_path,
        "tier": entry.tier.value,
        "lifecycle": entry.lifecycle,
        "origin": entry.origin,
        "prefix": entry.prefix,
        "tags": list(entry.tags),
        "requires_role": list(entry.requires_role),
        "requires_jurisdiction": list(entry.requires_jurisdiction),
        "requires_gate": entry.requires_gate,
        "feature_flag": entry.feature_flag,
        "dev_notes": entry.dev_notes,
        "visibility_label": entry.visibility_label,
        "is_external": entry.is_external,
        "next_lifecycle": get_next_lifecycle(entry.lifecycle),
        "current_checklist": get_checklist(entry.lifecycle),
        "next_checklist": get_checklist(get_next_lifecycle(entry.lifecycle)) if get_next_lifecycle(entry.lifecycle) else [],
        "has_tests": tests_dir is not None,
        "tests_dir": tests_dir,
    }


@router.get("/{module_path:path}/status")
async def get_module_status(
    module_path: str,
    request: Request,
    _admin=Depends(_stealth_admin),
) -> dict:
    """Show module's maturity checklist with progress indicators."""
    entry = MANIFEST.find(module_path)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_path}' not found in manifest",
        )

    current_lifecycle = entry.lifecycle
    next_lifecycle = get_next_lifecycle(current_lifecycle)

    # Build checklist status for current and all future stages
    stages = {}
    for stage in LIFECYCLE_ORDER:
        stages[stage] = {
            "requirements": get_checklist(stage),
            "is_current": stage == current_lifecycle,
            "is_next": stage == next_lifecycle,
            "is_passed": LIFECYCLE_ORDER.index(stage) < LIFECYCLE_ORDER.index(current_lifecycle)
                if stage in LIFECYCLE_ORDER and current_lifecycle in LIFECYCLE_ORDER
                else False,
        }

    return {
        "module_path": entry.module_path,
        "current_lifecycle": current_lifecycle,
        "next_lifecycle": next_lifecycle,
        "can_promote": next_lifecycle != "",
        "stages": stages,
        "generated_at": utc_now().isoformat(),
    }


@router.post("/{module_path:path}/promote")
async def promote_module(
    module_path: str,
    body: PromoteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """Promote a module to the next lifecycle stage.

    Sets a runtime override on the module's lifecycle. The override
    persists in the module_overrides table and takes effect immediately
    (resolver cache invalidated).
    """
    entry = MANIFEST.find(module_path)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_path}' not found in manifest",
        )

    if not can_promote(entry.lifecycle, body.target_lifecycle):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot promote from '{entry.lifecycle}' to '{body.target_lifecycle}'. "
                f"Must be adjacent in lifecycle order: {LIFECYCLE_ORDER}"
            ),
        )

    # Set the override
    try:
        from app.core.module_overrides import set_override as _set_override
        override = await _set_override(
            db=db,
            module_path=module_path,
            lifecycle=body.target_lifecycle,
            notes=body.notes or f"Promoted from {entry.lifecycle} to {body.target_lifecycle}",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    await invalidate_all_caches()

    logger.info(
        "DevLab: module %s promoted from %s to %s by admin",
        module_path, entry.lifecycle, body.target_lifecycle,
    )

    return {
        "status": "ok",
        "module_path": module_path,
        "previous_lifecycle": entry.lifecycle,
        "new_lifecycle": body.target_lifecycle,
        "override": override,
        "promoted_at": utc_now().isoformat(),
    }


@router.post("/{module_path:path}/test")
async def run_module_tests(
    module_path: str,
    body: RunTestsRequest,
    request: Request,
    _admin=Depends(_stealth_admin),
) -> dict:
    """Run a module's test suite.

    Uses pytest to run the module's tests/ directory. Returns the test
    results summary (passed, failed, errors, skipped).
    """
    entry = MANIFEST.find(module_path)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_path}' not found in manifest",
        )

    # Determine test path
    test_path = body.test_path
    if not test_path:
        try:
            mod = importlib.import_module(entry.module_path)
            if hasattr(mod, "__file__") and mod.__file__:
                module_dir = Path(mod.__file__).parent
                candidate = module_dir / "tests"
                if candidate.exists():
                    test_path = str(candidate)
        except Exception as e:
            logger.warning("DevLab: could not locate tests for %s: %s", module_path, e)

    if not test_path or not Path(test_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tests directory found for module '{module_path}'. "
                   f"Expected tests/ directory or specify test_path.",
        )

    # Run pytest in subprocess
    import subprocess
    import sys

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--json-report"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(Path(__file__).parent.parent.parent.parent),
        )

        # Try to parse JSON report
        import json
        report_path = Path(".report.json")
        test_report = {}
        if report_path.exists():
            try:
                test_report = json.loads(report_path.read_text())
                report_path.unlink(missing_ok=True)
            except json.JSONDecodeError:
                pass

        return {
            "status": "ok",
            "module_path": module_path,
            "test_path": test_path,
            "exit_code": result.returncode,
            "passed": test_report.get("summary", {}).get("passed", 0),
            "failed": test_report.get("summary", {}).get("failed", 0),
            "errors": test_report.get("summary", {}).get("errors", 0),
            "skipped": test_report.get("summary", {}).get("skipped", 0),
            "total": test_report.get("summary", {}).get("total", 0),
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "ran_at": utc_now().isoformat(),
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Test suite timed out after 120 seconds",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test execution failed: {e}",
        )


# =============================================================================
# Module Contracts — SSOT signatures
# =============================================================================

try:
    from app.core.module_contracts import FunctionGroupContract, register_function_group

    register_function_group(FunctionGroupContract(
        module="dev_lab",
        group_name="dev_modules_list",
        title="Dev Modules List (SSOT)",
        description=(
            "CANONICAL list of all dev_only/preview/experimental modules. "
            "GET /dev/lab. Stealth admin guard enforced."
        ),
        inputs=("admin_user_id",),
        outputs=("modules", "total", "lifecycle_order", "maturity_checklist"),
        dependencies=("app.modules.dev_lab.router", "app.core.product_manifest.MANIFEST"),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="dev_lab",
        group_name="dev_module_status",
        title="Dev Module Maturity Status (SSOT)",
        description=(
            "CANONICAL maturity checklist status for a module. "
            "GET /dev/lab/{module_path}/status. "
            "Returns checklist requirements for each lifecycle stage."
        ),
        inputs=("module_path", "admin_user_id"),
        outputs=("module_path", "current_lifecycle", "next_lifecycle", "stages"),
        dependencies=("app.modules.dev_lab.router", "app.modules.dev_lab.maturity"),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="dev_lab",
        group_name="dev_module_promote",
        title="Dev Module Promote (SSOT)",
        description=(
            "CANONICAL promote a module to the next lifecycle stage. "
            "POST /dev/lab/{module_path}/promote. "
            "Sets runtime override and invalidates resolver caches."
        ),
        inputs=("module_path", "target_lifecycle", "notes", "admin_user_id"),
        outputs=("status", "module_path", "previous_lifecycle", "new_lifecycle"),
        dependencies=("app.modules.dev_lab.router", "app.core.module_overrides"),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="dev_lab",
        group_name="dev_module_test",
        title="Dev Module Test Runner (SSOT)",
        description=(
            "CANONICAL run a module's test suite via pytest. "
            "POST /dev/lab/{module_path}/test. "
            "Returns pass/fail/error counts and stdout/stderr."
        ),
        inputs=("module_path", "test_path", "admin_user_id"),
        outputs=("status", "exit_code", "passed", "failed", "errors", "skipped"),
        dependencies=("app.modules.dev_lab.router",),
        deterministic=False,
    ))

except Exception:
    pass
