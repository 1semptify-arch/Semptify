# Semptify Active Context

**Last Updated**: 2026-07-20

---

## 🎯 Current Priority: GUI Phase 1 — four-pillar interface (`Home`, `Record`, `Know`, `Act`)

Focusing on the tenant-facing GUI. The `/gui/*` four-pillar navigation is in place.
`know.html`, `act.html`, `record.html`, `home.html` all extend `gui/base.html` and
link to real routes. Icon policy decided and applied 2026-07-19: minimal unicode
markers (`▸`, `◆`, `●`, `○`) replace emoji across all 5 GUI templates + Document Center.

Sync-orchestrator pre-commit hook loop fixed 2026-07-19 (commits `05119a1`, `b53b780`):
LF + trailing newline + idempotent writes. All hooks now pass clean, no `--no-verify`.

## ✅ Completed 2026-07-19 Session

- **Icon replacement policy applied**: 5 GUI templates + `document_center.html` now use
  minimal unicode markers (`▸`, `◆`, `●`, `○`) instead of emoji. Functional status markers
  (`✕`, `⚙`, `↗`, `✅`, `🔄`, `⚠️`, `⬜`, `∅`, `!`) preserved.
- **Sync-orchestrator hook loop fixed**: root cause was CRLF writes + non-idempotent
  timestamps. All sync-chain Python scripts now use `newline="\n"` + trailing newline +
  only-write-if-changed.
- **Document Center verified live**: 22 DC tests pass, 3-pane layout live at
  `/tenant/documents`, OAuth-gated as expected.
- **Visual smoke test passed**: all 4 public GUI pages verified on live deploy.
- **Attorney Intake Packet rendering + GUI trigger**: PDF/ZIP export endpoints added to
  `app/modules/case_builder/router.py`, download UI added to `case_builder.html`,
  `test_intake_packet.py` updated with 3 new helper tests, all 21 tests pass.

## 🅿️ NEXT TO BUILD (in priority order)

| # | Project | Design Doc | Status | Blocked By |
|---|---------|------------|--------|------------|
| 1 | **UPL guardrail wiring** | `app/core/upl_guardrails.py` | ✅ Complete 2026-07-10 | — |
| 2 | **GUI Phase 1 — Four-pillar interface** | `Semptify_Site_GUI_Framework.md` | ✅ Pages live + icons shipped 2026-07-19 | — |
| 3 | **Document Center** | `docs/planning/DOCUMENT_CENTER_PLAN.md` | ✅ Implemented (22 tests pass, live at `/tenant/documents`) | — |
| 4 | **Attorney Intake Packet** — PDF/ZIP rendering + GUI trigger | `app/modules/case_builder/router.py:2477-2930` | ✅ Complete 2026-07-19 | — |
| 5 | **Journal module** — free-form tenant journal CRUD + briefcase integration | `app/modules/journal/router.py` | ✅ Complete 2026-07-20 | — |
| 6 | **Rent Ledger** — full account ledger (payments, fees, deposits, credits, charges) with running balance | `app/modules/rent/router.py` | ✅ Complete 2026-07-20 | — |

> **Note:** Rows #1-#6 are complete. The `feature/attorney-intake-packet` branch was merged and deleted on 2026-07-10. The endpoint `GET /cases/{case_id}/intake-packet` returns a canonical facts-only JSON packet; `/pdf` and `/zip` render it for attorney review. GUI download panel added to `case_builder.html`.
> **Journal:** `/api/journal` CRUD, `/api/journal/summary`, and `/tenant/journal` are live; `app/modules/journal/tests/test_journal.py` passes 8/8.
> **Rent Ledger:** `/api/rent/payments` endpoints support full ledger entry types and compute running balance; `app/modules/rent/tests/test_ledger.py` passes 6/6.

## 🎯 Candidate Next Priorities (awaiting user direction)

- **Calendar auto-populate** — todo-043. Wire documents, deadlines, and ledger into Calendar events.
- **Calendar total-recollection viewer** — RECORD pillar. Not yet built.
- **Timeline interactive query viewer** — RECORD pillar. Not yet built.
- **Comms Log** — RECORD pillar. Not yet built.
- **vault_sync** — ON HOLD per user 2026-07-01. Plan captured in memory.
- **DC Slice 2+** — viewer rendering, unlock pattern wiring (DC_DESIGN_SONNET.md open checkboxes)

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
per-document-type checklists, verification states, unlock pattern. 22 tests pass.

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
