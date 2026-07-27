# Semptify Active Context

**Last Updated**: 2026-07-26 (Task 3 content pass on main; Tasks 1–4, 8–10 complete; Tasks 5–7, 11 are next)

---

## 🎯 Current Priority: Trauma-Informed UX + Admin/Logging + Input/Import/Resource Directory

Master Handoff promoted from `temp/Semptify_MASTER_HANDOFF.md`, consolidating:
- `temp/Semptify_TraumaInformed_UX_Admin_Spec.md`
- `temp/Semptify_Input_Import_Resource_Spec.md`

Scope: 11 build tasks across shared UX foundation, footer/help content, voice-to-text,
multi-language, mobile media capture, third-party contact model, asymmetric redaction,
communication import pipeline, and resource directory. All tasks are tenant-side,
public-service, and follow the four-pillar model (RECORD/KNOW/ACT/GOVERN).

Task 1 — Shared UX foundation — is complete (viewport-locked CSS, function-budget classes,
persistent "Get help now" in `gui/base.html`, calm/alarm color tokens, convention documented).

Previous priority: Review/merge Funding Forge standalone add-on — completed 2026-07-25.
Previous priority before that: GUI Phase 1 — four-pillar interface (`Home`, `Record`, `Know`, `Act`).

## ✅ Completed 2026-07-25 Session

- **Funding Forge add-on** — standalone package `funding_forge/` with FastAPI backend, async SQLAlchemy models, full CRUD JSON API, SPA GUI, document uploads, admin-only auth, optional Cloudflare R2 document storage, and 33 pre-seeded suggested funding entities. Tests pass.
- **Document Center gap fill** — persisted field confirm/correct state via `VaultReviewState`, user-controlled verification status, real document sharing via `DocumentShare`, old `documents.html` pages redirected to `/dc`, and frontend wiring in `document_center.html` to load/save state and create share links. Backend and integration tests pass; full live browser viewer verification pending storage-connected onboarding.

## ✅ Completed 2026-07-19 Session

- **Icon replacement policy applied**: 5 GUI templates + `document_center.html` now use
  minimal unicode markers (`▸`, `◆`, `●`, `○`) instead of emoji. Functional status markers
  (`✕`, `↗`) preserved.
- **Sync-orchestrator hook loop fixed**: root cause was CRLF writes + non-idempotent
  timestamps. All sync-chain Python scripts now use `newline="\n"` + trailing newline +
  only-write-if-changed.
- **Document Center verified live**: 22 DC tests pass, 3-pane layout live at
  `/tenant/documents`, OAuth-gated as expected.
- **DC Slice 2+ complete**: viewer rendering wired to real vault data (`/api/dc/document/{id}/view`), unlock pattern panel uses `/api/dc/unlocks`, all `alert()`/`prompt()` removed from `document_center.html` in favor of `SemptifyFeedback` + non-blocking `showValueModal()`.
- **Calendar total-recollection viewer complete**: `calendar.html` now pulls the full `GET /api/calendar/` timeline, groups events by month, and uses minimal unicode markers for event type icons.
- **Timeline interactive query viewer complete**: `timeline.html` now wires search, date-axis, item-type, urgency, evidence-only, and date-range filters to `POST /api/timeline/unified`; all emoji icons and `alert()` fallbacks removed.
- **Comms Log complete**: `comms_log.html` and `GET /comms-log` route added; logs are stored as `event_type='communication'` timeline events and displayed on `/comms-log`.
- **MNDES todo-021 unblocked**: `MNDESRestClient` speculative REST implementation added; related `MNDESExhibitPackage`/`MNDESExhibitService` model and serialization bugs fixed; `tests/test_mndes_service.py` passes 19/19.
- **Visual smoke test passed**: all 4 public GUI pages verified on live deploy.
- **Attorney Intake Packet rendering + GUI trigger**: PDF/ZIP export endpoints added to
  `app/modules/case_builder/router.py`, download UI added to `case_builder.html`,
  `test_intake_packet.py` updated with 3 new helper tests, all 21 tests pass.

## 🅿️ NEXT TO BUILD (in priority order) — Master Handoff

| # | Project | Design Doc | Status | Blocked By |
|---|---------|------------|--------|------------|
| 1 | **Shared UX foundation** — viewport-locked desktop template, function-budget convention, persistent "Get help now" component, calm/alarm CSS tokens | `Semptify_MASTER_HANDOFF.md` section A–B | ✅ Complete | — |
| 2 | **Footer + Help page redo** — trust-signaling footer, "What's happening to you right now?" Help page | `Semptify_MASTER_HANDOFF.md` Task 2 | ✅ Complete | — |
| 3 | **Content pass** — welcome/about plain-language rewrite, words of wisdom moved to About only, subject starters | `Semptify_MASTER_HANDOFF.md` Task 3 | ✅ Complete | — |
| 4 | **Admin/dev access + logging** — Tailscale-gated admin, JSON logging, R2 async flush, live tail, feature flags, health/status page | `Semptify_MASTER_HANDOFF.md` Task 4 | ✅ Complete | — |
| 5 | **Voice-to-text** — Web Speech API client-side default, Whisper fallback with raw-audio discard | `Semptify_MASTER_HANDOFF.md` Task 5 | ✅ Complete | — |
| 6 | **Multi-language i18n** — JSON/.po catalogs, human-reviewed legal/plain-language translation | `Semptify_MASTER_HANDOFF.md` Task 6 | ✅ Complete | Human review of 13 stub catalogs pending |
| 7 | **Mobile media capture** — `getUserMedia` photo/audio evidence capture with recording-consent note | `Semptify_MASTER_HANDOFF.md` Task 7 | ✅ Complete | Browser permission UX pending live device test |
| 8 | **Third-party contact model** — `ThirdPartyContact` table, case-linked, entity types, audit source | `Semptify_MASTER_HANDOFF.md` Task 8 | ✅ Complete | — |
| 9 | **Asymmetric redaction pass** — strip user's own PII while preserving third-party info from imports | `Semptify_MASTER_HANDOFF.md` Task 9 | ✅ Complete | — |
| 10 | **Communication import pipeline** — `.eml`/`.mbox`, SMS CSV/XML, voicemail audio→transcription→discard, call logs CSV | `Semptify_MASTER_HANDOFF.md` Task 10 | ✅ Complete | — |
| 11 | **Resource directory** — `Resource` table, bulk CSV import, staleness tracking | `Semptify_MASTER_HANDOFF.md` Task 11 | 🅿️ Pending | None |

> **Open decisions before Tasks 4/6/9–10 can be fully scoped:**
> 1. ✅ Log retention window — **90 days rolling** (resolved 2026-07-26).
> 2. ✅ Confirmed language priority list — English, Spanish, Somali, Hmong, Arabic, Amharic, Tigrinya, Mandarin, French, German, Korean, Japanese, Portuguese, Italian.
> 3. ✅ Redaction matching strategy — user-known contact info plus heuristic PII detection with a `ThirdPartyContact` allowlist.

### ✅ Completed (reference, not to-do)
- Funding Forge — complete 2026-07-25.
- UPL guardrail wiring — complete 2026-07-10.
- GUI Phase 1 — complete 2026-07-19.
- Document Center — 22 tests pass, live at `/tenant/documents`.
- Attorney Intake Packet — complete 2026-07-19.
- Journal, Rent Ledger, Packet Builder — complete 2026-07-20.

## 🎯 Candidate Next Priorities (awaiting user direction)

- **Packet Builder UI** — four-pillar GUI panel for building and downloading packets. Not yet built.
- **vault_sync** — ON HOLD per user 2026-07-01. Plan captured in memory.

### Action Feedback Helper — COMPLETE
All 13 retrofittable pages now use `SemptifyFeedback.*` directly. No `alert()` fallbacks
remain. Helper is globally loaded via `feedback.js` in `base.html`.

### GUI Phase 1 — Four-Pillar Interface Model
The user-facing GUI is organized around the four-pillar model defined in
`Semptify_Site_GUI_Framework.md`:
- **RECORD** — capture and organize evidence (Vault, Timeline, Document Center, Calendar, Journal, Comms Log, Rent Ledger, PDF Tools)
- **KNOW** — facts only, no opinions (Library, State Laws, Context Engine, RISC, Court Case Lookup, Search)
- **ACT** — lawful, guided action (Case Builder, Eviction Defense, Court Forms, Complaint Wizard, Plan Maker)
- **GOVERN** — platform integrity (Admin Console, Forge, Capabilities, Onboarding, Auth, Audit Logs)

The older 2026-06-28 Journal/Calendar/Timeline vision is superseded by this framework.
Each RECORD feature still does the same work (Journal captures, Calendar shows all
events, Timeline queries data), but now sits inside the four-pillar structure.

### Document Center — IMPLEMENTED
Design docs in `docs/planning/`, implementation in `app/modules/document_center/`.
3-pane layout (vault list / viewer / overlays), 5 actions (upload/store/process/review/share),
per-document-type checklists, verification states, unlock pattern. Slice 2+ wired the viewer
and unlock panel to live vault data. 22 tests pass.

---

## 🚫 Anti-Priorities (Don't Start These)

> **Exception for this session:** the Master Handoff tasks below are explicitly promoted
to active priority, overriding the "no new features" rule for this scope only.
> This exception is recorded in the Decision Log.

1. **Refactoring** unrelated to the Master Handoff tasks
2. **Documentation** that isn't critical path for the Master Handoff
3. **Testing** of non-core systems
4. **New features outside the Master Handoff scope**

---

## 📋 Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-07-26 | ✅ Log retention window set to 90 days rolling | Default recommended in `Semptify_TraumaInformed_UX_Admin_Spec.md`; balances operational troubleshooting needs against unbounded R2 storage growth. Task 4 admin/logging can now scope R2 lifecycle policy and async flush with a fixed window. |
| 2026-07-25 | ✅ Master Handoff promoted to active priority (11 tasks: UX foundation, admin/logging, voice, i18n, media capture, contacts, redaction, import pipeline, resource directory) | User explicitly promoted `temp/Semptify_MASTER_HANDOFF.md` to active priority; recorded in this file. Anti-priority "no new features" temporarily lifted for this scope only. Three open decisions (retention, language list, redaction strategy) still need resolution before full scoping. |
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
