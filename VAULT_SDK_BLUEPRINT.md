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

| Tier   | Provider               | Purpose                                      |
|--------|------------------------|----------------------------------------------|
| USER   | Google Drive / Dropbox / OneDrive | User's own files. User owns them. Survives Semptify shutdown. |
| SYSTEM | Cloudflare R2          | System indexes, caches, metadata. Not user data. Rebuild-safe. |
| LOCAL  | Server memory          | Token cache, session state. Lost on restart. Never source of truth. |

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
# Semptify Tenant
STORAGE_SET = "B"  # User-Only for now

# Semptify Advocate (future)
STORAGE_SET = "A"  # Full Stack, needs R2 for cross-client indexes

# Semptify Research (future)
STORAGE_SET = "C"  # Serverless, stateless analysis tool
```

---

## 3. Vault SDK Architecture

### File Structure

```
app/sdk/vault/
  __init__.py              # Public API: VaultClient, StorageSet, VaultFolderSpec
  client.py                # VaultClient, the one class all products use
  folder_spec.py           # Folder structure definitions (declarative)
  errors.py                # VaultError hierarchy
  providers/
    __init__.py            # get_provider() factory
    base.py                # StorageProvider ABC (moved from app/services/storage/)
    google_drive.py        # Google Drive implementation
    dropbox.py             # Dropbox implementation
    onedrive.py            # OneDrive implementation
  auth/
    __init__.py
    token_store.py         # MasterToken, encrypt/decrypt (from vault_manager.py)
    device_keys.py         # Device authorization
  artifacts/
    manifest.py            # VAULT_MANIFEST.txt generator
    readme.py              # README.txt generator
    rehome.py              # Rehome.html generator
```

### Public API Surface

```python
from app.sdk.vault import VaultClient

vault = VaultClient(
    provider="google_drive",
    access_token="ya29.xxxxx",
    user_id="GU2L3wyfBy",
)

# Folder Operations
await vault.create_folders()
await vault.verify_folders()
folders = vault.list_expected_folders()

# File Operations
await vault.upload("documents", filename, content)
await vault.download("documents", filename)
files = await vault.list_files("documents")
await vault.delete("documents", filename)

# Vault Lifecycle
result = await vault.initialize()
status = await vault.health_check()
await vault.repair()

# Auth Token Operations
await vault.write_master_token(token_data)
token = await vault.read_master_token()
await vault.update_oauth_backup(access_token, refresh_token)

# Product-Specific Extensions
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

# Pre-built specs
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
```

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
# Old code (today):
from app.services.storage import get_provider
storage = get_provider("google_drive", access_token=token)
await storage.create_folder("Semptify5.0/Vault/documents")

# New code (SDK):
from app.sdk.vault import VaultClient
vault = VaultClient(provider="google_drive", access_token=token, user_id=uid)
await vault.create_folders()

# Transition: old imports still work (thin wrapper)
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
```

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
# Gate is NEVER marked unless folders actually exist
```

### Problem 4: Render Deploy Caching Stale Code
Docker layer cache serves old code.

**Solution:** Already fixed with ARG CACHEBUST in Dockerfile. Also, SDK
has a __version__ logged on startup for verification.

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
# result.folders = [
#   {"path": "Semptify5.0", "status": "ok"},
#   {"path": "Semptify5.0/Vault", "status": "ok"},
#   {"path": "Semptify5.0/Vault/documents", "status": "error", "detail": "timeout"},
# ]
# result.all_ok = False
```

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
