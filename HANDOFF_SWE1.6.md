# Semptify — SWE 1.6 Task List
# Prepared: 2026-06-16 | For: SWE 1.6 (code-execution agent)
# Stack: Python 3.11.9 / FastAPI / PostgreSQL / Redis / SQLAlchemy async
# Repo: C:\Semptify\Semptify-FastAPI
# HEAD: 6bb0fa3 (clean, pushed)

---

## RULES BEFORE EVERY TASK

1. Activate venv: `.\venv311\Scripts\Activate.ps1`
2. Read `BUILD_STATE.md` top section (last session state)
3. Read `AGENTS.md` Known Failure Registry (15 documented bugs — do not repeat)
4. Never use `datetime.now()` — always `from app.core.utc import utc_now`
5. Never hardcode redirect URLs — always `navigation.get_stage("stage_id").path`
6. Never create `_v2` or `_new` files — rewrite into original filename
7. After every file change: `python -m py_compile <file> && echo OK`
8. After every session: compile all core files, commit, push

---

## TASK LIST

### TASK 1 — Verify Alembic Migrations Run on Render `HIGH`

**Goal:** Confirm `admin_audit_logs` and `document_annotations` tables exist in production DB.

**Steps:**
1. Check Render deploy logs for: `Running upgrade 68e486c460de -> 20260616_add_missing_tables`
2. If logs confirm migration ran, query the DB:
   - `SELECT COUNT(*) FROM admin_audit_logs;`  → must not error
   - `SELECT COUNT(*) FROM document_annotations;` → must not error
3. If tables missing: trigger a manual redeploy from Render dashboard.
4. Update `BUILD_STATE.md`: mark as "verified live" or "migration failed — see logs"

**Files:** `alembic/versions/20260616_add_admin_audit_logs_and_document_annotations.py`

---

### TASK 2 — Live Test: Upload → Timeline Chain `HIGH`

**Goal:** Confirm that uploading a document creates a `TimelineEvent` row automatically.

**Steps:**
1. Log in at https://semptify.org as a real tenant (need test account)
2. Upload any document via the vault
3. Call `GET /api/timeline/unified` (authenticated)
4. Verify response includes an entry with:
   - `event_type: "document_uploaded"`
   - `title` containing the filename
   - `event_date` within the last minute
5. Also check PostgreSQL directly:
   ```sql
   SELECT id, event_type, title, event_date
   FROM timeline_events
   WHERE user_id = '<test_uid>'
   ORDER BY event_date DESC
   LIMIT 5;
   ```
6. If the row is NOT created: check server logs for `_on_document_added subscriber failed`
7. Update `BUILD_STATE.md` with result

**Files involved:**
- `app/core/event_subscribers.py` — subscriber
- `app/core/event_bus.py` — event dispatch
- `app/modules/vault/router.py` lines 427-436 — where event is fired

---

### TASK 3 — Live Test: Case Builder Survives Restart `HIGH`

**Goal:** Confirm cases are stored in PostgreSQL and not wiped on Render restart.

**Steps:**
1. Create a case via `POST /api/case-builder/cases` (authenticated)
2. Note the returned `case_id` (now a PostgreSQL integer, not a UUID)
3. Trigger a Render restart (from dashboard → "Restart service")
4. After restart, `GET /api/case-builder/cases/{case_id}` must return the same case
5. If case is lost: the storage is still writing to local files. Check
   `app/modules/case_builder/router.py` `load_case()` / `save_case()` — must use `Incident` model
6. Update `BUILD_STATE.md` with result

**Files involved:**
- `app/modules/case_builder/router.py` — `load_case`, `save_case`, `create_case`
- `app/models/models.py` — `Incident` model (`incident_metadata` JSONB column)

---

### TASK 4 — Live Test: Capability Seeding on Login `MEDIUM`

**Goal:** Confirm `user_capabilities` rows are seeded when a user logs in.

**Steps:**
1. Log in with a fresh account (or clear capabilities for a test user)
2. Check PostgreSQL:
   ```sql
   SELECT module_name, is_active, source
   FROM user_capabilities
   WHERE user_id = '<uid>'
   ORDER BY module_name;
   ```
3. Expected: at minimum these modules seeded for a tenant:
   `case_builder`, `timeline`, `vault`, `rent_ledger`, `court_forms`
4. If rows are missing: check `app/modules/storage/router.py` around line 1952 for
   `seed_capability_defaults()` call — must be inside the OAuth callback, not wrapped
   in a condition that skips it
5. Update `BUILD_STATE.md` with result

**Files involved:**
- `app/core/capabilities.py` — `seed_capability_defaults()`
- `app/modules/storage/router.py` — OAuth callback (around line 1952)

---

### TASK 5 — Fix: HAS_STORAGE Meaningless Guard `MEDIUM`

**Goal:** Fix a bug where both branches of a try/except set `HAS_STORAGE = True`.

**Steps:**
1. Open `app/services/vault_upload_service.py`
2. Search for `HAS_STORAGE`
3. If both the `try:` and `except:` blocks set it to `True`, the guard is meaningless
4. Fix: the `except` block should set `HAS_STORAGE = False` OR remove the guard
   entirely and raise immediately (preferred — per Known Failure #2 in AGENTS.md:
   fix the root, not the symptom)
5. `python -m py_compile app/services/vault_upload_service.py && echo OK`
6. Commit: `fix: remove meaningless HAS_STORAGE guard in vault_upload_service`

**File:** `app/services/vault_upload_service.py`

---

### TASK 6 — Wire Role Hierarchy: can_access() `MEDIUM`

**Goal:** The `user_relationships` table exists and `can_access()` function exists but is
not called anywhere. Wire it so Advocate can act on behalf of Tenant.

**Context:**
- `user_relationships` table: `app/models/models.py` class `UserRelationship`
- `can_access()`: `app/core/security.py` — async function, queries `user_relationships`
- `UserContext`: `app/core/user_context.py` — has `acting_as` and `acting_as_role` fields

**Steps:**
1. Read `app/core/security.py` — find `can_access(requester_id, target_id)`
2. Read `app/core/user_context.py` — find `acting_as` / `acting_as_role`
3. Add endpoint: `POST /api/user/act-as` (advocate/admin only)
   - Body: `{"target_user_id": "...", "reason": "..."}`
   - Checks `can_access()` — if allowed, sets `acting_as` in session/cookie
   - Returns new scoped token or session marker
4. Add endpoint: `DELETE /api/user/act-as` — clears impersonation
5. Wire `acting_as` check into `get_current_user()` dependency so downstream
   endpoints see the impersonated user's data when `acting_as` is set
6. Compile check all changed files
7. Write a Playwright smoke test: `tests/e2e/role_hierarchy_smoke.spec.js`
   - Test 1: unauthenticated → 401 on `POST /api/user/act-as`
   - Test 2: tenant trying to act-as another user → 403
   - Test 3: advocate acting as tenant → 200 (if relationship exists)

**Files:**
- `app/core/security.py`
- `app/core/user_context.py`
- `app/modules/storage/router.py` or a new `app/modules/user/router.py`

---

### TASK 7 — Fix: Rent Ledger Live Test `MEDIUM`

**Goal:** Verify rent ledger CRUD works end-to-end.

**Steps:**
1. Find the rent ledger router: search for `RentPayment` in `app/`
2. Find the `POST` endpoint for creating a payment
3. Test: `POST /api/rent/payments` with:
   ```json
   {"amount": 950.00, "payment_date": "2026-06-01", "status": "paid", "notes": "June rent"}
   ```
4. Verify response includes `payment_id` and the row exists in PostgreSQL:
   ```sql
   SELECT * FROM rent_payments WHERE user_id = '<uid>' ORDER BY created_at DESC LIMIT 3;
   ```
5. If endpoint does not exist: check `app/modules/rent/router.py` or create it
6. Update `BUILD_STATE.md`

---

### TASK 8 — Fix: Filedored On-Demand Folder Creation `LOW`

**Goal:** When the `filedored_ready` Redis flag is not set, folder creation should be
triggered lazily on first document access, not skipped entirely.

**Context:**
- `app/services/filedored_service.py` — `ensure_filedored_folders()`
- Redis flag: `semptify:filedored_ready:<user_id>` — set after first folder creation
- Current state: if flag is missing, creates folders. If flag is present, skips. CORRECT.
- Problem: overlay/AI subdirectories are never created. They must be on-demand.

**Steps:**
1. Read `app/services/filedored_service.py` fully
2. Identify which folders are "on-demand" (overlay, AI, etc.) vs "always needed"
3. Add lazy trigger: when a module first tries to write to an on-demand folder and gets
   `path_not_found`, call `ensure_filedored_folders()` for just that path
4. This should NOT be an upfront batch — it must be lazy per folder
5. Compile check, commit

---

### TASK 9 — Scan: Find Any Remaining TODO / STUB Code in Core Paths `LOW`

**Goal:** Find production code that still has stub/placeholder behavior.

**Steps:**
```powershell
# Run these in repo root
grep -rn "TODO\|FIXME\|HACK\|not implemented\|placeholder\|stub\|pass  #" app/ --include="*.py" | grep -v "test_" | grep -v "#.*TODO"
```

**For each hit:**
1. Decide: is this in a code path a user will hit? (core upload, auth, timeline, case builder = YES)
2. If yes: fix it or file it in BUILD_STATE.md as a known gap
3. If no (admin debug tool, background analytics): leave it, note in BUILD_STATE.md

---

### TASK 10 — Documentation: Update ACTIVE_CONTEXT.md `LOW`

**Goal:** ACTIVE_CONTEXT.md is stale (still references Milestone 3 as "next priority").
Update it to reflect the current state after this session's 6 milestones.

**Steps:**
1. Open `ACTIVE_CONTEXT.md`
2. Update the "Next Priority" section to reflect the task list above (Tasks 1-4 are live tests)
3. Mark Milestones 1-6 as completed
4. Set next priority clearly:
   - **IMMEDIATE**: Live tests (Tasks 1-4) — verify what was built actually works
   - **NEXT**: Role hierarchy wiring (Task 6)
   - **THEN**: Rent ledger (Task 7), Filedored on-demand (Task 8)
5. Commit: `docs: update ACTIVE_CONTEXT after session 2026-06-16`

---

## COMPILE CHECK COMMAND (run after every task)

```powershell
.\venv311\Scripts\python.exe -m py_compile `
  app/main.py `
  app/core/navigation.py `
  app/modules/vault/router.py `
  app/modules/onboarding/router.py `
  app/modules/documents/router.py `
  app/services/vault_upload_service.py `
  && echo "ALL OK"
```

---

## GIT COMMIT FORMAT

```
<verb>(<scope>): <what changed>

- app/path/file.py: what changed and why
- app/path/file2.py: what changed and why
```

Examples:
```
fix(vault): remove meaningless HAS_STORAGE guard
feat(role-hierarchy): wire can_access() into act-as endpoint
test(rent): add rent ledger smoke test
docs(active-context): update priorities after 2026-06-16 milestones
```

---

## DO NOT TOUCH WITHOUT EXPLICIT INSTRUCTION

- `app/core/navigation.py` — SSOT for all paths. Changes require full regression test.
- `app/models/models.py` — adding columns requires an Alembic migration, never `create_all()`
- `app/services/vault_upload_service.py` `upload()` method — the single upload pipeline.
  Any change here affects every document in the system.
- `alembic/env.py` — do not modify
- `.env` — never commit, never read into code directly (use `app/core/config.py` Settings)

---

*Generated: 2026-06-16 | HEAD: 6bb0fa3 | Render: auto-deploys from main*
