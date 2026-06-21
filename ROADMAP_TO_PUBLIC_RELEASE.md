# Semptify Roadmap to Public Release

**Goal:** All roles fully developed (no stubs). All tiers working end-to-end. Module flag overlay system implemented. Dev system for new ideas. Then build a public GUI on solid mechanics.

**Philosophy:** Mechanics first, GUI second. A pretty GUI on broken mechanics will fail users.

---

## Roles Supported (from `app/core/user_context.py`)

| Role | Code | Status | Primary User |
|------|------|--------|--------------|
| **TENANT** | U | ✅ Most developed | Standard housing case user |
| **ADVOCATE** | V | ⚠️ Partial | Helps multiple tenants |
| **MANAGER** | M | ⚠️ Stub | Case manager — multi-client coordination |
| **LEGAL** | L | ⚠️ Stub | Attorneys, clerks, court staff |
| **ADMIN** | A | ✅ Developed | System admin — full access |
| **JUDGE** | J | 🚫 Not built | Judicial officer (future) |

## Tiers (from `app/core/product_manifest.py`)

| Tier | Status | Purpose |
|------|--------|---------|
| **CORE** | ✅ Active | Foundation: auth, vault, documents, timeline, search |
| **EXTENDED** | ✅ Active | Legal tools: eviction defense, court forms, case builder |
| **ADVOCATE** | ✅ Active | Collaboration: document delivery, comms, invite codes |
| **ADMIN** | ✅ Active | Dashboards, analytics, batch, registry |
| **RESEARCH** | ✅ Active | AI, overlays, brain, location, funding |
| **DEV** | ✅ Active | Internal tools: setup, editor, testing, docs |

---

## Phase 1 — Stabilize & Verify Current Mechanics (Week 1)

### 1.1 Deploy Current Fixes
- [ ] Deploy `1339b59` on Render (admin redirect loop fix)
- [ ] User logs out of admin and back in (get new cookie scoped to `/`)
- [ ] Verify admin dashboard loads once, no loop, no 429s
- [ ] Commit `BUILD_STATE.md` doc cleanup (rate limit note)

### 1.2 Module Health Audit
For each of the 75 registered modules:
- [ ] Hit every endpoint with test call (authenticated + unauthenticated)
- [ ] Log 500 errors, import errors, silent failures
- [ ] Verify Pydantic models match response shapes
- [ ] Confirm DI works (`get_db`, `get_current_user`, `require_admin`)
- [ ] Check `FunctionGroupContract` registrations match signatures

**Highest-risk modules (large route count, complex logic):**
- `briefcase` (49 routes), `admin_console` (41), `case_builder` (36), `storage` (31), `tenancy_hub` (26), `documents` (26)

### 1.3 Cross-Module Integration Verification
- [ ] **Upload → Timeline** — doc appears in `/api/timeline/unified`
- [ ] **Upload → Registry** — doc appears in `/api/registry/list`
- [ ] **Upload → Briefcase** — doc appears in briefcase
- [ ] **Case Builder → Timeline** — case creation emits timeline events
- [ ] **OAuth → Token Refresh** — auto-refresh on expiry
- [ ] **Admin Impersonation** — admin acts as tenant, scoped access
- [ ] **Document Delivery** — advocate sends doc → tenant inbox
- [ ] **Communication** — tenant messages advocate → thread
- [ ] **Overlay Create → Compose View** — highlight → composed view
- [ ] **Vault Init → Folder Structure** — new user → all folders created

### 1.4 Fix Known Stubs (from `STUB_AUDIT.md`)
- [ ] **`housing_accountability/router.py:83`** — Implement `detect_repeated_fees()`
- [ ] **`filedored_service.py:91`** — Wire AI classification OR document fallback as intentional
- [ ] **`state_laws/router.py`** — Add data for 5 priority states (NY, CA, TX, FL, IL)
- [ ] **`eviction/seed_court_data.py`** — Complete MN court seed data
- [ ] **MNDES `NotImplementedError` (3)** — Leave as-is (external API dependency)

### 1.5 Clean Up Legacy / Duplicate Files
- [ ] **Delete loose .py duplicates** (all have subdir equivalents):
  - `app/modules/case_builder.py`, `complaint_wizard_module.py`, `document_converter.py`, `research_module.py`, `free_api_pack.py`, `example_payment_tracking.py`, `legal_filing_module.py`
- [ ] **Decide on `local_ai/`** — Wire into product_manifest OR delete
- [ ] **Decide on `vault_installer/`** — Wire into product_manifest OR delete
- [ ] **Decide on INACTIVE modules:**
  - `plugins`, `components`, `auto_mode` — keep inactive, document
  - `litigation_intelligence` — fully retire OR build `graph_engine`

### 1.6 Register Missing FunctionGroupContracts
- [ ] `case_builder`, `fems`, `timeline_events`, `onboarding`, `documents`, `preamble`, `cloud_sync`, `tenancy_hub`, `briefcase`, `storage`

### 1.7 Test Suite Expansion
- [ ] Unit tests for each module's router
- [ ] Integration tests for cross-module flows
- [ ] Role-based tests — each role sees only what it should
- [ ] E2E Playwright tests for critical paths

---

## Phase 2 — Module Flag Overlay System (Week 2) ✅ COMPLETE

**Goal:** Extend `ModuleEntry` with a flag/metadata system so modules can be marked as `stable`, `beta`, `experimental`, `dev_only`, `preview`, `internal`. This replaces the binary "active/inactive" with a rich lifecycle.

### 2.1 Extend `ModuleEntry` (in `product_manifest.py`) ✅

Added new fields to `ModuleEntry`:
- `lifecycle` — `stable` | `beta` | `experimental` | `dev_only` | `preview` | `internal`
- `origin` — `internal` (first-party) | `external` (third-party)
- `requires_role` — tuple of roles allowed (empty = all)
- `requires_jurisdiction` — tuple of jurisdictions (empty = all)
- `requires_gate` — gate that must be set (e.g. `vault_initialized`)
- `feature_flag` — optional Feature enum value
- `dev_notes` — developer notes for unfinished work
- `external_repo`, `external_version`, `external_signature`, `external_sandbox` — external module fields

Validation in `__post_init__` enforces allowed values. Helper properties: `is_external`, `is_dev_only`, `is_preview`, `visibility_label`.

### 2.1a Internal vs External Module Distinction ✅

**Internal modules** (first-party, built by Semptify team):
- Live in `app/modules/`
- Have direct access to `app.core.*`, DB, Redis, other modules
- Registered in `product_manifest.py` with `origin="internal"`
- Examples: all current 75 registered modules

**External modules** (third-party, community-built):
- Live in `app/modules/external/<vendor>/<name>/`
- Cannot import `app.core.*` directly — only via `app.sdk.*`
- Must declare dependencies in manifest (no hidden imports)
- Run in sandboxed execution context (restricted permissions)
- Registered in `product_manifest.py` with `origin="external"`
- Signed with content hash — verified on load
- Examples: future plugin marketplace, partner integrations, community tools

### 2.2 Build `module_resolver.py` (new file in `app/core/`) ✅

Created `app/core/module_resolver.py` with:
- `resolve_modules(role, jurisdiction, gates, device)` — pure resolution function
- `resolve_modules_for_user(user_id, ...)` — Redis-cached version (5 min TTL)
- `is_module_allowed(module_path, ...)` — fast path for middleware
- `invalidate_user_cache(user_id)` — call on role/gate/flag change
- `invalidate_all_caches()` — call on lifecycle/flag bulk change
- `get_user_module_summary(role, ...)` — admin UI / debugging

Resolution order per module: lifecycle → role → jurisdiction → gate → feature_flag.
Fails open if Redis unavailable (falls back to uncached resolution).

### 2.3 Build `ModuleGateMiddleware` ✅

Integrated with existing `app/core/module_gate.py`:
- `ModuleAccess` dataclass extended with `resolved_module_paths: Set[str]`
- New method: `can_use_module_path(module_path)` — checks against resolver
- `ModuleGateMiddleware.dispatch` now calls `resolve_modules()` and populates `resolved_module_paths`
- Extracts gates from `request.state.onboarding_state` (storage_connected, vault_initialized)
- Fails open on resolver error (legacy behavior preserved)
- `get_module_access()` fallback populates `resolved_module_paths` from MANIFEST

### 2.4 Build `ModuleFlagOverlay` Admin UI

- New admin page: `/admin/module-flags`
- Lists every module with its lifecycle, role requirements, gate, feature flag
- Admin can toggle lifecycle, feature flags, role requirements
- Shows which users currently have access to each module
- "Test as user" button — preview what a specific user sees

### 2.5 Tag All Existing Modules with Lifecycle ✅

Tagged 92 modules in `product_manifest.py`:
- 82 stable (production-ready)
- 4 beta: `state_laws` (only MN), `mndes` (3 NotImplementedError), `housing_accountability` (2 routers with stubs)
- 5 experimental: `brain`, `emotion`, `positronic_mesh`, `mesh_network`, `module_hub` (heavy AI services, feature-flagged)
- 1 dev_only: `functionx` (concept not yet defined)

INACTIVE modules remain commented out (plugins, components, auto_mode, litigation_intelligence) — will be tagged when registered.

---

## Phase 3 — Dev System for Internal + External Ideas (Week 2-3)

**Goal:** A structured workflow for developing new ideas — both **internal** (first-party) and **external** (third-party) — without breaking production. New ideas start as `dev_only`, progress through `experimental` → `beta` → `stable` as they mature.

### 3.1 Internal Ideas (First-Party, Built by Us)

#### 3.1a Dev Tier Expansion — Incubator

Expand the DEV tier to be the **incubator** for new internal ideas:
- [ ] **`app/modules/dev_lab/`** — Dev experiments hub
  - `/dev/lab` — List of all `dev_only` modules (internal + external)
  - `/dev/lab/{module}` — Sandbox page for a specific dev module
  - `/dev/lab/{module}/test` — Run module's test suite
  - `/dev/lab/{module}/status` — Show module's maturity checklist
  - `/dev/lab/{module}/promote` — Request promotion to next lifecycle stage
- [ ] **`app/modules/dev_sandbox/`** — Isolated execution environment
  - Each dev module gets its own DB schema prefix (`dev_<module>_`)
  - Errors in dev modules don't affect production modules
  - Automatic cleanup of dev data after 24h
  - Resource limits: 50MB DB, 10MB RAM, 30s request timeout

#### 3.1b Internal Idea Pipeline

Idea → Spec → Dev Module → Experimental → Beta → Stable

1. **Idea submitted** — `/dev/ideas/new` form (any team member)
2. **Spec written** — `dev_ideas` table stores: name, description, target role, tier, dependencies, success criteria
3. **Module created** — Admin promotes idea → scaffold from `_template/`
4. **Dev module built** — Coded at `dev_only` lifecycle, only visible to admin
5. **Tests written** — Unit + integration tests required to reach `experimental`
6. **Dogfooded** — Team uses it internally, reaches `beta`
7. **Released** — Real users get access, reaches `stable`

### 3.2 External Ideas (Third-Party, Community-Built)

#### 3.2a External Module Architecture

External modules let third parties extend Semptify without touching core:

- [ ] **`app/modules/external/<vendor>/<name>/`** — External module storage
- [ ] **`app/sdk/external/`** — Public SDK for external developers
  - `vault_client` — Vault access via SDK contract
  - `timeline_client` — Timeline event creation
  - `overlay_client` — Overlay system access
  - `document_client` — Document access (read-only by default)
  - `notification_client` — Send notifications to users
  - **No access** to: DB directly, Redis directly, other modules' internals, user PII
- [ ] **`app/core/external_loader.py`** — External module loader
  - Verifies module signature (content hash)
  - Loads module in sandboxed execution context
  - Enforces permission boundaries
  - Reports permission violations to admin console

#### 3.2b External Module Manifest

Each external module ships a `semptify.module.json` manifest:
```json
{
  "name": "court-forms-ny",
  "vendor": "legalaid-ny",
  "version": "1.0.0",
  "description": "NY court forms integration",
  "lifecycle": "beta",
  "requires_role": ["tenant", "advocate"],
  "requires_jurisdiction": ["NY"],
  "requires_gate": "vault_initialized",
  "permissions": ["vault.read", "timeline.write", "overlay.write"],
  "dependencies": ["app.sdk.vault", "app.sdk.timeline"],
  "entry_point": "router.py:router",
  "content_hash": "sha256:...",
  "homepage": "https://github.com/legalaid-ny/semtify-court-forms-ny",
  "support": "support@legalaid-ny.org",
  "license": "MIT"
}
```

#### 3.2c External Permission System

External modules run with **least privilege**. Permissions must be declared in manifest and approved by admin:

| Permission | Description |
|------------|-------------|
| `vault.read` | Read user's vault files |
| `vault.write` | Upload/modify vault files |
| `timeline.read` | Read timeline events |
| `timeline.write` | Create timeline events |
| `overlay.read` | Read overlays |
| `overlay.write` | Create/modify overlays |
| `document.read` | Read document content |
| `document.write` | Upload/modify documents |
| `notification.send` | Send notifications to user |
| `user.profile.read` | Read user profile (name, role) |
| `user.contacts.read` | Read user's contacts |

**Forbidden for external modules:**
- Direct DB access
- Direct Redis access
- Access to other modules' internals
- Access to user PII beyond declared permissions
- Network calls to non-declared domains
- File system access outside sandbox

#### 3.2d External Module Lifecycle

1. **Submitted** — Developer submits module via `/dev/external/submit`
2. **Reviewed** — Admin reviews manifest, permissions, code
3. **Sandboxed** — Module runs in `dev_only` mode, admin only
4. **Tested** — Admin runs module's test suite, verifies permissions
5. **Approved** — Module promoted to `experimental`, visible to admin + opt-in users
6. **Beta** — Module promoted to `beta`, visible to users with `beta_dashboard` flag
7. **Stable** — Module promoted to `stable`, visible to all applicable roles
8. **Revoked** — Admin can revoke at any time (signature mismatch, permission violation, user reports)

### 3.3 Module Maturity Checklist (Internal + External)

Each module must pass this checklist to progress from `dev_only` → `experimental` → `beta` → `stable`:

- [ ] **dev_only** — Just code, no tests, no docs. Admin-only visibility.
- [ ] **experimental** — Has unit tests, has basic docs, works in isolation. Admin + opt-in.
- [ ] **beta** — Has integration tests, has user docs, works with other modules, registered in `FunctionGroupContract`. Admin + beta-flag users.
- [ ] **stable** — Has E2E tests, has admin docs, used by real users, monitored for errors. All applicable roles.

### 3.4 Dev Module Template (Internal)

Create `app/modules/_template/` as a starting point for new internal ideas:
- `router.py` — Skeleton with health check + CRUD endpoints
- `__init__.py` — Exports
- `models.py` — Pydantic models
- `service.py` — Business logic
- `tests/` — Unit + integration test stubs
- `README.md` — Module description, maturity checklist
- `register.py` — `register_module()` function

### 3.5 External Module Template (External)

Create `app/sdk/external/_template/` as a starting point for external developers:
- `router.py` — Skeleton using only `app.sdk.*` imports
- `semptify.module.json` — Manifest template
- `models.py` — Pydantic models (no DB models)
- `tests/` — Test stubs
- `README.md` — Developer guide, permission reference
- `examples/` — Example integrations

### 3.6 Idea Submission Workflow (Internal + External)

- [ ] **`/dev/ideas`** — Page where anyone can submit a new idea
- [ ] **Idea form fields:**
  - Name, description, target role, target tier
  - Internal or external
  - Dependencies (which SDK clients, which modules)
  - Success criteria
  - Mockups/screenshots (optional)
- [ ] **Idea stored in `dev_ideas` table** with `origin` field (`internal` or `external`)
- [ ] **Admin can promote idea:**
  - Internal → scaffold from `_template/`, assign developer
  - External → generate SDK template package for developer
- [ ] **Module starts at `dev_only` lifecycle**
- [ ] **Progress tracked through maturity checklist**
- [ ] **Public idea board** — Users can upvote ideas they want (future)

### 3.7 External Marketplace (Future, Post-Release)

- [ ] **`/marketplace`** — Browse external modules
- [ ] **Categories** — Legal forms, analytics, integrations, utilities
- [ ] **Reviews + ratings** — Users review external modules
- [ ] **Install flow** — User clicks "Install" → admin approves → module activated
- [ ] **Revenue share** — Optional, paid external modules (post-funding)
- [ ] **Security audit** — All external modules audited before listing

### 3.8 Module Visibility Rules (Internal + External)

| Lifecycle | Visible To |
|-----------|------------|
| `dev_only` | Admin only |
| `experimental` | Admin + users with `experimental_ui` flag |
| `beta` | Admin + users with `beta_dashboard` flag |
| `stable` | All roles per `requires_role` |
| `internal` | Same as lifecycle — first-party, trusted |
| `external` | Same as lifecycle — third-party, sandboxed |

### 3.9 Dev Module Dashboard

- [ ] **`/dev/dashboard`** — Developer dashboard (admin only)
- [ ] **Lists all modules** with: name, origin (internal/external), lifecycle, health, test status
- [ ] **Filter by:** origin, lifecycle, tier, role, health
- [ ] **Actions:** promote, demote, revoke, test, view sandbox, view logs
- [ ] **Metrics:** active users, error rate, latency, test coverage
- [ ] **Alerts:** permission violations, signature mismatches, test failures

---

## Phase 4 — Role Development Completion (Week 3-4)

**Goal:** Every role has a complete, working feature set. No role sees broken buttons or 501s.

### 4.1 TENANT Role (✅ Mostly done)

**Already works:**
- Onboarding → storage → vault → upload → timeline
- Case builder, complaints, court forms
- Law library, state laws (MN only)
- Messages with advocate
- Document delivery inbox

**Stubs to fix:**
- [ ] `state_laws` — Add 5 priority states (NY, CA, TX, FL, IL)
- [ ] `housing_accountability` — Implement `detect_repeated_fees()`
- [ ] Verify all tenant-visible endpoints return 200

### 4.2 ADVOCATE Role (⚠️ Partial)

**Already works:**
- Document delivery, communication, invite codes
- Everything tenant has

**Stubs to fix:**
- [ ] **Advocate dashboard** — Verify `/advocate` page loads with real data
- [ ] **Client list** — Advocate sees list of tenants they're helping
- [ ] **Case sharing** — Tenant can share case with advocate
- [ ] **Document review** — Advocate can annotate tenant docs (overlays)
- [ ] **Invite flow** — Advocate sends invite code → tenant onboarded to advocate's network
- [ ] **Multi-tenant view** — Advocate sees all their tenants' timelines

### 4.3 MANAGER Role (⚠️ Stub)

**Currently:** `manager_dashboard.html` exists but minimal. `manager_dashboard.py` has some functions.

**Build out:**
- [ ] **Manager dashboard** — `/manager` page with team overview
- [ ] **Staff management** — Manager sees list of advocates in their org
- [ ] **Case assignment** — Manager assigns cases to advocates
- [ ] **Reporting** — Manager sees aggregate metrics across advocates
- [ ] **Bulk operations** — Manager can reassign cases, export data
- [ ] **Permissions** — Manager can only see their org's data

### 4.4 LEGAL Role (⚠️ Stub)

**Currently:** `legal.html` exists but minimal. `CONTRACT_LEGAL` in `page_contracts.py` defines `/legal` route.

**Build out:**
- [ ] **Legal workspace** — `/legal` page with case list
- [ ] **Court filing** — Legal role can file with courts (when MNDES API ready)
- [ ] **Discovery management** — Legal role manages discovery docs
- [ ] **Case files** — Legal role has private case file storage
- [ ] **Court exhibits** — Legal role manages MNDES exhibits
- [ ] **Legal-specific overlays** — Attorney-client privilege annotations
- [ ] **Judge interface** (future) — Separate role with case oversight

### 4.5 ADMIN Role (✅ Developed)

**Already works:**
- Admin console, analytics, batch, registry, capabilities
- Impersonation, Fix-It button, error queue

**Stubs to fix:**
- [ ] Deploy redirect loop fix
- [ ] Verify all 41 admin console endpoints return 200
- [ ] Module flag overlay UI (Phase 2.4)

### 4.6 JUDGE Role (🚫 Not built)

**Future role.** Build only when court integration is real.
- [ ] **Judge workspace** — `/judge` page with case docket
- [ ] **Case oversight** — Judge sees all cases in their jurisdiction
- [ ] **Ruling templates** — Judge can generate ruling templates
- [ ] **Exhibit review** — Judge reviews MNDES exhibits

**For now:** Mark as `dev_only` in module flags. Don't build until courts request it.

---

## Phase 5 — Cross-Role Integration (Week 4)

**Goal:** All roles interact correctly. Data flows between roles as expected.

### 5.1 Role Transition Workflows
- [ ] **Tenant → Advocate** — Tenant invites advocate, advocate accepts
- [ ] **Advocate → Manager** — Advocate joins manager's org
- [ ] **Manager → Legal** — Manager escalates case to legal
- [ ] **Legal → Judge** — Legal files with court, judge assigned
- [ ] **Admin → Any** — Admin impersonates any role for support

### 5.2 Shared Data Workflows
- [ ] **Case sharing** — Tenant shares case with advocate, advocate shares with manager
- [ ] **Document sharing** — Doc uploaded by tenant, visible to advocate, annotated by legal
- [ ] **Timeline sharing** — All roles see the same timeline for a case
- [ ] **Overlay sharing** — Advocate's overlays visible to tenant, manager, legal
- [ ] **Communication threads** — Tenant ↔ Advocate ↔ Manager ↔ Legal

### 5.3 Permission Boundaries
- [ ] **Tenant** — Only sees their own data
- [ ] **Advocate** — Sees data for tenants in their network
- [ ] **Manager** — Sees data for advocates in their org
- [ ] **Legal** — Sees data for cases they're assigned to
- [ ] **Admin** — Sees everything, can impersonate
- [ ] **Judge** — Sees cases in their jurisdiction (future)

---

## Phase 6 — Public GUI Development (Week 5-8)

**Goal:** Build a polished, accessible, mobile-first GUI on top of the verified mechanics.

### 6.1 GUI Design Principles
- **Mobile-first** — Tenants are stressed, often on phones
- **Accessibility** — WCAG 2.1 AA minimum
- **Plain language** — No legal jargon when possible
- **Progressive disclosure** — Show only what's needed now
- **Role-aware** — UI adapts to role without separate codebases
- **Offline-tolerant** — Queue actions when offline, sync when online

### 6.2 GUI Architecture
- [ ] **Choose framework** — React (recommended) or continue with Jinja2 templates
- [ ] **Design system** — Component library, color tokens, typography
- [ ] **Role router** — Single entry point that routes to role-specific dashboard
- [ ] **Module loader** — Dynamically load modules based on `resolve_modules()`
- [ ] **State management** — Zustand or Redux Toolkit
- [ ] **API client** — Typed client from `FunctionGroupContract` registry

### 6.3 Tenant GUI (Priority 1)
- [ ] **Onboarding** — Welcome → role → storage → vault (current flow, polished)
- [ ] **Dashboard** — Today's tasks, recent docs, timeline preview
- [ ] **Vault** — File browser with preview, upload, organize
- [ ] **Timeline** — Visual timeline with filters
- [ ] **Case Builder** — Step-by-step case wizard
- [ ] **Messages** — Threaded conversation with advocate
- [ ] **Library** — Law library with search
- [ ] **Help** — Contextual help, Fix-It button

### 6.4 Advocate GUI (Priority 2)
- [ ] **Client list** — All tenants advocate is helping
- [ ] **Client detail** — Tenant's vault, timeline, case
- [ ] **Document review** — Annotate tenant docs with overlays
- [ ] **Invite** — Send invite codes
- [ ] **Messages** — All conversations with tenants

### 6.5 Manager GUI (Priority 3)
- [ ] **Team overview** — All advocates, their caseloads
- [ ] **Case assignment** — Drag-and-drop case assignment
- [ ] **Reports** — Aggregate metrics, export

### 6.6 Legal GUI (Priority 4)
- [ ] **Case docket** — All assigned cases
- [ ] **Filing** — Court filing interface (when MNDES ready)
- [ ] **Discovery** — Discovery doc management

### 6.7 Admin GUI (Priority 5)
- [ ] **Module flags** — Toggle module lifecycle, roles, gates
- [ ] **User management** — List, edit, impersonate
- [ ] **System health** — Logs, metrics, error queue
- [ ] **Feature flags** — Toggle features, rollout %

### 6.8 Public Landing Page (Priority 6)
- [ ] **Homepage** — What Semptify is, who it's for
- [ ] **Get started** — Role selection → onboarding
- [ ] **Resources** — Law library, state laws (public)
- [ ] **About** — Mission, team, funding

---

## Phase 7 — Testing & Release (Week 8-9)

### 7.1 Testing
- [ ] **Unit tests** — 90%+ coverage on all modules
- [ ] **Integration tests** — All cross-module flows
- [ ] **E2E tests** — Playwright for all role workflows
- [ ] **Load tests** — Simulate 100 concurrent users
- [ ] **Security tests** — OWASP top 10, pen test
- [ ] **Accessibility audit** — WCAG 2.1 AA
- [ ] **Mobile testing** — iOS, Android, various screen sizes

### 7.2 Release
- [ ] **Staging environment** — Deploy to staging, test with real users
- [ ] **Beta program** — 10-20 tenants, 2-3 advocates
- [ ] **Feedback loop** — Fix-It button captures all issues
- [ ] **Public release** — semptify.org homepage, onboarding open

---

## Execution Order

**Start with Phase 1.1** (deploy current fixes) — nothing else matters if the admin dashboard is broken.

**Then Phase 2** (module flag overlay) — this unlocks the ability to tag modules as `dev_only` without breaking production.

**Then Phase 3** (dev system) — gives us a structured way to develop new ideas.

**Then Phase 4** (role development) — fill in the stubs for each role.

**Then Phase 5** (cross-role integration) — make sure roles interact correctly.

**Then Phase 6** (GUI) — build the public face on solid mechanics.

**Then Phase 7** (testing & release) — verify everything works, release to public.

---

## What We Work On Next Session

1. **Deploy `1339b59`** on Render
2. **Verify admin dashboard** no longer loops
3. **Start Phase 2.1** — Extend `ModuleEntry` with `lifecycle`, `requires_role`, `requires_jurisdiction`, `requires_gate`, `feature_flag`, `dev_notes` fields
4. **Start Phase 2.2** — Build `app/core/module_resolver.py`
5. **Start Phase 2.3** — Build `ModuleGateMiddleware`

This gives us the foundation to tag all modules with their maturity level and build the dev system for new ideas.
