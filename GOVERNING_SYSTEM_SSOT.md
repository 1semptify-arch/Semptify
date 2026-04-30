# Semptify 5.0 — Governing System (SSOT)

**Purpose:** Single source of truth for system orchestration, authentication flow, and cross-module integration.  
**Conductor Philosophy:** Distributed governance with centralized routing. No single point of failure.  
**Last Updated:** April 29, 2026

---

## 🎼 The Conductor — Distributed Orchestration

Semptify uses a **distributed conductor model** — no single orchestrator, but coordinated subsystems with clear contracts:

```
┌─────────────────────────────────────────────────────────────┐
│                    THE CONDUCTOR LAYER                      │
├─────────────────────────────────────────────────────────────┤
│  workflow_engine.py    │  Single source of truth for routing │
│  cookie_auth.py        │  Identity verification (HMAC)      │
│  module_contracts.py   │  Service capability registry         │
│  vault_paths.py        │  Canonical path constants            │
│  action_maps.py        │  Quick action routing                │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Library │    │  Office  │    │  Tools   │
    │  (Pages) │    │  (Vault) │    │(Analysis)│
    └──────────┘    └──────────┘    └──────────┘
```

---

## 🔐 Cookie & Authentication System

### Cookie Format (HMAC-Signed)
```
<user_id>.<hmac_signature>
Example: GD7x9kM2pQ.a3f8c2d1e4b7...
```

### User ID Structure
```
Format: <provider_code><role_code><8-char-random>
Example: GU7x9kM2pQ = Google Drive + User (Tenant) + 7x9kM2pQ
         │ │ │
         │ │ └── 8-character random suffix
         │ └──── Role code (U=User/Tenant, A=Admin, V=Advocate, L=Legal)
         └────── Provider code (G=Google, D=Dropbox, O=OneDrive)
```

**Provider Codes (1 char):**
- `G` = Google Drive
- `D` = Dropbox  
- `O` = OneDrive

**Role Codes (1 char):**
- `U` = User (displayed as Tenant in housing context)
- `A` = Admin
- `M` = Manager
- `V` = Advocate
- `L` = Legal
- `J` = Judge

**Important:** The underscore-separated format (`google_drive_tenant_abc123`) is NOT valid for `parse_user_id()`. Use the compact 10-character format.

### Auth Flow Diagram
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser    │────▶│   /reconnect │────▶│ Session Check│
│  (Cookie)    │     │   Endpoint   │     │   (DB/API)   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          │ Valid                 │ Invalid               │ No Cookie
                          ▼                       ▼                       ▼
                   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
                   │ route_user()│        │ Silent OAuth│        │ Provider    │
                   │ → Home      │        │ → Callback  │        │ Picker      │
                   └─────────────┘        └─────────────┘        └─────────────┘
```

### Key Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `sign_user_id()` | `cookie_auth.py:32` | Create HMAC-signed cookie at OAuth callback |
| `verify_user_id()` | `cookie_auth.py:43` | Verify cookie on every request |
| `extract_user_id()` | `cookie_auth.py:79` | Middleware helper |
| `parse_user_id()` | `user_id.py` | Decode provider/role/unique from user_id |
| `get_role_from_user_id()` | `user_id.py` | Extract role string |

---

## 🚦 Routing System (The Conductor)

### `route_user()` — Single Source of Truth
**Location:** `app/core/workflow_engine.py:253`

**Purpose:** Every redirect in the app goes through this function. No hardcoded paths.

**Logic:**
```python
def route_user(user_id, documents_present=None, has_active_case=False) -> str:
    1. Parse user_id → provider, role, unique
    2. If no user_id → /storage/providers (onboarding)
    3. Check vault for documents (if documents_present not provided)
    4. Call evaluate_from_params(role, storage_state, documents_present)
    5. Return decision.next_route
```

**Routing Decision Matrix:**

| Role | Storage | Documents | Route |
|------|---------|-----------|-------|
| Tenant | Need Connect | — | `/storage/providers` |
| Tenant | Connected | 0 | `/tenant/home` (B1 - Upload) |
| Tenant | Connected | 1+ | `/tenant/home` (B2 - Triage) |
| Advocate | Any | Any | `/advocate` (B4) |
| Legal | Any | Any | `/legal` (B4) |
| Admin | Any | Any | `/admin` (B4) |

### Workflow Engine Processes

| Code | Name | Description |
|------|------|-------------|
| A | Welcome | Role selection, first-time setup |
| B1 | Upload Wizard | Document upload for new users |
| B2 | Quick Triage | Tenant case assessment |
| B3 | Filing | Court packet preparation |
| B4 | Professional | Advocate/legal workspace |

---

## 🔄 Integration Points

### 1. Storage → Workflow Integration
**File:** `storage.py` → `workflow_engine.route_user()`

When OAuth completes:
```python
# storage.py:1762 (callback)
landing = _route_user(user_id)  # Never hardcode paths
```

### 2. Page → Action Integration
**File:** `action_maps.py`

Quick actions route through action maps, not hardcoded URLs:
```python
DASHBOARD_QUICK_ACTIONS["view_timeline"] → QuickAction(
    target="/timeline",
    required_roles=["user", "advocate", "legal"],
)
```

### 3. Module → Contract Integration
**File:** `module_contracts.py`

Services register their capabilities:
```python
contract_registry.register(FunctionGroupContract(
    module="legal_analysis",
    group_name="evidence_classification",
    inputs=("document",),
    outputs=("classification", "summary"),
    dependencies=(),  # No external deps = works in Core
))
```

### 4. Path → Vault Integration
**File:** `vault_paths.py`

All cloud storage paths use canonical constants:
```python
VAULT_DOCUMENTS = "Semptify5.0/Vault/documents"
VAULT_TIMELINE_EVENTS_FILE = "Semptify5.0/Vault/timeline/events.json"
```

---

## 🐛 Debugging Guide

### Cookie Issues

**Symptom:** User keeps redirecting to `/storage/providers`
```bash
# Check cookie format
curl -I http://localhost:8000/tenant/home -H "Cookie: semptify_uid=<value>"

# Verify in logs
# Look for: "cookie_auth: signature mismatch" → SECRET_KEY changed
# Look for: "cookie_auth: malformed cookie" → Wrong format
```

**Fix:** If SECRET_KEY changed, users must re-authenticate (expected behavior).

### Routing Issues

**Symptom:** User lands on wrong page after OAuth
```bash
# Check route_user() logic
grep -n "landing = _route_user" app/routers/storage.py

# Verify workflow decision
# Add debug: logger.info(f"Routing decision: {decision}")
```

### Session Issues

**Symptom:** `/reconnect` loops to storage selection
```bash
# Check get_valid_session() in storage.py:738
# Look for: Session auto-refresh failures
# Check: OAuth state preservation
```

**Recent Fix:** `storage.py:780-785` - Added session validation before OAuth

---

## 📋 Final Assembly Checklist

### Pre-Launch Verification

- [ ] **Cookie System**
  - [ ] `sign_user_id()` works at OAuth callback
  - [ ] `verify_user_id()` validates on every request
  - [ ] HMAC uses SECRET_KEY from environment
  - [ ] Cookie secure flag = True for production

- [ ] **Routing System**
  - [ ] `route_user()` is called for all redirects
  - [ ] No hardcoded URLs in storage.py OAuth flow
  - [ ] Workflow decisions match product requirements
  - [ ] return_to parameter works for task recovery

- [ ] **Integration Points**
  - [ ] All services use vault_paths constants
  - [ ] Module contracts registered for Core features
  - [ ] Action maps route to correct pages
  - [ ] Page contracts declare module dependencies

- [ ] **Conductor Coordination**
  - [ ] workflow_engine → cookie_auth integration
  - [ ] storage.py → route_user() integration
  - [ ] action_maps → page routing integration
  - [ ] module_contracts → service discovery

---

## 🏛️ Governance Principles

1. **No Hardcoded Paths** — Always use `route_user()` or constants
2. **Contract-First** — Services declare inputs/outputs before implementation
3. **HMAC Identity** — Cookie is source of truth; verify on every read
4. **Deterministic Routing** — Same state → same route (no randomness)
5. **Distributed but Accountable** — Each subsystem has clear contracts

---

## 📚 Related Documents

- `BUILD_GUIDE_SSOT.md` — Build status and testing
- `SEMPFIFY_INVENTORY.md` — Feature categorization
- `app/core/workflow_engine.py` — Routing logic
- `app/core/cookie_auth.py` — Identity verification
- `app/core/module_contracts.py` — Service contracts
- `app/core/vault_paths.py` — Canonical paths
- `app/core/action_maps.py` — Action routing

---

## 🔧 System Health Check

```bash
# 1. Verify imports
python -c "from app.core.workflow_engine import route_user; print('✓ workflow_engine')"
python -c "from app.core.cookie_auth import verify_user_id; print('✓ cookie_auth')"
python -c "from app.core.module_contracts import contract_registry; print('✓ module_contracts')"
python -c "from app.core.vault_paths import VAULT_DOCUMENTS; print('✓ vault_paths')"

# 2. Test route_user
python -c "from app.core.workflow_engine import route_user; print(route_user('google_drive_tenant_test123'))"

# 3. Verify cookie signing
python -c "from app.core.cookie_auth import sign_user_id, verify_user_id; uid='test'; signed=sign_user_id(uid); print(f'Signed: {signed}'); print(f'Verified: {verify_user_id(signed)}')"

# 4. Check contracts
python -c "from app.core.module_contracts import contract_registry; print(f'Registered: {len(contract_registry.list_contracts())}')"
```

---

## 🎯 The Conductor in One Sentence

> **workflow_engine.py's `route_user()` is the conductor** — every path decision flows through it, backed by HMAC-verified identity from `cookie_auth.py`, with service capabilities declared in `module_contracts.py` and canonical paths from `vault_paths.py`.

All systems are accountable to these contracts. That's the governing system.
