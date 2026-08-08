"""
Advanced / Dev Tools Router
===========================

Admin-only module for the Advanced hub tile:
- Build Orchestrator status
- Guardrail, sync, and per-module verify triggers
- Cost-guard tools (starting with `detect_repeated_fees` as cost-guard only)

This module deliberately starts with non-cost-guard functions; the cost-guard
endpoint is at the end and is constrained to PII-free fee metadata.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import require_admin

router = APIRouter(
    prefix="/api/admin/advanced",
    tags=["Advanced / Dev Tools"],
    dependencies=[Depends(require_admin)],
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


@router.get("/health")
async def advanced_health() -> dict[str, Any]:
    """Admin health check for the Advanced / Dev Tools module."""
    return {
        "status": "ok",
        "service": "advanced",
        "cost_guard_mode": "fee-metadata only (no full audit)",
    }


@router.get("/tools")
async def list_tools() -> dict[str, Any]:
    """List the advanced/dev tools available in this module."""
    return {
        "tools": [
            {"id": "guardrail", "name": "Guardrail Engine", "method": "POST", "path": "/guardrail"},
            {"id": "sync_orchestrator", "name": "Sync Orchestrator", "method": "POST", "path": "/sync-orchestrator"},
            {"id": "verify", "name": "Verify Module", "method": "POST", "path": "/verify"},
            {"id": "build", "name": "Build Status", "method": "GET", "path": "/build"},
            {"id": "cost_guard", "name": "Cost Guard", "method": "POST", "path": "/cost-guard/detect-repeated-fees"},
        ],
    }


@router.get("/build")
async def build_status() -> dict[str, Any]:
    """Return a non-PII summary of the orchestrator task queue."""
    tasks_path = _repo_root() / "tools" / "agent_orchestrator_tasks.json"
    if not tasks_path.exists():
        return {"tasks": [], "counts": {}, "note": "orchestrator task file not found"}

    try:
        tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not read build tasks: {exc}") from exc

    counts: dict[str, int] = {}
    for t in tasks:
        status = t.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    return {
        "total": len(tasks),
        "counts": counts,
        "recent": [
            {"id": t.get("id"), "title": t.get("title"), "status": t.get("status")}
            for t in tasks[:10]
        ],
    }


def _run_script(script_name: str, extra_args: list[str]) -> subprocess.CompletedProcess:
    repo_root = _repo_root()
    script = repo_root / "tools" / script_name
    if not script.exists():
        raise HTTPException(status_code=500, detail=f"{script_name} not found")
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script), *extra_args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )


@router.post("/guardrail")
async def run_guardrail() -> dict[str, Any]:
    """Run the guardrail engine and return its output."""
    result = await asyncio.to_thread(_run_script, "guardrail_engine.py", [])
    output = (result.stdout or "") + (result.stderr or "")
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "output": output[-4000:] if len(output) > 4000 else output,
    }


@router.post("/sync-orchestrator")
async def run_sync_orchestrator() -> dict[str, Any]:
    """Run sync_orchestrator --write and return its output."""
    result = await asyncio.to_thread(_run_script, "sync_orchestrator.py", ["--write"])
    output = (result.stdout or "") + (result.stderr or "")
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "output": output[-4000:] if len(output) > 4000 else output,
    }


@router.post("/verify")
async def run_verify(module_id: str = "") -> dict[str, Any]:
    """Run verify_modules for a single module ID."""
    if not module_id:
        raise HTTPException(status_code=400, detail="module_id is required")
    result = await asyncio.to_thread(_run_script, "verify_modules.py", ["--id", module_id])
    output = (result.stdout or "") + (result.stderr or "")
    return {
        "module_id": module_id,
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "output": output[-4000:] if len(output) > 4000 else output,
    }


# =============================================================================
# Cost-guard tools (PII-free fee metadata only)
# =============================================================================


class FeeItem(BaseModel):
    """A single fee entry for repeated-fee detection."""

    fee_type: str = Field(..., description="Fee type or description")
    amount: float = Field(..., description="Fee amount in dollars")
    date: str = Field(..., description="Fee date as ISO string (YYYY-MM-DD)")


class DetectRequest(BaseModel):
    """Request to detect repeated fees from fee metadata."""

    fee_history: list[FeeItem] = Field(..., min_length=2)
    jurisdiction: str = Field("MN", description="US state jurisdiction code")


@router.post("/cost-guard/detect-repeated-fees")
async def detect_repeated_fees_cost_guard(request: DetectRequest) -> dict[str, Any]:
    """Cost-guard only: detect repeated fees from fee metadata (no PII).

    This endpoint accepts only fee type, amount, and date. It does NOT accept
    tenant names, addresses, or case identifiers. The underlying pattern engine
    is the same as `housing_accountability`, but this wrapper is constrained to
    cost-guard use (no full fee audit).
    """
    try:
        from app.modules.housing_accountability.router import PatternDetectionService
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Pattern detection service unavailable: {exc}") from exc

    fee_history = [
        {"fee_type": f.fee_type, "amount": f.amount, "date": str(f.date)}
        for f in request.fee_history
    ]
    data = {
        "fee_history": fee_history,
        "jurisdiction": request.jurisdiction,
    }

    result = await asyncio.to_thread(PatternDetectionService().detect_repeated_fees, data)
    return {
        "jurisdiction": request.jurisdiction,
        "cost_guard": True,
        "result": result,
    }
