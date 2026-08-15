# HANDOFF: Establish the State-Doc System (Not Just Files — a Working Habit)

**Why this exists:** `BUILD_STATE.md`, `ACTIVE_CONTEXT.md`, and `BACKLOG.md` only work as a "single source of truth" if they (1) actually exist in the repo, (2) are current, and (3) reliably get updated every session — not just when a session happens to remember to. Tonight's sessions did this manually. This handoff makes it a checked, structural part of the repo, not a habit that depends on remembering.

This is partly build, partly organize, partly enforce. Run in this order.

---

## 1. Audit what already exists (do this first — don't assume)

1. Check whether `BUILD_STATE.md` and `ACTIVE_CONTEXT.md` currently exist in the repo, where, and how current they actually are (last real edit date, does it reflect tonight's PRs #69–#93).
2. Confirm `BACKLOG.md` does NOT yet exist in the repo (it was drafted this session as a downloaded file, not yet committed).
3. Report findings before doing anything else — don't overwrite existing docs blind.

## 2. Commit `BACKLOG.md` into the repo

1. Add the `BACKLOG.md` draft (from this session) to the repo root or `docs/`, matching wherever `BUILD_STATE.md`/`ACTIVE_CONTEXT.md` already live.
2. Reconcile it against whatever's actually in `BUILD_STATE.md`/`ACTIVE_CONTEXT.md` already — if there's overlap or conflict, resolve it, don't just paste both versions in.

## 3. Establish the update discipline as a real rule, not a memory

1. Add a short section to `AI_TEAM_OPERATING_PROTOCOL.md`: **every session that merges a PR, resolves a tracker task, or makes an architectural decision must update the relevant state doc(s) before the session is considered closed.** Name which doc for which kind of change:
   - `BUILD_STATE.md` — what shipped, current build status.
   - `ACTIVE_CONTEXT.md` — what's actively being worked on right now, open threads.
   - `BACKLOG.md` — any new idea, gap, or future item that came up, at whatever stage it's at.
2. This rule should sit next to the other standing rules already in that doc (one task per commit, no self-approval, `admin:`/`user:`/`help:`/`adr:` prefixes) — same tier of importance, not a footnote.

## 4. Make it checkable, not just stated

A rule that only lives in prose gets skipped under pressure — the same failure mode that caused the pre-commit convergence bug and the empty-ruleset bug earlier tonight. Add a lightweight check:

1. A small script (e.g., `tools/check_state_docs_freshness.py`) that flags if `BUILD_STATE.md`/`ACTIVE_CONTEXT.md` haven't been touched in the same PR/session as a significant tracker status change (e.g., multiple `todo-*` items flipped to `resolved` without a corresponding state-doc update nearby in git history).
2. This does not need to be a hard CI gate (don't block merges over it) — start as a soft warning/report, similar in spirit to how `sync_orchestrator.py --check` reports rather than force-fixes. Escalate to a hard gate later only if soft warnings prove insufficient.

## 5. Organize repo-wide — where things actually live

Beyond the three state docs, do a light pass on overall doc organization so the four-tier system (`considering` → ADR → handoff → build → close-out) is discoverable:

1. Confirm `docs/adr/` is the actual, consistent home for all ADRs (0008, 0009, and any future ones) — no ADRs living loose elsewhere.
2. **Decided: handoffs are kept in-repo.** Create `docs/handoffs/` as their permanent home. Use a consistent naming convention: `YYYY-MM-DD_short-topic-slug.md` (e.g. `2026-08-15_tier2-adr0008-reconciliation.md`), so they sort chronologically and are searchable by topic.
3. Move/commit every handoff doc generated this session into `docs/handoffs/`, at minimum:
   - Tier 2 / ADR-0008 reconciliation handoff (initial scan + methodology)
   - Post-PR#69 dispatch handoff
   - P4 merge / P5 kickoff handoff
   - P5 close-out handoff
   - Root-cause main-divergence investigation handoff
   - Fact-check/freshness build plan handoff
   - Fact-check/freshness docs-integration handoff
   - Information Orchestrator (ADR-0008) recap handoff
   - Production-readiness audit handoff
   - This handoff itself, once complete
   If any of these only exist as files Brad downloaded and never pasted into a session with repo access, flag which ones are missing from the agent's context so Brad knows which to re-paste for committing.
4. Report the resulting structure back as a simple tree/map so Brad has one picture of "where does X kind of document live," confirming `docs/handoffs/` now holds the full session history alongside `docs/adr/` for decisions and the three root-level state docs for current status.

## 6. Deliverable

1. `BACKLOG.md` committed and reconciled.
2. `AI_TEAM_OPERATING_PROTOCOL.md` updated with the state-doc-update rule.
3. `tools/check_state_docs_freshness.py` added (soft-check, not blocking).
4. A short report back to Brad: current doc structure map, and the one open question from step 5.2 (in-repo handoff archive or not).

---

## Standing rules — apply throughout

- One task per commit, PR-only (no direct commits to `main`, per the ruleset fixed tonight).
- `sync_orchestrator.py --check` after any tracker-touching change.
- This is infrastructure/discipline work, same spirit as tonight's CI fixes — do it once, do it right, so it doesn't quietly become dead code the way the freshness scheduler did before tonight.
