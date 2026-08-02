# Semptify Vault SDK Blueprint

## 1. Problem Statement

Vault creation is tangled across 5+ files:

- `app/routers/storage.py` (OAuth callback, the actual running path)
- `app/modules/onboarding/oauth.py` (different callback, never called)
- `app/modules/onboarding/vault.py` (folder creation)
- `app/services/storage/vault_manager.py` (full vault init with encryption)
- `app/core/vault_paths.py` (folder path definitions)
- `app/modules/onboarding/config.py` (folder list for onboarding)

Result: vault creation fails silently, gates get marked without folders existing,
debug takes hours, and building Semptify Advocate or Legal means duplicating it all.

---

## 2. Storage Classification System

### Storage Tiers

Every Semptify product uses up to 3 storage tiers:

| Tier | Provider | Purpose |
| -------- | ------------------------ | ---------------------------------------------- |
| USER | Google Drive / Dropbox / OneDrive | User's own files. User owns them. Survives Semptify shutdown. |
| SYSTEM | Cloudflare R2 | System indexes, caches, metadata. Not user data. Rebuild-safe. |
| LOCAL | Server memory | Token cache, session state. Lost on restart. Never source of truth. |

### Storage Sets (Product Configurations)

A "storage set" is a named combination of tiers. Products choose a set:

**SET A: "Full Stack"** (production target)

- USER: Google Drive / Dropbox / OneDrive
- SYSTEM: Cloudflare R2
- LOCAL: In-memory token cache

**SET B: "User-Only"** (current, what is running now)

- USER: Google Drive / Dropbox / OneDrive
- SYSTEM: PostgreSQL (DB fallback for metadata)
- LOCAL: In-memory token cache

**SET C: "Serverless"** (future, edge/mobile)

- USER: Google Drive / Dropbox / OneDrive
- SYSTEM: None (stateless)
- LOCAL: Browser localStorage / device storage

Products declare which set they use:

```python
## Semptify Tenant
STORAGE_SET = "B"  # User-Only for now

## Semptify Advocate (future)
STORAGE_SET = "A"  # Full Stack, needs R2 for cross-client indexes

## Semptify Research (future)
STORAGE_SET = "C"  # Serverless, stateless analysis tool
```text

---

## 3. Vault SDK Architecture

### File Structure

```

app/sdk/vault/
  **init**.py              # Public API: VaultClient, StorageSet, VaultFolderSpec
  client.py                # VaultClient, the one class all products use
  folder_spec.py           # Folder structure definitions (declarative)
  errors.py                # VaultError hierarchy
  providers/
    **init**.py            # get_provider() factory
    base.py                # StorageProvider ABC (moved from app/services/storage/)
    google_drive.py        # Google Drive implementation
    dropbox.py             # Dropbox implementation
    onedrive.py            # OneDrive implementation
  auth/
    **init**.py
    token_store.py         # MasterToken, encrypt/decrypt (from vault_manager.py)
    device_keys.py         # Device authorization
  artifacts/
    manifest.py            # VAULT_MANIFEST.txt generator
    readme.py              # README.txt generator
    rehome.py              # Rehome.html generator

```text

### Public API Surface

```python
from app.sdk.vault import VaultClient

vault = VaultClient(
    provider="google_drive",
    access_token="ya29.xxxxx",
    user_id="GU2L3wyfBy",
)

## Folder Operations
await vault.create_folders()
await vault.verify_folders()
folders = vault.list_expected_folders()

## File Operations
await vault.upload("documents", filename, content)
await vault.download("documents", filename)
files = await vault.list_files("documents")
await vault.delete("documents", filename)

## Vault Lifecycle
result = await vault.initialize()
status = await vault.health_check()
await vault.repair()

## Auth Token Operations
await vault.write_master_token(token_data)
token = await vault.read_master_token()
await vault.update_oauth_backup(access_token, refresh_token)

## Product-Specific Extensions
vault.register_folders([
    "Semptify5.0/Vault/legal_filings",
])
await vault.create_folders()
```

### Key Design Decisions

1. **No database dependency.** VaultClient takes a token and does storage ops.
   It does not import SQLAlchemy, know about gates, or care about onboarding.

2. **No HTTP/FastAPI dependency.** Pure library. Usable in CLI tools,
   background jobs, tests, or other frameworks.

3. **No singleton state.** Each call creates a fresh client. No global caches,
   no module-level state that breaks between tests or concurrent users.

4. **Folder specs are declarative.** Products define what folders they need,
   the client creates them. No hardcoded paths in business logic.

5. **Provider abstraction stays.** The existing StorageProvider ABC is solid.
   We move it into the SDK and the old app/services/storage/ becomes a thin
   wrapper that imports from the SDK.

---

## 4. Folder Specification System

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class VaultFolderSpec:
    root: str = "Semptify5.0"

    core_folders: List[str] = field(default_factory=lambda: [
        "Semptify5.0",
        "Semptify5.0/Vault",
        "Semptify5.0/Vault/documents",
        "Semptify5.0/Vault/certificates",
    ])

    auth_folders: List[str] = field(default_factory=lambda: [
        ".Semptify5.0/auth",
        ".Semptify5.0/vault",
    ])

    product_folders: List[str] = field(default_factory=list)

    @property
    def all_folders(self) -> List[str]:
        return self.core_folders + self.auth_folders + self.product_folders

    def extend(self, folders: List[str]) -> "VaultFolderSpec":
        return VaultFolderSpec(
            root=self.root,
            core_folders=self.core_folders,
            auth_folders=self.auth_folders,
            product_folders=self.product_folders + folders,
        )

## Pre-built specs
TENANT_VAULT = VaultFolderSpec()

ADVOCATE_VAULT = VaultFolderSpec().extend([
    "Semptify5.0/Vault/client_files",
    "Semptify5.0/Vault/case_notes",
    "Semptify5.0/Vault/legal_filings",
])

LEGAL_VAULT = VaultFolderSpec().extend([
    "Semptify5.0/Vault/court_exhibits",
    "Semptify5.0/Vault/case_files",
    "Semptify5.0/Vault/discovery",
])

RESEARCH_VAULT = VaultFolderSpec().extend([
    "Semptify5.0/Vault/research",
    "Semptify5.0/Vault/dossiers",
])
```text

---

## 5. Integration Plan

### Phase 1: Build SDK (This Session)

- Create `app/sdk/vault/` with client, providers, folder_spec
- Wire `/debug/create-vault` to use VaultClient
- Verify folders actually appear in Google Drive

### Phase 2: Rewire Onboarding (Next Session)

- `storage.py` OAuth callback calls `VaultClient.initialize()` directly
- Remove `app/modules/onboarding/vault.py` (replaced by SDK)
- Remove duplicate vault logic from `vault_manager.py`

### Phase 3: Module Registry (Future)

- Build the `load_modules()` system
- Vault becomes a registered module with its own folder spec
- Each product's main.py declares which modules to load

### Migration Path (Backward Compatible)

```python
## Old code (today):
from app.services.storage import get_provider
storage = get_provider("google_drive", access_token=token)
await storage.create_folder("Semptify5.0/Vault/documents")

## New code (SDK):
from app.sdk.vault import VaultClient
vault = VaultClient(provider="google_drive", access_token=token, user_id=uid)
await vault.create_folders()

## Transition: old imports still work (thin wrapper)
```

---

## 6. Foreseeable Problems and Solutions

### Problem 1: Token Expiry During Vault Creation

Access token expires mid-folder-creation (1hr lifetime, slow API calls).

**Solution:** VaultClient accepts optional token_refresher callback:

```python
async def refresh(current_token: str) -> str:
    return new_token

vault = VaultClient(
    provider="google_drive",
    access_token=token,
    user_id=uid,
    token_refresher=refresh,
)
```text

### Problem 2: Multi-Product Folder Conflicts

User has Tenant AND Advocate. Both try to create Semptify5.0/Vault/.

**Solution:** create_folder() is idempotent. Creating an existing folder is a no-op.
Each product adds its own subfolders. Shared root is safe.

### Problem 3: Gate Marked But Folders Missing (Current Bug)

Gate says vault_initialized=true but folders do not exist.

**Solution:** SDK separates folder creation from gate marking.
The client does NOT touch gates. That is the caller's job.

```python
vault = VaultClient(...)
result = await vault.create_folders()
if result.all_ok:
    await mark_gate(db, user_id, "vault_initialized")
## Gate is NEVER marked unless folders actually exist
```

### Problem 4: Render Deploy Caching Stale Code

Docker layer cache serves old code.

**Solution:** Already fixed with ARG CACHEBUST in Dockerfile. Also, SDK
has a **version** logged on startup for verification.

### Problem 5: Race Between OAuth Callback and Token Cache

Vault creation starts before token is cached.

**Solution:** VaultClient takes access_token directly. No lookup needed.
Token is a parameter, not fetched from cache or DB.

### Problem 6: Google Drive API Rate Limits

Creating 10+ folders in rapid succession may hit rate limits.

**Solution:** VaultClient uses sequential creation with configurable delay
between calls (default 100ms). Folders are created in dependency order
(parent before child). If rate-limited, exponential backoff with 3 retries.

### Problem 7: Partial Vault Creation (Some Folders Created, Some Failed)

Network drops mid-creation. Some folders exist, some do not.

**Solution:** create_folders() returns per-folder status. repair() re-runs
creation for any missing folders. All operations are idempotent.

```python
result = await vault.create_folders()
## result.folders = [
##   {"path": "Semptify5.0", "status": "ok"},
##   {"path": "Semptify5.0/Vault", "status": "ok"},
##   {"path": "Semptify5.0/Vault/documents", "status": "error", "detail": "timeout"},
## ]
## result.all_ok = False
```text

### Problem 8: Provider API Differences

Google Drive uses folder IDs (not paths). Dropbox uses paths. OneDrive uses
drive item IDs. Each has different error codes and rate limits.

**Solution:** StorageProvider ABC hides these differences. Each provider
implements path-to-ID resolution internally. The client always works with
logical paths like "Semptify5.0/Vault/documents".

### Problem 9: Logging Invisible on Render

Python logging module output not captured by Render.

**Solution:** SDK uses print(flush=True) for critical operations during
development. Production switches to structured logging with explicit
stdout handler configuration.

---

## 7. What the SDK Does NOT Do

These remain the responsibility of the calling application:

- OAuth authentication (getting the access_token)
- Gate management (marking vault_initialized)
- Cookie management
- Middleware / route protection
- Database operations
- User ID generation
- SSOT navigation

The SDK is a tool. The application is the user of the tool.

---

## 8. Acceptance Criteria

The SDK is done when:

1. `VaultClient.create_folders()` creates all folders in Google Drive
2. `VaultClient.verify_folders()` returns True after creation
3. `VaultClient.health_check()` reports vault status accurately
4. No imports from app.routers, app.core.database, or app.core.navigation
5. Can be tested with a mock provider (no real API calls needed)
6. `/debug/create-vault` endpoint uses VaultClient successfully
7. Folders visible in user's Google Drive under Semptify5.0/

---

## 9. Decision Log (For Future Adapter Developers)

This section explains WHY decisions were made — not just WHAT was built.
Read this before building adapters for new products or providers.

### Decision 1: BASE_VAULT vs Product Specs (Separation)

**Question:** Should the SDK know what folders each product needs?

**Answer:** No. The SDK creates ONLY the universal skeleton:

- `Semptify5.0/` (root)
- `Semptify5.0/Vault/` (vault root)
- `.Semptify5.0/auth/` (identity + encryption)
- `.Semptify5.0/vault/` (metadata + manifest)

Each product adds its own subfolders via `register_folders()` or a pre-built spec.

**Why:** If the SDK hardcodes "documents" or "certificates", then every product
inherits folders it may not use. Advocate doesn't need "certificates". Research
doesn't need "documents". Clean separation means each product is self-contained.
A developer building Advocate never needs to know what Tenant's folders are.

### Decision 2: Auth Folders Are Universal (Not Product-Specific)

**Question:** Should each product have its own .auth/ folder?

**Answer:** No. One user = one identity = one `.Semptify5.0/auth/` folder shared
across all products.

**Why:** The auth folder contains the encrypted master token — the proof of "who
is this person." If Tenant and Advocate each had their own auth, you'd have two
competing identity systems in one vault. When the token expires or rotates, which
one is authoritative? Which one does Rehome.html point to? Conflicting auth is
the #1 cause of "account locked out" bugs in multi-product systems. One auth,
many products.

### Decision 3: SDK Does NOT Touch Gates or Database

**Question:** Should the SDK mark `vault_initialized` after creating folders?

**Answer:** No. The SDK creates folders and reports success/failure. The CALLER
marks the gate.

**Why:** Gates are an application concern, not a storage concern. The SDK doesn't
know what gates exist, what database schema is being used, or what the onboarding
flow looks like. If a product doesn't use gates (e.g., a CLI tool), the SDK still
works fine. Mixing storage and application state is exactly what caused the
original bug (gate marked but folders missing).

### Decision 4: Access Token Passed Directly (Not Looked Up)

**Question:** Should the SDK look up the token from a cache or database?

**Answer:** No. The token is passed as a constructor parameter.

**Why:** Token lookup introduces dependencies on `token_manager`, database sessions,
and cache state. It also creates race conditions — the token might not be cached
yet when the SDK is called (this was the original vault creation bug). Passing the
token directly means: if you have a token, vault works. Period. No timing issues,
no cache misses, no DB queries.

### Decision 5: All Paths From vault_paths.py (Never Duplicated)

**Question:** Should the SDK define its own path constants?

**Answer:** No. Every path is imported from `app/core/vault_paths.py`.

**Why:** vault_paths.py is the single source of truth for folder names. If someone
renames "Semptify5.0" to "Semptify6.0", it changes in ONE file and propagates
everywhere — SDK, routers, middleware, vault_manager. If the SDK had its own
strings, you'd have to update two places and pray they stay in sync.

### Decision 6: Idempotent Operations (No "Already Exists" Errors)

**Question:** What happens if create_folders() is called twice?

**Answer:** Nothing bad. Every operation is idempotent. Creating an existing
folder is a no-op. The SDK reports "ok" for existing folders, not "error: exists."

**Why:** Multi-product environments. User installs Tenant (creates base + documents).
Later installs Advocate (creates base + legal_filings). The base already exists
from Tenant — Advocate's `create_folders()` should succeed, not crash. Also:
network retries, interrupted flows, repair operations — all depend on idempotency.

### Decision 7: Per-Folder Status (Not All-Or-Nothing)

**Question:** Should create_folders() fail entirely if one folder fails?

**Answer:** No. It creates everything it can and reports per-folder status.

**Why:** Partial success is real. If 5/6 folders are created but the 6th hits a
rate limit, you don't want to lose the 5 that worked. The caller can inspect
`result.failed` and decide: retry? repair? alert user? This is especially
important for `repair()` — you want to know WHAT is broken, not just "something
is broken."

### Decision 8: No Framework Dependency (Pure Library)

**Question:** Should VaultClient use FastAPI's dependency injection or middleware?

**Answer:** No. Zero framework imports.

**Why:** Semptify Advocate might not use FastAPI. It might be a Django app, a CLI
tool, or a serverless function. The vault SDK must work in ALL of these. If it
imports FastAPI, it's locked to one framework forever. A developer building a
Semptify mobile backend in Node.js can still use the Python SDK as a reference
implementation or call it as a microservice — it has no opinions about HTTP.

### Decision 9: VaultFolderSpec Is Frozen (Immutable)

**Question:** Can products modify a spec after creation?

**Answer:** No. `@dataclass(frozen=True)`. Use `.extend()` to get a NEW spec.

**Why:** Specs are shared. TENANT_VAULT is a module-level constant. If one part
of the code mutates it, every other part sees the mutation. Frozen dataclasses
prevent accidental state corruption. `.extend()` returns a new object, leaving
the original untouched. Safe for concurrent access, safe for testing.

---

## 10. How To Build A New Product Adapter

When creating a new Semptify product (e.g., "Semptify Advocate"):

```python
## 1. Define your product's folders (in your product's config, NOT in the SDK)
from app.sdk.vault import BASE_VAULT

ADVOCATE_FOLDERS = [
    "Semptify5.0/Vault/client_files",
    "Semptify5.0/Vault/case_notes",
    "Semptify5.0/Vault/legal_filings",
]

MY_VAULT = BASE_VAULT.extend(ADVOCATE_FOLDERS)

## 2. After OAuth, create the vault
from app.sdk.vault import VaultClient

vault = VaultClient(
    provider="google_drive",
    access_token=token_from_oauth,
    user_id=user_id,
    folder_spec=MY_VAULT,
)
result = await vault.create_folders()

## 3. Check result — mark your own gates however your product does it
if result.all_ok:
    # Your product's gate system (not the SDK's job)
    mark_user_ready(user_id)
else:
    # Handle partial failure
    log_failed_folders(result.failed)
```

You do NOT need to:

- Understand auth folder encryption
- Know about other products' folders
- Import anything from app.routers or app.core.database
- Worry about token caching or refresh timing
- Care about SSOT navigation or middleware
