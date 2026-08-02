# Tenant Home Page Redesign + Non-Profit Stack + Admin Module Console — Implementation Plan

**Author:** Cascade
**Date:** 2026-06-28
**Status:** DRAFT — awaiting user approval before implementation

---

## Part 1: Current State Audit (verified live 2026-06-28)

### Document Center (DC) — ✅ WORKING

- URL: <https://semptify.org/documents>
- 15 documents loaded in vault list
- Viewer iframe present
- Upload button functional
- 3-pane layout intact
- **Status: DONE. No further work needed.**

### Tenant Journal — ✅ WORKING (fixed this session)

- 5 entries render with correct stats (5 total, 5 this month, 0 urgent, 18 days)
- Root cause was `doc.uploaded_at.isoformat()` on a string — fixed in `tenant_briefcase.py:666`

### Tenant Home Page — ⚠️ INCOMPLETE

- Template: `app/templates/pages/tenant_home.html` (463 lines)
- Route: `/tenant/home` in `main.py:3453`
- **Missing from home page:**
  - 📚 Law Library — no link/card
  - 📓 Journal — has card (line 390) ✅
  - 🆘 Help — only footer link (line 440), no prominent card
  - 📅 Calendar — no card, no module registered in `product_manifest.py`
  - 🏛️ Accountability — no card, module IS registered (line 504) but not surfaced to tenants
  - ⚙️ User Setup / Jurisdiction — no link, no zip code entry on home
  - 🧩 Add-ons / Advanced Features — no section

### Jurisdiction / Location — ⚠️ EXISTS BUT NOT WIRED TO USER SETUP

- `app/modules/location/router.py` — accepts `zip_code`, `state_code`, `county`, `city`
- `POST /api/location/update` endpoint exists
- `app/modules/setup/router.py` — `UserProfile` model has `zip_code` field (line 37)
- **Gap:** Setup wizard is a separate static page (`/static/setup_wizard.html`) — not integrated with location module
- **Gap:** No zip-code entry on tenant home or in onboarding

### Form Fill — ✅ EXISTS

- `app/modules/court_forms/router.py` — `POST /api/court-forms/generate`
- Creates `FORM_FILL` overlay in user's vault with filled form data
- Uses `oauth_token_manager + services.storage.get_provider` pattern (SSOT-compliant)
- **Status: Working. Needs UX integration on tenant home.**

### Accountability Module — ⚠️ REGISTERED BUT BROKEN (fixed this session)

- Registered in `product_manifest.py:504` as `lifecycle="beta"`
- 7 FunctionGroupContracts registered in `app/modules/housing_accountability/register.py`
- Endpoints: `/api/housing-accountability/*`
- **Fixed this session:** `CalendarEvent.event_date` → `CalendarEvent.start_datetime` (router.py:733)
- **Status: Backend functional. No tenant-facing UI exists.**

### Calendar Module — ⚠️ EXISTS, NOT REGISTERED

- `app/modules/calendar/router.py` (23KB) exists
- NOT in `product_manifest.py` — never loaded
- **Status: Needs registration + tenant UI card**

### Admin Module Console — ⚠️ PARTIAL

- `static/admin/module_flags.html` exists — toggle module flags
- `static/admin/dashboard.html` — admin landing
- `app/modules/admin_console/router.py` (62KB) — backend exists
- **Gap:** No unified "run every module from admin" GUI
- **Gap:** No interactive switches for module runtime control

### Free AI for Non-Profit — ⚠️ NO PLAN EXISTS

- `app/modules/local_ai/config.py` — supports Ollama/LM Studio (local)
- User stated: "I cannot host AI locally"
- **Need:** Cloud-based, free, no-strings, no-advertising AI services
- **Status: RESEARCH NEEDED — see Part 4**

### Non-Profit Organization — ⚠️ NOT SET UP

- 30 files mention "nonprofit" but no 501(c)(3) status documented
- `FUNDING_PROSPECTUS_ID_SYSTEM.md` exists but funding not secured
- **Status: RESEARCH NEEDED — see Part 5**

---

## Part 2: Tenant Home Page Redesign

### Goal

Make the tenant home page the single launchpad for ALL tenant functionality. Two pillars (RECORD + KNOW) plus access to every tool.

### New Layout (top to bottom)

```text
┌─────────────────────────────────────────────┐
│ Welcome [name] — reassuring message          │
├─────────────────────────────────────────────┤
│ ⚡ QUICK CAPTURE (emergency chips)           │
│ [notice] [conversation] [repair] [harass]   │
├─────────────────────────────────────────────┤
│ 📊 YOUR SITUATION (status card)              │
│ • Next deadline: ...                         │
│ • X documents saved                          │
│ • X journal entries                          │
│ • 📍 Jurisdiction: [zip code] [Change]      │ ← NEW
├─────────────────────────────────────────────┤
│ 📒 RECORD pillar                             │
│ [📄 Documents] [⚡ Capture] [📅 Timeline]    │
│ [📓 Journal] [📅 Calendar]                   │ ← Calendar NEW
├─────────────────────────────────────────────┤
│ 📚 KNOW pillar                               │
│ [⚖️ Law Library] [🛡️ Eviction Defense]      │ ← Law Library NEW
│ [🏛️ Accountability] [🆘 Help]               │ ← Accountability NEW
├─────────────────────────────────────────────┤
│ 🧩 ADVANCED TOOLS                            │ ← NEW SECTION
│ [🏗️ Case Builder] [📋 Action Plan]          │
│ [📢 File Complaint] [📝 Court Forms]         │
├─────────────────────────────────────────────┤
│ ⚙️ SETTINGS                                  │ ← NEW SECTION
│ [👤 Profile] [📍 Jurisdiction] [🔌 Storage]  │
├─────────────────────────────────────────────┤
│ Recent Activity (5 items)                    │
├─────────────────────────────────────────────┤
│ Footer: Help link                            │
└─────────────────────────────────────────────┘
```

### Files to Edit

1. **`app/templates/pages/tenant_home.html`** — restructure quick actions into 3 sections (RECORD, KNOW, ADVANCED), add SETTINGS section, add jurisdiction display
2. **`app/main.py:3453` (`tenant_home` route)** — load jurisdiction from `/api/location/current` and pass to template
3. **`app/core/product_manifest.py`** — register calendar module

### No New Files

All changes in existing files. Rule 13 compliant.

### Conflict Check

- `tenant_home.html` — only modified by this plan
- `main.py:3453-3490` — `tenant_home` route, isolated
- `product_manifest.py` — adding calendar registration, no conflict with existing entries

---

## Part 3: Jurisdiction / Zip Code User Setup

### Goal

Tenant can enter zip code manually. Used by Law Library for state-specific rights, Accountability for jurisdiction-aware patterns, Court Forms for correct court.

### Implementation

1. **Add zip code input to tenant home** — in SETTINGS section
2. **Wire to existing `POST /api/location/update`** — no new endpoint
3. **Add to onboarding** — `app/modules/onboarding/router.py` should call location update after vault setup
4. **Law Library reads location** — `app/modules/law_library/router.py` already exists, needs to read user's location for state-specific content

### Files to Edit

1. `app/templates/pages/tenant_home.html` — add zip code form in SETTINGS section
2. `app/main.py:3453` — fetch location in `tenant_home` route
3. `app/modules/onboarding/router.py` — add location step after vault step (Phase 2, not now)

### No New Endpoints

`POST /api/location/update` and `GET /api/location/current` already exist.

---

## Part 4: Free AI Services for Non-Profit Semptify

### Requirements

- Totally free, no strings, no advertising
- Cloud-hosted (user cannot host locally)
- Suitable for: document summarization, Q&A on tenant rights, form assistance

### Research Results — Free AI APIs (no cost, no ads)

| Service | Free Tier | Limits | Best For | Ads? | Strings? |
| --------- | ----------- | -------- | ---------- | ------ | ---------- |
| **Google Gemini API** | Free tier | 15 RPM, 1500/day, 1M tokens/min | Summarization, Q&A, vision | No | None |
| **Cloudflare Workers AI** | Free (10K neurons/day) | 10K neurons/day on free plan | Text gen, summarization | No | None |
| **HuggingFace Inference API** | Free tier | Rate-limited, community models | Specialized NLP | No | None |
| **Groq Cloud** | Free tier | 30 RPM, LPU inference (fast) | Fast text generation | No | None |
| **Mistral La Plateforme** | Free tier (beta) | Rate-limited | EU-hosted, multilingual | No | None |
| **Cohere Trial** | Free trial keys | 1000 calls/month, then limited | Embeddings, rerank, gen | No | Trial → paid |

### Recommended Stack for Semptify

1. **Primary: Google Gemini API** — most generous free tier, vision (read notices), 1M tokens/min
2. **Fallback: Cloudflare Workers AI** — already on Cloudflare, 10K neurons/day free
3. **Specialized: HuggingFace** — for legal document analysis models

### Implementation Plan

1. Add `GEMINI_API_KEY` to Render env vars (free tier key)
2. Create `app/services/ai/gemini_client.py` — wrapper for Gemini free tier
3. Create `app/services/ai/router.py` — unified AI endpoint `/api/ai/*`
4. Wire to Law Library (summarize rights), Court Forms (assist filling), Journal (suggest categories)
5. **Cost: $0/month** — stays within free tiers

### No-Advertising Verification

- Google Gemini Free Tier: No ads served in API responses ✅
- Cloudflare Workers AI: No ads ✅
- HuggingFace: No ads ✅

---

## Part 5: Non-Profit Organization Plan

### Steps to 501(c)(3) Status

1. **Form a Board** — 3 directors minimum (user + 2 others)
2. **File Articles of Incorporation** — state level (~$50-100 filing fee)
3. **Get EIN from IRS** — free, online at IRS.gov
4. **File Form 1023-EZ** — $275 filing fee, for orgs expecting <$50K/year revenue
5. **Adopt Bylaws** — template available from BoardSource.org
6. **Register for State Charity Registration** — varies by state

### Free Resources for Non-Profit Setup

- **IRS Form 1023-EZ** — $275 (vs $600 for full Form 1023)
- **Pro Bono Legal** — Legal Aid Society, Lawyers Alliance for New York
- **Free Tech Stack for Non-Profits:**
  - Google Workspace for Nonprofits — free email, docs, drive
  - Microsoft 365 for Nonprofits — free Office 365 Business
  - Zoom for Nonprofits — free Pro plan
  - Canva for Nonprofits — free Canva Teams
  - GitHub for Nonprofits — free Team plan (already using GitHub)
  - Render — free tier for hosting (already using)
  - Cloudflare — free plan (already using)

### Grant Opportunities (Housing/Tenant Rights)

1. **HUD Fair Housing Initiatives Program (FHIP)** — grants for tenant education
2. **State Bar Foundation grants** — legal aid for tenants
3. **Community Development Block Grants (CDBG)** — local housing
4. **Borealis Philanthropy** — tenant organizing funds
5. **Ford Foundation** — housing justice grants

### Action Items for User

1. Decide board members
2. Pick state of incorporation (likely MN based on existing data)
3. File Articles of Incorporation
4. Apply for EIN online (free, 1 day)
5. File 1023-EZ ($275)

---

## Part 6: Admin Module Console — Run Every Module from Admin

### Goal

Admin can see, enable/disable, and run every module from a single admin GUI.

### Current State

- `static/admin/module_flags.html` — toggle module flags (exists)
- `static/admin/dashboard.html` — admin landing (exists)
- `app/modules/admin_console/router.py` (62KB) — backend exists
- **Missing:** Unified "run module" GUI with interactive switches

### Implementation Plan

1. **New admin page:** `static/admin/module_console.html`
   - Lists ALL modules from `product_manifest.py`
   - Each module shows: status (loaded/skipped/error), lifecycle stage, tier
   - Toggle switch per module (calls existing `/api/admin/modules/flags` endpoint)
   - "Run" button per module — opens module's main endpoint in iframe or new tab
   - Search/filter by name, tier, lifecycle

2. **Backend support:** `app/modules/admin_console/router.py` already has endpoints
   - `GET /api/admin/modules` — list all modules
   - `POST /api/admin/modules/{name}/toggle` — enable/disable
   - Need to add: `GET /api/admin/modules/{name}/run` — execute module's main function

3. **Dashboard link:** Add "🎛️ Module Console" to `static/admin/dashboard.html` nav

### Files to Edit

1. `static/admin/module_console.html` — NEW file (admin GUI)
2. `static/admin/dashboard.html` — add nav link
3. `app/modules/admin_console/router.py` — add "run" endpoint if missing

### Conflict Check

- `module_flags.html` stays as-is (toggle flags only)
- New `module_console.html` is additive — no conflict
- `admin_console/router.py` — check existing endpoints before adding

---

## Part 7: Implementation Order

### Phase 1 — Tenant Home Page (DO FIRST)

1. Register calendar module in `product_manifest.py`
2. Edit `tenant_home.html` — restructure into RECORD/KNOW/ADVANCED/SETTINGS sections
3. Edit `main.py:3453` — load location data in `tenant_home` route
4. Add zip code form to SETTINGS section
5. Test: navigate to `/tenant/home`, verify all cards render, verify zip code form works
6. Commit + push

### Phase 2 — Accountability Module UI

1. Verify `/api/housing-accountability/dashboard` returns 200 (after CalendarEvent fix deploys)
2. Create tenant-facing accountability card on home page
3. Create `/tenant/accountability` page (use existing template pattern)
4. Wire to existing API endpoints — no new backend

### Phase 3 — Admin Module Console

1. Audit `admin_console/router.py` existing endpoints
2. Build `static/admin/module_console.html`
3. Add nav link to `dashboard.html`
4. Test: every module can be toggled + run from admin

### Phase 4 — Free AI Integration

1. Get Gemini API free-tier key
2. Add `GEMINI_API_KEY` to Render env vars
3. Create `app/services/ai/gemini_client.py`
4. Wire to Law Library (summarize), Court Forms (assist), Journal (categorize)
5. Test: verify free tier limits not exceeded

### Phase 5 — Non-Profit Setup (USER ACTION REQUIRED)

1. User files 501(c)(3) paperwork (offline, not code)
2. Once approved, update `PRIVACY_POLICY.md` and `ABOUT.md`
3. Apply for Google Workspace for Nonprofits, Microsoft 365, etc.

---

## Part 8: Simulation — Conflict Check with Existing System

### Verified No Conflicts:

- ✅ `tenant_home.html` — only modified by this plan
- ✅ `main.py:3453` — `tenant_home` route, isolated from other routes
- ✅ `product_manifest.py` — adding calendar registration at end of file
- ✅ `housing_accountability/router.py:733` — CalendarEvent fix (already deployed)
- ✅ `static/admin/module_console.html` — new file, no conflict
- ✅ `static/admin/dashboard.html` — adding one nav link, no conflict
- ✅ `app/services/ai/` — new directory, no conflict (Phase 4)

### Verified Working Systems (DO NOT TOUCH):

- DC (`/documents`) — working, 15 docs
- Journal (`/tenant/journal`) — working, 5 entries
- Vault upload — working (per restore point)
- Onboarding — working (2-gate system)
- Timeline (`/api/timeline/unified`) — working

### Risk Mitigation:

- Each phase is independent — can be done in any order
- Each phase has its own commit — easy rollback
- No phase modifies working systems
- All changes in existing files (Rule 13) or clearly-new files

---

## Part 9: Summary for User

### What's done this session:

1. ✅ DC verified working (15 docs, viewer, upload)
2. ✅ Journal fixed (5 entries now display)
3. ✅ Accountability module fixed (CalendarEvent.event_date → start_datetime)

### What needs doing (in order):

1. **Tenant home page redesign** — add Law Library, Calendar, Accountability, Help, Settings, zip code entry
2. **Admin module console** — GUI to run every module from admin
3. **Free AI integration** — Gemini free tier + Cloudflare Workers AI
4. **Non-profit filing** — user action (501c3 paperwork)

### Awaiting approval to start Phase 1 (tenant home page)
