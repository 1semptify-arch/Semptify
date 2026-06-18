# Semptify Active Context

**Last Updated**: 2026-06-17 PM

---

> ## ⚠️ AI AGENT — READ THIS FIRST
> **If you are starting a new session, run `/preflight` BEFORE touching any code.**
> This file and `BUILD_STATE.md` are your ground truth. Do not assume the previous session's state.
> Do not repeat failures from the Known Failure Registry in `AGENTS.md`.
> All structural terms are defined in `SEMPTIFY_DICTIONARY.md`. Read it before asking what a "module" is.

---

## ✅ COMPLETED THIS SESSION (2026-06-17 PM) — Deployment Warnings, Status Indicator, Reconnect Fix

| What | Commit |
|------|--------|
| Fixed security module syntax error (import in docstring) | `c77b425` |
| Fixed .gitignore to allow security directory | `2f1f8c7` |
| Disabled litigation_intelligence router (missing graph_engine) | `9701553` |
| Added persistent status indicator in header (user ID + storage status) | `9302589` |
| Added double-click verify/reconnect handler | `9302589` |
| Added returning user auto-reconnect in preamble router | `0aee35d` |
| Fixed reconnect callback to use 3-step vault setup (no timeout) | `7a808ea` |

**HEAD: `2dfbccc` — clean, pushed**

---

## ✅ COMPLETED PREVIOUS SESSION (2026-06-16 AM) — Milestones 1–9 ALL DONE

| Milestone | What | Commit |
|-----------|------|--------|
| M1 | Case builder → PostgreSQL, filedored idempotency, vault timeout fix, smoke tests | `8093096` |
| M2 | Timeline Pydantic fix, upload→timeline wired, smoke tests | `59c8c62` |
| M3 | Capability system audit (already built), smoke tests 7/7 | `9780a1f` |
| M4 | 13× `datetime.now()` → `utc_now()` across 8 files. 0 violations remain. | `9780a1f` |
| M5 | Event bus UTC fix, `notify_document_added()` now fired from upload path | `4c56a77` |
| M6 | 2 missing Alembic migrations created: `admin_audit_logs`, `document_annotations` | `6bb0fa3` |
| M7 | Role hierarchy wiring: `POST /api/user/act-as`, `DELETE /api/user/act-as`, smoke test | `41392fb` |
| M8 | Rent Ledger CRUD router: `POST/GET/DELETE /api/rent/payments`, smoke test | `2ea26c4` |
| M9 | Filedored on-demand: split base vs AI folders, lazy `ensure_filedored_folder()` | `5b3990b` |

**HEAD: `5b3990b` — clean, pushed**

---

## 🎯 IMMEDIATE NEXT: Live Tests (verify what was built)

These are marked "pending live test" — need a real action on semptify.org:

1. **Upload → timeline** — Upload a document. Check `/api/timeline/unified` for
   `event_type: "document_uploaded"` row. See `HANDOFF_SWE1.6.md` Task 2.
2. **Case builder restart** — Create case, restart Render, reload case. Must survive.
   See `HANDOFF_SWE1.6.md` Task 3.
3. **Capability seeding** — Fresh login → check `user_capabilities` table has rows.
   See `HANDOFF_SWE1.6.md` Task 4.
4. **Migration ran** — Verify `admin_audit_logs` table exists on production DB.
   See `HANDOFF_SWE1.6.md` Task 1.
5. **DB SSL mode** — Set `DB_SSL_MODE=require` in Render dashboard (manual action).

## 🎯 NEXT AFTER LIVE TESTS

1. **Documentation cleanup** — Update stale docs, retire completed handoff items
2. **Scan for remaining TODO/stub code** — No critical stubs in core paths (already completed)

## 📋 FULL TASK LIST: See `HANDOFF_SWE1.6.md`
## 📋 FULL CONTEXT + INSTRUCTIONS: See `HANDOFF_KIMI2.6.md`

---

## 🔵 Capability System (Milestone 3 — COMPLETE)

### Architecture Decision — LOCKED (2026-06-16)

The following decisions are final. Do not re-litigate them. Build to these specs.

| # | Decision | Answer |
|---|----------|--------|
| 1 | Module types | **Pipeline Module** (always-on engine) + **Feature Module** (user-loadable capability) |
| 2 | Capability store | **New `user_capabilities` DB table** + Redis cache per session |
| 3 | Role defaults | **Defined in `product_manifest.py`** — small set per role, everything else opt-in |
| 4 | Overlay boundary | **Add-only**. Overlays can never replace existing routes. Pipeline modules cannot be overlaid. |
| 5 | Relationships vs capabilities | **Separate tables**. `user_relationships` = who sees who. `user_capabilities` = what features are on. |
| 6 | Load trigger | **Role defaults on login** (preloaded, no friction). **Everything else lazy** — loads on first navigation, stays for session. |

### Data Flow Rule — NEVER VIOLATE
```
USER
  ↓
Feature Module  (case_builder, fems, timeline, court_forms...)
  ↓
Pipeline Module (registry, certification, extraction, context_loop...)
  ↓
Database / Storage / External APIs
```
Feature modules call DOWN to pipeline modules.
Pipeline modules NEVER call UP to feature modules.
Feature modules NEVER call sideways to other feature modules directly.

---

## 🔴 NEXT — Build the Capability System (3 sessions estimated)

### Session A — Foundation
1. Add `user_capabilities` table to `app/models/models.py`
2. Create Alembic migration
3. Define role default sets in `product_manifest.py` (tenant=5, advocate=9, admin=all)
4. Wire defaults: on login, insert missing defaults for the user's role

### Session B — Loading
1. Lazy feature module loader — checks `user_capabilities` before mounting route
2. Session cache in Redis — capability set loaded once per session
3. `can_load_module(user_id, module_name)` helper in `app/core/capabilities.py`

### Session C — Overlay + Dev Node
1. Overlay flag on `ModuleEntry` in `product_manifest.py`
2. Dev session attach/detach endpoint (admin only)
3. Overlay mount enforces add-only rule at registration time
4. Overlay stripped on session end

---

## 🔴 ALSO PENDING (lower priority than capability system)

- **Role hierarchy wiring** — `user_relationships` table exists but `can_access()` not wired
- **`acting_as` session context** — admin impersonation of child roles
- **Filedored/overlay folders** — on-demand creation not yet wired
- **`HAS_STORAGE` bug** — both branches of try/except set `True` — meaningless guard

---

## 🎯 Previously Completed

### ✅ COMPLETED: Unified Overlay System (2026-04-21)

| Component | File | Status |
|-----------|------|--------|
| **Core Types** | `app/core/overlay_types.py` | ✅ Complete |
| **Data Models** | `app/models/unified_overlay_models.py` | ✅ Complete |
| **Cloud Manager** | `app/services/unified_overlay_manager.py` | ✅ Complete |
| **API Router** | `app/routers/unified_overlays.py` | ✅ Complete |
| **Vault Integration** | `app/services/vault_upload_service.py` | ✅ Complete |
| **Router Integration** | `app/main.py` | ✅ Complete |
| **Old System Deprecated** | `document_overlay.py`, `document_overlay_service.py` | ✅ Marked |

**API Available**: `/api/unified-overlays/*`
**Storage**: `Semptify5.0/Vault/overlays/` (cloud-only, stateless)

### ✅ COMPLETED: Core Mechanics (2026-04-20)

| Area | Task | Status | Notes |
|------|------|--------|-------|
| **Routing** | Single source of truth for OAuth routing | ✅ Complete | `route_user()` in `workflow_engine.py` |
| **Workflow** | Stateless behavior, deterministic routing | ✅ Complete | Removing stateful fallbacks |
| **Vault** | Cloud storage patterns finalized | ✅ Complete | Path constants in `vault_paths.py` |

### 🅿️ PARKED (Awaiting Decision)

| Project | Design Doc | Status | Blocked By |
|---------|------------|--------|------------|
| **rehome.html / Identity Recovery** | Research encrypted alternative | 🅿️ PARKED | User researching encrypted format vs plain HTML |

### ✅ COMPLETED: Document Delivery System

| Component | File | Status |
|-----------|------|--------|
| **Page Contracts** | `app/core/page_contracts.py` | ✅ Complete (inbox, send, signature flows) |
| **Data Models** | `app/models/document_delivery_models.py` | ✅ Complete |
| **Service Layer** | `app/services/document_delivery_service.py` | ✅ Complete |
| **API Router** | `app/routers/document_delivery.py` | ✅ Complete |
| **Send HTML** | `static/delivery_send.html` | ✅ Complete (w/ communication integration) |
| **Inbox HTML** | `static/delivery_inbox.html` | ✅ Complete |
| **Signer HTML** | `static/document_signer.html` | ✅ Complete (fill, sign, chat, reject) |
| **Main Integration** | `app/main.py` | ✅ Complete |

**API Available**: `/api/delivery/*`
**Delivery Types**: REVIEW_REQUIRED, SIGNATURE_REQUIRED, PROCESS_SERVER (future)
**Who Can Send**: Advocate, Manager, Legal, Admin
**Storage**: Cloud overlays in recipient vault

### ✅ COMPLETED: Communication System (2026-04-21)

| Component | File | Status |
|-----------|------|--------|
| **Data Models** | `app/models/communication_models.py` | ✅ Complete |
| **Service Layer** | `app/services/communication_service.py` | ✅ Complete |
| **API Router** | `app/routers/communication.py` | ✅ Complete |
| **Browser UI** | `static/document_signer.html` | ✅ Complete |
| **Overlay Type** | `app/core/overlay_types.py` | ✅ Added COMMUNICATION |
| **Main Integration** | `app/main.py` | ✅ Complete |

**API Available**: `/api/communications/*`
**Features**:
- Direct messaging between tenant and all roles
- Document collaboration threads
- In-browser document filling and signing
- Signed documents saved to user's vault
- Real-time chat interface

**Storage**: Cloud overlays (COMMUNICATION type) in `Semptify5.0/Vault/communications/`

### ✅ COMPLETED: EXTENDED Tier Enabled (2026-05-29)

- 50 modules registered (was 35)
- All 5 import errors fixed (progress, actions, document_converter, tenant_defense, pattern_history)
- `pattern_records` table excluded from `create_all` (needs Alembic migration when ready)
- Tenant navigation menu updated with new tools
- `preview` module skipped — `libmagic` already installed, likely a Windows DLL path issue

---

## 🎯 NEXT MOVE

### Step 1 — Ship tonight's changes
```
/ship
```

### Step 2 — Build the generic module page template ✅ COMPLETE

Generic module page template built and working:
- `app/templates/pages/module_page.html` — existing template updated
- Route: `GET /tool/{page_id}` in `app/main.py` — maps PageContract to template
- Proof modules available:
  - `/tool/eviction_answer` → Eviction Answer Form
  - `/tool/counterclaim` → Counterclaim Builder  
  - `/tool/complaints` → Complaints
- Every module with a PageContract now gets a UI automatically

**How it works:**
1. Route looks up `page_id` in `PAGE_CONTRACTS` registry
2. Maps PageContract fields to template context (title, expectations, groups, etc.)
3. Renders `module_page.html` with contract metadata
4. Role protection enforced from `contract.roles_supported`
5. Shows entry/exit criteria as sections in the UI

### Step 3 — Live test with a real tenant scenario 🚧 PENDING SERVER START
- New user → onboarding → vault → upload a lease → check eviction defense page
- Confirm the full path works end to end

### Step 4 — Admin System Phase 4 ✅ COMPLETE
- Analytics API endpoints: overview, signup-funnel, feature-usage, retention
- Analytics dashboard UI with retention metrics and detailed modal
- All 4 phases of admin system now functional

---

## 🚫 NOT YET (documented, not building)
- ~~Role + jurisdiction module activation~~ ✅ `ModuleGateMiddleware` built
- ~~Feature flags DB table~~ ✅ Migration created
- ~~Event bus wire-up for `context_loop`~~ ✅ Subscribers wired in main.py
- ~~`pattern_records` Alembic migration~~ ✅ Migration created

---

## ✅ UNPARKED (Recently Completed)

| Project | Design Doc | Status |
|---------|------------|--------|
| **Unified Overlay System** | `docs/OVERLAY_SYSTEM_DESIGN.md` | ✅ Complete and deployed |

---

## 🚫 Anti-Priorities (Don't Start These)

Things that might seem important but should NOT be worked on now:

1. **New features** that aren't core mechanics
2. **Refactoring** unrelated to statelessness
3. **Documentation** that isn't critical path
4. **Testing** of non-core systems

---

## ✅ Definition of "Core Mechanics Stable"

- [ ] `route_user()` is single source of truth for all routing
- [ ] No hardcoded redirect tables anywhere
- [ ] No local file storage for user data (all cloud)
- [ ] Deterministic behavior: same input = same output
- [ ] Stateless: no server-side session state

---

## 📋 Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-04-21 | ✅ Document Send uses Communication System | Send creates conversation thread + delivery record |
| 2026-04-21 | ✅ Document Rejection saves to vault | Rejection records stored as COMMUNICATION overlays with watermark |
| 2026-04-21 | ✅ Completed Communication System | Document fill/sign + messaging + vault storage |
| 2026-04-21 | ✅ Completed Unified Overlay System | All components integrated, vault upload migrated |
| 2026-04-21 | Ready for next major system | Core mechanics + overlays stable |
| 2026-04-20 | Parked Unified Overlay System | Core mechanics must stabilize first |
| 2026-04-20 | Prioritized stateless routing | Foundation for all other work |

---

## 🔗 Quick Links

- **Parked Design**: `docs/OVERLAY_SYSTEM_DESIGN.md`
- **Build Status**: `docs/BUILD_OUT_STATUS.md`
- **Blueprint**: `BLUEPRINT.md`
- **Vault Paths**: `app/core/vault_paths.py`

---

*This file is the single source of truth for what is being worked on RIGHT NOW.*
