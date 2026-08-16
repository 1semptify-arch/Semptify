# ADR-0009 — Fact-Check / Freshness System for Public-Facing Claims

**Status:** Accepted
**Date:** 2026-08-15
**Author:** swe-1.7 (per `HANDOFF_factcheck_freshness_buildnow.md` and `HANDOFF_factcheck_docs_integration.md`)

---

## 1. Context

The landing page rebuild requires a sourced hero fact strip. A pre-build audit found that Semptify already has the *bones* of a fact-checking system:

- `app/modules/context_engine/verifier.py` checks that a `ContextFact.source_url` still resolves.
- `app/core/data_freshness_manager.py` has staleness rules and alerting plumbing.
- `app/modules/resource_directory/router.py` tracks `last_verified` staleness for community resource listings.

However, none of these were scheduled, none covered landing-page or marketing claims, and none performed *content-level* supersession detection. The immediate trigger was the Calder-Wang/Kim rent-pricing figure, which drifted from `$25/month` in one version to `$53/month` in a newer version without anything in the system catching the change.

The goal is to make sure public-facing numeric or factual claims are live-verified, not hardcoded and forgotten.

## 2. Decision

### 2.1 Extend existing systems, do not build a third

Reuse the `ContextFact` model and `context_engine/verifier.py` as the foundation, and `data_freshness_manager.py` as the scheduling/alerting layer. Add a `canonical_value` field to `ContextFact` so the system can detect *drift in the figure itself*, not just link death.

### 2.2 Content-level verification is the core new capability

Upgrade the verifier from an HTTP `HEAD` check to a full `GET` fetch, extract the relevant figure using a configured per-claim pattern (regex/snippet), and compare it to `canonical_value`. Mismatch → `is_verified=False` and a freshness alert. If the pattern cannot extract cleanly, that also raises an alert ("could not verify, needs human check"), because an unverifiable claim is not the same as a verified one.

### 2.3 Landing claims get their own subject

Public-facing hero/marketing claims are stored as `ContextFact` rows with `subject="landing"`. This lets the existing `GET /api/context/facts` path and the freshness scheduler target them without a parallel model.

### 2.4 Scheduling must actually run

Add a `FreshnessType.MARKETING_CLAIMS` (or `LANDING_STATS`) rule with a short `max_age_hours` (24–168h) and high priority. Wire a real trigger:

- **Preferred:** Render cron hitting `/api/data-freshness/cron/verify-landing-claims` (or the existing `/cron/daily-refresh` after it includes the new rule).
- **Fallback:** start `data_freshness_manager.start_background_scheduler()` in `app/main.py` lifespan for local/non-Render environments.

The in-process scheduler currently exists as dead code; this decision makes it either run or be replaced by an external cron, but not left unwired again.

### 2.5 Landing page renders from verified data

The hero fact strip is rendered from `GET /api/landing/facts`, which returns only `is_verified=True`, non-expired claims with their `source_name`, `source_url`, and `citation`. If a claim is stale or unverifiable, the UI hides it or shows an honest "checking..." state — it never displays a number that might be wrong as if it were confirmed.

## 3. Why

- **Root-cause fix, not band-aid:** Hardcoding the hero stat and promising to fix the system later would repeat the exact failure mode that let the Calder-Wang/Kim drift go undetected.
- **Reuse over duplication:** The Context Engine and Data Freshness Manager already have the right abstractions. A third, parallel fact-checking system would fragment the truth-source and be forgotten just as easily.
- **Information Integrity is a standing process:** MOTIVATIONS.md §7 already says factual claims must be sourced and freshness-checked. This ADR gives that policy a mechanical implementation.
- **Calm-by-design:** Landing-page claims are high-trust, low-context moments. Showing a stale or unverifiable number there undermines the rest of the platform's "no fear, no manipulation" standard.

## 4. Consequences

### Positive

- Public-facing numeric claims are mechanically verified on a schedule, not just at publish time.
- The same system can be reused for future marketing, about-page, or library stats by adding more `subject="landing"` (or other subject) `ContextFact` rows.
- Drift in a cited source is detected as an alert, not as a user complaint.

### Costs / risks

- Adds a small maintenance surface: per-claim extraction patterns must be updated if a source page restructures.
- Requires discipline to treat "could not extract" as an alert, not a silent pass.
- `data_freshness` is currently registered in `ProductTier.DEV`; once the landing page depends on it, it must be promoted to `ProductTier.CORE`.

## 5. Dependencies on existing systems

- `app/modules/context_engine/models.py` — `ContextFact` table (add `canonical_value`).
- `app/modules/context_engine/verifier.py` — currently HTTP `HEAD`; to be extended with `GET` + pattern extraction.
- `app/core/data_freshness_manager.py` — rules, alerts, scheduling.
- `app/modules/data_freshness/router.py` — cron endpoints.
- `app/core/product_manifest.py` — tier registration for `data_freshness`.
- `app/templates/index.html` and new landing page — consumers of `GET /api/landing/facts`.

## 6. Open decisions

1. **Auto-hide vs. last-known-good on unverifiable claims:** Decided **auto-hide**. A hero claim that fails verification or was never verified does not render on the landing page — no fallback display, no placeholder number. This preserves the "no fear, no manipulation" standard and prevents a stale or contested figure from being shown as confirmed.

## 7. Related documents

- `HANDOFF_factcheck_freshness_buildnow.md` — phased implementation plan (Phase A–E).
- `HANDOFF_factcheck_docs_integration.md` — how this ADR is folded into protocol, standards, and build docs.
