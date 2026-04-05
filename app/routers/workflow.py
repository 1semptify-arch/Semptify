"""
Semptify 5.0 - Workflow & Contract API Router
Exposes the workflow engine and page contract registry as API endpoints.

Endpoints:
  POST /api/workflow/route       — deterministic routing decision
  GET  /api/workflow/groups      — all 8 process groups
  GET  /api/workflow/contracts   — all page contracts
  GET  /api/workflow/contracts/{page_id} — single contract
  GET  /api/workflow/health      — contract + registry validation report
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from collections import Counter
from datetime import datetime

from app.core.workflow_engine import evaluate_from_params
from app.core.process_registry import PROCESS_GROUPS, get_groups_for_role
from app.core.page_contracts import PAGE_CONTRACTS, get_contract, validate_all_contracts
from app.core.user_context import UserRole
from app.services.positronic_brain import get_brain

router = APIRouter(prefix="/api/workflow", tags=["Workflow Engine"])


# =============================================================================
# Request / Response Models
# =============================================================================

class RouteRequest(BaseModel):
    role: str
    storage_state: str
    documents_present: bool = False
    has_active_case: bool = False


class RouteResponse(BaseModel):
    next_process: str
    next_route: str
    allowed_actions: list[str]
    blocked_actions: list[str]
    deterministic_reason: str
    block_reason: Optional[str] = None
    warnings: list[str]


class AdvanceRequest(BaseModel):
    current_page: str = "welcome"
    role: str
    storage_state: str
    completed_actions: list[str] = []
    documents_present: bool = False
    has_active_case: bool = False


class AdvanceResponse(BaseModel):
    status: str
    current_page: str
    missing_requirements: list[str]
    next_process: Optional[str] = None
    next_route: Optional[str] = None
    allowed_actions: list[str] = []
    blocked_actions: list[str] = []
    deterministic_reason: Optional[str] = None
    warnings: list[str] = []


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/route", response_model=RouteResponse)
async def get_route_decision(body: RouteRequest) -> RouteResponse:
    """
    Return a deterministic routing decision for the given role + storage state.
    This is the core workflow engine — no AI, fully predictable.
    """
    try:
        decision = evaluate_from_params(
            role=body.role,
            storage_state=body.storage_state,
            documents_present=body.documents_present,
            has_active_case=body.has_active_case,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return RouteResponse(
        next_process=decision.next_process.value,
        next_route=decision.next_route,
        allowed_actions=decision.allowed_actions,
        blocked_actions=decision.blocked_actions,
        deterministic_reason=decision.deterministic_reason,
        block_reason=decision.block_reason,
        warnings=decision.warnings,
    )


@router.post("/advance", response_model=AdvanceResponse)
async def advance_workflow(body: AdvanceRequest) -> AdvanceResponse:
    """
    Gate-based transition endpoint.
    For now, enforces full welcome requirements before allowing Process A -> Process B routing.
    """
    page = body.current_page.strip().lower()
    completed = {action.strip() for action in body.completed_actions if action and action.strip()}

    if page != "welcome":
        raise HTTPException(status_code=422, detail="Only current_page='welcome' is supported at this time")

    missing_requirements: list[str] = []

    if not body.role.strip():
        missing_requirements.append("role_selected")
    else:
        if "role_selected" not in completed:
            missing_requirements.append("role_selected")

    if not body.storage_state.strip():
        missing_requirements.append("storage_status_set")
    else:
        if "storage_status_set" not in completed:
            missing_requirements.append("storage_status_set")

    if "process_start_clicked" not in completed:
        missing_requirements.append("process_start_clicked")

    if missing_requirements:
        return AdvanceResponse(
            status="blocked",
            current_page=page,
            missing_requirements=missing_requirements,
            warnings=[
                "Complete required welcome actions before advancing.",
            ],
        )

    try:
        decision = evaluate_from_params(
            role=body.role,
            storage_state=body.storage_state,
            documents_present=body.documents_present,
            has_active_case=body.has_active_case,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AdvanceResponse(
        status="advance",
        current_page=page,
        missing_requirements=[],
        next_process=decision.next_process.value,
        next_route=decision.next_route,
        allowed_actions=decision.allowed_actions,
        blocked_actions=decision.blocked_actions,
        deterministic_reason=decision.deterministic_reason,
        warnings=decision.warnings,
    )


@router.get("/groups")
async def list_process_groups(role: Optional[str] = None) -> dict:
    """
    Return all 8 process groups, optionally filtered by role.
    """
    if role:
        try:
            role_enum = UserRole(role)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Unknown role: '{role}'") from exc
        groups = get_groups_for_role(role_enum)
    else:
        groups = list(PROCESS_GROUPS)

    return {
        "groups": [
            {
                "group_id": g.group_id,
                "name": g.name,
                "title": g.title,
                "purpose": g.purpose,
                "scope_includes": list(g.scope_includes),
                "scope_excludes": list(g.scope_excludes),
                "entry_criteria": list(g.entry_criteria),
                "exit_criteria": list(g.exit_criteria),
                "success_metrics": list(g.success_metrics),
                "roles_with_access": [r.value for r in g.roles_with_access],
            }
            for g in groups
        ],
        "total": len(groups),
    }


@router.get("/contracts")
async def list_contracts() -> dict:
    """Return all registered page contracts (summary view)."""
    return {
        "contracts": [
            {
                "page_id": c.page_id,
                "title": c.title,
                "route": c.route,
                "roles_supported": [r.value for r in c.roles_supported],
                "primary_groups": c.primary_groups,
                "secondary_groups": c.secondary_groups,
                "group_coverage": c.group_coverage,
            }
            for c in PAGE_CONTRACTS.values()
        ],
        "total": len(PAGE_CONTRACTS),
    }


@router.get("/contracts/{page_id}")
async def get_page_contract(page_id: str) -> dict:
    """Return the full page contract for a specific page."""
    try:
        contract = get_contract(page_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=(
            f"No contract registered for page_id='{page_id}'. Available: {sorted(PAGE_CONTRACTS.keys())}"
        )) from exc
    return {
        "page_id": contract.page_id,
        "title": contract.title,
        "route": contract.route,
        "roles_supported": [r.value for r in contract.roles_supported],
        "primary_groups": contract.primary_groups,
        "secondary_groups": contract.secondary_groups,
        "group_coverage": contract.group_coverage,
        "qualification": contract.qualification,
        "expectations": contract.expectations,
        "scope_of_use": contract.scope_of_use,
        "entry_criteria": contract.entry_criteria,
        "exit_criteria": contract.exit_criteria,
        "telemetry_events": contract.telemetry_events,
    }


@router.get("/health")
async def contract_health() -> dict:
    """
    Run the contract validation suite and return a health report.
    Useful for admin dashboards and CI status checks.
    """
    violations = validate_all_contracts()
    total_contracts = len(PAGE_CONTRACTS)
    total_groups = len(PROCESS_GROUPS)
    failed_contracts = len(violations)
    passed_contracts = total_contracts - failed_contracts

    return {
        "status": "pass" if failed_contracts == 0 else "fail",
        "summary": {
            "total_contracts": total_contracts,
            "passed": passed_contracts,
            "failed": failed_contracts,
            "total_groups": total_groups,
        },
        "violations": violations,
    }


def _is_help_action(page: str, action: str) -> bool:
    page_value = page.lower()
    action_value = action.lower()

    if page_value in {"tenant_help", "public_help", "welcome"}:
        return True

    help_markers = (
        "help",
        "hotline",
        "county_",
        "rent_help",
        "welcome_call_",
        "welcome_open_",
        "semptify_",
        "open_external_help_link",
        "open_internal_help_link",
    )
    return any(marker in action_value for marker in help_markers)


def _event_day(timestamp: str) -> str:
    normalized = timestamp.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return "unknown"
    return dt.date().isoformat()


@router.get("/help-telemetry-summary")
async def help_telemetry_summary(limit: int = 1000, page: Optional[str] = None) -> dict:
    """
    Aggregate help-related click telemetry from the positronic brain event history.
    Useful for admin dashboards that need day-by-day and resource-level usage trends.
    """
    if limit < 1 or limit > 5000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 5000")

    page_filter = page.lower() if page else None
    events = get_brain().get_recent_events(limit=limit)

    total_user_actions = 0
    help_events = 0
    by_day: Counter[str] = Counter()
    by_action: Counter[str] = Counter()
    by_page: Counter[str] = Counter()
    by_href: Counter[str] = Counter()

    for event in events:
        if event.get("event_type") != "user.action":
            continue

        total_user_actions += 1
        data = event.get("data") or {}
        action = str(data.get("action") or "unknown")
        page_name = str(data.get("page") or "unknown")
        href = str(data.get("href") or "")

        if page_filter and page_name.lower() != page_filter:
            continue

        if not _is_help_action(page_name, action):
            continue

        help_events += 1
        by_day[_event_day(str(event.get("timestamp") or ""))] += 1
        by_action[action] += 1
        by_page[page_name] += 1
        if href:
            by_href[href] += 1

    return {
        "status": "ok",
        "window": {
            "requested_limit": limit,
            "page_filter": page,
            "events_scanned": len(events),
            "user_actions_scanned": total_user_actions,
        },
        "summary": {
            "help_events_total": help_events,
            "active_days": len(by_day),
            "unique_actions": len(by_action),
            "unique_pages": len(by_page),
            "unique_links": len(by_href),
        },
        "by_day": [
            {"day": day, "count": count}
            for day, count in sorted(by_day.items())
        ],
        "top_actions": [
            {"action": action_name, "count": count}
            for action_name, count in by_action.most_common(25)
        ],
        "top_pages": [
            {"page": page_name, "count": count}
            for page_name, count in by_page.most_common(10)
        ],
        "top_links": [
            {"href": href_value, "count": count}
            for href_value, count in by_href.most_common(25)
        ],
    }
