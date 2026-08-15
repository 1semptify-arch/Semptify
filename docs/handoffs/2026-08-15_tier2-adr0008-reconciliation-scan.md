# HANDOFF: Tier 2 / ADR-0008 Pilot Branch Reconciliation

**Status at time of writing:** Scan in progress, not complete. This doc exists so any agent (or Brad) can pick up the process cold, with full reasoning, no re-explaining needed.

---

## 1. Why this scan exists

`github-direct/adr-0008-pilot` is a long-lived branch implementing the Information Orchestrator (ADR-0008: Object Context Envelopes, Three-Layer Retrieval, Experience Token). Some of that work has already been merged forward into `main` in batches over time. The question driving this scan: **what pilot work is still NOT on main, and does it need to land, get re-architected, or get discarded?**

---

## 2. Key lesson learned this session (don't repeat the mistake)

**Three-dot diff (`main...branch`) is NOT "what's left to merge."** It shows all commits reachable from the branch since the merge-base, including work already cherry-picked/merged forward into main under different SHAs. It massively overcounts.

**Two-dot diff (`main branch`)** is the correct comparison for "what's different between main's current tip and the pilot branch's tip, file-by-file." That's the real "what's left" view.

Rule going forward: **always use two-dot diff for reconciliation scans.**

---

## 3. Key findings (two-dot diff, `app/modules/` + `app/services/` scope)

Command used:
```
git diff --name-status main github-direct/adr-0008-pilot -- app/modules/ app/services/
```

Result: **179 files** — 8 deletions, 171 modifications, 0 pure additions.

### 8 deletions (Tier A decision required)
Pilot branch deletes 12 services entirely, implying absorption into the new envelope/orchestrator pattern. For each: confirm the replacement functionality actually exists on main before deleting — do not delete on assumption (Build Bible root-cause rule).

### 171 modifications — mixed cosmetic and substantive
Clusters: `page_composer/`, `page_shell/`, `context_engine/`, `eviction_timeline/`, `vault/`, and ~15 other module/service directories.

### Outside scope of this scan
`app/core/page_manifest.py` was flagged as a live migration point but is outside `app/modules/`/`app/services/` — needed its own two-dot diff pass (later completed, became `todo-065`).

---

## 4. Process note

This was exploratory git archaeology, not blind execution — every step produced a report back before the next Tier A decision got made. Follow Build Bible: no band-aids, confirm root cause before deleting anything.

**Outcome:** This scan and its follow-on triage became the basis for the full P1–P5 dispatch and PRs #69–#89. See `2026-08-15_p5-closeout.md` and related handoffs for the resolution.
