# SEMPTIFY MODULE BLUEPRINT — SPEC & TEMPLATE

**Version:** 2.0 | **Last Updated:** 2026-09-05
**Read this BEFORE building any module, plugin, or add-on for Semptify.**

> This file replaces the archived `archive/obsolete-2026-06-29/MODULE_BLUEPRINT.md`
> (v1.0, 2026-06-14). It is the "Part 0A" spec referenced by `AGENTS.md`,
> `docs/blueprints/README.md`, and `docs/admin/SEMPTIFY_DEVELOPER_ONBOARDING.md`.
> For the module lifecycle pipeline itself, see `.devin/skills/forge/SKILL.md`
> and `.devin/rules/09-forge.md`.

---

## PART 0 — WHO WE ARE AND WHAT WE STAND FOR

Every module built for Semptify must honor these mandates without exception.

### Our Mission

Semptify is a **public utility for tenant rights**, not a product and not a business.
The north star is **Time to Real Help** — every feature either reduces it or doesn't
belong. We are on the side of tenants, always — but only when they exercise their
lawful rights.

### The Non-Negotiable Mandates

| Mandate | Rule |
| --- | --- |
| **No cost, ever** | No paywalls, subscriptions, tiers, or gates. Never describe Semptify itself as "free" — that implies other things cost money. (Factual descriptions of *external* resources like "free legal aid" are fine.) |
| **No advertising. Ever.** | No ad networks, sponsored content, affiliate links, or promoted results. Neutral resource listings only when relevant, factual, and owner-approved. |
| **No tracking** | No analytics pixels, third-party trackers, behavioral profiling, or fingerprinting. |
| **No data retention beyond need** | Tenants own their data. Export and delete must always be possible. |
| **No data selling** | Tenant data is never sold, shared, licensed, or monetized. |
| **No hidden state** | Every system action must be auditable by the tenant. |
| **Privacy by design** | Documents live in the tenant's own cloud (Google Drive / Dropbox / OneDrive). PII lives in vault overlays, not PostgreSQL. |
| **No manipulation** | No dark patterns, urgency tricks, engagement bait, or growth-hack flows. |
| **No dead ends** | Every error or broken flow must route the user toward real help. |
| **Calm, clear UX** | Users are often stressed and short on time. Every UI decision reduces friction and anxiety. |

### What This Means for Module Builders

- No external analytics or ad SDK calls — none.
- No third-party data brokers; no tenant data leaves the system without explicit consent and disclosure.
- No retention beyond the operation that needs it.
- No user profiling — do not infer, score, or categorize tenants from behavior.
- Tenant-deletable records — anything your module stores, the tenant can remove.
- Plain language — readable under stress, no legal background assumed.
- Facts only — when the law protects a tenant, say so plainly; never hedge legal facts into uselessness.

### The Product Decision Filter

When choosing between approaches, prefer the one that better serves: **rights
protection → evidence integrity → tenant control → clarity under stress.**

---

## PART 0A — REQUIRED BLUEPRINT SECTIONS (the full list)

Every blueprint in `docs/blueprints/` MUST contain all of the following. A blueprint
missing any section is not reviewable.

| # | Section | Required content |
| --- | --- | --- |
| 1 | **Status line** | `Status: DRAFT — pending approval` / `Status: APPROVED — approved YYYY-MM-DD` / `Status: BUILT — shipped in commit <hash>` |
| 2 | **Module name + `module_path`** | Dotted path, e.g. `app.modules.your_module.router` |
| 3 | **Module type** | **Pipeline Module** (internal, no UI, no gating) or **Feature Module** (user-facing, UI + routes, gated via `user_capabilities`). Never confuse them. |
| 4 | **Pillar** | Exactly one: RECORD / KNOW / ACT / GOVERN (`.devin/rules/06-four-pillars.md`) |
| 5 | **Problem** | Which tenant right or workflow gap this serves, in plain language |
| 6 | **Scope** | What it does **AND** what it explicitly does NOT do |
| 7 | **Roles** | Which roles get it by default → `CAPABILITY_DEFAULTS` entries in `product_manifest.py` |
| 8 | **DB tables** | Every new table (or "none"). All models on `app.core.database.Base`, SQLAlchemy async |
| 9 | **Routes** | Every API endpoint: method + path + one-line purpose. Include the `/health` route |
| 10 | **Dependencies** | Which existing modules/services it calls — by their `FunctionGroupContract` names, not invented signatures |
| 11 | **Tier** | CORE / EXTENDED / ADVOCATE / ADMIN / RESEARCH / DEV |
| 12 | **Risk** | What could break; UPL risk tier if user-facing legal content; `fees_policy` if the word "fee" appears |
| 13 | **Verification plan** | How it will be proven: `py_compile`, `pytest tests/module_health`, `guardrail_engine`, live check |

**Approval rule:** code written before a blueprint is approved will be removed.
If asked to build a module without one, write the blueprint first and wait for
explicit approval ("yes build it" counts).

**Naming & location:** `docs/blueprints/your_module_name_blueprint.md`

---

## PART 0B — FILLABLE TEMPLATE

Copy this skeleton into `docs/blueprints/<name>_blueprint.md` and fill it in:

```markdown
# <Module Name> Blueprint

**Status:** DRAFT — pending approval
**Module path:** `app.modules.<name>.router`
**Type:** Pipeline | Feature
**Pillar:** RECORD | KNOW | ACT | GOVERN
**Tier:** CORE | EXTENDED | ADVOCATE | ADMIN | RESEARCH | DEV
**Date:** YYYY-MM-DD

## Problem
<which tenant right / workflow gap, plain language>

## Scope
Does: <...>
Does NOT: <...>

## Roles & capability defaults
<which roles get it; CAPABILITY_DEFAULTS lines to add — Feature modules only>

## DB tables
<tables or "none"; PII boundary note: PII goes in vault overlays, not Postgres>

## Routes
| Method | Path | Purpose |
| --- | --- | --- |
| GET | /api/<name>/health | Health check |

## Dependencies
<contracts called, e.g. overlays::overlay_create; "none" if standalone>

## Risk
<what could break; UPL risk tier; fees_policy if applicable>

## Verification plan
<py_compile / pytest tests/module_health / guardrail_engine / live checks>
```

---

## PART 1 — IMPLEMENTATION RULES AFTER APPROVAL

Once a blueprint is APPROVED, build to it exactly:

1. Folder: `app/modules/<name>/` with `__init__.py`, `router.py`, `config.py`, `models.py` (if tables), `register.py` (if contracts), `README.md`.
2. Register in `app/core/product_manifest.py` with one `_register(...)` line — `optional=True` always.
3. Declare `FunctionGroupContract`s in `register.py` for anything other modules may call. The contract is the SSOT — if it's not in the contract, it doesn't exist.
4. Feature modules: add to `CAPABILITY_DEFAULTS` for the approved roles.
5. DB tables: import models in `app/core/database.py`, write an Alembic migration.
6. Redirects: `navigation.get_stage(...)` — never hardcoded URLs.
7. Time: `utc_now()` from `app.core.utc` — never bare `datetime.now()`.
8. Errors: specific exception types — never bare `except:`.
9. Async paths: async I/O only — no `httpx.Client`/`requests` inside `async def`.
10. Verify: `python -m py_compile` on changed files → `pytest tests/module_health -q --no-cov` → `python tools/guardrail_engine.py` → live check via IronBee DevTools where UI is involved.
11. One task per commit. Update `BUILD_STATE.md`. Do not self-approve — Brad confirms completion.

*Questions this file doesn't answer: `AGENTS.md` (behavior/ethics + Known Failure Registry) → `PROJECT_BIBLE.md` (governance) → `SECURITY_AND_PRIVACY_ARCHITECTURE.md` (security).*
