# Public Research Outputs — Aggregate-Only Blueprint

**Status:** DRAFT — pending approval
**Phase:** P10 Research (L4) — orchestrator task `sorg-p10-research`
**Engine:** civic
**Level:** L4 — "Public records and anonymous totals only"
**Toolbox entries served:** `landlord_research`, `litigation_intelligence`
(public name: *Housing court patterns*), `housing_accountability`,
`fraud_exposure` (public name: *Pattern documentation*),
`public_records_suite`, `researcher_data`, `policy_reporting`
**Date:** 2026-11-07

## Problem

Seven toolbox entries promise public research outputs. The backing modules
exist and pass health checks, but every public-research module is
`ProductTier.RESEARCH`, which production does not mount — so nothing is
reachable on semptify.org today. More importantly, several backing modules
were built to output *named-party* findings (a fraud report against a named
landlord, an entity graph naming people and organizations, a press-release
generator). That shape cannot ship publicly: it conflicts with the L4
contract, the no-PII rule, the non-adversarial voice rules, and creates
defamation/UPL exposure the project cannot carry.

## The aggregate-only contract (the actual decision this blueprint asks for)

Any output a member of the public can see follows these rules:

1. **Combined totals only.** Counts, rates, distributions, trends. Never a
   row about one party, case, or address.
2. **Small-cell suppression.** A group smaller than 5 underlying records is
   not shown — it folds into the next-larger grouping. (Matches common
   statistical-disclosure practice for public reports.)
3. **Geography floor:** city or ZIP at smallest — never street address,
   never parcel.
4. **No named parties.** No landlord names, LLC names, attorney names,
   tenant names, or case numbers in any public output. Entity-level findings
   stay internal.
5. **Sources shown.** Every published figure names its source dataset and
   its coverage window ("Hennepin County eviction filings, 2023–2025").
6. **Official channels only.** Inputs come from sanctioned public sources —
   court-published datasets, agency open data, records obtained through
   proper channels. No scraping that violates a site's terms.
7. **Calm framing.** Findings are stated as facts ("14% of filings in this
   county repeat a fee pattern") — never as accusations against a party.

## What already exists (verified 2026-11-07)

| Module | Tier | Mounted in prod | Shape vs contract |
|---|---|---|---|
| `litigation_intelligence` | RESEARCH | No | Reporting layer produces aggregate reports (fits); graph engine produces named-entity graphs (does NOT fit public use) |
| `housing_accountability` | EXTENDED (beta) | Yes | `detect_repeated_fees()` pattern detection — per-subject, internal shape |
| `accountability_ledger` | RESEARCH | No | Named-subject registry — internal shape by design |
| `legal_intel` | RESEARCH | No | "Who owns this LLC" lookups — named entities, internal |
| `crawler` | RESEARCH | No | Legal-data crawler — internal tooling |
| `external_mappings` | EXTENDED (beta) | Yes | Cross-system ID mapping — internal plumbing |
| `fraud_exposure` | RESEARCH | No | Per-landlord `FraudReport` with named parties and damages — internal shape |
| `public_exposure` | RESEARCH | No | Press-release generator — not a records suite at all (name/backing mismatch on the `public_records_suite` entry) |

## Proposed build (v1)

One read-only public surface, no new PII surface:

- **Aggregation job** (internal, scheduled): reads sanctioned public
  datasets → produces aggregate fact rows `(metric, geography, period,
  value, source_dataset)` — nothing finer than the contract floor.
- **Public read surface**: `/research` (or the existing
  `/legal-research`/toolbox path) renders published aggregate facts with
  source labels. One page, one job; eye-path per the chronological rule.
- **Publishing gate**: nothing reaches the public surface without a human
  "publish" mark — same posture as the settlement_awareness Part 3B gate
  (silence beats fabrication).
- Entry flips only when a real aggregate fact ships, per build-loop step 7.

## Explicit non-goals (v1)

- No public per-landlord lookup, scoring, or "wall of shame."
- No public entity graph visualization.
- No public fraud findings about named parties.
- No press-release / journalist-pipeline features on the public site.
- No live court scraping on a public request path.

## Open decision for Brad — `litigation_intelligence` graph engine

The "build or remove" question resolves differently than expected: the
graph engine **already exists and works** (~4,700-line module, 17
auth-gated endpoints, health check OK, BFS paths + SVG/PNG viz). It is
simply dormant because RESEARCH tier is not mounted in production.

Options:

- **A. Keep dormant, build aggregate surface separately (recommended).**
  The internal module keeps its value for case-side work; the public L4
  promise is fulfilled by the aggregate contract above. Nothing to delete,
  nothing to expose. Public graph viz is the wrong shape — it names
  parties, which the contract forbids.
- **B. Build public graph feature.** Requires a re-aggregated,
  de-identified graph — significant new work for a feature the contract
  mostly forbids anyway.
- **C. Remove the module.** Deletes working, tested code that still has
  internal/case-side value; the entry's public promise still needs an
  aggregate answer regardless.

**Recommendation: A.** The decision point isn't the engine (it's built) —
it's whether any public output names parties, and the answer stays no.
