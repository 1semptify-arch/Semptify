# Semptify Active Context

**Last Updated**: 2026-06-15

---

> ## ⚠️ AI AGENT — READ THIS FIRST
> **If you are starting a new session, run `/preflight` BEFORE touching any code.**
> This file and `BUILD_STATE.md` are your ground truth. Do not assume the previous session's state.
> Do not repeat failures from the Known Failure Registry in `AGENTS.md`.

---

## 🎯 Current Priority: Test Onboarding End-to-End

### ✅ COMPLETED — Admin OAuth Role Fix (2026-06-15)
- Fixed: `app/modules/storage/router.py` — returning users now use `matched_user.default_role` from DB, not parsed from user_id string
- Admin elevation system shipped: time-limited HMAC-signed cookie, 2h TTL, `app/core/admin_elevation.py`

### ✅ COMPLETED — document_uploaded Gate Re-enabled (2026-06-15)
- `get_document_registry()` helper added to `app/services/document_registry.py`
- `registry.register_document()` wrapped in `asyncio.run_in_executor()` in `vault_upload_service.py`
- Gate re-enabled in `app/modules/onboarding/config.py`

### ✅ COMPLETED — Vault Folder Creation Root Cause Fixed (2026-06-15)
- Root cause: Google Drive `_get_folder_id()` returned `None` when folder existed due to race/eventual consistency
- Fix: `app/services/storage/google_drive.py` — search-before-create with retry + exponential backoff
- Removed VaultClient downstream workaround — storage provider now correct
- Commits: `14a9e2c`, `73eaeca`

### 🔴 PENDING — Test Onboarding Flow End-to-End
- Clear browser cookies for `semptify.org`
- Complete OAuth → vault init → document upload
- Verify `document_uploaded` gate marked
- Verify `registry_id` in SEM-YYYY-NNNNNN-XXXX format and `integrity_status` = "verified"

### 🔴 PENDING — Role Hierarchy Design
- Admin needs to be able to assume child roles (tenant, manager, advocate) for testing
- Manager needs conditional access to tenant documents (if lease relationship exists)
- Advocate needs conditional access to client documents (if engagement exists)
- Need: `user_relationships` table + `can_access(user, target_user)` permission check
- Need: `acting_as` session context for role impersonation

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
