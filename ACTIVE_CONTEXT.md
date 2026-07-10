# Semptify Active Context

**Last Updated**: 2026-07-10 AM

---

## 🎯 Current Priority: UPL guardrail infrastructure + GUI Phase 1 prep

### UPL Guardrail Infrastructure — IN PROGRESS (2026-07-07)
- `app/core/upl_guardrails.py` shipped to main — `UPLRiskTier` enum (LOW, LOW_MEDIUM, MEDIUM, MEDIUM_HIGH, HIGH, VERY_HIGH_DO_NOT_BUILD) is the SSOT for legal-risk classification.
- **Follow-up (not urgent)**: Add `upl_risk_tier: UPLRiskTier` field to `ModuleEntry` in `product_manifest.py` and register the 8 modules (eviction_notice_explainer, complaint_wizard, court_prep, case_builder, response_letter_generator, eviction_defense_content, library, ai_copilot) with their tiers from the matrix. Requires the tier matrix from the project owner.
- **Parallel branch**: `feature/attorney-intake-packet` has uncommitted attorney intake packet scaffold work (separate, in-progress). Do not mix with UPL work.

### Phase 5b — Action Feedback Helper: ✅ COMPLETE (2026-06-30 AM)

`SemptifyFeedback` helper is globally loaded via `static/templates/base.html` → `static/components/feedback.js`. All retrofitted pages now call `SemptifyFeedback.*` directly with no `alert()` fallbacks.

**Retrofit completed across 13 pages:**
- **Tier 1 (tenant-facing):** `tenant/journal.html`, `tenant/tools/letters.html`, `tenant/tools/deadlines.html`
- **Tier 2 (admin):** `admin/dashboard.html` (22 alerts removed), `admin/dev_lab.html` (11 alerts), `admin/review-checklist.html`, `admin/module_flags.html`, `admin/api_workbook.html`
- **Tier 3 (office):** `office/inbox.html`, `office/delivery.html`, `office/signer.html`, `office/vault.html`
- **Tier 4 (tools):** `tools/generators.html`, `tools/calculators.html`, `tools/checklists.html`
- **Tier 5:** `components/vault-portal.html`, `templates/journal-refactored.html`

**Verification:** `grep "else { alert(" static/**/*.html` returns zero results.

### Phase 4 — Role Development: ✅ COMPLETE (2026-06-24)

| Role | Status | Endpoints |
|------|--------|-----------|
| **4.1 TENANT** | ✅ Complete | 41 endpoints (tenant_defense, state_laws, housing_accountability, free_api_pack) |
| **4.2 ADVOCATE** | ✅ Complete | 14 endpoints (dashboard, clients, queue, intake, timeline, documents, review, annotate, overlays, invite-codes, link-request, my-advocates) |
| **4.3 MANAGER** | ✅ Complete | 10 endpoints (dashboard-stats, cases, staff, activity, assign, status, bulk/export, reports/cases, reports/staff, staff/role) |
| **4.4 LEGAL** | ✅ Complete | 27 endpoints (matters, filings, discovery, exhibits, overlays) |
| **4.5 ADMIN** | ✅ Complete | 41+ endpoints (admin console, module flags, analytics, batch ops, capabilities) |
| **4.6 JUDGE** | ✅ Merged | Merged into Legal as sub-role (is_legal_sub_role(user_id, 'judge')) |

### Phase 5a — Context Engine + Page Composer: ✅ COMPLETE (2026-06-24 PM)

| Component | Status | Endpoints |
|-----------|--------|-----------|
| **Context Engine** | ✅ Complete | 9 endpoints (/api/context/*) — subjects, facts, refresh, stories, moderate, verify, overview |
| **Page Composer** | ✅ Complete | 3 endpoints (/api/page/*) — composed view, preview, list |
| **Case Builder wiring** | ✅ Complete | `get_context_facts` action + enriched `analyze_defenses` |
| **Complaint Wizard wiring** | ✅ Complete | `get_complaint_context` action + enriched `create_complaint` |
| **Tenant Defense wiring** | ✅ Complete | `get_defense_context` action + enriched `get_case_progress` |
| **DB migration** | ✅ Shipped | `20260624_add_context_engine_tables.py` creates context_facts + tenant_stories |

### Filedored Overlay Integration Fix: ✅ COMPLETE (2026-06-29 PM)

- All 3 callers (`filedored/router.py`, `main.py` event subscriber, `documents/router.py` step 9) now build and pass `overlay_manager` to `process_uploaded_document()`
- Fixed 2 router signature bugs (`get_document` arity, non-existent `_get_document_content`)
- Fixed 4 pre-existing `await`-on-sync-function bugs in filedored router endpoints
- Commit `19d0860` shipped 2026-06-29 PM

### Repo Cleanup: ✅ COMPLETE (2026-06-29 PM)

- 108 obsolete docs archived to `archive/obsolete-2026-06-29/` (git history preserved)
- Root .md files reduced from 80+ to 17 canonical/active docs
- `docs/` reduced from 40+ to 22 active docs

### Litigation Intelligence Module — ✅ Activated 2026-06-24
- 17 endpoints live at `/api/litigation-intelligence/*`
- Was INACTIVE since 2026-06-23 due to dataclass field ordering bugs (now fixed)
- Only remaining stub: graph_engine (statistics endpoint returns `{"status": "not_implemented"}` for graph section)

---

## 🅿️ NEXT TO BUILD (in priority order)

| # | Project | Design Doc | Status | Blocked By |
|---|---------|------------|--------|------------|
| 1 | **UPL guardrail wiring** — add `upl_risk_tier` to `ModuleEntry`, register 8 modules with tiers | `app/core/upl_guardrails.py` | ✅ Complete 2026-07-10 | — |
| 2 | **GUI Phase 1 — Four-pillar interface** | `Semptify_Site_GUI_Framework.md` + `Semptify_Master_Inventory_LIVE.xlsx` | 🅿️ Next priority | — |
| 3 | **Document Center planning** | `docs/planning/DOCUMENT_CENTER_PLAN.md` | 🅿️ Pending | — |
| 4 | **Attorney Intake Packet** (parallel branch) | `feature/attorney-intake-packet` | 🅿️ In progress (uncommitted) | User review of scaffold |

### Action Feedback Helper — COMPLETE
All 13 retrofittable pages now use `SemptifyFeedback.*` directly. No `alert()` fallbacks remain. Helper is globally loaded via `feedback.js` in `base.html`.

### GUI Phase 1 — Four-Pillar Interface Model
The user-facing GUI is now organized around the four-pillar model defined in `Semptify_Site_GUI_Framework.md`:
- **RECORD** — capture and organize evidence (Vault, Timeline, Document Center, Calendar, Journal, Comms Log, Rent Ledger, PDF Tools)
- **KNOW** — facts only, no opinions (Library, State Laws, Context Engine, RISC, Court Case Lookup, Search)
- **ACT** — lawful, guided action (Case Builder, Eviction Defense, Court Forms, Complaint Wizard, Plan Maker)
- **GOVERN** — platform integrity (Admin Console, Forge, Capabilities, Onboarding, Auth, Audit Logs)

The older 2026-06-28 Journal/Calendar/Timeline vision is superseded by this framework. Each RECORD feature still does the same work (Journal captures, Calendar shows all events, Timeline queries data), but now sits inside the four-pillar structure instead of being its own top-level model.

### Document Center Planning
Design docs committed this session in `docs/planning/`:
- `DC_DESIGN_SONNET.md`, `DC_HANDOFF_SONNET.md`, `DOCUMENT_CENTER_PLAN.md`

---

## 🚫 Anti-Priorities (Don't Start These)

1. **New features** that aren't Action Feedback, GUI Phase 1 (four-pillar interface), or DC planning
2. **Refactoring** unrelated to Phase 5
3. **Documentation** that isn't critical path
4. **Testing** of non-core systems

---

## 📋 Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-07-10 | ✅ Superseded 2026-06-28 GUI vision (Journal/Calendar/Timeline) with four-pillar model (RECORD/KNOW/ACT/GOVERN) | Framework formalized across a full planning session; GUI Screens 1-3 (nav shell, home, record) already shipped under new model. See `Semptify_Site_GUI_Framework.md` for the canonical pillar definitions. |
| 2026-06-30 AM | ✅ Action Feedback helper retrofit complete | 13 pages retrofitted. All `alert()` fallbacks removed. `SemptifyFeedback` is globally loaded, so `if (window.SemptifyFeedback)` guards and `else { alert() }` branches were dead code. Also added success toast to journal save (was silently succeeding). |
| 2026-06-29 PM | ✅ Repo cleanup — 108 obsolete docs archived | Reduce doc sprawl from 130+ to ~40 active docs. All obsolete docs moved to `archive/obsolete-2026-06-29/` with git history preserved. |
| 2026-06-29 PM | ✅ Filedored overlay integration fixed | 3 callers now wire overlay_manager. Router signature bugs fixed. Commit `19d0860`. |
| 2026-06-24 PM | ✅ Context Engine + Page Composer complete | 9+3 endpoints live, 4 consumers wired, migration shipped (commit 375b45d) |
| 2026-06-24 PM | ✅ Context Engine wired into 4 consumers | Case Builder, Complaint Wizard, Tenant Defense, Page Composer |
| 2026-06-24 | ✅ Phase 4 role development complete | All 6 roles have full endpoint coverage |
| 2026-06-24 | ✅ Litigation Intelligence activated | Fixed dataclass field ordering bugs, 17 endpoints live |
| 2026-06-24 | ✅ Advocate dashboard added | GET /api/advocate/dashboard with aggregate stats |
| 2026-06-21 | ✅ Completed audit + design docs | STATUS_AUDIT.md, ACTION_FEEDBACK_AUDIT.md written |
| 2026-06-21 | ✅ Context Engine design captured | PostgreSQL cache, stories after task, avoided_court hero |
| 2026-06-21 | ✅ Action Feedback design captured | SemptifyFeedback helper, 5-tier retrofit |
| 2026-06-21 | Start Phase 4 — Role Development | Audit complete, ready to fix stubs |
| 2026-06-04 | Reconnect session persistence fix | DB-first session save |
| 2026-04-21 | Completed Communication System | Document fill/sign + messaging + vault storage |
| 2026-04-21 | Completed Unified Overlay System | All components integrated |

---

## 🔗 Quick Links (canonical docs only)

- **Project Bible**: `PROJECT_BIBLE.md` — governance + doc hierarchy
- **Build Status**: `BUILD_STATE.md` — live deploy state
- **Status Audit**: `STATUS_AUDIT.md` — 2026-06-21 module snapshot
- **Stub Audit**: `STUB_AUDIT.md` — 2026-06-19 TODO/stub inventory
- **Action Feedback Audit**: `ACTION_FEEDBACK_AUDIT.md` — Phase 5b design
- **GUI Framework**: `Semptify_Site_GUI_Framework.md` — canonical four-pillar model (RECORD/KNOW/ACT/GOVERN)
- **Roadmap**: `ROADMAP_TO_PUBLIC_RELEASE.md`
- **Blueprint**: `BLUEPRINT.md`
- **System Manifest**: `SEMPTIFY_SYSTEM_MANIFEST.md` — module registry
- **Build Guide**: `BUILD_GUIDE_SSOT.md`
- **Deployment**: `DEPLOYMENT_READINESS.md`
- **Security**: `SECURITY_AND_PRIVACY_ARCHITECTURE.md`
- **Vault Paths**: `app/core/vault_paths.py`

---

*This file is the single source of truth for what is being worked on RIGHT NOW.*
