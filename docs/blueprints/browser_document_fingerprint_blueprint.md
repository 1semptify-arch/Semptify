# Browser Document Fingerprint Blueprint

**Status:** DRAFT — pending approval
**Module path:** `app.modules.fingerprint.router`
**Type:** Feature
**Pillar:** RECORD
**Tier:** CORE
**Lifecycle:** experimental → stable once verified
**Date:** 2026-11-05
**Toolbox entry:** `timestamp_seal` ("Prove a document existed — fingerprint & timestamp") — L0 capability, must work with no account and no connected storage.

## Problem

The `timestamp_seal` Toolbox entry promises a tenant can prove a document
existed at a point in time. Today the only path to a hash + timestamp is
uploading the file through `VaultUploadService` — which requires a connected
vault and stores the file. A tenant who only wants "prove I had this letter
on this date" gets nothing usable at L0, and the upload path quietly couples
fingerprinting to storage.

The SHA-256 + RFC 3161 machinery already exists
(`app/services/storage/tsa.py`) — what's missing is a way to fingerprint a
document **without the file ever leaving the tenant's device**, and to say
honestly what a fingerprint does and doesn't prove.

## Scope

Does:

- Provide a page (`/record/fingerprint`, shell page, L0 — any visitor, no
  storage connection, no identity gate) with three steps in chronological
  order per the GUI rule: (1) choose a file, (2) see its fingerprint, (3)
  optionally get a timestamp receipt.
- Compute the document's SHA-256 **entirely in the browser** via Web Crypto
  (`crypto.subtle.digest("SHA-256", arrayBuffer)`). The file bytes never
  leave the device. Display: file name (rendered locally, never
  transmitted), size, SHA-256 hex, local time fingerprinted.
- Offer an optional step 3: POST only the 64-hex hash to
  `POST /api/record/fingerprint/stamp`, which calls the existing
  `stamp_document_hash(document_hash, timestamp_iso)` → returns
  `TSAResult`-shaped JSON (`token_b64`, `tsa_backed`, `timestamp_iso`,
  `error`). **Stateless — the server stores nothing.** RFC 3161 when the
  TSA is reachable; the existing HMAC fallback otherwise, labeled honestly
  in the UI ("Semptify-signed timestamp — a third-party stamp is
  stronger").
- Offer a verify step: tenant drops a file + pastes a saved receipt →
  browser recomputes the hash → `POST /api/record/fingerprint/verify`
  calls `verify_tsa_token(token_b64, document_hash)` → shows
  match / does-not-match in plain language.
- Generate a downloadable receipt `.json` **client-side**
  `{filename, sha256, stamped_at, method: "rfc3161"|"hmac_fallback",
  token_b64}` — the tenant keeps it next to the file it describes.
- State the honest-claims text on the page (see below), verbatim, before
  the stamp button.
- Register per the three-step rule: one `_register(...)` line in
  `product_manifest.py` (CORE tier), a `CAPABILITY_DEFAULTS` entry, the
  models-import line in `app/core/database.py` (no-op if no models — omit).

Does NOT:

- Upload, store, or log the document, its name, or any content. Only a
  64-character hex digest ever crosses the wire, and it is never persisted
  server-side.
- Claim blockchain anchoring, legal admissibility, or proof of
  authorship/truth — a hash only proves a later file is byte-identical to
  what was stamped.
- Touch `app/modules/onboarding/` (NO-TOUCH), `vault_upload_service.py`,
  or `certificate_generator.py`. This is a separate L0 surface, not a
  change to the upload pipeline.
- Require a vault, a session, or storage connection for the hash step.
  The TSA stamp step is server-mediated but still needs no identity —
  rate-limit by IP instead of by user.
- Persist a fingerprint registry on the server (no "we saw this hash"
  table — that's a surveillance surface with zero tenant benefit).
- Implement a new hashing/timestamp backend — reuses `tsa.py` verbatim.

## Honest-claims text (required, verbatim on page)

> A fingerprint shows that the file you have **now** is identical to the
> file that was fingerprinted **then**. A timestamp receipt adds an
> independent time record to that claim. Neither proves who created the
> file, that its contents are true, or that a court will accept it — it is
> documentation that supports your paper trail.

## Roles & capability defaults

Tenant (only role post-#317) gets the capability by default via
`CAPABILITY_DEFAULTS["tenant"]`. The page itself is L0-public: no
`require_capability` gate on the hash path; the stamp/verify endpoints are
public but rate-limited.

## DB tables

None. PII boundary: nothing persists — no hash log, no fingerprint table,
no request-body logging on the stamp endpoint beyond the standard request
log line (which already excludes bodies).

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /record/fingerprint | Fingerprint tool page (shell, L0) |
| GET | /api/record/fingerprint/health | Module health check |
| POST | /api/record/fingerprint/stamp | `{sha256}` → `TSAResult` JSON. Validates 64-hex input. |
| POST | /api/record/fingerprint/verify | `{sha256, token_b64}` → `{match, method, detail}` |

## Dependencies

- `app.services.storage.tsa.stamp_document_hash` / `verify_tsa_token` —
  existing, unchanged.
- `app.core.utc.utc_now` — stamp timestamp.
- `app.core.config.get_settings` — `tsa_url` (FreeTSA default; no new
  settings needed).
- `app.core.rate_limit` (or the existing rate-limiting dependency used by
  public endpoints) — stamp/verify abuse control.
- Browser Web Crypto API — `crypto.subtle.digest`, plus a plain-language
  fallback message when unavailable (non-secure context / legacy browser).

## Files

- `app/modules/fingerprint/` — `__init__.py`, `router.py`, `service.py`
  (thin: validate hash hex, call tsa.py, shape response),
  `module_contract.json`, `README.md`
- `app/templates/pages/fingerprint.html` — three-step page (choose →
  fingerprint → optional stamp/verify), chronological top-to-bottom
- `static/js/fingerprint.js` — file-read + `crypto.subtle.digest`, receipt
  JSON download, verify flow; no external dependencies
- `app/core/product_manifest.py` — one `_register(...)` line
- `app/core/capabilities.py` — `CAPABILITY_DEFAULTS["tenant"]` entry

## Risk

- **Memory on huge files:** `subtle.digest` needs the whole file in an
  ArrayBuffer. Cap at ~500 MB with a plain-language message for larger
  files ("for very large files, fingerprint on your own device using
  built-in tools" + pointer). Covers essentially all tenant documents.
- **Hash-as-canary concern:** a hash is not PII and cannot be reversed to
  content; a stateless endpoint that doesn't log it keeps it that way.
- **HMAC fallback honesty:** fallback tokens must be labeled as
  Semptify-signed, never silently presented as third-party. `tsa_backed`
  drives the label.
- **UPL risk:** none — documentation tooling with a disclaimer, no legal
  advice. `upl_risk_tier=LOW`.
- **fees_policy:** nothing priced, no fee text.

## Verification plan

- `python -m py_compile` on all new/changed files (venv311, Python 3.11.9)
- `pytest tests/module_health -q --no-cov`
- `python tools/guardrail_engine.py` — all checks pass
- Unit test: stamp endpoint with a known hash → response shape +
  `tsa_backed` boolean present; malformed hash → 422
- Live check (IronBee browser): `/record/fingerprint` → set a fixture file
  via file input → shown SHA-256 equals `certutil -hashfile` of the same
  fixture → stamp → receipt JSON downloads → re-drop file + receipt →
  verify shows match → console clean, screenshot + ARIA snapshot taken
- IronBee backend `request_http` evidence on stamp + verify endpoints
