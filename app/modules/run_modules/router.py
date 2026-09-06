"""
Run Modules Router
==================

Admin-only execution surface for operational module health checks.

Routes:
- GET /api/admin/run/modules                — list runnable modules
- POST /api/admin/run/modules/{module_id}   — run health check for a module

This module deliberately does NOT expose PII. The only execution it performs is
calling the trusted `tools/verify_modules.py` script for a specific module ID.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.module_registry_loader import load_registry
from app.core.security import require_admin

router = APIRouter(
    tags=["Run Modules"],
    dependencies=[Depends(require_admin)],
)


def _registry_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    return repo_root / "tools" / "verify_modules.py"


@router.get("/modules")
async def list_runnable_modules() -> dict[str, Any]:
    """List registry modules that have a real module_path and can be run."""
    entries = await asyncio.to_thread(load_registry)
    runnable = [
        {
            "id": e["id"],
            "display_name": e.get("display_name"),
            "module_path": e.get("module_path"),
            "status": e.get("status"),
        }
        for e in entries
        if e.get("module_path")
    ]
    return {"modules": runnable, "count": len(runnable)}


@router.post("/modules/{module_id}")
async def run_module(module_id: str) -> dict[str, Any]:
    """Run the trusted health-check verifier for a single module.

    Only module IDs present in the registry with a real module_path are accepted.
    This is an execution surface, but it is constrained to a single audited subprocess.
    """
    entries = await asyncio.to_thread(load_registry)
    entry = next((e for e in entries if e.get("id") == module_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
    if not entry.get("module_path"):
        raise HTTPException(status_code=400, detail=f"Module {module_id} has no module_path")

    verify_script = _registry_path()
    if not verify_script.exists():
        raise HTTPException(status_code=500, detail="verify_modules script not found")

    def _run() -> subprocess.CompletedProcess:
        return subprocess.run(  # noqa: S603
            [sys.executable, str(verify_script), "--id", module_id],
            cwd=verify_script.parent.parent,
            capture_output=True,
            text=True,
            timeout=120,
        )

    try:
        result = await asyncio.to_thread(_run)
    except subprocess.TimeoutExpired as exc:
        return {
            "module_id": module_id,
            "status": "timeout",
            "timeout_seconds": 120,
            "detail": exc.stdout[-2000:] if exc.stdout else "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "module_id": module_id,
            "status": "error",
            "returncode": -1,
            "detail": str(exc),
        }

    output = (result.stdout or "") + (result.stderr or "")
    return {
        "module_id": module_id,
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "output": output[-4000:] if len(output) > 4000 else output,
    }
