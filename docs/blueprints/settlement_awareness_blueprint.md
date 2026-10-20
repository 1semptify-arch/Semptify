# Settlement Awareness Blueprint

**Status:** DRAFT — pending approval
**Module path:** `app.modules.settlement_awareness.router`
**Type:** Feature (user-facing contextual surface, no standalone page)
**Pillar:** KNOW
**Tier:** DEV (lifecycle `dev_only` — Forge rule: all new modules start dev_only)
**Date:** 2026-10-20
**Source spec:** orchestrator task `settlement-awareness-module-2026-09-28` (Brad 2026-09-28;
open decisions answered by orchestrator: own `module_contract.json`, weekly cadence,
`news_secondary` held back until primary source, reuse existing Part 3B gate)

## Problem

Tenants facing a landlord usually have no idea whether the fight in front of them
is one other tenants have already had — and won, settled, or lost. Real outcomes
(settlements, consent decrees, enforcement actions, resolved cases) are scattered
across court dockets and agency press releases. This module keeps a verified
record pool of housing-litigation and settlement outcomes and surfaces the
relevant ones *contextually* — next to the statute or citation a tenant is already
looking at — so awareness arrives inside the reading they were already doing,
not on another page they have to find.

## Scope

Does:
- Store `settlement_or_case_record` rows: title, record kind, parties,
  jurisdiction, citation (optional match key), subject tag, source_url,
  source_authority, headline facts, relief summary, resolution/verification fields.
- Enforce the Part 3B hard gate *at write time and read time*: a record cannot
  become `Resolved` — and can never surface — without a populated `source_url`,
  `fabrication_check` pass, `ai_generated = false`, and a named human
  `attested_by`. `Unresolved`/`Disputed` records are quarantined from every
  consumer endpoint (auto-hide per ADR-0009 — no placeholders, no stale fallback).
- Hold back secondary/news sources: a record whose `source_authority` is a
  `news_*` type cannot resolve without a populated `primary_source_url`
  pointing at the official record.
- Freshness machinery: `last_verified_date`, `next_recheck_date` (90-day rolling),
  `is_verified` flag; a record stale >90 days stops surfacing until rechecked.
  `GET /recheck/due` returns the worklist the weekly pass consumes (cadence
  carried in MAINTENANCE_TASKLIST.md, same pattern as the Part 3B sampling audit).
- One consumer surface: `GET /api/settlement-awareness/related?subject=…` and
  `?citation=…` — tag/citation-matched list of surfaceable records. Empty list
  when nothing qualifies (silence beats fabrication). Wired into the Law Linker
  pop-out (`law_linker_popout.html`) as a quiet "Related case records" block.
- Operator endpoints for intake/resolve/verify (Brad-facing tools; no public UI).

Does NOT:
- No standalone page, menu entry, or nav item — contextual surfacing only.
- No AI-drafted summaries of outcomes or holdings — `headline`/`relief_summary`
  are human-attested factual text only; anything interpretive graduates to
  Part 3 / RIIE editorial review and does not belong here.
- No automated scraping/ingestion in v1 — intake is operator-initiated; the
  weekly pass is a recheck of known records, not discovery.
- No UPL territory: records are pointers to real public outcomes plus the link;
  no advice, no "you will win," no outcome predictions.

## Roles & capability defaults

Tenant-only repo (PR #317) — all users are tenants; public-information reads are
ungated like the Law Library. No `CAPABILITY_DEFAULTS` changes.

## DB tables

One new table on `app.core.database.Base` (SQLAlchemy async — no new Base):

`settlement_or_case_records`
`record_id` (str, unique, indexed), `record_kind` (str:
settlement|judgment|consent_decree|enforcement_action|pending_case), `title`,
`parties`, `jurisdiction`, `subject` (taxonomy.py Subject value — the
tag-match key, indexed), `citation` (optional match key), `source_url` (Text,
required), `primary_source_url` (Text, nullable — required to resolve news_*
sources), `source_authority`, `headline`, `relief_summary`, `resolution_status`
(Resolved|Unresolved|Disputed), `resolution_method`, `resolved_date`,
`last_verified_date`, `next_recheck_date`, `ai_generated` (Bool, hard false),
`attested_by` (nullable until human attests), `fabrication_check` (Bool),
`is_verified`, `verified_at`, `created_at`, `updated_at`. Index on
`(subject, resolution_status)` for the surfacing query.

PII boundary: records are public-record pointers — no tenant PII in Postgres;
nothing user-specific is stored. Alembic migration included
(`alembic/versions/*_add_settlement_or_case_records.py`); model imported in
`app/core/database.py` per module rules.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/settlement-awareness/health` | Health check (module rule) |
| GET | `/api/settlement-awareness/related` | Consumer surface — `?subject=` or `?citation=`; Resolved + fresh + attested records only |
| GET | `/api/settlement-awareness/records/{record_id}` | Single record detail, same surfacing gate |
| POST | `/api/settlement-awareness/records` | Intake — always lands Unresolved; `ai_generated` forced false |
| POST | `/api/settlement-awareness/records/{record_id}/resolve` | Operator: mark Resolved after manual source verification (hard-gate fields required) |
| POST | `/api/settlement-awareness/records/{record_id}/verify` | Operator/weekly pass: recheck result — refreshes `last_verified_date`, pushes `next_recheck_date` +90d, or flags `is_verified=false` (auto-hides) |
| GET | `/api/settlement-awareness/recheck/due` | Worklist for the weekly pass — records past `next_recheck_date` or >90d unverified |

## Dependencies

- `app.core.database.Base` / session (`get_session` pattern used by context_engine)
- `app.modules.context_engine.taxonomy` — `Subject` enum for the tag vocabulary
- `app.core.utc.utc_now` — all timestamps
- Law Linker surface: `app/templates/pages/law_linker_popout.html` gets a small
  fetch block calling `/related?citation=` (the only UI touch — one template,
  additive section, silent-empty)
- No cross-module imports (module rule 11); Law Linker stays untouched —
  integration is via the shared API surface, not a module import.

## Contracts (register.py)

- `settlement_awareness::related` — tag/citation-matched surfaceable records
- `settlement_awareness::intake` — record intake (forced Unresolved)
- `settlement_awareness::resolve` — gated resolution
- `settlement_awareness::verify` — recheck write (90-day machinery)
- `settlement_awareness::recheck_due` — weekly worklist

`module_contract.json` written in the module folder (spec requirement — same
derived-record shape as `law_linker/module_contract.json`).

## Risk

- **UPL tier: low-moderate.** Records are public-outcome pointers with links, no
  advice. The hard Part 3B gate + auto-hide is the control — a record that can't
  verify never shows. Disclaimer copy on the surface: "These are real public
  outcomes, shown for awareness — not a prediction of your result. Get legal
  advice from a qualified attorney."
- **What could break:** table migration on prod Postgres (mitigated: standard
  alembic, additive table only); stale records silently surfacing (mitigated:
  the surfacing filter requires `last_verified_date` within 90 days — staleness
  self-hides); news-source bypass (mitigated: `news_*` authority can't resolve
  without `primary_source_url`).
- `fees_policy`: not applicable — no fee claims.

## Verification plan

- `py_compile` all new/changed files (venv311 — Python 3.11.9)
- `pytest` module suite `app/modules/settlement_awareness/tests/`:
  gate enforcement (unresolvable without source_url/attestation/fabrication),
  news-secondary holdback, surfacing filter (unresolved/stale/AI-flagged hidden),
  citation normalization match, health route
- `pytest tests/module_health -q --no-cov` — no regression
- `python tools/guardrail_engine.py` — Part 3B-style record can't reach output
  unattested (the service-level gate mirrors the existing pattern)
- Live check: app boots, `/api/settlement-awareness/health` 200, `/related`
  returns [] on empty pool, Forge lists the module at dev_only
