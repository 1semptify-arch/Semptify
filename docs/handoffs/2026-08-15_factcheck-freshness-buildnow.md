# HANDOFF: Fact-Check / Freshness System — Build Now, Not After

**Why this exists:** The landing page rebuild (per SEMPTIFY_ORG_GAP_ANALYSIS_AND_LANDING_HANDOFF) requires a sourced hero fact strip. Two independent agent audits confirmed Semptify has the *bones* of a fact-checking system (Context Engine Verifier, Data Freshness Manager) but nothing scheduled, nothing covering marketing/landing claims, and no content-level supersession detection — the exact gap that let a cited academic figure ($25/month) get superseded by its own authors' newer version ($53/month) without anything catching it.

**Decision: don't ship the landing page with hardcoded stat numbers and a "fix it later" note. Build the minimum real version of the freshness system as part of this same effort**, so the hero fact strip is the first real consumer of it — not a hardcoded value that becomes the next piece of stale content nobody notices.

This does not block or slow the rest of the landing page rebuild — it runs as a parallel workstream, feeding into Phase 2 (landing page rebuild) at the wiring step.

---

## 1. Scope decision — extend existing systems, do not build a third

Confirmed by two independent audits: `ContextFact` model + `context_engine/verifier.py` is the right foundation. `data_freshness_manager.py` is the right scheduling/alerting layer. Do not create a parallel/new fact-check system — extend these two.

---

## 2. Build plan, phased and sequenced

### Phase A — Data model + landing claim storage (do first, small, unblocks everything else)

1. Add `subject="landing"` support to `ContextFact` usage (no schema change needed — reuse existing model per the audit).
2. Add a `canonical_value` field/column to store the actual figure/number being tracked (e.g., `"53"`, unit `"$/month"`) separate from the display copy — this is the piece that lets the system detect *drift in the number*, not just link death.
3. Seed the table with the two hero-strip claims once finalized:
   - Representation gap stat (NCCRC) — verified this session, safe to seed as-is.
   - Rent-pricing algorithm stat — **do not seed until Phase B's content-check can confirm which figure ($25 vs $53 vs the separate White House $70) is current and correct.** Seeding a wrong number defeats the purpose.

### Phase B — Real content-level verifier (the actual gap; this is the core deliverable)

This is the piece neither existing system does today, and the piece that would have caught the Calder-Wang/Kim drift automatically. Build it as an extension of `context_engine/verifier.py`, not a new file where avoidable:

1. Upgrade from HTTP `HEAD` to a full `GET` fetch of `source_url`.
2. Extract the relevant figure from the fetched content — starting simple: a configured regex/snippet pattern per claim (e.g., "markup increase of \$(\d+) per unit monthly" for the Calder-Wang paper), not a general-purpose NLP extraction system. Keep this narrow and specific per claim; don't over-engineer a universal fact-extractor for a handful of hero stats.
3. Compare extracted figure to `canonical_value`. Mismatch → set `is_verified=False`, create a freshness alert (reuse `data_freshness_manager`'s existing alert plumbing).
4. Handle the "can't extract cleanly" case explicitly — if the source page structure changes and the regex/pattern fails, that should ALSO raise an alert ("could not verify, needs human check"), not silently pass. This matches Semptify's "we don't guess" commitment — an unverifiable claim is not the same as a verified one.

### Phase C — Actually turn on scheduling (currently dead code — this is a real bug, fix it regardless of landing page)

1. Add a `FreshnessType.MARKETING_CLAIMS` (or `LANDING_STATS`) rule to `data_freshness_manager.py` — short `max_age_hours` (24–168h), priority 1–2 given it's public-facing.
2. Wire an actual trigger. Pick one, don't leave it unwired again:
   - Preferred: Render cron service hitting `/api/data-freshness/cron/daily-refresh` (or a new dedicated `/cron/verify-landing-claims` endpoint).
   - Fallback for local/non-Render environments: start `data_freshness_manager.start_background_scheduler()` in `main.py` lifespan.
3. Replace the seven stubbed `refresh_*` functions related to this rule with the real Phase B verifier call. Leave other stubs (legal_content, court_data, etc.) alone unless separately scoped — don't scope-creep this effort into fixing every stub in the file.

### Phase D — Landing page wiring (this is where it meets the original landing-page handoff's Phase 2)

1. Add `GET /api/landing/facts` — returns only `is_verified=True`, non-expired hero claims with their citation.
2. Landing page template renders the fact strip **from this endpoint**, not hardcoded HTML. If a claim is stale/unverified, the UI hides it or shows an honest "checking..." state rather than displaying a number that might be wrong — never display an unverified number as if it were confirmed.
3. Footnote/source links render from the same data (`source_name`, `source_url`, `citation` fields already in `ContextFact`).

### Phase E — Admin visibility (small, do last)

1. Surface stale/unverified landing claims on the existing admin freshness alerts view (`/api/data-freshness/alerts` already exists) — add a filter or section for `subject="landing"` so a human can see at a glance if the homepage is currently showing something flagged as stale.

---

## 3. What ships in the landing page vs. what's a following task

- **Landing page (Phase 2 of the original handoff) ships with Phase A–D of this plan complete** — meaning the hero fact strip is genuinely live-verified from day one, not hardcoded-with-a-promise-to-fix-later.
- **Phase E (admin dashboard panel) can follow shortly after** without blocking landing page launch — it's visibility tooling, not correctness-critical.
- **Do not extend this effort to fixing the other five stubbed `refresh_*` functions** (legal_content, court_data, forms, state_laws, deadlines/cache/index) — those are real, pre-existing gaps, but they're a separate, already-flagged piece of technical debt. Note them for a future task, don't fold them in here.

---

## 4. Fact-checking the two hero stats specifically, using this new system

Once Phase B exists, use it to settle the open question from this session rather than picking a number by judgment call:

- **Representation gap** — seed with NCCRC's figure now; it's independently verified across 5+ secondary sources already. Low risk.
- **Rent-pricing figure — this is the test case for the whole system.** Point Phase B's verifier at the Calder-Wang/Kim source directly (the paper itself, ideally its final published version if one exists beyond the Feb 2026 FTC conference presentation — check for a peer-reviewed/journal version before treating the conference paper as final). Let the system extract and confirm the actual current figure rather than hand-picking between $25, $53, or the separate White House $70/month estimate. Whichever number the verifier confirms and can re-confirm on a schedule is the number that ships.

---

## 5. Standing rules — apply throughout

- Build Bible: root-cause fix, not a band-aid — this plan exists specifically because "ship hardcoded numbers, fix the system later" is the band-aid version and isn't acceptable here.
- One task per commit, stop-and-report on ambiguity, preflight full-file reads before editing `context_engine/verifier.py` and `data_freshness_manager.py` given both are shared infrastructure other modules depend on.
- No `git reset --hard` without explicit confirmation. `sync_orchestrator.py --check` after merges affecting tracker files, same as every prior effort.
- Commit prefix `admin:`/`user:`/`help:`/`adr:` per existing hook.
- Information Integrity Standards apply to this system's own output too: an unverifiable claim must alert as unverifiable, not silently pass as verified.

---

## 6. Open question back to Brad

Phase B needs one judgment call once implemented: **if the verifier cannot cleanly extract a figure from a source (page structure changed, paywall, PDF-only, etc.), should the hero stat auto-hide from the landing page until a human confirms, or should it keep showing the last-known-good value with a "last verified [date]" note?** Both are defensible — auto-hide is more conservative/honest, keep-showing-with-date is less disruptive to the page. Worth deciding before Phase D ships, not during.
