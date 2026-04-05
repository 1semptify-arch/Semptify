"""
Semptify 5.0 - Workflow Engine
Deterministic transition engine for Process A → B1/B2/B4 routing.

Given a user's role, storage state, and current process state, the engine
returns a WorkflowDecision: allowed_actions, the next process, and a
plain-English reason for every decision.

Design principle: NO AI in routing decisions. The engine is fully deterministic
and reproducible. AI layers (Recommender, Auditor, Explainer) sit above this
and may influence what the user SEES, but they never override the engine's
routing logic or permission decisions.

Process codes:
  A   — Welcome & Role Selection
  B1  — Document Upload Wizard (storage required)
  B2  — Quick Case Triage (tenant/mobile path)
  B4  — Professional Review Workspace (advocate/manager/legal/admin)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from app.core.user_context import UserRole, get_role_definition


# =============================================================================
# State Enums & Constants
# =============================================================================

class StorageState(str, Enum):
    NEED_CONNECT = "need_connect"           # not authenticated yet
    ALREADY_CONNECTED = "already_connected" # OAuth token valid
    REVIEW_ONLY = "review_only"             # no storage, read-only mode


class ProcessState(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class ProcessCode(str, Enum):
    A = "A"      # Welcome
    B1 = "B1"    # Document Upload Wizard
    B2 = "B2"    # Quick Case Triage (Tenant path)
    B4 = "B4"    # Professional Review Workspace


# Mapping of process codes to route paths
PROCESS_ROUTES: dict[ProcessCode, str] = {
    ProcessCode.A: "/",
    ProcessCode.B1: "/onboard/upload",
    ProcessCode.B2: "/tenant",
    ProcessCode.B4: "/advocate",
}

# Legal role has a dedicated route at the B4 tier
ROLE_SPECIFIC_ROUTES: dict[UserRole, str] = {
    UserRole.LEGAL: "/legal",
    UserRole.ADMIN: "/admin",
    UserRole.MANAGER: "/admin",
}


# =============================================================================
# Workflow State — input to the engine
# =============================================================================

@dataclass
class WorkflowState:
    """
    Represents everything the engine needs to make a routing decision.
    Constructed from the active UserContext plus request parameters.
    """
    role: UserRole
    storage_state: StorageState
    process_state: ProcessState = ProcessState.NOT_STARTED
    permissions: frozenset[str] = field(default_factory=frozenset)
    jurisdiction_set: bool = False
    documents_present: bool = False
    has_active_case: bool = False


# =============================================================================
# Workflow Decision — output from the engine
# =============================================================================

@dataclass
class WorkflowDecision:
    """
    The engine's deterministic answer for a given WorkflowState.
    """
    next_process: ProcessCode               # where to send the user
    next_route: str                         # exact URL to redirect to
    allowed_actions: list[str]              # actions available from current state
    blocked_actions: list[str]              # actions present but locked
    deterministic_reason: str              # plain-English routing explanation
    block_reason: Optional[str] = None      # why the user is blocked (if applicable)
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# Core Routing Logic
# =============================================================================

def _resolve_route(process: ProcessCode, role: UserRole) -> str:
    """Return the most specific route for a role+process combination."""
    if process == ProcessCode.B4:
        return ROLE_SPECIFIC_ROUTES.get(role, PROCESS_ROUTES[ProcessCode.B4])
    return PROCESS_ROUTES[process]


def _tenant_decision(state: WorkflowState) -> WorkflowDecision:
    """Routing logic for UserRole.USER (Tenant)."""
    warnings: list[str] = []

    if state.storage_state == StorageState.NEED_CONNECT:
        return WorkflowDecision(
            next_process=ProcessCode.A,
            next_route=PROCESS_ROUTES[ProcessCode.A],
            allowed_actions=["select_role", "connect_storage"],
            blocked_actions=["upload_document", "start_case", "view_vault"],
            deterministic_reason=(
                "Tenant has not connected a storage provider. "
                "Routing back to Process A to complete storage setup."
            ),
            block_reason="Storage provider not connected.",
        )

    if state.storage_state == StorageState.REVIEW_ONLY:
        warnings.append("Review-only mode: document uploads are disabled.")

    if not state.documents_present and state.storage_state != StorageState.REVIEW_ONLY:
        return WorkflowDecision(
            next_process=ProcessCode.B1,
            next_route=PROCESS_ROUTES[ProcessCode.B1],
            allowed_actions=["upload_document", "connect_storage"],
            blocked_actions=["start_case", "view_timeline", "get_ai_analysis"],
            deterministic_reason=(
                "Tenant has no documents in vault. "
                "Routing to Process B1 (Document Upload Wizard) before triage."
            ),
            warnings=warnings,
        )

    return WorkflowDecision(
        next_process=ProcessCode.B2,
        next_route=PROCESS_ROUTES[ProcessCode.B2],
        allowed_actions=[
            "view_vault",
            "upload_document",
            "view_timeline",
            "use_letter_builder",
            "use_court_forms",
            "get_ai_analysis",
            "request_advocate",
        ],
        blocked_actions=[],
        deterministic_reason=(
            "Tenant has storage connected and documents present. "
            "Routing to Process B2 (Quick Case Triage)."
        ),
        warnings=warnings,
    )


def _professional_decision(state: WorkflowState) -> WorkflowDecision:
    """Routing logic for Advocate, Manager, Legal, Admin roles."""
    warnings: list[str] = []
    process = ProcessCode.B4
    route = _resolve_route(process, state.role)

    if state.storage_state == StorageState.NEED_CONNECT:
        warnings.append(
            "Storage provider not connected. "
            "Document operations will be unavailable until connection is made."
        )

    allowed_actions = [
        "view_case_list",
        "open_case",
        "view_documents",
        "run_research",
        "generate_actions",
        "export_case_packet",
    ]

    blocked_actions: list[str] = []

    if state.storage_state == StorageState.NEED_CONNECT:
        blocked_actions = ["upload_document", "sync_vault"]
        allowed_actions = [a for a in allowed_actions if a not in ("upload_document",)]

    if state.role == UserRole.LEGAL:
        allowed_actions.extend([
            "create_privileged_note",
            "generate_court_filing",
            "run_conflict_check",
        ])

    if state.role == UserRole.ADMIN:
        allowed_actions.extend([
            "view_system_dashboard",
            "manage_users",
            "inspect_contract_health",
        ])

    role_def = get_role_definition(state.role)
    reason = (
        f"{role_def['display_name']} session. "
        f"Routing to Process B4 ({route}). "
        f"Storage state: {state.storage_state.value}."
    )

    return WorkflowDecision(
        next_process=process,
        next_route=route,
        allowed_actions=allowed_actions,
        blocked_actions=blocked_actions,
        deterministic_reason=reason,
        warnings=warnings,
    )


# =============================================================================
# Public API
# =============================================================================

def evaluate(state: WorkflowState) -> WorkflowDecision:
    """
    Main engine entry point. Returns a deterministic WorkflowDecision.

    Example:
        state = WorkflowState(
            role=UserRole.USER,
            storage_state=StorageState.ALREADY_CONNECTED,
            documents_present=True,
        )
        decision = evaluate(state)
        redirect_to(decision.next_route)
    """
    if state.role == UserRole.USER:
        return _tenant_decision(state)
    return _professional_decision(state)


def evaluate_from_params(
    role: str,
    storage_state: str,
    documents_present: bool = False,
    has_active_case: bool = False,
    permissions: Optional[frozenset[str]] = None,
) -> WorkflowDecision:
    """
    Convenience wrapper that accepts raw string values (from query params / cookies).
    Raises ValueError for unknown role or storage_state strings.
    """
    try:
        role_enum = UserRole(role)
    except ValueError as exc:
        raise ValueError(f"Unknown role: '{role}'. Must be one of {[r.value for r in UserRole]}") from exc

    try:
        storage_enum = StorageState(storage_state)
    except ValueError as exc:
        raise ValueError(
            f"Unknown storage_state: '{storage_state}'. Must be one of {[s.value for s in StorageState]}"
        ) from exc

    state = WorkflowState(
        role=role_enum,
        storage_state=storage_enum,
        documents_present=documents_present,
        has_active_case=has_active_case,
        permissions=permissions or frozenset(),
    )
    return evaluate(state)
