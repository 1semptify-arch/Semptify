# Semptify Developer Kit (SDK) — Guide

The Semptify SDK is the kit for building modules that work with Semptify's
vault, documents, timeline, and workflow engine. It lives inside the
repository at `app/sdk/` — it is real and in use, but it is **not a packaged
release**: there is no `pip install semptify-sdk`. You build against it
inside the repo.

This guide describes what each piece does. For the module lifecycle
(`dev_only` → `preview` → `experimental` → `beta` → `stable`), see the Forge
rules in `.devin/rules/09-forge.md`.

---

## 1. Module SDK — `app/sdk/module_sdk.py`

The base layer for a new module. You define a `ModuleDefinition`, register
the actions your module can perform, and initialize against the workflow
engine (the "Positronic Mesh").

```python
from app.sdk.module_sdk import (
    ModuleSDK,
    ModuleDefinition,
    ActionDefinition,
    ModuleCategory,
)

module = ModuleDefinition(
    name="my_module",
    display_name="My Module",
    description="What it does",
    version="1.0.0",
    category=ModuleCategory.UTILITY,
)

sdk = ModuleSDK(module)

@sdk.action("do_something", produces=["result_data"])
async def do_something(user_id: str, params: dict, context: dict):
    return {"result_data": "ok"}

sdk.initialize()
```

`ModuleCategory` organizes modules: `DOCUMENT`, `LEGAL`, `CALENDAR`,
`COMMUNICATION`, `ANALYSIS`, `STORAGE`, `UI`, `UTILITY`, `AI`,
`INTEGRATION`.

## 2. Vault SDK — `app/sdk/vault/`

`VaultClient` is the single class all Semptify products use for vault
operations — the tenant's folder tree inside their own cloud storage.

- Zero dependencies on FastAPI, SQLAlchemy, middleware, or navigation.
- All paths come from `app.core.vault_paths` (the SSOT).
- Takes the provider name, access token, and user ID directly — no lookups.
- Methods: `create_folders()`, `health_check()`, `repair()`.
- Pre-built folder specs: `TENANT_VAULT`, `ADVOCATE_VAULT`, `LEGAL_VAULT`,
  `RESEARCH_VAULT` (advocate/legal specs are for the separate add-on repo;
  this app is tenant-only).
- Gate marking is the caller's responsibility — the SDK never touches
  onboarding gates or the database.

```python
from app.sdk.vault import VaultClient, TENANT_VAULT

vault = VaultClient(
    provider="google_drive",
    access_token="<token>",
    user_id="GU2L3wyfBy",
    folder_spec=TENANT_VAULT,
)
result = await vault.create_folders()
```

Storage tiers: **USER** (Google Drive / Dropbox / OneDrive — the tenant owns
it), **SYSTEM** (Cloudflare R2 indexes), **LOCAL** (server memory / token
cache, ephemeral).

## 3. External module SDK — `app/sdk/external/`

Clients for modules loaded by `app.core.external_loader` — code that runs
inside Semptify but is not part of the core. Every call goes through an
immutable `ExternalModuleContext` (`context.py`) carrying the module name,
vendor, acting user, and its granted `PermissionSet`.

Least privilege is enforced in code (`permissions.py`): each permission is
declared in the module's `semptify.module.json` manifest and approved before
use. External modules can never get direct database access, other modules'
internals, network calls to undeclared domains, or file-system access
outside their sandbox.

| Client | Permission enforced | What it does |
|---|---|---|
| `overlay_client.py` | `overlay.read` / `overlay.write` | Read and create record overlays for the acting user |
| `vault_client.py` | `vault.read` / `vault.write` | Vault file operations via the internal `VaultClient`, with audit logging |
| `document_client.py` | `document.read` (write is rarely granted) | List and read the user's documents |
| `timeline_client.py` | `timeline.read` / `timeline.write` | Read and append timeline events |
| `notification_client.py` | `notification.send` | Send the user a notification, audited under the module's name |

## 4. Navigation SDK — `app/sdk/navigation/`

Client helpers for resolving the canonical SSOT navigation stages so a
module links to real routes instead of hardcoded paths.

## 5. Auth helpers — `app/sdk/auth/`

User-ID, cookie, role, and token helpers shared by modules.

## 6. Plugin manager — `app/sdk/plugin_manager.py`

Discovers, loads, and unloads add-on plugin modules at runtime, with
dependency resolution and versioning. A public module marketplace is a
long-term goal, not a shipped feature — this is the loading machinery, not
a store.

## 7. Scaffolding and migration helpers

- `app/sdk/generate_module.py` — CLI that scaffolds a new module:
  `python -m app.sdk.generate_module my_module "My Module" "Description" --category legal --has-ui`
- `app/sdk/flask_converter.py` — converts a Flask app file into a Semptify
  module skeleton.
- `app/sdk/phase2_sdk.py` — an earlier, broader kit (document preview,
  batch operations, security, testing helpers). It predates the
  manifest/permission model — prefer the module + external SDK above for
  new work.

---

## Rules that apply to anything you build on this

- **Python 3.11.9 only.** The whole codebase is pinned to it.
- **No tenant PII server-side.** A tenant's records live in their own
  storage. Modules go through the SDK clients — never around them.
- **Contracts first.** Module capabilities are declared through
  `FunctionGroupContract` registrations; the contract loader
  (`app/core/contract_loader.py`) is what makes a function callable.
- **New modules start `dev_only`** in the Forge and are promoted through
  the documented lifecycle. They are never born `stable`.
- Read `AGENTS.md` and `CONTRIBUTING.md` before opening a pull request.
