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
```text

### Path Usage Summary

| Constant | Path | Purpose |
| ---------- | ------ | --------- |
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

## 1.1 Document Upload Flow Analysis

### Path (4 Steps)

```

Step 0: [Entry - HTTP POST /api/setup/documents/upload]
Step 1: [Vault Upload Service - upload()]
Step 2: [Document Processing - _process_document()]
Step 3: [Form Data Hub Update]

```text

### Storage Locations

| Type | Primary | Backup | Cache |
| ------ | --------- | -------- | ------- |
| Original File | User's cloud storage (Semptify5.0/Vault/documents/) | None | None |
| Document Metadata | PostgreSQL (documents table) | None | In-memory |
| Timeline Events | PostgreSQL (timeline_events table) | None | None |
| Form Data | PostgreSQL (form_data_hub table) | None | None |

### SSOT Rule
>
> **"Every document upload is a single atomic operation: store → process → certify"**

### Certification States

| State | vault_id | registry_id | is_valid | Meaning |
| ------- | ---------- | ------------- | ---------- | --------- |
| Valid | ✅ | ✅ | `True` | Successfully uploaded and processed |
| Partial | ✅ | ❌ | `False` | Uploaded but processing failed |
| Invalid | ❌ | - | `False` | Upload failed (no file stored) |

### Code Pattern

```python
## OLD: Upload then process separately (potential partial state)
vault_doc = await vault_service.upload(...)
extracted = await _process_document(...)  # Separate call

## NEW: Atomic upload with processing
certified_doc = await vault_service.upload_and_process(...)
## All in one transaction, no partial states
```

---

## 1.2 Unified Vault + Registry Document Flow

**Files:** `app/services/vault_upload_service.py`, `app/services/document_registry.py`

### Principle: Single Entry Point, Automatic Certification

Every document entering Semptify follows ONE path:

```text
Tenant Upload
    ↓
Vault Upload Service (vault_upload_service.upload())
    ├─ Store in user's cloud storage (Semptify5.0/Vault/documents/)
    ├─ Create VaultDocument (vault_id, sha256_hash, storage_path)
    ├─ Generate certificate
    ├─ AUTO-REGISTER in Document Registry ← NEW: Unified step
    │   └─ Create chain of custody record
    │   └─ Assign SEM-YYYY-NNNNNN-XXXX ID (registry_id)
    │   └─ Verify integrity (sha256)
    └─ Create unified overlay (upload manifest)
    ↓
Return CertifiedVaultDocument
    ├─ vault_id: Semptify internal reference
    ├─ registry_id: Chain of custody ID
    ├─ is_certified: True (has both vault + registry)
    └─ integrity_status: "verified"
```

### VaultDocument Certification States

| State | vault_id | registry_id | is_certified | Meaning |
| ------- | ---------- | ------------- | -------------- | --------- |
| **Certified** | ✅ | ✅ | `True` | Full chain of custody, ready for processing |
| **Uncertified** | ✅ | ❌ | `False` | In vault but registration failed - retry needed |
| **Invalid** | ❌ | - | `False` | Upload failed, document not stored |

### SSOT Rule

> **"Every document in the vault IS a registered document. No exceptions."**

- Vault upload auto-registers - router doesn't call registry separately
- Registry enrichment (case_number, IP) happens after auto-registration
- Downstream modules check `doc.is_certified` before processing
- Uncertified docs are logged but not rejected - they can be re-registered

### Code Pattern

```python
## OLD: Router called registry separately (two-step)
vault_doc = await vault_service.upload(...)
registry_doc = registry.register_document(...)  # REDUNDANT

## NEW: Vault auto-registers, router enriches (unified)
vault_doc = await vault_service.upload(...)  # Auto-registers
if vault_doc.registry_id:
    registry.enrich_document(vault_doc.registry_id, case_number=..., ip_address=...)
```text

---

## 2. Role Mapping (Frontend ↔ Backend)

**File:** `static/onboarding/storage-select.html`

### Canonical Role Names

| Backend (API) | Frontend (UI) | Description |
| --------------- | --------------- | ------------- |
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
import os
is_localhost = os.environ.get("ENVIRONMENT", "development") == "development"

response.set_cookie(
    key="semptify_session",
    value=session_data["session_id"],
    max_age=86400,  # 24 hours
    httponly=True,
    secure=False if is_localhost else True,  # Conditional!
    samesite="lax",
)
```text

### Implementation Notes

#### Role Name Consistency (Critical Fix)

**Bug:** Redirect loop caused by role name mismatch between user ID encoding and page guards.

**Root Cause:** User IDs encode role as `"tenant"` but page guards checked for `{"user"}`.

**Files Fixed:**

- `app/main.py` `_guard_role_page` calls for tenant routes:
  - `/tenant/` → changed `{"user"}` to `{"tenant"}`
  - `/tenant/{subpage}` → changed `{"user"}` to `{"tenant"}`  
  - `/tenant/home/` → changed `{"user"}` to `{"tenant"}`

**Rule:** Page guard allowed_roles must match the role string encoded in user IDs (via `get_role_from_user_id`).

#### HTTP/HTTPS Cookie Security Pattern

**Standard:** `secure=False` for localhost HTTP, `secure=True` for production HTTPS

```python
## Correct pattern for cookie security
import os
is_localhost = os.environ.get("ENVIRONMENT", "development") == "development"
response.set_cookie(
    key="semptify_session",
    value=session_data["session_id"],
    max_age=86400,  # 24 hours
    httponly=True,
    secure=False if is_localhost else True,  # Conditional!
    samesite="lax",
)
```

### Configuration

Set in `.env` or environment:

```bash
## Development (HTTP localhost)
ENVIRONMENT=development

## Production (HTTPS)
ENVIRONMENT=production
```text

### Implementation Checklist

All cookie-setting locations must use this pattern:

| File | Function | Line | Status |
| ------ | ---------- | ------ | -------- |
| `app/routers/security.py` | `login` | ~325 | ✅ Fixed |
| `app/routers/storage.py` | `oauth_callback` | ~1700 | ✅ Fixed |
| `app/routers/storage.py` | `oauth_callback` (error path) | ~1744 | ✅ Fixed |
| `app/routers/storage.py` | `rehome` | ~2134 | ✅ Fixed |
| `app/routers/storage.py` | `restore_session` | ~2344 | ✅ Fixed |
| `app/routers/storage.py` | `update_user_id` | ~2677 | ✅ Fixed |

**Critical:** Never hardcode `secure=True` or `secure=False`. Always use the conditional pattern.

**Common Bug:** Each cookie-setting block must define `is_localhost` in its own scope. Don't assume it's inherited from earlier in the function. Example bug fixed at line ~1744 where error handler used `is_localhost` without defining it first.

**Critical Consistency:** The `semptify_uid` cookie must ALWAYS use `httponly=False` (not True) so JavaScript can read it for auth checks. Bug fixed at line ~2346 where `restore_session` incorrectly used `httponly=True` while all other locations used `httponly=False`.

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
>
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
```text

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
```text

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
```text

### Consumers of route_user()

| File | Function | Usage |
| ------ | ---------- | ------- |
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

```text

### Authority Principle

The **cloud paths are authoritative**. Database is fallback only.

| Data | Authority | Fallback |
| ------ | ----------- | ---------- |
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

## Correct: Use canonical paths
cloud_path = f"{VAULT_DOCUMENTS}/{filename}"
timeline_path = VAULT_TIMELINE_EVENTS_FILE
```

### How to Use Module Contracts

```python
from app.core.module_contracts import FunctionGroupContract, register_function_group

## Register a new function group
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

## Validate all contracts
result = contract_registry.validate()
```text

### How to Use Routing

```python
from app.core.workflow_engine import route_user

## Single source of truth for redirects
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
| ------------- | ---------------- | ------ | -------- | --------- |
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
| ------ | --------- |
| `app/core/vault_paths.py` | Canonical cloud storage paths |
| `app/core/module_contracts.py` | Function-group contract registry |
| `app/core/workflow_engine.py` | Deterministic routing engine |
| `app/routers/storage.py` | User session recovery (contract: `proc_user_session_recovery`) |
| `app/services/timeline_chronology.py` | Timeline chronology builder |

---

## 1.3 First Document Upload — Contract & Pipeline Verification

**Scope:** trace a single file from the tenant's browser into the user's vault and back out again, and list the `FunctionGroupContract`s that govern that path.

### Entry Points (canonical routes)

| Route | Purpose | When to use |
| ------- | --------- | ------------- |
| `POST /api/intake/upload` | Queue upload for later processing | Generic intake |
| `POST /api/intake/upload/auto` | Upload + run Light Intake (Pass 1) in one call | Tenant "Add Record" / auto-processing |
| `POST /api/intake/upload/batch` | Multiple files at once | Folder/batch drop |
| `POST /api/vault/upload` | Internal/service vault upload (not UI) | Service-to-service only |
| `POST /api/vault/sidebar/upload` | Sidebar quick upload | Persistent sidebar "Add Record" |

Tenant-facing uploads **must** target `POST /api/intake/upload/auto`. `POST /api/vault/upload` is documented as internal-only.

### Pipeline Flow (first document)

```text
[Browser UploadForm]
    │
    ▼
Step 0: POST /api/intake/upload/auto
        app/modules/intake/router.py:482
    │
    ├─ Step 0a: Resolve authenticated user (yellow_access / form user_id)
    ├─ Step 0b: Resolve access token (form → session → ensure_valid_token)
    │              app/modules/intake/router.py:532-542
    │              app/core/auto_refresh.py:38
    │
    ▼
Step 1: File validation
        app/modules/intake/router.py:551-557
        - empty file rejected
        - hard 25 MB limit (intake router)
        ⚠️ extension check is NOT done here
    │
    ▼
Step 2: Optional notarization
        app/modules/intake/router.py:559-586
        app/services/notarization (best-effort)
    │
    ▼
Step 3: VaultUploadService.upload()
        app/services/vault_upload_service.py:536
    │   ├─ validate input / size / extension / mime
    │   ├─ compute SHA-256 and deduplicate by hash
    │   ├─ generate vault_id and safe_filename
    │   ├─ _store_document() → Semptify5.0/Vault/documents/{safe_filename}
    │   │              app/services/vault_upload_service.py:803
    │   ├─ _create_certificate() → Semptify5.0/Vault/certificates/{cert_id}.json
    │   │              app/services/vault_upload_service.py:837
    │   ├─ DocumentRegistry.register_document()
    │   │              app/services/document_registry.py:652
    │   │              → registry_id (SEM-YYYY-NNNNNN-XXXX)
    │   │              → content_hash, metadata_hash, combined HMAC
    │   │              → integrity_status = "verified"
    │   ├─ write VAULT_UPLOAD_MANIFEST overlay (best-effort)
    │   ├─ VaultDocumentIndex.add() → DB vault_index / vault_user_index / vault_hash_index
    │   └─ emit DOCUMENT_UPLOAD_RECEIVED + DOCUMENT_ADDED events
    │
    ▼
Step 4: SSOT certification gate
        app/modules/intake/router.py:409-427
        - if vault_doc.is_certified is False, downstream is blocked
    │
    ▼
Step 5: IntakeEngine.intake_document()
        app/services/document_intake.py:1056
        - creates IntakeDocument, local working copy in data/intake/{user_id}/
    │
    ▼
Step 6: IntakeEngine.process_document()
        app/services/document_intake.py:1119
        - text extraction (pdf / image / txt)
        - document classification
        - date / amount / party / issue extraction (Pass 1)
        - summary + key_points
    │
    ▼
Step 7: Deep OCR / Flow Orchestration
        app/modules/intake/router.py:642-689
        - skipped under DEPLOY_TARGET=render_mvp
        - queued as background job otherwise
    │
    ▼
Step 8: vault_service.mark_processed()
        app/services/vault_upload_service.py:994
        - writes extracted data as cloud overlays
    │
    ▼
Step 9: event_bus.publish(DOCUMENT_PROCESSED)
        app/modules/intake/router.py:721-732
    │
    ▼
[Response] AutoProcessResponse { id, filename, status, vault_id,
          extracted_data, timeline_events, issues_found }
```

### From Vault Back Out

```text
[vault_id]
    │
    ├─ GET /api/vault/document/{vault_id}/content
    │   → VaultUploadService.get_document_content()
    │   → storage.download_file() by provider_file_id, then storage_path
    │
    ├─ GET /api/vault/{vault_id}/certificate
    │   → certificate JSON from Semptify5.0/Vault/certificates/
    │
    ├─ GET /api/vault/
    │   → VaultUploadService.get_user_documents()
    │   → SELECT from vault_index
    │
    └─ GET /api/intake/{doc_id}
        → IntakeEngine._documents or data/intake/documents.json
```

### Contract List — First-Upload Pipeline

| Module | Group | Title | Inputs | Outputs | Deterministic | Dependencies |
| -------- | ------- | ------- | -------- | --------- | --------------- | -------------- |
| `intake` | `intake_upload` | Intake Upload (SSOT) | `file`, `user_id` | `doc_id`, `filename`, `status` | No | `app.modules.intake.router` |
| `intake` | `intake_upload_auto` | Intake Upload and Auto-Process (SSOT) | `file`, `user_id` | `doc_id`, `document_type`, `issues_found`, `dates`, `amounts`, `parties`, `status` | No | `app.modules.intake.router`, `app.modules.documents.router` |
| `intake` | `intake_upload_batch` | Intake Batch Upload (SSOT) | `files`, `user_id` | `results`, `total`, `succeeded`, `failed` | No | `app.modules.intake.router` |
| `intake` | `intake_process` | Intake Process Document (SSOT) | `doc_id`, `user_id` | `doc_id`, `status`, `document_type` | No | `app.modules.intake.router` |
| `intake` | `intake_status` | Intake Processing Status (SSOT) | `doc_id` | `doc_id`, `status`, `progress` | Yes | `app.modules.intake.router` |
| `intake` | `intake_get_document` | Intake Get Document (SSOT) | `doc_id` | `document` | Yes | `app.modules.intake.router` |
| `vault` | `vault_upload` | Vault Upload (SSOT) | `file`, `user_id`, `document_type?`, `description?`, `tags?` | `document_id`, `certificate_id`, `sha256_hash`, `storage_path` | Yes | `app.modules.vault.router`, `app.services.vault_upload_service` |
| `vault` | `vault_list_documents` | Vault List Documents (SSOT) | `user_id`, `document_type?` | `documents`, `total` | Yes | `app.modules.vault.router` |
| `vault` | `vault_download_document` | Vault Download Document (SSOT) | `document_id`, `user_id` | `file_stream`, `filename`, `mime_type` | Yes | `app.modules.vault.router` |
| `vault` | `vault_get_certificate` | Vault Get Certificate (SSOT) | `document_id`, `user_id` | `certificate_id`, `sha256`, `certified_at`, `storage_path` | Yes | `app.modules.vault.router` |
| `vault` | `vault_init` | Vault Initialize (SSOT) | `user_id`, `provider` | `ok`, `message` | No | `app.modules.vault.router`, `app.sdk.vault` |
| `vault` | `vault_verify` | Vault Verify (SSOT) | `user_id`, `provider` | `ok`, `folders` | Yes | `app.modules.vault.router`, `app.sdk.vault` |
| `documents` | `documents_process` | Documents Process (SSOT) | `file`, `user_id` | `document_id`, `document_type`, `extracted_text`, `dates`, `amounts`, `parties`, `issues` | No | `app.modules.documents.router`, `app.modules.intake.router` |
| `documents` | `documents_list` | Documents List (SSOT) | `user_id` | `documents` | Yes | `app.modules.documents.router` |
| `documents` | `documents_get` | Documents Get Detail (SSOT) | `doc_id`, `user_id` | `document`, `intelligence`, `issues` | Yes | `app.modules.documents.router` |
| `storage` | `storage_oauth_initiate` | Storage OAuth Initiate (SSOT) | `provider`, `semptify_uid?` | `redirect` | No | `app.modules.storage.router` |
| `storage` | `storage_oauth_callback` | Storage OAuth Callback (SSOT) | `provider`, `code`, `state` | `redirect`, `user_id` | No | `app.modules.storage.router` |
| `storage` | `storage_session_restore` | Storage Session Restore (SSOT) | `user_id` | `success`, `user_id` | No | `app.modules.storage.router` |
| `unified_overlays` | `unified_overlays_create_overlay` | Unified_Overlays Create Overlay (POST) (SSOT) | (none in contract) | `result` | No | `app.modules.unified_overlays.router` |

*Contracts verified from the live `contract_registry` after `load_all_contracts()` (Python 3.11.9, venv311).*

### Storage Locations

| Data Type | Primary | Backup / Cache | Access Pattern |
| ----------- | --------- | ---------------- | ---------------- |
| Original file bytes | User's cloud storage `Semptify5.0/Vault/documents/{safe_filename}` (`VAULT_DOCUMENTS`) | `VaultUploadService._local_dir` if `storage_provider=local` | Write-once, read-many |
| Certificate | `Semptify5.0/Vault/certificates/{certificate_id}.json` (`VAULT_CERTIFICATES`) | None | Write-once, read-many |
| Upload manifest overlay | `Semptify5.0/Vault/overlays/documents/` (`VAULT_OVERLAY_DOCUMENTS`) | None | Write-once, read-many |
| Vault metadata | PostgreSQL/SQLite `vault_index`, `vault_user_index`, `vault_hash_index` | In-memory dict + `data/vault_index/vault_index.json` | Read/Write frequently |
| Processing working copy | `data/intake/{user_id}/{doc_id}_{filename}` | None | Ephemeral |
| Intake document records | `data/intake/documents.json` | In-memory dict | Read/Write |
| Document registry | `data/document_registry/registry.json` | In-memory dict | Read/Write |

### SSOT Rule

> **A document only enters Semptify through the intake router, is stored in the user's vault first, is automatically registered for chain of custody, and only then is passed to extraction, overlays, and downstream modules.**

### Certification States

| State | vault_id | registry_id | `is_certified` | Meaning |
| ------- | ---------- | ------------- | ---------------- | --------- |
| **Certified** | ✅ | ✅ | `True` | In vault + registered + `integrity_status="verified"` — safe to process |
| **Uncertified** | ✅ | ❌ / unverified | `False` | Stored but registration or integrity check failed; processing is blocked by the SSOT gate |
| **Invalid** | ❌ | - | `False` | Upload failed before reaching the vault |

### Code Pattern

```python
## OLD (violation): separate, potentially inconsistent steps
vault_doc = await some_storage.upload(...)
registry_doc = registry.register_document(...)  # separate, can fail independently
extracted = await extraction.process(...)

## NEW (SSOT): one canonical path, automatic registration
vault_doc = await VaultUploadService.upload(...)
# vault_doc already has vault_id, registry_id, certificate_id, is_certified
if vault_doc.is_certified:
    doc = await IntakeEngine.intake_document(vault_id=vault_doc.vault_id, ...)
    doc = await IntakeEngine.process_document(doc.id)
    await vault_service.mark_processed(vault_doc.vault_id, extracted_data=...)
```

### MVP / Render Gating

- `app/core/product_manifest.py:1319` → `get_mvp_allowed_modules()` includes `app.modules.intake.router`, `app.modules.vault.router`, `app.modules.documents.router`, and `app.modules.storage.router`.
- `app/modules/intake/router.py:642` skips Deep OCR Pass 2 under `DEPLOY_TARGET=render_mvp`.
- `app/modules/intake/router.py:679` skips `DocumentFlowOrchestrator` under `render_mvp`.
- `requirements-render-mvp.txt` removes `sentence-transformers`, `playwright`, and test/dev packages; `numpy` is retained for vector / extraction code.

### Configuration & Verification Checklist

For the first document to reach the vault correctly, confirm:

- [ ] Python 3.11.9 active (`venv311` on Windows).
- [ ] `SECRET_KEY` configured; `SECURITY_MODE` matches environment (`open` for dev, `enforced` for production).
- [ ] `DATABASE_URL` set and tables initialized (run migrations or `sqlite` file exists).
- [ ] `DEPLOY_TARGET` set as intended (`render_mvp` for Render, unset or `render_full` for full).
- [ ] `app/core/contract_loader.py` loads all contracts without errors for `intake`, `vault`, `documents`, `storage`.
- [ ] Storage OAuth token present in DB (or `local` fallback only in `open` dev mode).
- [ ] Vault folder structure created (onboarding `vault_init` / `vault_verify`).
- [ ] `app/core/vault_paths.py` is the only source of `Semptify5.0/...` paths.
- [ ] Run `python -m py_compile` on changed pipeline files.
- [ ] Run `pytest tests/module_health -q --no-cov` (after resolving disk-space issue if present).
- [ ] Run a live upload test via `POST /api/intake/upload/auto` and verify response has `vault_id`, `notarization_id`, `status` not `uncertified`.
- [ ] Verify `vault_index` row, `data/document_registry/registry.json` entry, and cloud/local file all exist for the test `vault_id`.

### Issues / Gaps Found During This Verification

1. **Local dev storage directory is not configured.**
   - `VaultUploadService` never sets `_local_dir`; tests manually assign it, but the app does not.
   - Result: any `storage_provider="local"` upload in dev raises `RuntimeError: local storage directory not configured`.
   - File: `app/services/vault_upload_service.py:433`.
   - **Fix:** initialize `_local_dir` from `settings.vault_dir` (e.g., `uploads/vault`) in `__init__` or in `get_vault_service()`.

2. **Upload size limits are inconsistent.**
   - `app/modules/intake/router.py:556` hardcodes `25 * 1024 * 1024`.
   - `app/services/vault_upload_service.py:473` uses `settings.max_upload_size_mb` (default `50`).
   - **Fix:** use `settings.max_upload_size_mb` in both places.

3. **File-extension validation is missing from the auto-intake route.**
   - `POST /api/vault/upload` checks `is_allowed_extension()`; `POST /api/intake/upload/auto` does not.
   - **Fix:** add extension validation to `upload_and_process()`.

4. **`vault::vault_upload` / `vault::vault_init` are registered twice.**
   - `app/modules/vault/register.py` and `app/services/vault_upload_service.py` both register the same `module::group_name` keys.
   - The contract loader overwrites one with the other depending on import order.
   - **Fix:** keep the contract in one place (recommended: `app/modules/vault/register.py`) and remove the duplicate registrations from the service file.

5. **Document Registry is local-JSON only.**
   - `DocumentRegistry` stores `data/document_registry/registry.json` and an in-memory dict; it is not mirrored to the database.
   - The DB (`vault_index.registry_id`) is the only persistent link between `vault_id` and `registry_id`.
   - **Implication:** DB backups are critical; a lost/corrupted `registry.json` can be partially rebuilt from DB + certificates.

6. **Overlay creation is best-effort with silent failures.**
   - `VAULT_UPLOAD_MANIFEST` and `mark_processed` overlays are wrapped in `try/except` and only logged.
   - **Implication:** the system continues to work, but long-term audit trails may be incomplete if cloud write fails.

### Next-Stage Recommendations

1. **Fix the local `_local_dir` initialization** before any dev upload smoke test; this is a hard blocker for first-document verification in `storage_provider=local` mode.
2. **Reconcile the duplicate size-limit and extension checks** across `intake/router.py` and `vault_upload_service.py`.
3. **Consolidate the duplicate `vault_upload` / `vault_init` contracts** to a single registration source.
4. **Run the full first-document E2E test** against the running server (`/debug/seed-test-user` then `POST /api/intake/upload/auto`) and inspect:
   - HTTP 200 response with `vault_id`
   - `vault_index` DB row with `registry_id` and `integrity_status='verified'`
   - Local/cloud file at `Semptify5.0/Vault/documents/{safe_filename}`
   - Certificate at `Semptify5.0/Vault/certificates/{certificate_id}.json`
5. **Once the E2E passes, proceed to the three-date sort/view verification and attorney invite-code stub** from the current backlog.

---

*This document serves as the authoritative reference for Single Source of Truth patterns in Semptify 5.0.*
