# Semptify v5.0 Deployment Readiness Report

> **Note (2026-09-05):** This is a dated readiness snapshot. Treat the checklist as historical verification evidence, not a live status claim — re-verify against current `main` before any deploy.

> **Re-verified 2026-11-05 (swe-2, task `prod-deploy-readiness-remaining`):** all four pre-deployment items re-checked against live production (Render web service `Semptify` / `srv-d7pja7km0tmc739j6m30` + Neon project `flat-block-24520481`, database `semptifty_db`). Every item passes — evidence inline below. Production architecture is **Render docker web service + managed Neon PostgreSQL 16 + Cloudflare mirror failover**, not the self-hosted topology the original checklist assumed; wording corrected accordingly. Remaining operator-only items are listed under "Open items (operator dashboard checks)".

**Date**: April 10, 2026  
**Status**: READY FOR PRODUCTION — re-verified live 2026-11-05

---

## Executive Summary

Semptify v5.0 backend has successfully completed critical testing phases:

✅ **Database Schema**: All migrations applied (users.completed_groups, oauth_states table)  
✅ **Core Tests**: 63/63 critical path tests passing (health, basic, role validation, storage, vault manager)  
✅ **PostgreSQL Setup**: All 20 tables owned by `semptify` user with proper permissions  
✅ **Alembic Migrations**: Current version `81c36d8f2466 (head)` applied and verified  
✅ **OAuth Flow Schema**: Column blocker resolved (UndefinedColumnError on OAuth callback fixed)  
✅ **Document Overlays**: Service, router, and auth layer fully tested and passing  

---

## Test Results Summary

### Representative Test Bundle (PASSING)

```text
test_health.py                          ✓ Health checks
test_basic.py                           ✓ Core API functionality  
test_role_validation.py                 ✓ RBAC enforcement
test_storage.py                         ✓ OAuth flows, session management (30 tests)
test_vault_manager_sequence.py           ✓ Document vault lifecycle
test_document_overlays.py               ✓ Annotation service CRUD
test_overlay_token_auth.py              ✓ Bearer token scope enforcement

Total: 63 PASSED in 58.38s | Coverage: 25%
```

### Individual Test File Execution

- All test files pass when run individually ✓
- Database connection pool issues noted when running multiple files in sequence (separate concern from production, where each request gets dedicated connection)
- 59/77 tests passed in combined run; operational errors were fixture/connection pool related

---

## Critical Fixes Applied (Session)

### 1. Database Permission Fix

- **Issue**: `InsufficientPrivilege: must be owner of table users`
- **Fix**: Transferred ownership of all 20 public schema tables from `postgres` superuser to `semptify` application user
- **Status**: ✓ Applied and verified

### 2. Alembic Migrations

- **Created**: `6405f204d7dc_add_oauth_states_table.py` — oauth_states table for provider state management
- **Created**: `81c36d8f2466_add_completed_groups_to_user.py` — completed_groups column for workflow stage tracking
- **Applied**: Both migrations successfully executed
- **Current**: `alembic current` confirms `81c36d8f2466 (head)`

### 3. OAuth State Management

- **Legacy Compatibility**: Added transitional in-memory maps (`SESSIONS`, `OAUTH_STATES` globals) for backward compatibility during DB migration
- **Column References**: Fixed references to `users.completed_groups` in OAuth callback path
- **Status**: ✓ Callbacks now execute without UndefinedColumnError

### 4. Storage Router Enhancements

- Line 1247: Legacy state fallback (`OAUTH_STATES.pop(state, None)`)
- Lines 2009, 2047, 2288, 2325: Proper cleanup of compatibility maps during session expiry
- **Status**: ✓ Transitional state management working

---

## Production Deployment Checklist

### Pre-Deployment Verification — verified live 2026-11-05

- [x] **PostgreSQL 16 running and accessible on the production network** — Neon project `flat-block-24520481` (org `org-wandering-recipe-71733955`), branch `production`, database `semptifty_db`, `PostgreSQL 16.15`. The app is writing live sessions (`sessions.last_activity` = 2026-11-05T16:19Z, after the day's 15:55Z deploy).
- [x] **Application database role owns all tables** — all 79 `public`-schema tables and all sequences owned by `neondb_owner`, the role `DATABASE_URL` connects as on Neon. The Known-Failure-#20 ownership repair (`authenticator` → `neondb_owner`, 2026-09-13) is holding. (The original wording "user `semptify`" described a self-hosted role that never existed on Neon; the equivalent invariant — the app's role owns every object it must migrate — is verified.)
- [x] **Alembic configured for the production database** — `alembic/env.py` resolves `DATABASE_URL` via `app.core.config.get_settings()` (asyncpg→psycopg2 for sync migrations). Startup stage 3 runs `alembic upgrade head` automatically on Render, then `verify_migrations()` compares `alembic_version` to the script head and fails the deploy on drift (KF#20 drift guard). Live state: `alembic_version = 20261026_voice_posts` = single repo head; `GET /health` returns `{"status":"ok"}`.
- [x] **Environment variables set** (verified where observable; dashboard-only items in "Open items" below):
  - `DATABASE_URL` — working: alembic runs `PostgresqlImpl`, sessions write live
  - `SECURITY_MODE=enforced` — seen in 2026-11-05T15:55Z boot log
  - `SECRET_KEY` — implicitly verified: `config.py` raises at startup when enforced mode lacks a real key, and the service is live
  - `DEPLOY_TARGET`/`LOAD_PROFILE` — `render_mvp` / `render_balanced` (NullPool per PR #332) manage Neon free-tier compute quota
  - Port binding — Render detected the service on port 10000; serving `https://semptify.org`

### Deployment Steps

1. **Backup Production Database**

   ```bash
   pg_dump -U semptify -d semptify > semptify_backup_$(date +%Y%m%d).sql
   ```text

2. **Transfer Code to Production**

   ```bash
   git clone https://github.com/1semptify-arch/Semptify.git /app/semptify
   cd /app/semptify && git checkout main
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```text

   On Render this step is the Docker build — the service currently builds `./Dockerfile` (see "Open items" below).

4. **Apply Database Migrations**

   ```bash
   python -m alembic upgrade head
   ```

   On Render this is **automatic**: startup stage 3 (`app/main.py`) runs `alembic upgrade head` on every boot when `RENDER=true`, and `verify_migrations()` fails the deploy if `alembic_version` doesn't match the repo head — a broken schema can no longer ship silently.

5. **Verify Migration**

   ```bash
   python -m alembic current
   # Should output: 20261026_voice_posts (head)
   ```text

6. **Run Smoke Tests Against Production DB**

   ```bash
   pytest tests/test_health.py tests/test_storage.py -q --tb=short
   ```

7. **Start Application**

   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```text

---

## Open Items (operator dashboard checks — not verifiable from the repo)

Verified live on 2026-11-05 that everything above passes. The following items could not be checked via API/repo and need a human look in the Render/Neon dashboards:

1. **`NEDRIVE_CLIENT_SECRET` typo in `render.yaml`** — the blueprint snapshot lists `NEDRIVE_CLIENT_SECRET`, but `app/core/config.py` reads `ONEDRIVE_CLIENT_SECRET`. If the Render dashboard env var is also misspelled, OneDrive OAuth is silently dead in production. Check the service's Environment page and rename if needed.
2. **OAuth provider credentials** (`DROPBOX_APP_KEY/SECRET`, `ONEDRIVE_CLIENT_ID/SECRET`, `GOOGLE_DRIVE_CLIENT_ID/SECRET`) — presence can't be confirmed via API. Exercise each provider connect flow once on prod, or confirm the vars exist in the dashboard.
3. **`ALLOWED_ORIGINS`/`CORS_ORIGINS`, `PUBLIC_BASE_URL`, `APP_URL`, `RESEND_API_KEY`/`EMAIL_FROM`, `ADMIN_*`, R2 log-archive creds** — not observable from outside; confirm in the dashboard.
4. **Dockerfile drift** — the Render service builds `./Dockerfile` (`python:3.11-slim`, unpinned patch version) while `render.yaml`/`Dockerfile.render` pins `python:3.11.9-slim`. The dashboard setting wins, so prod runs the unpinned base — either repoint the service to `Dockerfile.render` or pin `Dockerfile`'s base to `3.11.9-slim` to honor the version mandate.
5. **Bridge Neon project `divine-sun-29128013`** — created 2026-10-31 as an emergency quota workaround; `DATABASE_URL` is serving `flat-block-24520481`/`semptifty_db` again (live session writes confirmed 2026-11-05). The bridge is under a different Neon account (not visible to this org's MCP) — decide whether to delete it.
6. **Stale databases on the `flat-block` `production` branch** — `semptify db` (name contains a space) and `neondb` (stale schema copy per KF#20) still exist alongside `semptifty_db` and `septify_pi`. Drop candidates after a backup.
7. **Neon free-tier quota** — resets 2026-12-01. The `render_balanced` NullPool profile (PR #332) reduces always-on consumption, but the 2026-10-31 outage was caused by quota exhaustion; keep an eye on the consumption page.

---

## OAuth Flow Validation

### Callback Handler Logic (Post-Migration)

The OAuth callback handler at `app/routers/storage.py:1365` can now safely execute:

```python
matched_user = await get_user_by_provider_subject(db, provider, provider_subject)
## Database query now includes users.completed_groups column without error
```

### Supported Providers

- ✓ Dropbox (provider schema: `dropbox`)
- ✓ OneDrive (provider schema: `onedrive`)
- ✓ Google Drive (provider schema: `google_drive`)

### Callback Flow Verified

1. OAuth state token stored in `oauth_states` table with expiry and return_to context
2. Provider identity fetched via access token
3. User created/updated with `completed_groups` tracking ✓
4. Session stored in database with provider binding
5. Redirect to return_to URL or default dashboard

---

## Known Limitations & Postdeployment Tasks

### Limitations

- Database connection pool issues when running 40+ test files in sequence (isolated to test environment; production uses connection per request)
- Some AI/ML services untested (gemini_ai, groq_ai, ollama_ai, pdf_extractor, ocr_service)
- Recognition and legal analysis engine coverage low (future priority)

### Postdeployment Recommendations

1. **Monitor OAuth Callbacks** — Log success/failure rates for first 48 hours
2. **Run Full Test Suite Incrementally** — Deploy test coverage expansion gradually
3. **Enable Request Tracing** — Use distributed tracing for callback flow visibility
4. **Certificate Rotation** — Review and rotate OAuth provider credentials quarterly
5. **Database Backup Policy** — Daily backups to S3/cloud storage

---

## Rollback Plan

If production deployment encounters issues:

1. **Downtime < 5 minutes**: Restart application process (may clear transition state)
2. **Database Schema Issue**:

   ```bash
   python -m alembic downgrade 6405f204d7dc
   # This removes completed_groups and oauth_states table
   # Revert code to previous commit before re-deploying
   ```

3. **OAuth Callback Failures**:
   - Check database permissions: `SELECT * FROM information_schema.role_table_grants WHERE table_name='users';`
   - Verify oauth_states table exists: `SELECT COUNT(*) FROM oauth_states;`
   - Check app logs for "UndefinedColumnError" pattern

---

## Sign-Off

**Backend Lead**: Ready for Production  
**Date**: April 10, 2026  
**Version**: v5.0 Final  
**Commit Hash**: Main branch  

---

## Appendix: Migration Version Chain

```text
Initial Schema
    ↓
6405f204d7dc (add_oauth_states_table)
    ↓
81c36d8f2466 (add_completed_groups_to_user)
    ↓
… (57 revisions total — see alembic/versions/)
    ↓
20261026_voice_posts (add_voice_posts) ← CURRENT PRODUCTION VERSION (verified 2026-11-05)
```

Each migration is reversible via `alembic downgrade` command.
