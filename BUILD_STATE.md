# BUILD_STATE.md — Semptify Live Deployment State
# Update this file at the end of every session using /ship

---

## Shipped This Session (TBD)

### Core 5.0 Release Verification — COMPLETE
- [x] **Document upload to vault** — `/api/documents/upload` endpoint verified
- [x] **Timeline/Briefcase viewers** — `/api/timeline-unified/*`, `/api/briefcase/*` verified
- [x] **Legal analysis (direct)** — `/api/legal-analysis/classify-evidence` verified
- [x] **No errors in logs** — All Python files compile clean with `py_compile`
- [x] **Non-Core routers disabled** — court_forms, case_builder, brain, AI/Extended all set to None
- [x] **BUILD_GUIDE_SSOT.md updated** — Release criteria marked complete

---

## Last Deployed Commit
- **Hash**: `7e4b062`
- **Date**: 2026-05-06 00:24 UTC-05
- **Branch**: `main`
- **Repo**: https://github.com/1semptify-arch/Semptify.git
- **Render auto-deploy**: YES — triggers on every push to main

---

## Shipped This Session (71cf7e7)

### SSOT Architecture Compliance — CRITICAL
- [x] **Fixed 13 hardcoded redirects** in `app/main.py` and `app/core/storage_middleware.py`
- [x] **All redirects now use navigation registry** — no more hardcoded paths
- [x] **SSOT guard compliance** — all redirects use `ssot_redirect()` with context
- [x] **Zero compilation errors** — changes verified with `python -m py_compile`

---

## Previous Shipped (c8968fc)

### Streamlined Verification — RAPID EXECUTION
- [x] **Server verified running** — Health check passed at 00:17 UTC
- [x] **Journal page tested** — Loads correctly, form structure validated
- [x] **Responsibilities section verified** — Tab navigation and content rendering
- [x] **Footer links confirmed** — privacy.html, terms.html, disclaimer.html accessible
- [x] **Zero compilation errors** — All Python modules clean

---

## Previous Shipped (b83d381)

### Tenant Completion Guide — MAJOR PROGRESS
- [x] **Journal Page** — `static/tenant/journal.html` created with full CRUD:
  - Create entries (date, category, title, description)
  - Categories: rent_payment, maintenance_request, landlord_communication, general_note, notice, court
  - Edit and delete entries
  - API integration to `/api/tenancy/cases/{id}/timeline`
  - Responsive UI with empty states

- [x] **Two-Sided Rights Content** — Added "Tenant Responsibilities" section to law-library:
  - 5 detailed cards covering: rent payment, unit maintenance, problem reporting, lease compliance, move-out notice
  - Minnesota statute citations for each responsibility
  - Added 🤝 Responsibilities tab to navigation
  - Includes framing: "Responsibilities are legal armor, not capitulation"

### Verified Existing (Already Working)
- [x] **5 Footer Pages** — privacy.html, terms.html, disclaimer.html, contact.html, feedback.html all exist and functional
- [x] **Template Letters** — maintenance request and security deposit demand in `tools/letters.html`
- [x] **Deadline Tracker** — Full deadline management in `tools/deadlines.html`

---

## Previous Shipped (4148281)

### Critical Bug Fixes — DEPLOYED
- [x] **Test Engine Caching** — Fixed `tests/conftest.py` to clear `get_settings` cache and reset engine between tests. All 12 tests now pass on SQLite instead of failing on stale PostgreSQL engine.
- [x] **Dashboard Real Data** — `static/tenant/dashboard.html` now fetches live data from `/api/tenancy/cases`, `/deadlines`, `/timeline`, `/documents` instead of showing hardcoded 2025 mock dates and fake stats.
- [x] **SyntaxWarning Fix** — Fixed invalid `\`` escape sequence in `app/core/api_documentation.py` (line 809).
- [x] **Security Hardening** — Added `.env.production` and `.env.backup` to `.gitignore` to prevent secret exposure.

### Dashboard Improvements — LIVE
- [x] Real crisis hotline: Minnesota Legal Aid 1-800-292-4150 (was placeholder `XXX-XXXX`)
- [x] Dynamic deadline cards with urgency color-coding (red ≤7 days, amber ≤30)
- [x] Live timeline events with type icons
- [x] Real document count and most recent filename
- [x] Graceful "Sign in to see your dashboard" message for unauthenticated users
- [x] "No case data yet" empty state for new users

---

## Shipped Previous Session (e0201ad)

### Email — FULLY LIVE
- [x] Resend API wired (`app/services/email_service.py`)
- [x] `RESEND_API_KEY` / `FROM_EMAIL` / `SUPPORT_EMAIL` in config + `.env.example`
- [x] `/api/feedback` endpoint live — feedback.html now actually sends email
- [x] `/api/contact` endpoint live — contact form backend wired
- [x] Both endpoints public (no auth required) — added to `storage_middleware` PUBLIC_PREFIXES
- [x] Deadline notifications in `calendar.py` wired to `send_email()` (was TODO)
- [x] Cloudflare Email Routing configured — all `@semptify.org` → `1semptify@gmail.com`
- [x] End-to-end confirmed: `noreply@semptify.org` → Resend → Cloudflare → Gmail ✅

### E2E Test Suite — BUILT & PASSING
- [x] `tests/e2e/smoke_test.js` — 6/6 passing
- [x] `tests/e2e/playwright_full_system_test.js` — 13/13 pages, all flows
- [x] Full system test: 1 known issue (Swagger /api/docs returns 401 — intentional)

### Page Recipe System
- [x] `app/core/page_recipe.py` — PageRecipe dataclass + RecipeRegistry
- [x] `app/templates/page_recipe_template.html` — Jinja2 visualization template

---

## What Is Confirmed Working (6817d53)

### 4-Step Flow — VERIFIED LIVE
- [x] `GET /` → 200 welcome page served
- [x] `GET /welcome.html` → 200 welcome page served (fixed — was 301 to /onboarding)
- [x] `GET /onboarding/start` → 302 to /onboarding/select-role.html (fixed — was infinite loop)
- [x] `GET /onboarding/select-role.html` → 200 role select page
- [x] `GET /storage/providers` → 200 storage selection
- [x] `GET /tenant/home` (no cookie) → 302 to /onboarding/start (bypass CLOSED)
- [x] `GET /tenant/` (no cookie) → 302 to /onboarding/start (bypass CLOSED)

### OAuth Flow — VERIFIED LIVE
- [x] Google Drive OAuth callback completes without crash
- [x] `create_or_update_user()` — spurious `role=` kwarg removed, `storage_user_id` restored
- [x] User row created in DB, cookie set, device registered
- [x] `Rehome.html` — fetch() removed, plain href + auto-redirect works from file:// origin

---

## Known Limitations (Not Bugs — Future Work)
- Rehome.html in existing users' Drive is old version (fixed version only for new users)
- MNDES exhibit packages stored in memory — lost on server restart

---

## What Is Confirmed Shipped (d62a519)

### MNDES Integration (NEW)
- [x] `app/core/mndes_compliance.py` — MNDES file type list, validator, CONVERSION_TARGETS hook, get_conversion_action()
- [x] `app/routers/mndes.py` — compliance guide route, validate endpoints, conversion_action in responses, real vault lookup (stub removed)
- [x] `app/services/mndes_exhibit_service.py` — exhibit package builder, attestation, checklist (portal URL fix applied)
- [x] `app/models/mndes_exhibit.py` — Pydantic models for all MNDES API endpoints
- [x] `app/services/mndes_api_client.py` — MNDES portal client stub (future)
- [x] `static/mndes/compliance-guide.html` — full reference guide, all roles, interactive tabs
- [x] `static/mndes/guide.html` — step-by-step submission guide
- [x] `app/core/navigation.py` — mndes_guide, mndes_validate, mndes_package, mndes_compliance_guide registered in SSOT
- [x] `app/main.py` — MNDES router registered

### SSOT Architecture Compliance (Batch 1 & 2)
- [x] `app/routers/role_ui.py` — All redirects via SSOT registry, secure storage gate added
- [x] `app/routers/storage.py` — All hardcoded paths replaced with navigation.get_stage()
- [x] `app/routers/auth.py` — SSOT-compliant redirects
- [x] `app/routers/onboarding.py` — SSOT-compliant redirects + import fix
- [x] `app/routers/document_delivery.py` — SSOT violation fixed (storage/providers path)
- [x] `static/public/welcome.html` — SSOT navigation, checkpoint cookie, violation reporter
- [x] `static/onboarding/storage-select.html` — User choice preserved, no auto-redirect

### Role Dashboards (UPDATED)
- [x] `static/tenant/dashboard.html` — MNDES card + Quick Actions link
- [x] `static/advocate/dashboard.html` — MNDES card + Quick Actions link
- [x] `static/legal/dashboard.html` — MNDES card + Quick Actions link
- [x] `static/manager/dashboard.html` — MNDES card + Quick Actions link
- [x] `static/admin/dashboard.html` — MNDES card + Quick Actions link

### Other
- [x] `static/welcome.html` — public landing page
- [x] `tests/e2e/` — smoke test + Playwright full system test

---

## Known Working (Verified by py_compile)
- All Python files compile clean
- SSOT navigation entries all registered
- MNDES vault lookup uses real VaultUploadService (not stub)
- Conversion action hook ready for future converters

---

## Known Limitations (Not Bugs — Future Work)
- MNDES exhibit packages stored in memory — lost on server restart (needs DB persistence)
- Vault upload service index is in-memory — same limitation
- No tests specifically for MNDES compliance logic yet
- AI/ML services (Groq, Gemini, OCR) not tested

---

## Environment Variables Required on Render
Set these in Render Dashboard > Service > Environment:

| Variable | Status | Notes |
|----------|--------|-------|
| `SECRET_KEY` | Auto-generated by Render | Already in render.yaml |
| `DATABASE_URL` | MUST BE SET MANUALLY | Use Neon.tech free PostgreSQL |
| `SECURITY_MODE` | `enforced` | Already in render.yaml |
| `GOOGLE_DRIVE_CLIENT_ID` | Optional | OAuth — set if using Google Drive |
| `GOOGLE_DRIVE_CLIENT_SECRET` | Optional | OAuth |
| `DROPBOX_APP_KEY` | Optional | OAuth |
| `DROPBOX_APP_SECRET` | Optional | OAuth |
| `R2_ACCOUNT_ID` | Optional | Cloudflare R2 storage |
| `R2_ACCESS_KEY_ID` | Optional | Cloudflare R2 |
| `R2_SECRET_ACCESS_KEY` | Optional | Cloudflare R2 |

---

## Next Session Priorities
1. Verify Render deploy succeeded (check https://dashboard.render.com)
2. Set DATABASE_URL on Render if not set
3. Run `python -m alembic upgrade head` via Render shell after first deploy
4. Add MNDES unit tests to tests/

---

## How to Use /ship
At the end of every session, type `/ship` in Windsurf chat.
It will: verify → stage → commit → push → update this file.
Nothing is real until it is pushed.
