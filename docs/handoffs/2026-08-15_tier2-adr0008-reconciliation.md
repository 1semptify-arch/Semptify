# HANDOFF: Tier 2 / ADR-0008 Pilot Branch Reconciliation

**Status as of this handoff:** Scan in progress, not complete. This doc exists so any agent (or Brad) can pick up the process cold, with full reasoning, no re-explaining needed.

---

## 1. Why this scan exists

`github-direct/adr-0008-pilot` is a long-lived branch implementing the Information Orchestrator (ADR-0008: Object Context Envelopes, Three-Layer Retrieval, Experience Token). Some of that work has already been merged forward into `main` in batches over time. The question driving this scan: **what pilot work is still NOT on main, and does it need to land, get re-architected, or get discarded?**

This matters because Tier 2 task generation was about to assume "mostly done, just `page_composer/router.py` and `page_manifest` left" — that assumption was wrong. The real remaining surface is much larger. Task generation must wait until the surface is correctly scoped, or agents will duplicate work or miss real integration gaps.

---

## 2. Key lesson learned this session (don't repeat the mistake)

**Three-dot diff (`main...branch`) is NOT "what's left to merge."** It shows all commits reachable from the branch since the merge-base, including work that's already been cherry-picked/merged forward into main under different SHAs. It massively overcounts.

**Two-dot diff (`main branch`, no dots between... just a space)** is the correct comparison for "what's different between main's current tip and the pilot branch's tip, file-by-file." That's the real "what's left" view.

Rule going forward: **always use two-dot diff for reconciliation scans.** Three-dot is only useful for "history of a branch since it diverged," not for current-state comparison.

---

## 3. Current findings (two-dot diff, `app/modules/` + `app/services/` only)

Command used:
```
git diff --name-status main github-direct/adr-0008-pilot -- app/modules/ app/services/
```

Result: **179 files** — 8 deletions, 171 modifications, 0 pure additions in this path scope (the 6 "added" files from the three-dot scan are already merged into main, confirmed by their absence here).

### 8 deletions (Tier A decision required — do not auto-resolve)
Pilot branch deletes these services entirely, implying their functionality was absorbed into the new envelope/orchestrator pattern:
- `app/services/auto_mode_orchestrator.py`
- `app/services/court_form_generator.py`
- `app/services/crawler.py`
- `app/services/document_notarization.py`
- `app/services/event_extractor.py`
- `app/services/fraud_exposure.py`
- `app/services/hud_funding_guide.py`
- `app/services/plan_maker_service.py`
- `app/services/proactive_tactics.py`
- `app/services/progress_tracker.py`
- `app/services/public_exposure.py`
- `app/services/vault_engine.py`

**For each: confirm the replacement functionality actually exists on main (or in the pilot's surviving modules) before deleting. Do not delete on assumption.** This is a Build Bible root-cause check — if the replacement isn't real yet, deleting the old service creates a functionality gap, not a cleanup.

### 171 modifications — needs categorization
Not yet broken down by module in this session. Known clusters (from the earlier noisier three-dot scan, still valid as a map even though the file *count* from that scan was wrong):
- `page_composer/` — assembly.py, register.py, service.py, models.py, router.py
- `page_shell/*`
- `context_engine/*` — explanation_entries.py, retrieval.py (already confirmed merged, may still show as modified if pilot has since diverged further)
- `eviction_timeline/*` — envelopes.py and related
- `vault/*` — envelopes.py and related
- possibly others not yet enumerated

### Outside scope of this scan
`app/core/page_manifest.py` was flagged as a live migration point but is **outside** `app/modules/` / `app/services/` — needs its own two-dot diff pass:
```
git diff --name-status main github-direct/adr-0008-pilot -- app/core/
```

---

## 4. Exact next steps (in order)

1. Run the `app/core/` two-dot diff above to capture `page_manifest.py` and any other core migration files.
2. Get the full 171-file modification list (not just the module clusters from memory) — run:
   ```
   git diff --name-status main github-direct/adr-0008-pilot -- app/modules/ app/services/ > tier2_179_diff.txt
   ```
   and categorize every file into its module bucket. Don't rely on partial recall of clusters — enumerate fully.
3. For each of the 8 service deletions: check whether main (or the pilot's own surviving files) contains equivalent functionality. Flag as Tier A decision list — do NOT resolve automatically.
4. For the 171 modifications: spot-check a sample (5-10 files) to determine whether changes are substantive (logic/architecture) or superficial (formatting, import reordering, lint). This determines whether Tier 2 tasks should be "port this logic forward" (heavy) or "reconcile formatting" (light).
5. Once categorized, generate Tier 2 tasks module-by-module — do not generate one giant "merge the pilot branch" task. One task per module cluster, sized appropriately, following existing agent discipline rules (one task per commit, preflight full-file reads, stop-and-report on ambiguity).
6. Standing rule still applies: **no `git reset --hard` on any branch without explicit human confirmation.** This reconciliation involves comparison only — no branch should be reset as part of this process without a separate explicit go-ahead from Brad.

---

## 5. Decisions that are Tier A (need Brad, not agent judgment)

- Whether each of the 12 deleted services is safe to delete (functionality genuinely replaced vs. gap).
- Whether the 171 modified files get merged as-is, cherry-picked selectively, or re-implemented fresh against current main's architecture (main has moved since the pilot branch was created — CI fixes, security gates, i18n selector — so a blind merge risks conflicts with newer main-only work).
- Whether `local/markdown-lint-pass` (278 files, still unpushed, separate from this reconciliation) gets pushed as PR before or after this Tier 2 work — recommend PR-first since it's low-risk and tests the new CI gates, but Brad's call on sequencing.

---

## 6. Process note for whoever picks this up

This is exploratory git archaeology, not blind execution — every step should produce a report back before the next Tier A decision gets made. Follow Build Bible: no band-aids, confirm root cause (i.e., confirm replacement functionality actually exists) before deleting anything.
