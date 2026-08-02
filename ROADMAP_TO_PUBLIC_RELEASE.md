# Semptify Roadmap to Public Release

**Last Updated**: 2026-06-29 PM
**Philosophy:** Mechanics first, GUI second. A pretty GUI on broken mechanics will fail users.

---

## ✅ COMPLETED

### Phase 4 — Role Development (2026-06-24)

All 6 roles have full endpoint coverage:

- **TENANT** — 41 endpoints
- **ADVOCATE** — 14 endpoints
- **MANAGER** — 10 endpoints (tenant-side advocate, NOT property manager)
- **LEGAL** — 27 endpoints (attorney + judge + clerk + paralegal sub-roles)
- **ADMIN** — 41+ endpoints
- **JUDGE** — merged into Legal as sub-role (is_legal_sub_role)

### Phase 5a — Context Engine + Page Composer (2026-06-24 PM)

- 9 context endpoints (`/api/context/*`)
- 3 page composer endpoints (`/api/page/*`)
- 4 consumers wired (Case Builder, Complaint Wizard, Tenant Defense, Page Composer)
- DB migration shipped (`context_facts`, `tenant_stories`)

### Litigation Intelligence Module (2026-06-24)

- 17 endpoints live at `/api/litigation-intelligence/*`

### Unified Overlay System (2026-04-21)

- Full CRUD for overlays in user cloud storage
- Filedored integration fixed 2026-06-29 (commit 19d0860)

### Semptify Forge — Canonical Dev System (2026-06-23)

- `/admin/forge.html` — module lifecycle pipeline (dev_only → preview → experimental → beta → stable)
- Admin runtime overrides persisted in PostgreSQL

### Vault SDK (2026-05-16)

- `app/sdk/vault/` — isolated, reusable vault management
- Pre-built specs: TENANT_VAULT, ADVOCATE_VAULT, LEGAL_VAULT, RESEARCH_VAULT

---

## 🅿️ NEXT TO BUILD (in priority order)

### 1. Phase 5b — Action Feedback Helper 🎯 CURRENT PRIORITY

**Design doc:** `ACTION_FEEDBACK_AUDIT.md`
**Status:** Ready to build, no blockers

Build the `SemptifyFeedback` helper and 5-tier retrofit per the audit doc.

### 2. GUI Phase 1 — Tenant Journal Restructuring

**Design doc:** `GUI_PHASE1_DESIGN.md`
**Status:** Pending

Per user's canonical vision (2026-06-28):

- **JOURNAL** = input vessel (personal narrative attached to document/event/personal statement)
- **CALENDAR** = total recollection viewer (graphical/media, shows everything in tenancy)
- **TIMELINE** = interactive data query viewer (vertical mobile / horizontal desktop, color-coded, filterable)

### 3. Document Center Planning

**Design doc:** `docs/planning/DOCUMENT_CENTER_PLAN.md`
**Status:** Pending

Design docs committed 2026-06-29:

- `DC_DESIGN_SONNET.md`, `DC_HANDOFF_SONNET.md`, `DOCUMENT_CENTER_PLAN.md`

---

## 🚫 ANTI-PRIORITIES (Don't Start These)

1. New features that aren't Action Feedback, GUI Phase 1, or DC planning
2. Refactoring unrelated to Phase 5
3. Documentation that isn't critical path
4. Testing of non-core systems

---

## 📋 Canonical Docs (per PROJECT_BIBLE.md hierarchy)

1. `PROJECT_BIBLE.md` — project governance, doc hierarchy
2. `README.md` — canonical build/run guide
3. `AGENTS.md` — canonical AI behavior + product standard
4. `SECURITY_AND_PRIVACY_ARCHITECTURE.md` — security/privacy
5. `DEPLOYMENT_READINESS.md` — deployment verification
6. `BUILD_GUIDE_SSOT.md` — build status, testing, known issues
7. `SEMPTIFY_SYSTEM_MANIFEST.md` — module registry

### Active context:

- `ACTIVE_CONTEXT.md` — what's being worked on RIGHT NOW
- `BUILD_STATE.md` — live deploy state
- `STATUS_AUDIT.md` (2026-06-21) — module snapshot
- `STUB_AUDIT.md` (2026-06-19) — TODO/stub inventory

### Phase 5 design docs:

- `ACTION_FEEDBACK_AUDIT.md` — Phase 5b spec
- `GUI_PHASE1_DESIGN.md` — GUI Phase 1 spec

---

*Obsolete docs archived in `archive/obsolete-2026-06-29/` — recoverable via git history.*
