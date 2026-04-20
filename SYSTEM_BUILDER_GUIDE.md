# Semptify System Builder's Guide
## Single Source of Truth for Development

This guide provides the authoritative reference for building, extending, and integrating with the Semptify system.

> **Mandate Compliance**: This guide follows the mandates defined in:
> - `AGENTS.md` — Core mission, non-negotiables, truth standard, architecture preferences
> - `SECURITY_AND_PRIVACY_ARCHITECTURE.md` — Privacy by design, no tracking, user-controlled storage
> - `PROJECT_BIBLE.md` — Documentation hierarchy and governance
>
> All development must align with: free forever, no ads, privacy by design, evidence preservation, and calm UX for stressed users.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Privacy & Security Requirements](#2-privacy--security-requirements)
3. [Routing System (Single Source of Truth)](#3-routing-system-single-source-of-truth)
4. [Module System](#4-module-system)
5. [Template System](#5-template-system)
6. [Adding New Features](#6-adding-new-features)
7. [Integration Patterns](#7-integration-patterns)
8. [Plain Language Glossary](#8-plain-language-glossary)
9. [Mesh Resource Mode Policy](#9-mesh-resource-mode-policy)
10. [Mesh Integration Patterns](#10-mesh-integration-patterns)

---

## 1. System Architecture Overview

### 1.1 Core Principle: Workflow-Driven Architecture

Semptify uses a **workflow-driven architecture** where all user journeys are defined as workflows. The system evaluates user state and determines the correct next step through the workflow engine.

**Key Rule**: Never hardcode redirect URLs. Always use `route_user()` from `workflow_engine.py`.

### 1.2 Architecture Preferences (per AGENTS.md)

- **Prefer** objects, qualifiers, functions, sequences, processes, and output objects as the structural model
- **Treat pages as UI surfaces** generated from process needs, not as the deepest source of truth
- **Keep policy and transition logic centralized** (in workflow_engine.py) rather than duplicated across routers or templates
- **Favor strict serial gating** for high-stakes workflows where later steps must not run before earlier steps complete
- **Build for facts, records, chronology, and evidence** — do not assume either tenant or landlord claims are automatically true

### 1.3 Layer Hierarchy

```
PRESENTATION LAYER      - Jinja2 Templates (app/templates/)
                        - Static HTML (static/)
                        - API Response Models

APPLICATION LAYER       - FastAPI Routers (app/routers/)
                        - Route Guards (main.py)
                        - Request/Response Handlers

WORKFLOW LAYER          - workflow_engine.py (Single Source of Truth)
                        - evaluate() function
                        - route_user() function
                        - Centralized policy logic

SERVICE LAYER           - app/services/ (Business logic)
                        - app/core/ (Core utilities)
                        - Module SDK

DATA LAYER              - SQLAlchemy Models
                        - Async Database Operations
                        - Cloud Storage (User-controlled only)

---

## 2. Privacy & Security Requirements

Per `SECURITY_AND_PRIVACY_ARCHITECTURE.md`:

**Security Purpose**: Security checks exist solely to verify that **users can access their own files** and **save documents to their own storage**. Semptify never inspects, controls, or analyzes user content. Security is for user benefit — never for surveillance, tracking, or data collection.

### 2.1 Non-Negotiable Rules

| Rule | Implementation |
|------|----------------|
| **Security Purpose** | Users access their own files only — never surveillance or inspection |
| **Stateless System** | No user state maintained server-side between requests |
| **No user registration** | Users authenticate via OAuth to their own storage |
| **No activity tracking** | No analytics, no logging of user actions |
| **No IP logging** | Location tracking disabled |
| **No personal data storage** | Store only minimal IDs, no names/emails/phones |
| **User data separation** | **ABSOLUTE: Zero user data in Semptify systems — NO EXCEPTIONS** |
| **User-controlled documents** | All docs in user's cloud (Google Drive, Dropbox, etc.) |
| **Encryption** | AES-256-GCM for all tokens |
| **System Storage** | R2 (Cloudflare R2) — **SYSTEM USE ONLY, NEVER USER DATA** |

### 2.2 Data Architecture

**ABSOLUTE RULE**: Under no circumstances does user data exist in Semptify infrastructure.

```
USER DATA FLOW:
═══════════════
User Documents → User's Cloud Storage ONLY (Google Drive, Dropbox, OneDrive)
                        ↓
                (via OAuth 2.0)
                        ↓
    Semptify → Stateless processing → Memory only → Immediate discard

SYSTEM DATA (R2):
═════════════════
R2 Storage → System configuration, code, templates
           → NEVER user documents
           → NEVER user metadata
           → NEVER case information
```

### 2.3 Stateless Design

Semptify is **stateless**:
- No server-side sessions
- No cached user state between requests
- Each request is independent
- User identity carried only via signed cookie
- No session storage in database

### 2.4 Data Flow Rules

```
User Documents → User's Cloud Storage ONLY
                    ↓
            (via OAuth 2.0)
                    ↓
Semptify → Temporary processing only → No storage
```

**Never:**
- Store documents locally on server
- Cache user data longer than the request
- Log document contents
- Send data to third-party services (except user's chosen cloud)

**Always:**
- Use user's own storage via OAuth
- Process data in memory only
- Clear data after processing
- Respect user control over their storage
```

---

## 3. Routing System (Single Source of Truth)

### 3.1 The Rule: One Function for All Routing

**File**: `app/core/workflow_engine.py`

**Function**: `route_user(user_id: str, documents_present: bool = False, has_active_case: bool = False) -> str`

This is the **only** function that determines where a user should be redirected. All other code must call this function.

### 3.2 How It Works

```python
from app.core.workflow_engine import route_user

# Correct way to redirect:
user_id = "usr_abc123"
redirect_url = route_user(user_id)  # Returns: "/tenant/documents"
return RedirectResponse(url=redirect_url, status_code=302)
```

### 3.3 URLs by Role

| Role Prefix | URL Path | Purpose |
|-------------|----------|---------|
| `usr_` | `/tenant/documents` | Tenant document management |
| `adv_` | `/advocate` | Advocate dashboard |
| `leg_` | `/legal` | Legal professional dashboard |
| `adm_` | `/admin` | Admin dashboard |
| `mgr_` | `/admin` | Manager dashboard |

### 3.4 Required Usage Locations

- `app/routers/storage.py` - After OAuth callback
- `app/routers/storage.py` - storage_home() for authenticated users
- `app/main.py` - _guard_role_page() for role mismatches
- Any code that redirects based on user role

---

## 4. Module System

### 4.1 Module Registration Pattern

```python
from app.sdk.module_sdk import ModuleSDK

MODULE_NAME = "my_module"
MODULE_VERSION = "1.0.0"

sdk = ModuleSDK(
    module_name=MODULE_NAME,
    version=MODULE_VERSION,
    description="Module description"
)

@sdk.action("my_action")
async def my_action_handler(params: dict) -> dict:
    return {"status": "success", "data": ...}

module_sdk = sdk
```

### 4.2 Module File Structure

```
app/modules/
├── __init__.py
└── my_module/
    ├── __init__.py          # Exports module_sdk
    ├── handlers.py          # Action handlers
    ├── models.py            # Pydantic models
    └── README.md            # Module documentation
```

---

## 5. Template System

### 5.1 Template Inheritance

All templates must extend `base.html`:

```html
{% extends "base.html" %}
{% block title %}Page Title{% endblock %}
{% block content %}
<div class="container">
    <h1>Content</h1>
</div>
{% endblock %}
```

### 5.2 Template Organization

```
app/templates/
├── base.html                    # Base template
├── components/                  # Reusable components
├── pages/                       # Page templates
├── partials/                    # Partial templates
└── legal/                       # Legal-specific
```

---

## 6. Adding New Features

### 6.1 Feature Development Checklist

**Step 1: Define the workflow**
- Add workflow step in `workflow_engine.py` if needed
- Add route mapping in `PROCESS_ROUTES`
- Test routing with `route_user()`

**Step 2: Create the router**
- Create file in `app/routers/`
- Use `route_user()` for all redirects
- Add guard using `_guard_role_page` pattern

**Step 3: Create templates**
- Extend `base.html`
- Use CSS variables from design system
- Follow responsive patterns

**Step 4: Register module (if needed)**
- Create module in `app/modules/`
- Register with Module Hub

**Step 5: Test**
- Verify routing through `route_user()`
- Test role-based access
- Test mobile responsiveness

---

## 7. Integration Patterns

### 7.1 Adding a New Router

```python
# app/routers/my_feature.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.workflow_engine import route_user

router = APIRouter(prefix="/my-feature")

@router.get("/")
async def my_feature_page(request: Request):
    # Get user from cookie
    user_id = request.cookies.get("semptify_uid")
    
    # Guard: Use route_user() for redirect if needed
    if not user_id:
        return Redirect(url="/storage/providers")
    
    return HTMLResponse(content="...")
```

### 7.2 Adding a New Template

```html
<!-- app/templates/pages/my_feature.html -->
{% extends "base.html" %}

{% block title %}My Feature - Semptify{% endblock %}

{% block content %}
<div class="container">
    <div class="card">
        <h1>My Feature</h1>
        <p class="text-secondary">Description here</p>
        <button class="btn btn--primary">Action</button>
    </div>
</div>
{% endblock %}
```

### 7.3 Connecting Router to Main App

```python
# In app/main.py
from app.routers import my_feature
fastapi_app.include_router(my_feature.router, tags=["My Feature"])
```

---

## 8. Plain Language Glossary

Use this section as the shared language for planning and implementation.

- **Page**: A screen the user can open (for example, dashboard, documents, timeline).
- **Route**: The URL path that opens a page (for example, `/timeline`).
- **Page Identity**: The basic ID card for a page: page ID, route, owner module, and supported roles.
- **Page Contract**: The page's rules: who can access it, what process groups it covers, entry/exit criteria, and telemetry events.
- **Process Group**: One of the 8 core job areas in Semptify (welcome, security, documentation, research, actions, output, help, admin/monitoring).
- **Route Guard**: The gate check before loading a page (valid user, role allowed, storage state valid).
- **Single Source of Truth (SSOT)**: One official place for a rule or data definition; no duplicated competing versions.
- **Data Source Contract**: Declaration of where page data comes from (DB model, cloud path, API) and what is authoritative.
- **Module**: A feature engine (for example, timeline, documents, calendar, forms).
- **Module Hub**: The central registry that tracks modules, status, and integration visibility.
- **Function Group**: A named bundle of related backend logic inside a module.
- **Function Group Contract**: Standard definition of a function group (inputs, outputs, dependencies, deterministic behavior).
- **Action**: One callable module operation (for example, `timeline.build_case_timeline`).
- **Action Set**: The collection of actions available for a workflow or page.
- **Positronic Mesh**: The action execution and routing layer that registers and invokes module actions.
- **Binding**: A declared connection between objects (for example, page -> module, page -> actions, page -> data source).
- **Page Manifest**: Master inventory of all pages and their required object-set wiring.
- **Telemetry**: Operational events used for monitoring behavior and system health.
- **Coverage**: How much of the required process behavior a page implements (`active`, `linked`, `guarded`, `n-a`).
- **Gap**: Missing required wiring (for example, page exists but no contract, guard, action map, or module binding).

---

## 9. Mesh Resource Mode Policy

This policy keeps development velocity high while protecting system integrity and resource usage.

### 9.1 Current Default: Lean Mesh Mode

Until the dataset and traffic justify deeper orchestration, run the Positronic Mesh in a lower-intensity profile:

- Prioritize deterministic, high-value actions only.
- Defer non-critical or duplicate action chains.
- Keep page contracts, workflow routing, and module contracts as the control plane.
- Avoid speculative fan-out action execution on normal requests.

**Implementation:**
- Configuration: `app/core/mesh_config.py` — `LEAN_MESH_CONFIG` vs `FULL_MESH_CONFIG`
- Mode switching: `set_mesh_mode("lean")` or `set_mesh_mode("full")`
- Deferred modules in lean mode: `fraud_exposure`, `public_exposure`, `research`, `legal_trails`, `adaptive_ui`, `context_engine`

### 9.2 What Must Stay Enabled (Integrity Guardrails)

These are never optional, even in Lean Mesh Mode:

- `route_user()` as the only routing source of truth.
- Route guards for role/storage validation.
- Canonical vault path constants from `app/core/vault_paths.py`.
- Registered module contracts for core mechanics (upload, overlay, timeline, workflow-critical services).
- Contract and health visibility endpoints (`/hub/contracts`, `/hub/contracts/health`).

### 9.3 Fast-Advance Rules

To move fast without breaking trust:

- Ship in small vertical slices (feature + guard + contract + health check).
- Prefer additive registration over broad rewrites.
- Keep timeline/workflow outputs deterministic.
- Do not introduce local fallbacks for user document storage.
- If a module is optional, fail soft; if core mechanics are affected, fail loud with clear errors.

### 9.4 Scale-Up Triggers (When to Raise Mesh Intensity)

Increase mesh depth only when at least two of these are true:

- Sustained traffic requires orchestration throughput improvements.
- Action coverage gaps are contract-defined and test-backed.
- Observability indicates stable low error rates in core workflows.
- Dataset breadth supports richer cross-module execution value.

### 9.5 Operating Principle

**Move fast, but never bypass truth, evidence integrity, privacy boundaries, or deterministic routing/contracts.**

### 9.6 Action Deferral System

When an action is skipped in lean mode, it is recorded for potential retry:

- **Queue:** `app/core/mesh_deferral.py` — `ActionDeferralQueue`
- **Recording:** Automatic on skipped actions in `_execute_step()` and `invoke_module()`
- **Retry:** Call `deferral_queue.retry_all(positronic_mesh)` after switching to full mode

### 9.7 Mesh Control API

Monitor and control mesh intensity via module hub endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/hub/mesh/status` | GET | Get current mode, deferred modules, queue status |
| `/hub/mesh/mode` | POST | Switch mode (`lean` or `full`) |
| `/hub/mesh/deferrals` | GET | View pending deferred actions |
| `/hub/mesh/retry-deferred` | POST | Retry all deferred actions (full mode only) |

---

## 10. Mesh Integration Patterns

### 10.1 Auto-Triggered Workflows

The mesh now automatically triggers workflows from user actions:

**Document Upload Flow:**
1. User uploads document to `/vault/upload`
2. System creates overlay and extracts timeline (standalone)
3. **Mesh triggers workflow** based on document type:
   - `eviction_notice` → `EVICTION_DEFENSE` workflow
   - `lease` → `LEASE_ANALYSIS` workflow
   - `hearing_notice` → `COURT_PREP` workflow
4. Workflow executes via mesh action chain

**Integration Point:** `app/routers/vault.py` — mesh workflow trigger added after upload success.

### 10.2 Timeline as Mesh Action

Timeline extraction is now available as a mesh-orchestrated step:

- **Action:** `timeline.extract_from_document`
- **Registration:** `app/services/module_actions.py`
- **Workflow Integration:** Called automatically in `EVICTION_DEFENSE` and `LEASE_ANALYSIS` workflows

### 10.3 Process Detection for Auto-Routing

The mesh can detect user state and recommend routing:

- **Action:** `process_detection.detect_current_process`
- **Input:** Document state, eviction state, timeline state
- **Output:** `detected_process`, `process_urgency`, `routing_destination`

Use this for automatic stage progression without hardcoded redirects.

---

## Quick Reference

### Essential Imports

```python
# Routing
from app.core.workflow_engine import route_user

# Database
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Models
from app.models import User

# Security
from app.core.security import require_user

# Templates
from fastapi.responses import HTMLResponse, RedirectResponse
```

### Essential File Locations

| Component | Location |
|-----------|----------|
| Routing Logic | `app/core/workflow_engine.py` |
| Main App | `app/main.py` |
| Routers | `app/routers/` |
| Models | `app/models.py` |
| Templates | `app/templates/` |
| Static Files | `static/` |
| Modules | `app/modules/` |
| Services | `app/services/` |

---

*This guide is the single source of truth for Semptify development. All features must follow these patterns.*
