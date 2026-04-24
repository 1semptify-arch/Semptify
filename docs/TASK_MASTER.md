# Semptify 5.0 - Task Master

**SSOT**: Single Source of Truth for all pending work  
**Last Updated**: 2026-04-23  
**Rule**: Update status in real-time as work progresses

---

## 📋 ACTIVE TASKS (Priority Order)

### 🔴 HIGH PRIORITY

#### Task 1: Returning User Reconnect Flow ✅ COMPLETE
**Objective**: Create complete reconnect flow for returning users clicking "Returning User" on welcome page

⚠️ **CRITICAL: Reconnect is SEPARATE from Onboarding - do not mix!**

**Acceptance Criteria**:
- [x] Contract created for returning user process
- [x] UI page: `static/reconnect/index.html` (NOT in onboarding/)
- [x] User can identify themselves (email lookup or provider selection)
- [x] OAuth flow reconnects their storage
- [x] Session restored, redirected to their dashboard

**Files Created/Modified**:
- ✅ `docs/process_contracts/returning_user_contract.md` - Process contract
- ✅ `static/reconnect/index.html` - Full UI (SEPARATE folder)
- ✅ `app/routers/storage.py`:
  - ✅ `/storage/reconnect` - Serves reconnect UI
  - ✅ `POST /api/user/lookup` - Find user by email
  - ✅ `POST /api/session/restore` - Restore session + set cookie
- ✅ `static/public/welcome.html` - Link to `/storage/reconnect`

**Reconnect Flow (End-to-End)**:
```
Welcome Page → "Returning User" → /storage/reconnect
                                    ↓
                            static/reconnect/index.html
                            • Enter email OR click provider
                            • POST /api/user/lookup
                                    ↓
                            Found? → POST /api/session/restore
                                    ↓
                            ├─ Valid Session → Set cookie → Dashboard
                            └─ Expired → OAuth → Back to reconnect
```

**Separation Enforced**:
- Onboarding: `static/onboarding/` - NEW users only (COMPLETE - DON'T TOUCH)
- Reconnect: `static/reconnect/` - RETURNING users only (separate module)

**Status**: ✅ COMPLETE (2026-04-23)  
**Blocked By**: None  
**Assigned**: Available

---

#### Task 2: Advocate Validation Page ⏳ NOT STARTED
**Objective**: Create invite code validation page for Advocate role

**Acceptance Criteria**:
- [ ] Page exists at `/onboarding/validation/validate-advocate.html`
- [ ] Input field for invite code
- [ ] Validation API call
- [ ] Success → continue to storage selection
- [ ] Failure → show error, allow retry

**Files to Create**:
- `static/onboarding/validation/validate-advocate.html`

**Status**: ⏳ NOT STARTED  
**Blocked By**: Invite code system (backend)  
**Assigned**: Available

---

#### Task 3: Legal Validation Page ⏳ NOT STARTED
**Objective**: Create bar verification page for Legal role

**Acceptance Criteria**:
- [ ] Page exists at `/onboarding/validation/validate-legal.html`
- [ ] Input fields for bar number and state
- [ ] Verification API call
- [ ] Success → continue to storage selection
- [ ] Failure → show error, allow retry

**Files to Create**:
- `static/onboarding/validation/validate-legal.html`

**Status**: ⏳ NOT STARTED  
**Blocked By**: Bar verification API (backend)  
**Assigned**: Available

---

#### Task 4: Storage Provider Selection Page ⏳ NOT STARTED
**Objective**: Create UI for selecting Google Drive / Dropbox / OneDrive

**Acceptance Criteria**:
- [ ] Page exists (route TBD - `/onboarding/storage-select.html` or API-generated)
- [ ] Shows 3 provider options with icons
- [ ] Clicking provider initiates OAuth
- [ ] After OAuth → vault initialization → dashboard

**Files to Create**:
- `static/onboarding/storage-select.html` (or API generates HTML)

**Status**: ⏳ NOT STARTED  
**Blocked By**: None  
**Assigned**: Available

---

### 🟡 MEDIUM PRIORITY

#### Task 5: Consolidate Dashboard Versions 🔄 PENDING AUDIT
**Objective**: Reduce 4 dashboard versions to 1

**Acceptance Criteria**:
- [ ] Audit all dashboard versions
- [ ] Pick canonical version (recommend `dashboard-v2.html`)
- [ ] Archive/delete others
- [ ] Update all links to point to canonical

**Current Versions**:
- `dashboard.html` (2675 lines, bloated)
- `dashboard-v2.html` (simplified, keep)
- `command_center.html` (specialized, keep but separate)
- `enterprise-dashboard.html` (future, archive)
- `tenant/index.html` (duplicate, archive)

**Status**: 🔄 PENDING AUDIT  
**Blocked By**: None  
**Assigned**: Available

---

#### Task 6: Consolidate Document Management Pages 🔄 PENDING AUDIT
**Objective**: Reduce 6 document versions to 1

**Acceptance Criteria**:
- [ ] Audit all document page versions
- [ ] Pick canonical version
- [ ] Archive duplicates

**Current Versions**:
- `documents.html` (main, 1254 lines, keep)
- `documents-v2.html` (duplicate, archive)
- `documents_simple.html` (duplicate, archive)
- `document_intake.html` (duplicate, archive)
- `tenant/documents.html` (duplicate, archive)
- `admin/document_intake.html` (specialized, keep)

**Status**: 🔄 PENDING AUDIT  
**Blocked By**: None  
**Assigned**: Available

---

#### Task 7: Consolidate Timeline Pages 🔄 PENDING AUDIT
**Objective**: Reduce 5+ timeline versions to 1-2

**Acceptance Criteria**:
- [ ] Keep `timeline.html` (main)
- [ ] Keep `timeline-builder.html` (auxiliary)
- [ ] Archive all others

**Current Versions**:
- `timeline.html` (main, keep)
- `timeline-v2.html` (duplicate, archive)
- `timeline-builder.html` (auxiliary, keep)
- `timeline_auto_build.html` (auxiliary, evaluate)
- `interactive-timeline.html` (duplicate, archive)
- `tenant/timeline.html` (duplicate, archive)

**Status**: 🔄 PENDING AUDIT  
**Blocked By**: None  
**Assigned**: Available

---

### 🟢 LOW PRIORITY

#### Task 8: WebSocket/Real-time Notifications 50% COMPLETE
**Objective**: Complete WebSocket system

**Acceptance Criteria**:
- [ ] WebSocket router created
- [ ] Notification system implemented
- [ ] Frontend notification component

**Status**: 🟡 50% COMPLETE  
**Blocked By**: None  
**Assigned**: Available

---

#### Task 9: Advanced Search with Indexing ⏳ NOT STARTED
**Objective**: Implement full-text search

**Acceptance Criteria**:
- [ ] Document indexing system
- [ ] Full-text search API
- [ ] Search relevance scoring

**Status**: ⏳ NOT STARTED  
**Blocked By**: None  
**Assigned**: Available

---

#### Task 10: Document Preview/Thumbnails ⏳ NOT STARTED
**Objective**: Add document preview capabilities

**Acceptance Criteria**:
- [ ] Multi-format document preview
- [ ] Thumbnail generation
- [ ] Preview caching

**Status**: ⏳ NOT STARTED  
**Blocked By**: None  
**Assigned**: Available

---

## ✅ COMPLETED (Do Not Work On Unless Bug Fix)

- ID Generation System (`app/core/id_gen.py`)
- Unified Overlay System (`app/services/unified_overlay_manager.py`)
- Vault Storage System (`app/services/storage/vault_manager.py`)
- Timeline System (`app/routers/timeline_unified.py`)
- Rehome System (generated in user cloud)
- Performance Monitoring (`app/core/performance_monitor.py`)
- Database Layer (`app/core/database_pool.py`)
- Rate Limiting (`app/core/advanced_rate_limiter.py`)
- OAuth/Storage Backend (`app/routers/storage.py`)
- Welcome Page Entry Point (`static/public/welcome.html`)
- Role Selection Page (`static/onboarding/select-role.html`)

---

## 📊 TASK STATUS LEGEND

| Symbol | Meaning |
|--------|---------|
| ⏳ | Not Started - Ready to pick up |
| 🔄 | In Progress / Pending Audit |
| 🟡 | Partially Complete |
| ✅ | Complete |
| 🔴 | High Priority |
| 🟡 | Medium Priority |
| 🟢 | Low Priority |

---

## 🎯 NEXT RECOMMENDED TASK

**For immediate work**: **Task 1 - Returning User Reconnect Flow**

Why:
- Welcome page button already links to `/storage/reconnect`
- No handler exists (404)
- Critical for user experience
- Can be built independently

---

## 📝 CHANGE LOG

### 2026-04-23
- Created Task Master document
- Baseline established
- Tasks prioritized and assigned status
### 2026-04-23 - Task 1 Complete + ID System Verified + Smart Gate
- ✅ **Task 1 COMPLETE** - Returning User Reconnect Flow
  - Contract, UI, API endpoints all implemented
  - Flow: Welcome → Reconnect UI → Lookup → Restore → Dashboard
  - Path fixes: oauth return_to = `/storage/reconnect`
- ✅ **ID System Verified** - All 18 provider+role combos pass
  - Format: `<Provider><Role><8-unique>` = 10 chars
  - Provider extracted from position 0
  - Role extracted from position 1
  - Gates (storage/vault/client) SEPARATE from role
- ✅ **Smart Gate Checkpoint IMPLEMENTED**
  - Single entry point enforcement (`/` welcome page)
  - `semptify_checkpoint=acknowledged` cookie on button click
  - Returning users with session bypass gate
  - Protected paths redirect to welcome if no checkpoint
  - Legal validation: Semptify's right to work with user documents
- ✅ **FIXED: Reconnect Page - NO ACCOUNTS AT ALL**
  - Removed ALL "account" language (Semptify has NO accounts of any kind)
  - Info box: "Semptify doesn't have accounts"
  - Emphasis: "We don't track or store personal information"
  - Language changed: "Reconnect your journal" (not account)
  - SSOT updated: "NO ACCOUNTS" - no email, no passwords, no accounts, no personal data tracking
- ✅ **Footer Alignment Standard (Site-Wide)**
  - Center-aligned footer columns on all pages
  - Updated `welcome.html` and `reconnect/index.html`
  - Added Site-Wide Footer Standard to SSOT DESIGN SYSTEM
  - Documented required footer sections for all future pages
- ✅ **REMOVED: advocate_invite Router (Email Dependency)**
  - Deleted `app/routers/advocate_invite.py` (used `EmailStr`, required email-validator)
  - Removed import and registration from `app/main.py`
  - Violated NO ACCOUNTS architecture - Semptify has no email
  - Fixes startup error: "email-validator is not installed, run `pip install 'pydantic[email]'`"
- ✅ Created `docs/SEMPTIFY_BASELINE_SSOT.md` - Master system status
- ✅ Created `docs/TASK_MASTER.md` - Prioritized task list

---

**Pick a task, update its status here, and start working!**
