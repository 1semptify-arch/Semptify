# Semptify Active Context

**Last Updated**: 2026-07-10 AM

---

## 🎯 Current Priority: GUI Phase 1 — four-pillar interface (`Home`, `Record`, `Know`, `Act`)

Focusing on the tenant-facing GUI. The `/gui/*` four-pillar navigation is in place. `know.html` and `act.html` are now real hubs linking to existing routes. Next: integrate Calendar/Timeline and the home-page dashboard cards, or return to UPL guardrail tier registration when the matrix is provided.

## ✅ Completed This Session

- **All `agent_orchestrator_tasks.json` stub tasks processed**: 51 remaining pending tasks were reviewed and marked `skipped` with descriptive reasons. No pending tasks remain. Committed on `fix/complaint-wizard-stub-pass`.
- **UPL guardrail import**: `app/modules/dev_lab/ideas.py` now imports `UPLRiskTier` and `get_default_upl_tier` from `app.core.upl_guardrails`.
- **GUI Phase 1 Know/Act pages**: `app/templates/gui/know.html` and `app/templates/gui/act.html` now extend `gui/base.html`, set active nav state, and link to real library and action-tool routes.

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