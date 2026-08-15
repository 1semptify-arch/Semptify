# STATUS: ADR-0008 Pilot Reconciliation — Full Effort Standing

**As of:** `main` at `a02161af`, clean working tree. This is the consolidated picture across the entire Tier 2 reconciliation effort, from the initial pilot-branch scan through CI infra fixes.

---

## 1. What's fully resolved

**CI infrastructure (this session's last thread) — CLOSED:**
- `todo-067` / `todo-068` — pre-commit convergence bug fixed (PR #82). Tracker sync is now read-only in all gates (`--check` only), fail-loud if stale, manual regeneration policy. No more false "files were modified by this hook" failures.
- `todo-081` — Test job slowness fixed (PR #83). PRs now run a fast marker-based subset (~1 min), full suite + coverage runs on `main`/`develop` only. Documented failure policy: full-suite failure on `main` blocks `build`/Docker push, creates a tracker incident, blocks merge queue, next PR must fix — no silent auto-revert.

**Tier 2 / ADR-0008 pilot reconciliation — SUBSTANTIALLY CLOSED:**
- P1 — security finding resolved (`document_flow_orchestrator.py` f-string SQL blocked, main's parameterized version is baseline).
- P2 — quick-win deletions merged (`hud_funding_guide.py`, `court_form_generator.py`).
- P3 — test migrations + deletions merged (`document_notarization.py`, `vault_engine.py`), plus two real access-control bugs found and fixed in `vault_engine/service.py` along the way.
- P4 — caller migrations merged (`auto_mode_orchestrator`, `event_extractor`, `proactive_tactics`, `progress_tracker`), including resolving a real file collision between two PRs.
- P5 — wiring clusters resolved: 19-task preserve-main batch, `vault/` ADR-0008 wiring applied, `litigation_intelligence/` DSN security fix applied.

That's PRs #69–#83 (15 PRs) merged across this effort, each gated by `sync_orchestrator.py --check`.

---

## 2. What's still open — three items, three different owners

| Item | What's needed | Owner |
|---|---|---|
| `phase2-50551b-067` — `modules/security/router.py` | One-line equivalence confirmation (`secure=not is_localhost` vs. ternary form) — test or explicit check | Agent, small task |
| `phase2-dc4e66-065` — dashboard/progress wiring review | Actual review of `dashboard/service.py` + `progress/router.py` wiring, not just import confirmation | Agent, standalone task |
| `phase2-1a1341-055` — `services/eviction/case_builder` | Manual legal review of tenant-extraction refactor + added DB query in legal-output code | **Brad** — not agent-actionable |

The first two are parked on `devin/p5-review-flags`, unmerged by design. Third is a genuine Tier A / human decision — no agent should resolve this on its own judgment.

---

## 3. Original 9 pending items — current state

From the last full enumeration:

- ~~`todo-067`~~ — **resolved** (PR #82)
- ~~`todo-068`~~ — **resolved** (PR #82)
- ~~`todo-081`~~ — **resolved** (PR #83)
- `todo-063` — provision Python 3.11.9 test env — **still open**
- `todo-064` — raise test coverage to threshold — **still open**, likely blocked by `todo-063`
- `todo-065` — page_manifest migration (the original deferred item from the very start of this scan) — **still open**
- `todo-066` — Tier 1 reconciliation, `vault_paths.py` — **still open**, flagged last round as possibly stale/superseded by the vault work in PR #80 — **not yet confirmed either way**
- `phase2-1a1341-055` / `phase2-50551b-067` — see section 2 above

So: 4 of the original 9 resolved, `todo-066`'s status is unconfirmed, 4 items genuinely remain.

---

## 4. Recommended next step

Don't start new work yet — one confirmation is still outstanding from two rounds ago and shouldn't get lost:

```
Confirm whether todo-066 (Tier 1 reconciliation, app/core/vault_paths.py) is stale/superseded 
by the vault ADR-0008 wiring merged in PR #80, or still genuinely open. Report before acting.
```

After that's answered, the remaining real work is:
1. `todo-063` → `todo-064` (test env provisioning, likely sequential)
2. `todo-065` (page_manifest migration — larger, do now that CI is stable)
3. `phase2-50551b-067` (small, standalone)
4. `phase2-dc4e66-065` (standalone review)
5. `todo-066` if confirmed still open

`phase2-1a1341-055` stays parked for Brad's legal review — not part of any agent dispatch.

---

## 5. Also still open, lower priority, unrelated to this specific thread

- `local/markdown-lint-pass` — 278-file lint pass, still unpushed. Recommended: push as its own PR now that CI is fast and stable, so its signal is easy to read.
