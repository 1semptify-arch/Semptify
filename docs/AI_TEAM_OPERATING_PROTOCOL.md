# AI Team Operating Protocol — Brad / Claude / SWE-1.7-Max

**Purpose:** Keep this three-way collaboration running with minimal Claude usage (limited/metered) and maximum SWE-1.7 usage (unlimited), while keeping Brad's job as simple as copy/paste.

---

## The three roles

**SWE-1.7-Max — does all the work.** Reading files, running diffs, running tests/CI, executing merges, first-pass analysis, drafting recommendations. Unlimited usage — this is where time should be spent generously.

**Claude — makes judgment calls only.** Reviews SWE-1.7's analysis, approves or corrects it, catches risks, makes architecture/safety/design decisions. Limited usage — should be invoked only when a real decision is needed, not for routine supervision.

**Brad — relays and breaks ties.** Pastes Claude's instructions to SWE-1.7, pastes SWE-1.7's results back to Claude. Only weighs in personally on priority/values/funding-strategy questions neither AI should decide alone. No technical reading required.

---

## Decision Authority Matrix — this is the cost-saving core

When SWE-1.7 compares two versions of something (like today's file-by-file reconciliation), sort every decision into one of three tiers:

### Tier A — Cosmetic, no functional difference
Example from today: `security.py` — same logic, different comment symbols.
**SWE-1.7 decides alone.** No Claude review needed. Just log the decision made and move on. Batch these into the report at the end for the record, not as a question.

### Tier B — Clear superset (one side strictly better, nothing lost)
Example from today: `database.py` — pilot version fixes a real bug and loses nothing main had.
**SWE-1.7 applies the fix automatically**, logs what it did and why, and reports it *after the fact* in the batch summary — not as a question requiring a real-time answer. Claude can spot-check these in the batch review, but they don't need to block progress waiting for a response.

### Tier C — Real judgment call or design tradeoff
Example from today: `navigation.py` (needs actual merging), `oauth_token_manager.py` (good direction, one real flaw to fix).
**This is the only tier that needs Claude.** Bring these to Claude in the proven format:
```
File: <name>
Core difference: <plain-English summary, not a line diff>
Missing fix or different approach?: <does one side lack something real>
Recommendation: <SWE-1.7's proposed call>
```
Claude reviews the *recommendation*, not the raw diff — approving is fast, disagreeing is a short correction, not starting from zero.

---

## Batching rule

**Never single-file check-ins.** SWE-1.7 works through a batch (5-10 files is a good size) fully — including all its own Tier A/B decisions — before ever coming back. Only Tier C items from that batch actually need Claude's time. One Claude review per batch, not per file.

## Escalation rule

SWE-1.7 only interrupts mid-batch for:
- Something that looks like it could break production if guessed wrong
- A genuine coin-flip where either side seems equally valid and the choice matters
- Anything touching money, legal/UPL risk, or tenant privacy — always escalate these regardless of tier

Everything else: proceed, log the reasoning, report in the batch summary.

## Format rule

Keep using the structured table/summary format proven today (Core difference / Missing fix / Recommendation, or the paste-ready table style). This is what let Claude review 5 files in one pass instead of five separate investigations. Don't paste raw `git diff` output for Claude to parse manually — that burns Claude's limited time doing SWE-1.7's job.

## Standing rules that still apply underneath all of this

One task per commit, no self-approval, full-file preflight reads, stop-and-report on real risk — none of that changes. This protocol is about *how often* to loop Claude in, not about relaxing any existing safety rule.

---

## Main branch protection and the no-direct-push rule

**No AI agent commits directly to `main`. Ever.**

`main` is intended to be protected by a repository ruleset named `protect-main`:

- `target`: `branch`
- `enforcement`: `active`
- Rules:
  - `deletion` — `main` may not be deleted.
  - `non_fast_forward` — force-pushes and history rewrites on `main` are blocked.
  - `pull_request` — changes must be introduced through a pull request; direct pushes are blocked.
- `bypass_actors`: none.
- `current_user_can_bypass`: `never`.

The allowed merge methods are `merge`, `squash`, and `rebase`, but a pull request is required for all of them.

**Operational rule for AI agents:**

- All work ships through a feature branch and a pull request.
- Use `gh pr create`, let CI run, then `gh pr merge`.
- Never `git push <remote> main` from a local `main` checkout, even for one-line or "obvious" fixes.
- If an emergency direct push appears possible, stop and escalate — that is a sign the ruleset is not working as intended.

**Known misconfiguration and correction:**

A 2026-08-15 verification showed that `protect-main` had `conditions.ref_name.include` set to an empty array, which caused the ruleset to match **no branches**. A direct `git push github-direct main` from a throwaway commit **succeeded**. The test commit was removed by a force-push, the ruleset was updated via `gh api .../rulesets/17660447` to set `conditions.ref_name.include` to `["refs/heads/main"]`, and a second throwaway direct push was then **rejected** with:

```text
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - Changes must be made through a pull request.
```

The ruleset now enforces the intended protection; the no-direct-push rule remains non-negotiable.

---

## Public-facing factual claims must be sourced through the fact-check/freshness system

**Public-facing factual claims (landing page, marketing copy, hero stats) must be sourced through the fact-check/freshness system (ADR-0009), never hardcoded.** Any new numeric or factual claim added to a public page requires:

1. A `ContextFact` row with `subject="landing"`, a real `source_url`, and a `canonical_value`.
2. Inclusion in the scheduled freshness check (`data_freshness_manager` / Render cron).
3. A citation/footnote rendered from the same data (`source_name`, `source_url`, `citation`).

No agent should hardcode a statistic into landing/marketing HTML going forward — this is how the Calder-Wang/Kim drift almost happened once and must not be allowed to happen silently again. If the freshness system cannot verify a claim, the UI must hide it or show an honest "checking..." state; it must not display the number as confirmed.

---

## State-doc update discipline

Every session that merges a PR, resolves a tracker task, or makes an architectural decision must update the relevant state doc(s) before the session is considered closed. Update the doc that matches the kind of change:

- `BUILD_STATE.md` — what shipped and current build status. Update on every merge or verified fix.
- `ACTIVE_CONTEXT.md` — what is actively being worked on right now and open threads. Update when the current priority or an open decision changes.
- `BACKLOG.md` — any new idea, gap, or future item that came up, at whatever stage it is in.

Do not let state docs drift. A tracker task is not "closed" if the state doc that explains it is still stale. Use `tools/check_state_docs_freshness.py` for a soft warning when a batch of tracker status changes has not been matched by a nearby state-doc update.

---

*Use this for Phase C and for anything similar going forward — any large batch-comparison or batch-decision task benefits from the same tiering.*
