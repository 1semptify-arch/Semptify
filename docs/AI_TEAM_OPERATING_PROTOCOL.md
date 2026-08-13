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

*Use this for Phase C and for anything similar going forward — any large batch-comparison or batch-decision task benefits from the same tiering.*
