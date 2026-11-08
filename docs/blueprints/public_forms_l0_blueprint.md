# Public Forms Browser L0 (Stand-alone) Blueprint

**Status:** DRAFT — pending approval
**Type:** Public page over an existing public read API (no new backend
module, no storage)
**Pillar:** ACT
**Tier:** CORE (page); no feature gate — L0 public
**Date:** 2026-11-06
**Toolbox entry:** `public_forms` ("Housing forms and templates to
download or fill") — L0, `engine=action`. Promised on `/tools` and
`/services`; `today` currently routes to `/preamble`.

## Problem

The name is misleading in two directions:

- The module `app/modules/public_forms/` is **not** a forms library — it
  is the feedback / contact / tool-request / your-voice machinery. There
  is no browsable "public forms" surface behind the name today.
- The real form catalog already exists elsewhere:
  `app/modules/court_forms/data/forms_library.json` holds **12 Minnesota
  district-court forms** (Housing and Civil categories) with title, case
  type, jurisdiction, signature requirement, related forms, and the
  official `mncourts.gov` download URL for each. It is already served by
  **public, no-auth, read-only** endpoints: `GET /api/forms/library` and
  `GET /api/forms/library/{form_id}` (the fill/render/save endpoints on
  the same router are `red_access`-gated — correctly, since form
  *generation* is `upl_risk_tier=HIGH` and belongs to P5's `court_forms`
  entry).

So the L0 deliverable is a browse surface, not a fill pipeline: a calm
page that lists the real catalog, links each form to its official source,
and says honestly what it is (12 Minnesota court forms) and is not (a
national library, fill-in-the-blank wizardry, or legal advice). Filling
stays where it belongs — inside Semptify, pointing to `/preamble`, and
explicitly deferred to P5's court-forms work.

## Scope

Does:

- Add `/tools/forms` — a `public_shell` page, no auth, no storage.
  Chronological layout:
  1. **Pick a category** — Housing first, then Civil (from the catalog's
     own `category` field, no invented taxonomy).
  2. **Read the row** — per form: plain title, case type, jurisdiction,
     a "signature required" marker when true, and related forms.
  3. **Get the official form** — one link per row to the form's
     `official_url` (mncourts.gov), marked as the official source.
  4. **Need to fill one?** — a single quiet pointer to `/preamble`
     ("fill inside Semptify"), plus the standing "Get help now" path.
- Serve the catalog through the existing public read endpoints —
  `GET /api/forms/library` (list) — rendered server-side into the page
  (no client fetch needed; the page can also fetch live for freshness,
  either is fine, pick one in build).
- One honest-scope line on the page (below): Minnesota court forms
  today, official source shown for each — nothing about other states or
  housing-agency forms that do not exist in the catalog yet.
- Register additively: one `PortalPage` in `pages.py`; no route code.
- Same-PR truth pass: repoint `standalone_public_forms` CTA in
  `registry.py` to `/tools/forms`; correct its `description_long`
  ("lease agreements, notice letters" do not exist in the catalog —
  the page lists what the JSON actually holds).

Does NOT:

- Collect, store, or transmit any personal data — read-only page.
- Render or fill forms at L0 — `/api/forms/library/{id}/render` and
  `/save` stay `red_access`-gated; P5 owns fill flows.
- Touch `app/modules/onboarding/` (NO-TOUCH), `app/modules/public_forms/`
  (misnamed but live machinery — renaming is out of scope, logged to
  intake), `court_forms`'s service/router, or `forms_library.json`
  (content additions are a content task, not this build).
- Imply a national forms library — 12 Minnesota forms, stated plainly.
- Give legal advice — one-line not-a-law-firm footer, no per-form
  commentary beyond the JSON's own fields.

## Honest-claims text (required, verbatim on page)

> These are Minnesota court forms, linked to the official court website
> for each one. Reading and downloading them sends nothing to Semptify.
> Filling one out is a bigger step — the fill path lives inside Semptify
> and keeps your answers in your own storage.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /tools/forms | Public forms browser (public_shell, L0) |

No new API routes (reuses public `GET /api/forms/library`).

## Dependencies

- `GET /api/forms/library` + `GET /api/forms/library/{form_id}` —
  existing, public, read-only (`app/modules/court_forms/router.py`,
  backed by `data/forms_library.json` via `library.py`).
- `app/templates/body/public_shell.html` — existing chrome; no changes.
- `app/modules/portal/pages.py` — one additive `PortalPage`.

## Files

- `app/templates/public/tools_forms.html` — category → rows → official
  link → fill pointer (public_shell)
- `app/modules/portal/pages.py` — one `PortalPage` entry
- `app/modules/portal/registry.py` — repoint `standalone_public_forms`
  CTA + corrected `description_long` (truth pass, same PR)
- Optional tiny `static/js/tools_forms.js` if live-fetch rendering is
  chosen over server-side render

## Risk

- **Catalog drift:** the JSON's `last_updated` is file-level; rows link
  out to mncourts.gov so a stale local record never sells a dead file —
  the official site is always the download source of truth.
- **Scope creep in copy:** the word "library" invites expectations;
  page copy names the count honestly ("the Minnesota court forms we can
  describe today") so it does not overpromise P5 work.
- **UPL risk:** LOW — a public catalog of official forms with sources is
  information, not advice; no field-level guidance at L0.
- **fees_policy:** nothing priced, no fee text.

## Verification plan

- `python -m py_compile` on changed Python files (venv311)
- `pytest tests/module_health -q --no-cov`
- `python tools/guardrail_engine.py` — all checks pass
- `python tests/test_ssot_architecture.py`
- Live check (IronBee browser, 127.0.0.1:8001, 375 px + 1280 px):
  `/tools/forms` renders all catalog rows grouped by category → each row
  shows its official link → console clean
- IronBee backend `request_http` on `/tools/forms` (200, no auth
  redirect) and `GET /api/forms/library` (200, 12 rows)
