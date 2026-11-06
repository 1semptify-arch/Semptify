# Content Review Pipeline + Next States Blueprint

**Status:** DRAFT — pending approval
**Type:** Process + data (no new module)
**Pillar:** KNOW
**Tier:** N/A — editorial pipeline and dataset honesty
**Date:** 2026-11-06
**Toolbox entries:** `law_library` (partial, engine=content),
`situation_research` (partial, engine=content) — P4 scope: "BETA→VETTED
review; next states."

## Problem

Three separate content systems carry a "is this checked?" question, and
each answers it differently — or not at all:

1. **Context explanation entries** (`context_explanation_entries` table,
   seeded from `app/data/context_explanation_workbook.csv`, 56 rows).
   ADR-0008 designed `review_status: beta | vetted` with beta entries
   carrying a lighter disclosure. On 2026-09-19 all 68 live entries were
   flipped BETA→VETTED in one commit (`aadff044`, noted as Brad-approved).
   So the *initial* review is done — but **there is no ongoing pipeline:**
   no field for who reviewed, when, or against what source, and no rule
   for what status new content starts at. The next entry someone writes
   lands in a system where VETTED is the only state anyone has ever used.
2. **`static/data/state-laws.json`** (50 states, served read-only by
   `GET /api/states`). Depth is actually three tiers, but every state
   record said `"status": "complete"` and file `metadata` claimed
   `complete_states: [50]`, `partial_states: []`, `stub_states: 0`:
   - **Full shape (11):** CA FL GA IL MI MN NC NY OH PA TX — every law
     section plus `forms_templates` + `special_programs`.
   - **Substantial (33):** all law-bearing sections present (3
     `housing_laws` items each, discrimination, legal_aid, government
     resources); missing only `nickname`/`forms_templates`/
     `special_programs` enrichment. Nine of these still carry a leftover
     `stub_url` field (AZ CO CT MA MD NJ OR VA WA).
   - **Crisis-tier (6):** IA IN MO ND SD WI — verified crisis fields only
     (notice, deposit, entry, eviction, repairs, sources, a legal-aid
     `stub_url`); own `notes` say "Crisis-tier fields only — verified
     against <code> 2026-09-07." No `housing_laws`, `discrimination`,
     `legal_aid`, `government_resources`.
   `GET /api/states` computed `complete_count: 50, stub_count: 0` from
   those `status` fields — an overclaim any consumer would inherit.
   **Fixed in this pass:** the six crisis-tier states now carry
   `"status": "partial"` and `metadata` regenerates honestly
   (44 complete / 6 partial / 0 stub). Residual honesty gap: the API's
   `stub_count` field name now means "not-complete count" — logged to
   intake, not renamed here.
   **Not fixed (needs Brad):** no per-state `last_verified` or
   `review_status` field exists — freshness rides on one file-level
   `last_updated` plus per-state `notes` strings.
3. **Curated library entries** (`ALL_LAWS` + `EXPANDED_LAWS` in the
   law_library module, `expanded_laws.py`) — MN-deep statutes, court
   rules, and federal programs with citations and `effective_date`s, but
   no `review_status` field at all. Their vetting signal is implicit:
   `law_linker` resolves each citation to the official source
   (revisor.mn.gov, govinfo) and can fetch the official text for the
   pop-out. The public `/law-library` page lede claims "Every entry shows
   the official source and the date it was last verified" — the first
   half is true via law_linker; **the "date it was last verified" half is
   not true for most entries** (no verified-date field exists on
   `ALL_LAWS`/`EXPANDED_LAWS` records — flagged, needs a schema decision).

## What "next states" concretely means

The public `/law-library` page's state dropdown is **Minnesota-only by
design** — "Other state" shows an honest "still building coverage"
message. `/api/states` can already serve all 50 states' data; nothing
public exposes it. So "next states" is two decisions, not one:

- **A. Deepen the crisis-tier six.** IA IN MO ND SD WI are the thinnest
  *and* the closest to the MN base — four are direct MN neighbors whose
  tenants may land on a Minnesota-built library. They already have
  verified crisis fields + named sources, so deepening means adding the
  standard sections (housing_laws, discrimination, legal_aid,
  government_resources) using the same verbatim-source method that built
  the current data (commits `435f795f`, `5b8301bd`, `06533e15` show the
  pattern: draft → verbatim-source pass → corrections pass).
- **B. Decide when/if non-MN states appear on `/law-library`.** Options:
  (1) keep MN-only until a state reaches full shape — calmest, most
  honest, matches the page's "Minnesota tenant law" lede; (2) open the 44
  non-crisis states now with a per-state completeness note; (3) open only
  states that reach full shape (the 11). Recommendation: **(1) now, (3)
  as each is deepened** — the page never shows a state we haven't
  finished, and "next states" stays a short visible queue (six states)
  rather than a vague promise.

## Decision needed (Brad)

1. **Review status semantics for `state-laws.json` and `ALL_LAWS`/
   `EXPANDED_LAWS`.** Add an explicit `review_status`/`last_verified`
   field per state and per curated entry (recommended — makes the
   /law-library "last verified" claim mechanically true and gives the
   BETA→VETTED rule one shape everywhere), or keep implicit vetting-via-
   citation and de-claim the page lede instead.
2. **Who may mark content VETTED going forward.** Options: Brad-only
   (current de facto), Brad + a documented rubric an agent applies
   (agent drafts, marks BETA, Brad flips to VETTED after spot-check), or
   a two-person rule. Recommended: **agent-authored content enters as
   BETA with a required `source_url`; Brad flips to VETTED.** That is one
   CSV/JSON field away from enforceable and keeps the 2026-09-19
   mass-flip from becoming the permanent norm.
3. **Next-state order.** Recommended: WI → IA → ND → SD → MO → IN
   (neighbors first), one state per pass, same draft→verbatim→correct
   loop. Alternatively pick by where actual users are (no data — we do
   not track).
4. **`/law-library` visibility rule** — per option B above.

## Scope if approved (future pass, not this task)

- Add `review_status` + `last_verified` + `source_url` fields to the
  six crisis-tier records as they're deepened (schema is free-form JSON;
  `StateDetails` already tolerates extra keys — `stub_url`/`sources`/
  `notes` prove it).
- Same fields on new `ALL_LAWS`/`EXPANDED_LAWS` entries; backfill dates
  where the git log gives a verified-source pass date.
- Loader rule: new workbook rows default `BETA` unless Brad flips
  (`tools/load_explanation_workbook.py`).
- Deepen the six states in the recommended order; flip `status` as each
  reaches full shape.
- Re-point the `/law-library` lede claim to whatever decision #1 lands.

## Out of scope (flagged, not done here)

- Rewriting any state content itself — this blueprint is the pipeline +
  ordering, the per-state deepening is its own task per build loop.
- `stub_count` API field-name semantics (intake-logged).
- Whether the 33 substantial states' missing `forms_templates`/
  `special_programs` sections matter — an enrichment question, not an
  honesty one.

## Verification (for the build pass)

- `GET /api/states` reports counts matching the JSON `status` fields.
- Each deepened state passes the verbatim-source check pattern already
  used (source URL per legal claim).
- `/law-library` shows no state whose record is not full shape, or shows
  the completeness note honestly if option B(2) is chosen.
