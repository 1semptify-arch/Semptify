# Semptify Active Context

**Last Updated**: 2026-06-21

---

## 🔧 Latest: Audit + Design Docs (2026-06-21)

| Output | File | Status |
|-----|------|--------|
| **Module/function/contract audit** | `STATUS_AUDIT.md` | ✅ Complete |
| **Context Engine design** | (captured in todo, write-up pending) | ✅ Designed |
| **Action Feedback audit** | `ACTION_FEEDBACK_AUDIT.md` | ✅ Complete |

### Audit Headlines
- **95** active module registrations, **6** INACTIVE
- **49** `FunctionGroupContract` registrations across **12** modules — **70+ modules have zero contracts** (biggest hole)
- **6** `NotImplementedError`, **11** `"not_implemented"` stubs (all in `free_api_pack.py`)
- **53** TODO markers, **60** pass-only bodies, **148** HTML placeholders
- **124** fetch() calls in HTML, **76 (62%) silent failures**, **82** alert() calls, **0** toast helpers

### Context Engine — Key Decisions
- Cache: **PostgreSQL `context_facts` table** (not Redis — already running, no new infra)
- Stories surface **after task completion** (not page load) — saved to user's journal
- Story frame: **`avoided_court` is the hero**, not "I won" — documentation is the win
- 13 subjects: eviction, repair, rent, lease, deposit, discrimination, safety, habitability, retaliation, small_claims, court_prep, evidence, timeline
- Sources: MN Revisor, HUD, EPA ECHO, MPCA, CourtListener, MN Courts, county parcel APIs, Eviction Lab, Census/ACS, Homeline MN, tenant stories (moderated)
- Guardrails: no hallucination (every fact cited), no legal advice, stories anonymized + moderated, calm tone, jurisdiction-aware
- Module: `app/modules/context_engine/` with router, gatherer, verifier, cache, stories, taxonomy, distributor, models
- Contracts: `context_query`, `context_refresh`, `story_submit`, `story_moderate`
- Repurposes `free_api_pack.py` stubs as real fetchers
- Fills 148 HTML placeholders with context panels

### Action Feedback — Key Decisions
- Build `static/components/feedback.html` — unified `SemptifyFeedback` helper
- API: `start(button, text)`, `success(msg)`, `error(msg, {detail})`, `info(msg)`, `story({...})`
- Reuses existing `loading-overlay.html` spinner + `btn--loading` class
- Toast: bottom-right, 4 variants, accessible, stackable, calm tone
- Retrofit priority: Tier 1 tenant pages → Tier 2 admin → Tier 3 office → Tier 4 tools → Tier 5 remaining
- `SemptifyFeedback.story()` is the bridge to Context Engine

---

## 🎯 Current Priority: Phase 4 — Role Development Completion

### Phase 4 Scope (from ROADMAP_TO_PUBLIC_RELEASE.md)

| Role | Status | Work Needed |
|------|--------|-------------|
| **4.1 TENANT** | ✅ Mostly done | `state_laws` +5 states, `housing_accountability.detect_repeated_fees()`, verify endpoints |
| **4.2 ADVOCATE** | ⚠️ Partial | Dashboard, client list, case sharing, doc review, invite flow, multi-tenant view |
| **4.3 MANAGER** | ⚠️ Stub | Dashboard, staff mgmt, case assignment, reporting, bulk ops, permissions |
| **4.4 LEGAL** | ⚠️ Stub | Workspace, court filing, discovery, case files, exhibits, overlays |
| **4.5 ADMIN** | ✅ Developed | Deploy redirect fix, verify 41 endpoints, module flag UI |
| **4.6 JUDGE** | 🚫 Not built | Future — mark `dev_only`, don't build until courts request |

### Phase 4 Execution Order
1. **4.1 TENANT** — smallest gap, finish first
2. **4.5 ADMIN** — mostly verification + small fixes
3. **4.2 ADVOCATE** — next in roadmap order, real feature work
4. **4.3 MANAGER** — stub buildout
5. **4.4 LEGAL** — stub buildout
6. **4.6 JUDGE** — mark `dev_only` in module flags, do not build

---

## 🅿️ PARKED (Awaiting Build)

| Project | Design Doc | Status | Blocked By |
|---------|------------|--------|------------|
| **Context Engine MVP** | (todo, needs write-up) | 🅿️ Ready to build | Phase 4 in progress |
| **Action Feedback helper** | `ACTION_FEEDBACK_AUDIT.md` | 🅿️ Ready to build | Phase 4 in progress |

---

## 🚫 Anti-Priorities (Don't Start These)

1. **New features** that aren't Phase 4 role completion
2. **Refactoring** unrelated to role stubs
3. **Documentation** that isn't critical path
4. **Testing** of non-core systems
5. **Context Engine / Action Feedback build** — parked until Phase 4 done

---

## ✅ Definition of "Phase 4 Complete"

- [ ] 4.1 Tenant: all stubs fixed, all tenant-visible endpoints return 200
- [ ] 4.2 Advocate: dashboard, client list, case sharing, doc review, invite flow, multi-tenant view
- [ ] 4.3 Manager: dashboard, staff mgmt, case assignment, reporting, bulk ops, permissions
- [ ] 4.4 Legal: workspace, court filing (when MNDES ready), discovery, case files, exhibits, overlays
- [ ] 4.5 Admin: deploy redirect fix, all 41 endpoints verified, module flag UI
- [ ] 4.6 Judge: marked `dev_only` in module flags, not built

---

## 📋 Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-06-21 | ✅ Completed audit + design docs | STATUS_AUDIT.md, ACTION_FEEDBACK_AUDIT.md written |
| 2026-06-21 | ✅ Context Engine design captured | PostgreSQL cache, stories after task, avoided_court hero |
| 2026-06-21 | ✅ Action Feedback design captured | SemptifyFeedback helper, 5-tier retrofit |
| 2026-06-21 | Start Phase 4 — Role Development | Audit complete, ready to fix stubs |
| 2026-06-04 | Reconnect session persistence fix | DB-first session save |
| 2026-04-21 | Completed Communication System | Document fill/sign + messaging + vault storage |
| 2026-04-21 | Completed Unified Overlay System | All components integrated |

---

## 🔗 Quick Links

- **Status Audit**: `STATUS_AUDIT.md`
- **Action Feedback Audit**: `ACTION_FEEDBACK_AUDIT.md`
- **Build Status**: `BUILD_STATE.md`
- **Roadmap**: `ROADMAP_TO_PUBLIC_RELEASE.md`
- **Blueprint**: `BLUEPRINT.md`
- **Vault Paths**: `app/core/vault_paths.py`

---

*This file is the single source of truth for what is being worked on RIGHT NOW.*
