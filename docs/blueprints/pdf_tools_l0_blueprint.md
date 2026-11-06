# PDF Tools L0 (Stand-alone) Blueprint

**Status:** DRAFT — pending approval
**Type:** Public page + vendored browser library (no new backend module)
**Pillar:** ACT
**Tier:** CORE (page); no feature gate — L0 public
**Date:** 2026-11-06
**Toolbox entry:** `pdf_tools` ("Merge, split, and convert PDFs without
setting anything up") — L0, `engine=action`. The entry's `today` line
currently says a stand-alone version "is being built" and its `note` flags
that pages promise no setup but route to `/preamble`. This blueprint is the
stand-alone version.

## Problem

Public pages (`/tools`, `/services`) promise PDF tools with no setup. What
actually exists today:

- A real backend, `app/modules/pdf_tools/router.py` at `/api/pdf/*`
  (CORE-registered): upload → in-memory `pdf_cache` → merge / split /
  extract pages / rotate / text / thumbnails. It never writes to disk, but
  uploads sit in process memory until a `DELETE /api/pdf/{id}` or restart.
- Two dead surfaces:
  - `/pdf-tools` (manifest-routed, `pages/pdf_tools.html`) is gated by
    `_guard_page` → valid storage cookie required, so it is not L0 — and
    even for onboarded users its JS posts to `/pdf-tools/process`, an
    endpoint that **does not exist**. The page cannot work for anyone.
  - `public/tools.html` is registered in `pages.py` but shadowed: `/tools`
    serves `pages/tools.html` (app chrome) via the dedicated handler in
    `main.py` (`_existing_public_paths` skips the registry copy).
- `/api/pdf/*` is public-in-name only: no file-size cap, no rate limit, an
  unbounded per-process cache, and CPU-bound PyMuPDF work. As-is it must
  not be pointed at by an unauthenticated public page — it is a memory/DoS
  surface.

So the promise is currently a dead end for exactly the person it is meant
for: a tenant who just needs to pull three pages out of an eviction packet
and does not want to "set up Semptify" first.

## Decision needed (Brad)

**Option A — fully in-browser (recommended).** Vendor `pdf-lib`
(MIT, single-file, ~530 KB minified; pin a released version ≥7 days old —
1.17.x line) to `static/js/vendor/pdf-lib.min.js`. Merge, split, extract
pages, rotate, and reorder run entirely in the browser via `PDFDocument`.
Page previews and PDF→text use the already-CDN-loaded `pdf.js` (same
cdnjs version pin as `document_center.html`, 3.11.174). File bytes never
leave the device — the strongest possible reading of "nothing stored,"
zero server cost, and the tool keeps working on a spotty connection after
first load. Cost: one new vendored asset + a `/credits` entry.

**Option B — hardened server-side.** Reuse `/api/pdf/*`, but first add:
upload size cap (~25 MB), per-IP rate limit via `app.core.rate_limit`,
cache TTL + delete-after-download, and page the user through an explicit
"remove my file" step. Honest copy then reads "processed in memory and
returned to you — nothing is saved" (weaker than "nothing leaves your
device"), and we still carry a public unauthenticated compute endpoint.

Recommendation: **A**. B is the documented fallback if the vendored
dependency is rejected. Do not ship the current `/api/pdf/*` to a public
page unhardened under any option.

## Scope

Does:

- Add `/tools/pdf` — a `public_shell` page, no auth, no storage, no
  identity. Chronological layout per the GUI rule:
  1. **Choose what to do** — four quiet rows: Merge PDFs · Split or pull
     pages · Rotate or reorder pages · Pull the text out.
  2. **Drop the file(s)** — drag-drop or file picker, entirely local.
  3. **See it / adjust** — pdf.js thumbnails (CDN) for page pick and
     rotate; skip preview silently if the CDN is unreachable.
  4. **Download the result** — object-URL download; a "start over" reset
     clears everything.
- Process all operations client-side with vendored `pdf-lib`: merge N
  files; extract a page selection (`1,3,5-8` — reuse the existing parse
  semantics from `parse_page_selection`); rotate/reorder; create a
  plain-text extract download via pdf.js `getTextContent`.
- Register the page additively: one `PortalPage` entry in
  `app/modules/portal/pages.py` (`in_sitemap=True`, `in_footer=False`),
  which the existing public-pages loop in `main.py` serves automatically.
  No new route code.
- Update `/credits` with pdf-lib (name, version, license, upstream URL).
- Same-PR truth pass (build-loop step 8): repoint the three
  `standalone_*` CTA paths in `app/modules/portal/registry.py` for
  `standalone_pdf_tools` from `/preamble` to `/tools/pdf`; set the toolbox
  entry `today`/`today_path`/`note` per step 7 **on the toolbox branch**
  (separate follow-up — see Out of scope).

Does NOT:

- Upload, store, cache, or log the file or its name anywhere. Zero
  network calls except the two static script fetches (pdf-lib vendored;
  pdf.js CDN — each documented on-page).
- Touch `app/modules/onboarding/` (NO-TOUCH), `app/modules/pdf_tools/`
  backend, `pages/pdf_tools.html`, or the `/pdf-tools` gated route. The
  dead in-app stub is logged to intake, not fixed here.
- Offer signing, redaction, form-filling, OCR, or compression — the
  registry's `description_long` says "sign" today; the truth pass corrects
  that copy to what the tool does (merge, split, rotate, extract, text).
- Claim the result is court-ready — standard not-legal-advice footer line
  only.
- Persist anything server-side. No new tables, no new endpoints under
  Option A.

## Honest-claims text (required, verbatim on page)

> Your file stays on your device — Semptify never sees it. The work
> happens in your browser; closing this page removes every trace.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /tools/pdf | Stand-alone PDF tools page (public_shell, L0) |

No new API routes under Option A. (Option B, if chosen, adds upload cap +
rate limit + TTL to `/api/pdf/*` and a small page-facing wrapper — spec
in a follow-up, not this blueprint.)

## Dependencies

- `static/js/vendor/pdf-lib.min.js` — new vendored asset, MIT license
  (Option A only). `/credits` updated in the same PR.
- pdf.js 3.11.174 via cdnjs — same pin already used by
  `pages/document_center.html`; used only for thumbnails/text extraction,
  with a no-preview fallback.
- `app/templates/body/public_shell.html` — existing chrome; no changes.
- `app/modules/portal/pages.py` — one additive `PortalPage`.

## Files

- `app/templates/public/tools_pdf.html` — the four-step page (public_shell)
- `static/js/tools_pdf.js` — file handling + pdf-lib operations +
  pdf.js thumbnails/text; no other dependencies
- `static/js/vendor/pdf-lib.min.js` — vendored (new, Option A)
- `app/modules/portal/pages.py` — one `PortalPage` entry
- `app/templates/public/credits.html` — pdf-lib credit line
- `app/modules/portal/registry.py` — repoint `standalone_pdf_tools` CTA
  (truth pass, same PR)

## Risk

- **Large files:** `pdf-lib` holds the document in memory. Cap input at
  ~50 MB with a plain-language message; covers real-world packets.
- **CDN unreachable:** pdf.js features degrade to a text-only flow
  (page numbers instead of thumbnails; text extraction unavailable,
  stated plainly). Core merge/split/rotate still works offline.
- **Vendored dependency risk:** pin a released version ≥7 days old;
  record version + license in `/credits`.
- **UPL risk:** none — document mechanics, no advice. `upl_risk_tier=LOW`.
- **fees_policy:** nothing priced, no fee text. Banned vocabulary check
  on all page copy ("no setup", not "no account").

## Verification plan

- `python -m py_compile` on changed Python files (venv311, Python 3.11.9)
- `pytest tests/module_health -q --no-cov`
- `python tools/guardrail_engine.py` — all checks pass
- `python tests/test_ssot_architecture.py` — nav/registry wiring passes
- Live check (IronBee browser, 127.0.0.1:8001): `/tools/pdf` loads at
  375 px and 1280 px → drop two fixture PDFs → merge → downloaded file
  opens with combined page count → split a range → rotate → console
  clean; no network calls carrying file bytes (observe via request log)
- IronBee backend `request_http` on `/tools/pdf` (200, public, no auth
  redirect) and on `/api/portal/toolbox` after the entry flip
