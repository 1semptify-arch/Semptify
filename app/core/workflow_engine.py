"""
Semptify 5.0 - Workflow Engine
Deterministic transition engine for Process A ▸ B1/B2/B4 routing.

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
    B3  — Filing & Packet Preparation
    B4  — Professional Review Workspace / Hearing Readiness
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

from app.core.navigation import navigation
from app.core.user_context import UserRole, get_role_definition

logger = logging.getLogger(__name__)


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
    B3 = "B3"    # Filing & Packet Preparation
    B4 = "B4"    # Professional Review Workspace


def _nav_path(stage_id: str, fallback: str) -> str:
    """Resolve a path from the SSOT navigation registry with a fallback."""
    stage = navigation.get_stage(stage_id)
    if stage:
        return stage.path
    item = next((n for n in navigation.MAIN_NAV if n.name.lower() == stage_id.lower()), None)
    return item.path if item else fallback


# Mapping of process codes to canonical SSOT paths.
# All paths resolved from navigation registry — never hardcoded here.
_home_item   = next((n for n in navigation.MAIN_NAV if n.name == "Home"),   None)
_office_item = next((n for n in navigation.MAIN_NAV if n.name == "Office"), None)

PROCESS_ROUTES: dict[ProcessCode, str] = {
    ProcessCode.A:  _home_item.path   if _home_item   else "/home",
    ProcessCode.B1: _office_item.path if _office_item else "/office",
    ProcessCode.B2: _office_item.path if _office_item else "/office",
    ProcessCode.B3: _office_item.path if _office_item else "/office",
    ProcessCode.B4: _office_item.path if _office_item else "/office",
}

# Role-specific portal routes — resolved from navigation registry.
# Each role lands on their /role/home rendered page after onboarding or reconnect.
ROLE_SPECIFIC_ROUTES: dict[UserRole, str] = {
    UserRole.LEGAL:    _nav_path("legal_home",    "/legal/home"),
    UserRole.ADMIN:    _nav_path("admin_home",    "/admin/home"),
    UserRole.MANAGER:  _nav_path("manager_home",  "/manager/home"),
    UserRole.ADVOCATE: _nav_path("advocate_home", "/advocate/home"),
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
    block_reason: str | None = None      # why the user is blocked (if applicable)
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
    """Routing logic for UserRole.TENANT and UserRole.USER (Tenant roles)."""
    warnings: list[str] = []

    if state.storage_state == StorageState.NEED_CONNECT:
        _providers_stage = navigation.get_stage("providers")
        _providers_path = _providers_stage.path if _providers_stage else "/storage/providers"
        return WorkflowDecision(
            next_process=ProcessCode.A,
            next_route=_providers_path,
            allowed_actions=["select_role", "connect_storage"],
            blocked_actions=["upload_document", "start_case", "view_vault"],
            deterministic_reason=(
                "Tenant has not connected a storage provider. "
                "Routing to storage provider selection to complete setup."
            ),
            block_reason="Storage provider not connected.",
        )

    if state.storage_state == StorageState.REVIEW_ONLY:
        warnings.append("Review-only mode: document uploads are disabled.")

    # All tenants land on their role home — upload CTA is built into the home page.
    # No separate "upload wizard" detour; home page handles first-document flow.
    _tenant_home_stage = navigation.get_stage("tenant_home")
    _tenant_home_path = _tenant_home_stage.path if _tenant_home_stage else "/tenant/home"

    if not state.documents_present and state.storage_state != StorageState.REVIEW_ONLY:
        return WorkflowDecision(
            next_process=ProcessCode.B1,
            next_route=_tenant_home_path,
            allowed_actions=["upload_document", "connect_storage"],
            blocked_actions=["start_case", "view_timeline", "get_ai_analysis"],
            deterministic_reason=(
                "Tenant has no documents in vault. "
                "Routing to tenant home — upload CTA is on the home page."
            ),
            warnings=warnings,
        )

    return WorkflowDecision(
        next_process=ProcessCode.B2,
        next_route=_tenant_home_path,
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
            role=UserRole.TENANT,
            storage_state=StorageState.ALREADY_CONNECTED,
            documents_present=True,
        )
        decision = evaluate(state)
        redirect_to(decision.next_route)
    """
    if state.role in (UserRole.TENANT, UserRole.USER):
        return _tenant_decision(state)
    return _professional_decision(state)


async def route_user(
    user_id: str | None,
    documents_present: bool | None = None,
    has_active_case: bool = False,
) -> str:
    """
    Single authoritative routing function for the entire application.

    Given a user_id (from cookie) returns the correct URL to send them to.
    Every redirect in the app should call this instead of hardcoding paths.

    If documents_present is not supplied, the vault index is queried directly
    so returning tenants with documents are not incorrectly sent to the upload wizard.

    Returns:
        URL string — always safe to redirect to.
    """
    from app.core.user_id import get_role_from_user_id, parse_user_id

    _preamble_stage = navigation.get_stage("preamble")
    _preamble_path = _preamble_stage.path if _preamble_stage else "/preamble"

    if not user_id:
        return _preamble_path

    # Validate format only — no HMAC check here because this function
    # is called server-side with a trusted raw user_id (not from cookie).
    provider, role, unique = parse_user_id(user_id)
    if not provider or not role or not unique:
        return _preamble_path

    role_str = get_role_from_user_id(user_id) or "user"

    # Strip HMAC signature for database operations (user_id may include HMAC from cookie)
    db_user_id = user_id.split('.')[0] if '.' in user_id else user_id

    if documents_present is None:
        try:
            from app.services.vault_upload_service import VaultUploadService
            vault_service = VaultUploadService()
            docs = await vault_service.get_user_documents(db_user_id)
            documents_present = len(docs) > 0
        except Exception as exc:
            logger.warning("route_user: vault query failed for user %s: %s — defaulting to False", db_user_id[:6] + "***", exc)
            documents_present = False

    try:
        decision = evaluate_from_params(
            role=role_str,
            storage_state=StorageState.ALREADY_CONNECTED.value,
            documents_present=documents_present,
            has_active_case=has_active_case,
        )
        return decision.next_route
    except ValueError:
        _preamble_stage = navigation.get_stage("preamble")
        return _preamble_stage.path if _preamble_stage else "/preamble"


def evaluate_from_params(
    role: str,
    storage_state: str,
    documents_present: bool = False,
    has_active_case: bool = False,
    permissions: frozenset[str] | None = None,
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
