# Handoff — Search: Sync-Token Bug Pattern (Read-Only)

**IMPORTANT: This task is READ-ONLY. Do not commit, branch, push, or modify any file. This is safe to run at the same time as the Tier 2 batch reconciliation work precisely because it never touches git state — breaking that rule would recreate the multi-agent conflict problem from earlier today.**

---

## What to search for

A confirmed bug pattern, already fixed in 10 files across Tier 2 batches 1-4: a synchronous function (`get_valid_token_for_user`) being called with `await`, or called directly inside an `async def` route/function, blocking the event loop. The fix pattern (already proven, don't reinvent it) is replacing it with `ensure_valid_token(user_id, db)` from `app.core.auto_refresh`.

## The search

```
Search the entire codebase (not just app/modules and app/services — check
everywhere) for:

1. Direct calls to get_valid_token_for_user( — both awaited and not
2. Any async def function that calls a synchronous token-related helper
   without await (the inverse bug — missing await where one should exist)
3. Cross-reference against known Failure Registry item 19 if that's
   documented anywhere in AGENTS.md or similar - use its exact description
   of the bug pattern to make sure the search is precise, not just a loose
   text match

For each match found, report:
- File path and line number
- The exact code snippet
- Whether it's inside an async def (making it a real bug) or not
- Whether this file has already been reconciled in a Tier 1/2 batch
  (check git log or the batch PR history if unsure) - if already fixed,
  skip it from the findings list

Do NOT fix anything. Do NOT create branches. Do NOT commit anything.
This is a findings report only.
```

## Output format

A simple table: file path, line number, snippet, already-fixed or not. Sorted so unfixed instances are at the top — those are the ones that matter for prioritizing future Tier 2 batches.

## When done

Report the findings list back. It should get folded into the Tier 2 batch planning (`HANDOFF_phase_C_tier2_continue.md`) — specifically, files with confirmed unfixed instances should get prioritized into upcoming batches rather than waiting for their normal turn in file order.
