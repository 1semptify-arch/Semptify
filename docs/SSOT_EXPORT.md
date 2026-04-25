# Semptify 5.0 — Single Source of Truth (SSOT) Architecture Export

**Generated:** April 20, 2026  
**Purpose:** Consolidated reference for all canonical sources of truth in the system

---

## 1. Vault Paths (Cloud Storage Canonical Paths)

**File:** `app/core/vault_paths.py`

```python
"""Canonical cloud vault paths (single source of truth)."""

SEMPTIFY_ROOT = "Semptify5.0"
VAULT_ROOT = f"{SEMPTIFY_ROOT}/Vault"

VAULT_DOCUMENTS = f"{VAULT_ROOT}/documents"
VAULT_CERTIFICATES = f"{VAULT_ROOT}/certificates"

VAULT_OVERLAY = f"{VAULT_ROOT}/.overlay"
VAULT_OVERLAY_REGISTRY = f"{VAULT_OVERLAY}/registry.json"

VAULT_TIMELINE = f"{VAULT_ROOT}/timeline"
VAULT_TIMELINE_EVENTS_FILENAME = "events.json"
VAULT_TIMELINE_EVENTS_FILE = f"{VAULT_TIMELINE}/{VAULT_TIMELINE_EVENTS_FILENAME}"
```

### Path Usage Summary

| Constant | Path | Purpose |
|----------|------|---------|
| `VAULT_DOCUMENTS` | `Semptify5.0/Vault/documents` | User document storage |
| `VAULT_CERTIFICATES` | `Semptify5.0/Vault/certificates` | Security certificates |
| `VAULT_OVERLAY` | `Semptify5.0/Vault/.overlay` | Document overlay metadata |
| `VAULT_OVERLAY_REGISTRY` | `Semptify5.0/Vault/.overlay/registry.json` | Overlay registry index |
| `VAULT_TIMELINE` | `Semptify5.0/Vault/timeline` | Timeline event storage |
| `VAULT_TIMELINE_EVENTS_FILE` | `Semptify5.0/Vault/timeline/events.json` | Canonical timeline events |

### Consumers
- `vault_upload_service.py` - Document uploads
- `document_overlay.py` - Overlay management
- `timeline_extraction.py` - Timeline event persistence
- `routers/vault.py` - Vault API endpoints

---

## 2. Role Mapping (Frontend ↔ Backend)

**File:** `static/onboarding/storage-select.html`

### Canonical Role Names

| Backend (API) | Frontend (UI) | Description |
|---------------|---------------|-------------|
| `tenant` | `user` | Tenant/end-user role (human-friendly label) |
| `manager` | `manager` | Property manager role |
| `advocate` | `advocate` | Tenant advocate role |
| `legal` | `legal` | Legal professional role |
| `judge` | `judge` | Judicial role |
| `admin` | `admin` | System administrator |

### Mapping Implementation

```javascript
// static/onboarding/storage-select.html
const FRONTEND_TO_BACKEND_ROLES = {
    'user': 'tenant',      // Frontend says "user", backend API expects "tenant"
    'manager': 'manager',   // Pass-through
    'advocate': 'advocate', // Pass-through
    'legal': 'legal',       // Pass-through
    'judge': 'judge',       // Pass-through
    'admin': 'admin'        // Pass-through
};

function mapFrontendRoleToBackend(frontendRole) {
    return FRONTEND_TO_BACKEND_ROLES[frontendRole] || frontendRole;
}
```

### Design Principle
- Frontend uses human-friendly terms ("I am a user/tenant")
- Backend uses canonical identifiers (`ALLOWED_ROLES = {"tenant", "manager", ...}`)
- Mapping happens at the API boundary, not in storage
- `localStorage` keeps the frontend role value; transformation occurs on outbound API calls

---

## 3. Security Configuration (Cookie Settings)

**Files:** `app/routers/security.py`, `app/routers/storage.py`

### Problem
Browsers reject `Secure` cookies over HTTP (localhost development). This causes:
- Malformed cookie dates (Friday/Saturday same day bug)
- Immediate cookie expiration
- Session loss on every request

### Solution
Environment-based conditional security flag:

```python
# Set secure cookie - secure=False for localhost HTTP, True for HTTPS production
import os
is_localhost = os.environ.get("ENVIRONMENT", "development") == "development"
response.set_cookie(
    key="semptify_session",
    value=session_data["session_id"],
    max_age=86400,  # 24 hours
    httponly=True,
    secure=False if is_localhost else True,
    samesite="lax"
)
```

### Configuration
Set in `.env` or environment:
```bash
# Development (HTTP localhost)
ENVIRONMENT=development

# Production (HTTPS)
ENVIRONMENT=production
```

### Design Principle
- Local development: `secure=False` allows HTTP cookies
- Production: `secure=True` enforces HTTPS-only cookies
- SameSite=Lax provides CSRF protection without breaking OAuth flows
- HttpOnly prevents JavaScript access to session cookie

---

## 4. Module Contracts (Function-Group Registry)

**File:** `app/core/module_contracts.py`

```python
"""
Standardized module and function-group contracts.

Purpose:
- Define one plug-and-play contract shape for module capabilities.
- Provide centralized registration + validation for deterministic integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FunctionGroupContract:
    """Standard contract for a function-group within a module."""

    module: str
    group_name: str
    title: str
    description: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    dependencies: tuple[str, ...]
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "group_name": self.group_name,
            "title": self.title,
            "description": self.description,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "dependencies": list(self.dependencies),
            "deterministic": self.deterministic,
        }


class ModuleContractRegistry:
    """In-memory registry for function-group contracts."""

    def __init__(self) -> None:
        self._contracts: dict[str, FunctionGroupContract] = {}

    @staticmethod
    def _make_key(module: str, group_name: str) -> str:
        return f"{module.strip().lower()}::{group_name.strip().lower()}"

    def register(self, contract: FunctionGroupContract) -> FunctionGroupContract:
        key = self._make_key(contract.module, contract.group_name)
        self._contracts[key] = contract
        return contract

    def list_contracts(self) -> list[FunctionGroupContract]:
        return list(self._contracts.values())

    def get(self, module: str, group_name: str) -> FunctionGroupContract | None:
        return self._contracts.get(self._make_key(module, group_name))

    def validate(self) -> dict[str, Any]:
        violations: list[dict[str, str]] = []

        for contract in self._contracts.values():
            if not contract.module.strip():
                violations.append(
                    {
                        "contract": f"{contract.module}::{contract.group_name}",
                        "reason": "module must be non-empty",
                    }
                )
            if not contract.group_name.strip():
                violations.append(
                    {
                        "contract": f"{contract.module}::{contract.group_name}",
                        "reason": "group_name must be non-empty",
                    }
                )
            if len(contract.outputs) == 0:
                violations.append(
                    {
                        "contract": f"{contract.module}::{contract.group_name}",
                        "reason": "outputs must define at least one key",
                    }
                )

        return {
            "status": "pass" if not violations else "fail",
            "summary": {
                "total_contracts": len(self._contracts),
                "violations": len(violations),
            },
            "violations": violations,
        }


contract_registry = ModuleContractRegistry()


def register_function_group(contract: FunctionGroupContract) -> FunctionGroupContract:
    return contract_registry.register(contract)
```

### Contract Key Format
- Pattern: `{module}::{group_name}` (lowercase, stripped)
- Example: `timeline::chronology`, `vault::upload`

### Validation Rules
1. Module name must be non-empty
2. Group name must be non-empty
3. Outputs must define at least one key

---

## 3. Workflow Engine (Routing Single Source of Truth)

**File:** `app/core/workflow_engine.py`

### Design Principle
> **NO AI in routing decisions.** The engine is fully deterministic and reproducible. AI layers (Recommender, Auditor, Explainer) sit above this and may influence what the user SEES, but they never override the engine's routing logic or permission decisions.

### State Enums

```python
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
```

### Route Mappings

```python
PROCESS_ROUTES: dict[ProcessCode, str] = {
    ProcessCode.A: "/",
    ProcessCode.B1: "/tenant/documents",
    ProcessCode.B2: "/tenant",
    ProcessCode.B3: "/static/eviction_answer.html",
    ProcessCode.B4: "/advocate",
}

ROLE_SPECIFIC_ROUTES: dict[UserRole, str] = {
    UserRole.LEGAL: "/legal",
    UserRole.ADMIN: "/admin",
    UserRole.MANAGER: "/admin",
}
```

### Workflow State (Input)

```python
@dataclass
class WorkflowState:
    """Represents everything the engine needs to make a routing decision."""
    role: UserRole
    storage_state: StorageState
    process_state: ProcessState = ProcessState.NOT_STARTED
    permissions: frozenset[str] = field(default_factory=frozenset)
    jurisdiction_set: bool = False
    documents_present: bool = False
    has_active_case: bool = False
```

### Workflow Decision (Output)

```python
@dataclass
class WorkflowDecision:
    """The engine's deterministic answer for a given WorkflowState."""
    next_process: ProcessCode
    next_route: str
    allowed_actions: list[str]
    blocked_actions: list[str]
    deterministic_reason: str
    block_reason: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
```

### Single Source of Truth: route_user()

```python
def route_user(
    user_id: Optional[str],
    documents_present: bool = False,
    has_active_case: bool = False,
) -> str:
    """
    Single authoritative routing function for the entire application.

    Given a user_id (from cookie) returns the correct URL to send them to.
    Every redirect in the app should call this instead of hardcoding paths.

    Returns:
        URL string — always safe to redirect to.
    """
    from app.core.storage_middleware import is_valid_storage_user
    from app.core.user_id import get_role_from_user_id

    if not user_id or not is_valid_storage_user(user_id):
        return "/storage/providers"

    role_str = get_role_from_user_id(user_id) or "user"

    try:
        decision = evaluate_from_params(
            role=role_str,
            storage_state=StorageState.ALREADY_CONNECTED.value,
            documents_present=documents_present,
            has_active_case=has_active_case,
        )
        return decision.next_route
    except ValueError:
        return "/storage/providers"
```

### Consumers of route_user()

| File | Function | Usage |
|------|----------|-------|
| `app/routers/storage.py` | `storage_home()`, OAuth callback | Post-auth redirect |
| `app/main.py` | `_guard_role_page()` | Role page guarding |
| `app/routers/onboarding.py` | (removed return_to param) | Prevent redirect loops |

### Routing Logic Summary

**Tenant (UserRole.USER):**
1. No storage connected → `/storage/providers` (Process A)
2. Storage connected, no documents → `/tenant/documents` (Process B1)
3. Storage + documents → `/tenant` (Process B2)

**Professional Roles (Advocate, Legal, Admin, Manager):**
- Always → `/advocate` or role-specific route (Process B4)
- Storage warnings shown if not connected

---

## 4. Cloud-First Mechanics

### Upload → Overlay → Timeline Flow

```
1. Document Upload
   ↓
2. Store at: Semptify5.0/Vault/documents/{filename}
   ↓
3. Create overlay at: Semptify5.0/Vault/.overlay/{overlay_id}.json
   ↓
4. Register in: Semptify5.0/Vault/.overlay/registry.json
   ↓
5. Extract timeline events → Semptify5.0/Vault/timeline/events.json
```

### Authority Principle

The **cloud paths are authoritative**. Database is fallback only.

| Data | Authority | Fallback |
|------|-----------|----------|
| Timeline events | `events.json` in cloud | DB timeline table |
| Document overlays | `.overlay/` directory | DB overlay records |
| Document registry | `registry.json` | DB document records |

### Timeline Chronology Service

**File:** `app/services/timeline_chronology.py`

- Function-group constant: `TIMELINE_FUNCTION_GROUP = "timeline_chronology"`
- Builder: `build_timeline_chronology(...)`
- `/timeline` route orchestrates cloud-event load + chronology build

### Three Timestamps Per Event

1. **Event time** — When the event occurred (extracted from document)
2. **Document-created time** — From pipeline payload (when available)
3. **Semptify ingestion time** — `uploaded_at` or `extracted_at` fallback

---

## 5. Integration Points

### How to Use Vault Paths

```python
from app.core.vault_paths import VAULT_DOCUMENTS, VAULT_TIMELINE_EVENTS_FILE

# Correct: Use canonical paths
cloud_path = f"{VAULT_DOCUMENTS}/{filename}"
timeline_path = VAULT_TIMELINE_EVENTS_FILE
```

### How to Use Module Contracts

```python
from app.core.module_contracts import FunctionGroupContract, register_function_group

# Register a new function group
contract = FunctionGroupContract(
    module="my_module",
    group_name="my_group",
    title="My Feature",
    description="Does something useful",
    inputs=("document_id", "user_id"),
    outputs=("result", "status"),
    dependencies=("storage", "auth"),
)
register_function_group(contract)

# Validate all contracts
result = contract_registry.validate()
```

### How to Use Routing

```python
from app.core.workflow_engine import route_user

# Single source of truth for redirects
redirect_url = route_user(
    user_id=request.cookies.get("se_user"),
    documents_present=True,
    has_active_case=False
)
return RedirectResponse(redirect_url)
```

---

## 6. Recent SSOT Hardening Changes

### OAuth Routing Consolidation
- **Before:** Multiple hardcoded redirect tables in `storage.py`, `main.py`, `onboarding.py`
- **After:** All redirects flow through `route_user()` in `workflow_engine.py`
- **Root cause fixed:** `return_to=/onboarding/status` parameter caused ERR_TOO_MANY_REDIRECTS — removed

### Vault Path Centralization
- **Before:** Path strings scattered across services
- **After:** All paths defined in `vault_paths.py`, imported by consumers
- **Result:** One location to change cloud storage structure

### Contract Registry
- **Before:** Function groups registered ad-hoc
- **After:** Centralized `ModuleContractRegistry` with validation
- **Benefit:** Deterministic integration, health checkable

---

## 7. Deterministic Principles

1. **Stateless over Stateful** — Prefer stateless behavior; avoid local fallbacks
2. **Cloud Authority** — Cloud storage is source of truth; DB is fallback
3. **One Router** — All routing decisions through `route_user()`
4. **One Path Source** — All cloud paths through `vault_paths.py`
5. **One Contract Shape** — All function groups use `FunctionGroupContract`

---

## 8. Process Contracts (Logged)

Process contracts define deterministic user workflows with defined entry criteria, steps, and exit criteria.

| Contract ID | Function Group | File | Status | Version |
|-------------|----------------|------|--------|---------|
| `proc_user_reconnect` | `user_session_recovery` | `docs/process_contracts/user_reconnect_v2.md` | Active | 2.0 |

### Contract: User Reconnect Flow

**Purpose**: Enable **returning users** to reconnect their Semptify session. Exclusively for users who have used Semptify before.

**Key Principles**:
- `provider_subject` is the single source of truth for user identity
- User ID cookie encodes `provider + role + random` (e.g., `GU7x9kM2pQ`)
- Returning users never select provider/role again - extracted from user ID
- Silent reauthorize when tokens expired but refresh fails
- **Separate from onboarding** - this is for existing users only

**Entry Points**:
- `/storage/` - Returning user with valid cookie
- `/storage/reconnect` - User lost cookie, must select provider

**Exit Criteria**:
- `semptify_uid` cookie set with 1-year expiry
- Valid storage tokens in DB
- User routed to role-appropriate dashboard via `route_user()`

**Implementation**: `app/routers/storage.py` (`storage_home()`, `initiate_oauth()`, `oauth_callback()`)

---

## Files That Implement SSOT

| File | Purpose |
|------|---------|
| `app/core/vault_paths.py` | Canonical cloud storage paths |
| `app/core/module_contracts.py` | Function-group contract registry |
| `app/core/workflow_engine.py` | Deterministic routing engine |
| `app/routers/storage.py` | User session recovery (contract: `proc_user_session_recovery`) |
| `app/services/timeline_chronology.py` | Timeline chronology builder |

---

*This document serves as the authoritative reference for Single Source of Truth patterns in Semptify 5.0.*
