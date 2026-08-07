# Semptify Partner & Developer Integration Guide

> **Version:** 1.0 — June 2026
> **Audience:** External developers, partner organisations, and anyone building on or integrating with Semptify.
> **Status:** Authoritative. If code and this document conflict, fix the code.

---

## 1. What Semptify Is

Semptify is a **free, privacy-first housing-rights platform** for tenants facing housing problems.
It is not a SaaS product. It is not an advertising platform. It has no freemium tier.

Its core job is to help people who cannot afford a legal team to:
- Organise documents and evidence
- Understand their rights under the law
- Build and preserve a legal record of housing violations
- Take informed next steps without needing a lawyer for every question

Everything built on or into Semptify must serve that mission. If it does not serve a tenant's
rights, safety, or legal standing, it does not belong here.

---

## 2. Non-Negotiables — These Are Hard Lines

These rules cannot be overridden by any partner, module, plugin, or contract. Violation means
the integration is rejected, full stop.

### 2.1 Mission Hard Lines

| Rule | What it means in practice |
|---|---|
| **Free forever** | No paywalls, no paid tiers, no "premium" features that gatekeep rights information |
| **No advertising** | No ad SDKs, no tracking pixels, no affiliate links, no sponsored content |
| **Privacy by design** | No user profiling, no behavioural analytics sold or shared, no third-party data brokers |
| **No victim-blaming content** | Do not produce content that hedges legal facts, blames tenants, or creates false moral equivalence |
| **Truth standard** | When the law protects a tenant, say so clearly. When a landlord violates the law, name it plainly. |
| **User-controlled documents** | User data lives in the user's own storage (Dropbox, Google Drive, OneDrive). Semptify does not own it. |

### 2.2 Technical Hard Lines

| Rule | Enforcement |
|---|---|
| **Python 3.11.9 only** | `main.py` hard-exits on wrong version. No 3.12+ dependencies. |
| **No secrets in code** | Runtime injection only. Never hardcode API keys, tokens, or passwords. |
| **No bare `except:`** | Always catch specific exceptions. `except ValueError`, `except RuntimeError`, etc. |
| **No `datetime.now()`** | Always use `utc_now()` from `app.core.utc`. |
| **No hardcoded URLs** | Use `navigation.get_stage("stage_id").path` — never string literals like `"/onboarding/step2"`. |
| **No mutable default arguments** | `def f(items=[])` is a bug. Use `None` and set default inside the function. |
| **No root containers** | Docker containers must use the `USER` directive — never run as root. |

---

## 3. Architecture Overview

Semptify is a **FastAPI monorepo** with three extension layers:

```
┌─────────────────────────────────────────────────────┐
│  Semptify Core (this repo)                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│  │  CORE     │  │ EXTENDED  │  │ ADVOCATE /    │   │
│  │  tier     │  │  tier     │  │ ADMIN /       │   │
│  │ (always   │  │ (legal    │  │ RESEARCH /    │   │
│  │  on)      │  │  tools)   │  │ DEV tiers     │   │
│  └───────────┘  └───────────┘  └───────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Module Registry  (app/core/module_sdk.py)   │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Product Manifest (app/core/product_manifest)│   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────────┐
│  Internal       │    │  External Plugin     │
│  Module         │    │  (plugins/ folder,   │
│  (in this repo) │    │   plugin.json)       │
└─────────────────┘    └──────────────────────┘
```

### Product Tiers

| Tier | Purpose | Always on? |
|---|---|---|
| `CORE` | Tenant-rights essentials, vault, documents, law library | ✅ Yes |
| `EXTENDED` | Eviction defense, court forms, case builder | ✅ Yes (live) |
| `ADVOCATE` | Advocate network, collaboration, invite codes | ✅ Yes (live) |
| `ADMIN` | Dashboards, analytics, admin console | ✅ Yes (live) |
| `RESEARCH` | AI intelligence, recognition, crawlers, dossiers | ✅ Yes (live) |
| `DEV` | Page editor, setup wizard, dev tools | ✅ Yes (live) |

### Module Capabilities

A module declares what it does. Each capability has a contract:

| Capability | What it means | Required |
|---|---|---|
| `ROUTER` | Provides FastAPI routes | Must set `router_module` |
| `CONTRACT` | Declares function-group contracts for the Positronic Mesh | Must set `contracts` |
| `MESH` | Integrates with the Positronic Mesh action bus | Must set `mesh_actions` |
| `DOCUMENT` | Handles document processing | Must use vault SDK for storage |
| `WIDGET` | Provides UI components | Must follow UI conventions |
| `BACKGROUND` | Has background tasks | Must use FastAPI `BackgroundTasks` |

---

## 4. Integration Types — Which One Are You?

### Type A: Internal Module (built into this repo)

You are contributing directly to the Semptify codebase. Your module lives in `app/modules/your_module/`.

**Required files:**
```
app/modules/your_module/
    __init__.py
    router.py          ← FastAPI APIRouter named `router`
    models.py          ← Pydantic request/response models
```

**Required registration** — one line in `app/core/product_manifest.py`:
```python
_register(
    "app.modules.your_module.router",
    tags=("Your Module",),
    tier=ProductTier.EXTENDED,  # pick the right tier
    optional=True,
)
```

**Required manifest declaration** (if using the full module SDK):
```python
from app.core.module_sdk import ModuleManifest, ModuleCapability, register_module
from app.core.product_manifest import ProductTier

manifest = ModuleManifest(
    name="your_module",
    display_name="Your Module",
    description="What it does in one sentence.",
    version="1.0.0",
    tier=ProductTier.EXTENDED,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.your_module.router",
    tags=("Your Module",),
)
```

---

### Type B: External Plugin (lives outside this repo)

You are building something that drops into a running Semptify instance without modifying this repo.

**Required structure:**
```
plugins/your_plugin/
    plugin.json        ← metadata descriptor
    main.py            ← entry point with initialize() and cleanup()
    __init__.py
    README.md
```

**Required `plugin.json`:**
```json
{
  "name": "your_plugin",
  "display_name": "Your Plugin",
  "description": "What it does.",
  "version": "1.0.0",
  "author": "Your Name or Org",
  "license": "MIT",
  "min_semptify_version": "1.0.0",
  "dependencies": [],
  "python_packages": [],
  "category": "utility",
  "tags": ["housing", "tenants"],
  "main_module": "main",
  "init_function": "initialize"
}
```

**Required `main.py` structure:**
```python
from app.sdk import ModuleSDK, ModuleDefinition, ModuleCategory

module_definition = ModuleDefinition(
    name="your_plugin",
    display_name="Your Plugin",
    description="What it does.",
    version="1.0.0",
    category=ModuleCategory.UTILITY,
)

sdk = ModuleSDK(module_definition)


@sdk.action("your_action", produces=["result"])
async def your_action(user_id: str, params: dict, context: dict):
    return {"result": "done"}


def initialize():
    sdk.initialize()


def cleanup():
    pass


__all__ = ["sdk", "module_definition", "initialize", "cleanup"]
```

**Plugin discovery directories** (checked in order):
1. `app/plugins/` — built-in plugins
2. `plugins/` — repo-level user plugins
3. `~/.semptify/plugins/` — user home plugins

---

### Type C: Blueprint Submission (preferred for external builders)

You describe what you want to build in a structured JSON blueprint. Semptify's team (or Cascade)
generates the correct module skeleton from the blueprint. This is the **fastest and safest path**
for external integrations because it guarantees compliance from the start.

**Blueprint format:**
```json
{
  "name": "rent_strike_tracker",
  "display_name": "Rent Strike Tracker",
  "description": "Tracks active rent strikes and tenant organizing.",
  "tier": "extended",
  "capabilities": ["router", "contract"],
  "routes": [
    {
      "method": "GET",
      "path": "/api/strike/{case_id}",
      "auth": "required",
      "returns": "StrikeStatus",
      "description": "Get status of a rent strike case"
    },
    {
      "method": "POST",
      "path": "/api/strike/register",
      "auth": "required",
      "body": "StrikeRegistration",
      "description": "Register a new rent strike"
    }
  ],
  "models": [
    {
      "name": "StrikeStatus",
      "fields": {
        "case_id": "str",
        "active": "bool",
        "start_date": "date",
        "tenant_count": "int"
      }
    },
    {
      "name": "StrikeRegistration",
      "fields": {
        "address": "str",
        "issue": "str",
        "tenant_count": "int"
      }
    }
  ],
  "dependencies": ["vault", "timeline"],
  "python_packages": [],
  "author": "Partner Org Name",
  "contact": "dev@partnerorg.example"
}
```

Submit the blueprint to Semptify. Do not submit partial code — a clean blueprint generates
better code than partially-written code that doesn't follow the conventions.

---

## 5. Code Standards — Required for All Integration Types

### Python

- **Python 3.11.9.** No exceptions.
- **Async first.** Use `async def` for all I/O-bound endpoints and functions.
- **Pydantic models** for all request bodies and responses. No raw dicts at API boundaries.
- **Specific exceptions.** `except ValueError`, never `except:`.
- **`utc_now()`** from `app.core.utc` for all timestamps. Never `datetime.now()`.
- **`pathlib.Path`** for file paths. Never `os.path` string manipulation.
- **Dependency injection** for auth, DB sessions, shared services. No global state.
- **PEP 8.** 4-space indent, 88-char line length (Black default), snake_case.

### FastAPI Routes

```python
# Required pattern — all authenticated routes
from app.core.security import require_user  # or yellow_access, require_role


@router.get("/api/your-module/{id}", tags=["Your Module"])
async def get_thing(
    id: str,
    current_user=Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> YourResponseModel: ...
```

- Every route must have a `tags` value matching your module's registered tag.
- Every authenticated route must use a security dependency — never roll your own auth check.
- Return Pydantic models, not raw dicts.
- Use `async def` — never blocking sync DB calls inside async routes.

### Navigation (SSOT — Critical)

**Never do this:**
```python
return RedirectResponse(url="/onboarding/step2")  # ❌ hardcoded
```
```javascript
window.location.href = "/onboarding/step2";        // ❌ hardcoded
```
```html
<a href="/onboarding/step2">Next</a>               // ❌ hardcoded
```

**Always do this:**
```python
from app.core.navigation import navigation

stage = navigation.get_stage("vault_setup")
return RedirectResponse(url=stage.path)  # ✅ SSOT
```
```javascript
// In static files — fetch the navigation API first
const nav = await fetch("/onboarding/ssot-navigation").then(r => r.json());
window.location.href = nav.stages.vault_setup.path; // ✅ SSOT
```

### Security

- **No secrets in code.** All credentials via environment variables, never hardcoded.
- **No logging of PII** — no user IDs in full, no email addresses, no document contents in logs.
- **Rate limiting** — use `rate_limit_dependency` from `app.core.security` on public endpoints.
- **Admin endpoints** — use `_stealth_admin` guard. Returns 404 (not 403) to non-admins.
- **File uploads** — validate MIME type and size. MNDES compliance applies to court documents.

### Docker (if containerised)

```dockerfile
FROM python:3.11-slim          # ✅ Pinned — never :latest
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
USER appuser                   # ✅ Non-root user
CMD ["uvicorn", "app.main:app"]
```

- Use `.dockerignore` — exclude `__pycache__`, `.env`, `*.pyc`, test files.
- Use multi-stage builds to keep images small.
- Never store secrets in the image — inject at runtime via Render env vars.

---

## 6. What Gets Rejected

Any integration exhibiting the following will not be accepted:

### Mission violations
- Monetisation of tenant data or document access
- Advertising, affiliate, or sponsored content of any kind
- Content that softens or hedges clear legal protections
- Content that blames tenants for landlord violations
- Surveillance features, engagement tracking, or behavioural profiling
- Any feature that primarily serves landlord interests over tenant interests

### Technical violations
- Python version other than 3.11.9
- Bare `except:` blocks
- Hardcoded URL strings in redirects or navigation
- `datetime.now()` without UTC
- Secrets committed to the repo
- Synchronous blocking calls inside async routes
- Rolling custom authentication instead of using the security dependency
- Creating `_v2`, `_new`, `_fixed` copies of existing files instead of editing originals
- Adding imports inside function bodies instead of at the top of the file

### Architectural violations
- Defining redirect targets outside the navigation registry
- Bypassing the product manifest for router registration
- Writing directly to the database without going through the vault SDK for user documents
- Duplicate exception handler registration

---

## 7. Submission Checklist

Before submitting any integration for review:

- [ ] Read `BUILD_STATE.md` — understand what is currently live and what is broken
- [ ] Read `ACTIVE_CONTEXT.md` — understand what is currently being worked on
- [ ] Read the Known Failure Registry in `AGENTS.md` — do not repeat past mistakes
- [ ] All Python files compile: `python -m py_compile app/modules/your_module/router.py`
- [ ] SSOT tests pass: `python tests/test_ssot_architecture.py`
- [ ] No hardcoded URLs in routes, templates, or static files
- [ ] No secrets in code
- [ ] `datetime.now()` does not appear anywhere in your module
- [ ] All routes use a security dependency
- [ ] Pydantic models on all API boundaries
- [ ] Module registered in `app/core/product_manifest.py`
- [ ] `optional=True` unless your module is genuinely required for the app to start

---

## 8. Contact & Blueprint Submission

To submit a blueprint or discuss an integration:

1. Prepare your blueprint JSON (see Section 4, Type C above)
2. Open a GitHub issue in this repository with the label `integration-proposal`
3. Include: blueprint JSON, your organisation name, intended tier, and a one-paragraph description
   of how this serves tenant rights

Integrations that do not serve the mission of protecting tenant rights will be declined
regardless of technical quality.

---

## 9. Quick Reference Card

| I want to... | Use this |
|---|---|
| Add routes to Semptify | Internal Module (Type A) |
| Build something outside the repo | External Plugin (Type B) |
| Propose a new feature | Blueprint Submission (Type C) |
| Navigate between pages | `navigation.get_stage("id").path` |
| Get the current time | `utc_now()` from `app.core.utc` |
| Authenticate a user | `Depends(require_user)` |
| Authenticate an admin | `Depends(_stealth_admin)` |
| Register my module | `_register(...)` in `product_manifest.py` |
| Handle a background task | `FastAPI BackgroundTasks` |
| Store a user document | Vault SDK — never direct filesystem |
| Declare module capabilities | `ModuleManifest(capabilities=(ModuleCapability.ROUTER,))` |

---

*This document is maintained alongside the codebase. Last updated: June 2026.*
