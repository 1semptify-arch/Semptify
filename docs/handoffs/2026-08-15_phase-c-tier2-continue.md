# Handoff — Phase C Tier 2: Continue Batch Reconciliation

**Status:** In progress. 18 of 507 Tier 2 files done (Batches 1-4, all merged).
**Source branches:** comparing `adr-0008-pilot` against `github-direct/main`.
**Process doc:** `AI_TEAM_OPERATING_PROTOCOL.md` (already in repo, wired into AGENTS.md preflight — should load automatically).

---

## Where things stand

Tier 1 (`app/core/`, 102 files) is fully done. Tier 2 (`app/modules/` + `app/services/`, 507 files) is underway:

| Batch | PR | Files | Result |
|---|---|---|---|
| 1 | #49 | 2 | Merged — court_forms/intake sync-token fix |
| 2 | #50 | 6 (2B, 4A) | Merged |
| 3 | #51 | 5 (5B) | Merged |
| 4 | #52 | 5 (3B, 2A) | Merged |

**Recurring pattern found so far:** 10 of 18 files fixed the same bug — sync `get_valid_token_for_user()` being awaited or called inside async routes, replaced with `ensure_valid_token(user_id, db)`. A parallel search task (see `HANDOFF_search_sync_token_pattern.md`) is finding all remaining instances of this — check its findings before/alongside future batches, since it may surface files faster than working through Tier 2 file-by-file.

## Process (same as Tier 1)

Tier A (cosmetic only) — decide alone, log it, no PR needed if a batch has zero A/B/C changes.
Tier B (clear improvement, nothing lost) — apply automatically, log it, include in batch PR.
Tier C (real judgment call, or touches money/legal/privacy) — stop, report in this format:
```
File: <name>
Core difference: <plain-English summary>
Missing fix or different approach?: <what's missing, if anything>
Recommendation: <proposed call>
```

One PR per batch of ~5 files. Report batch results, wait for merge go-ahead before starting the next batch — same discipline as Tier 1.

## Known items already flagged, don't re-litigate

- `page_manifest.py` / `product_manifest.py`'s page router — static-to-template migration, deliberately deferred (`todo-065`), needs its own dedicated review, not a Tier 2 batch decision.
- Icon/symbol style question (emoji vs. geometric symbols) — appeared 3+ times in Tier 1, always kept main. Same call applies in Tier 2 if it comes up again — no need to re-ask.
- FIPS `usedforsecurity=False` on hashlib calls — always keep main's version with the flag present.
- `StrEnum` vs `(str, Enum)` — always keep main's `StrEnum` version, this is a consistent regression pattern in the pilot branch, not a real decision each time.

## Next step

Continue with Tier 2 Batch 5, same process. If the parallel search task (see other handoff) has already found and reported specific files with the sync-token bug, consider prioritizing those files into upcoming batches rather than working strictly in whatever order `git diff` returns them.
