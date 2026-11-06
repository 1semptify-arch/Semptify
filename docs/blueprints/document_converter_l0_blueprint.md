# Document Converter L0 (Stand-alone) Blueprint

**Status:** DRAFT — pending approval
**Type:** Public page + existing vendored browser libraries (no new
backend module, no new vendored dependency)
**Pillar:** ACT
**Tier:** CORE (page); no feature gate — L0 public
**Date:** 2026-11-06
**Toolbox entry:** `document_converter` ("Change documents between PDF,
Word, web page, and text") — L0, `engine=action`. Same standing as
`pdf_tools`: promised "no setup", actually routes to `/preamble`.

## Problem

What exists today:

- Backend `app/modules/document_converter/` at `/api/convert/*`
  (CORE-registered): **markdown → DOCX and markdown → HTML only** —
  `DocumentConverter` in `converter.py` has no other input format. It
  **writes every output to `data/converted_documents/` on disk** and
  serves `GET /api/convert/list` enumerating all converted files (any
  visitor could list every document anyone converted) plus
  `POST /api/convert/path` reading arbitrary server file paths. None of
  that is exposable to an L0 public page — flagged to intake for
  hardening/removal, not fixed here.
- `pages/document_converter.html` (manifest-routed at
  `/document-converter`) is storage-cookie gated **and** posts to
  `/document-converter/convert`, which does not exist. Dead for everyone.
- The promise is also wider than the backend: "PDF to DOCX, DOCX to HTML,
  HTML to PDF" — the server does none of these.

Meanwhile the browser-side machinery is already vendored and proven:
`static/js/vendor/mammoth.browser.min.js` (real DOCX → HTML, used by the
document center and media player) and `static/js/docx_export.js`
(hand-rolled HTML → genuine OOXML `.docx` — deliberately built so output
re-reads through mammoth). Those two cover the highest-value conversions
with zero new dependencies and zero bytes leaving the device.

## Scope

Does:

- Add `/tools/convert` — a `public_shell` page, no auth, no storage.
  Chronological layout:
  1. **Drop a file or pick a format** — accepts `.docx`, `.html`, `.txt`
     (and pasted text).
  2. **Choose what you need** — rows: Word document (.docx) · Web page
     (.html) · Plain text (.txt) · Printable / PDF.
  3. **Convert** — runs in the browser.
  4. **Download the result** — object-URL download; "convert another"
     reset.
- Client-side conversions (all files stay on the device):
  - `.docx` → `.html` and `.txt` via vendored **mammoth**
    (`mammoth.convertToHtml` / `extractRawText`).
  - `.html` / `.txt` / pasted text → `.docx` via vendored
    **`docx_export.js`** (existing, unchanged).
  - Any input → "Printable / PDF": render a clean print-stylesheet view
    and invoke the browser's own print ("Save as PDF" is built into every
    modern browser) — an honest, dependency-free PDF path stated plainly
    on the page.
  - `.html` → `.txt`: DOM text extraction. `.txt` → `.html`: minimal
    paragraph wrap + escape.
- Honest capability statement on the page (below) — including what it
  does NOT do (see Does NOT).
- Register additively: one `PortalPage` in `pages.py`; no route code.
- Same-PR truth pass: repoint `standalone_document_converter` CTA in
  `registry.py` to `/tools/convert`; correct `description_long` to the
  supported matrix (no "PDF to DOCX" claim — PDF is an output via print,
  not an input).

Does NOT:

- Upload, store, cache, or log the document anywhere. Zero network calls
  after page load.
- Touch `app/modules/onboarding/` (NO-TOUCH), the
  `app/modules/document_converter/` backend, or the dead
  `pages/document_converter.html` stub.
- Accept PDF input — PDF→DOCX/HTML is real OCR-class work the vendored
  stack does not do; the page states this plainly and points PDF work at
  `/tools/pdf` (text extraction path).
- Claim Word-fidelity for complex documents: mammoth maps to clean
  semantic HTML; tracked changes, embedded objects, and exotic styling do
  not survive — the page says so in one line.
- Use `/api/convert/*` — its disk writes and file listing are the exact
  opposite of the L0 promise.

## Honest-claims text (required, verbatim on page)

> Your file stays on your device — Semptify never sees it. Conversion
> happens in your browser; closing this page removes every trace. For
> "PDF" output, your browser's own Save-as-PDF does the conversion.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /tools/convert | Stand-alone document converter page (public_shell, L0) |

No new API routes.

## Dependencies

- `static/js/vendor/mammoth.browser.min.js` — already vendored; unchanged.
- `static/js/docx_export.js` — already vendored; unchanged.
- `app/templates/body/public_shell.html` — existing chrome; no changes.
- `app/modules/portal/pages.py` — one additive `PortalPage`.
- No new third-party assets.

## Files

- `app/templates/public/tools_convert.html` — the four-step page
  (public_shell)
- `static/js/tools_convert.js` — format detect + mammoth/docx_export
  orchestration + print view
- `app/modules/portal/pages.py` — one `PortalPage` entry
- `app/modules/portal/registry.py` — repoint `standalone_document_converter`
  CTA + corrected `description_long` (truth pass, same PR)

## Risk

- **Fidelity expectations:** mammoth + docx_export cover paragraphs,
  headings, lists, simple tables, basic inline formatting — that is the
  honest matrix; the page names it rather than implying general fidelity.
- **Large files:** browser-memory bound; cap input ~25 MB with a
  plain-language message.
- **UPL risk:** none — format conversion, no advice. `upl_risk_tier=LOW`.
- **fees_policy:** nothing priced, no fee text.
- **Drift risk (server path):** `/api/convert/*` keeps its disk-write +
  `/list` behavior for internal use until the intake-logged hardening
  task lands; the public page must never link to it.

## Verification plan

- `python -m py_compile` on changed Python files (venv311)
- `pytest tests/module_health -q --no-cov`
- `python tools/guardrail_engine.py` — all checks pass
- `python tests/test_ssot_architecture.py`
- Live check (IronBee browser, 127.0.0.1:8001, 375 px + 1280 px):
  `/tools/convert` → drop fixture `.docx` → download `.html` and verify
  content → drop `.html` → download `.docx` and re-open through mammoth
  to confirm round-trip → print view opens → console clean; confirm zero
  POST/file-bearing requests
- IronBee backend `request_http` on `/tools/convert` (200, no auth
  redirect)
