# Handoff — Extended Session (Claude usage conservation mode)

**Purpose:** Let both agents keep working for ~3 hours with minimal Claude check-ins. Brad approves pattern-matched merges directly. Only genuinely new judgment calls wait for Claude.

---

## Immediate task — do this first

**PR #56 still needs its checklist confirmed before merge.** Send to agent 2 (Alan):
```
Before merging PR #56: the PR body has a Core Gate Checklist (Gate 1/2/3,
Vault Immutability, Overlay Adapter, Reviewer Sign-off) with unchecked
boxes. This change only touches token-refresh calls, not upload/overlay/
workflow logic. Update the PR description to explicitly state these
gates are not applicable to this change (rather than leaving boxes
unchecked), then confirm.
```
Once confirmed: **Brad can approve this merge directly** — it's a pattern-matched fix (sync token → ensure_valid_token), already reviewed in concept 14+ times today.

---

## Standing Decision Rulebook — expanded

Any file matching these patterns: **apply automatically, no escalation needed, no waiting for approval to include in a batch.**

| Pattern | Decision |
|---|---|
| `StrEnum` (main) vs `(str, Enum)` (pilot) | Always keep main's `StrEnum` |
| Emoji/icon log messages (main) vs geometric symbols ▸●◆○ (pilot) | Always keep main |
| `→` vs `▸` in docstrings/comments | Always keep main |
| `usedforsecurity=False` present (main) vs removed (pilot) | Always keep main (FIPS compliance) |
| `# pragma: allowlist secret` / `# noqa: S###` present (main) vs removed (pilot) | Always keep main (scanner suppressions are intentional) |
| `any(...)`/`all(...)` (main) vs explicit for-loop (pilot) | Always keep main (functionally identical, main is more idiomatic) |
| `contextlib.suppress(...)` (main) vs explicit try/except (pilot) | Always keep main |
| Sync `get_valid_token_for_user()` called/awaited inside `async def` | Always take pilot's fix pattern: `await ensure_valid_token(user_id, db)` from `app.core.auto_refresh` |
| `datetime.now(UTC)` or similar naive/direct calls | Always take pilot's fix: replace with project's `utc_now()` helper |
| Mutable default argument (e.g. `dict = {}`) introduced by pilot | Always reject, keep main's `None`-default + guard pattern |
| SQLAlchemy filter using Python `not`/`and`/`or` on a column (main) vs `~column` (pilot) | Take pilot's `~column` fix — this is a real correctness bug, not style |
| Hardcoded Postgres-only SQL vs dialect-aware (pilot adds SQLite branch) | Take pilot's dialect-aware version |
| Hardcoded URL string in a redirect vs `navigation.get_stage(...)` (pilot) | Take pilot's SSOT navigation version |
| New file that only exists on pilot, is a core ADR-0008 file (context_envelope, page_envelope, experience_token, event_bus additions) | Take as-is, no modification needed |

## Still requires escalation (queue, don't block on it — see below)

- Anything touching `page_manifest.py` or the static-to-template migration (`todo-065`) — already deferred, do not revisit.
- Anything that changes an API response shape (removing/renaming a field clients might depend on).
- Anything that's a genuine two-sided architecture choice with no clear "main is better" or "pilot is better" — i.e. real Tier C.
- Anything touching money, legal/UPL risk, or tenant privacy, regardless of how small it looks.
- Any new dependency being added to `requirements.txt` beyond what's already approved today (`qrcode` is approved; nothing else is pre-approved).

## How to handle a Tier C item without stopping everyone for 3 hours

**Don't halt the whole session on one hard file.** Instead:
1. Skip that file for now, note it in a running list (append to `E:\master-repo\phase_c_tier2_pending_review.md` — create if it doesn't exist).
2. Continue the batch with the rest of the files.
3. Include the skipped file's summary in that pending-review doc using the same format as always: Core difference / Missing fix or different approach? / Recommendation.

When Claude is available again, that one file gets reviewed in a single pass — much cheaper than stopping progress every time something new comes up.

---

## Batching change for this session

**Increase batch size to 8-10 files** instead of 5 — fewer round-trips needed since most decisions are now pre-approved by the rulebook above. A batch only needs a stop for genuine Tier C content; pure Tier A/B batches can go straight to PR and wait for Brad's merge go-ahead, no written report needed beyond the PR description itself.

## Who approves merges now

**Brad approves directly** for any PR where every file matches the rulebook above (no Tier C items). Check: CI green, PR description lists which rulebook pattern each file matched. If both true, Brad can just say "merge" without routing through Claude.

**Still wait for Claude specifically** on: anything in the pending-review doc, anything touching the "still requires escalation" list above, or anything an agent flags as "I'm not confident this matches an existing pattern."

---

## Hard safety rules — unchanged, apply regardless of usage pressure

- One task/batch per commit, still.
- No self-merge by any agent — Brad or Claude must say "merge," never the agent that wrote the code.
- No `git reset --hard` on any branch without explicit confirmation first.
- The two-folder separation stays: agent 1 in `E:\master-repo\sources\app-semptify-fastapi`, agent 2 (Alan) in `E:\master-repo\sources\app-semptify-fastapi-agent2`. Don't collapse back to one folder.
- If anything looks like it could break production, or an agent is guessing rather than confident — stop and add to the pending-review doc rather than proceeding on a guess.

---

## End of session — what to prepare for Claude's return

- Update `HANDOFF_phase_C_tier2_continue.md`'s status table with all batches completed during this session.
- Make sure `phase_c_tier2_pending_review.md` (if created) is complete and readable — that's the first thing to review next.
- Report total files reconciled, total PRs merged, and current Tier 2 remaining count.
