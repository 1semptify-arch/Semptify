# Export My Record Blueprint

**Status:** DRAFT — pending approval
**Module path:** `app.modules.record_export.router` (new) superseding the
record half of `app.modules.export_import`
**Type:** Feature
**Pillar:** RECORD
**Tier:** EXTENDED
**Lifecycle:** experimental → stable once verified
**Date:** 2026-11-05
**Toolbox entry:** `document_vault` "download your record" path — and the
cross-cutting "export my record" promise of the zero-persistence model.

## Problem

Post-migration the tenant's record lives in their own cloud:
`Semptify5.0/.semptify/vault.db` (live record tables) + `Semptify5.0/Vault/`
document binaries + export/provenance overlay JSONs. But there is no way
for a tenant to *take their record with them* in one step.

The existing `DataExportImportManager` (`app/core/data_export_import.py`)
reads **server-side SQLAlchemy tables** — which post-Phase-1 migration are
empty or legacy for record data — writes exports to server disk, tracks
them in process memory, and offers seven-day retention. As a
"record export" it is now the wrong data source, the wrong privacy model,
and the wrong retention story.

## Scope

Does:

- Define the export surface as **vault truth, not server tables**. One
  `RecordExportService` that, given a connected-storage session, produces
  a portable archive assembled entirely in memory/temp (already the
  `read_remote` pattern in `app/sdk/vault/db.py` — pull, read, discard).
- Export contents:
  - `record.db` — verbatim copy of vault.db (the full machine-readable
    record; SQLite is portable and openable by free tools).
  - `record/` — human-readable JSON per domain dumped from vault.db:
    `journal.json`, `timeline.json`, `calendar.json`, `contacts.json`,
    `ledger.json` (incl. `hash_prev`/`hash_self` chain fields),
    `documents.json` (index rows incl. `storage_ref`), `interactions.json`,
    `dispute_packets.json`, `overlays.json` (annotations/provenance).
  - `manifest.json` — generated_at, schema_version, per-domain row counts,
    sha256 of `record.db`, Semptify build/version stamp.
  - `documents/` — optional flag (`include_documents`) pulling each binary
    via `storage_ref`. Default **off** for a fast metadata+record export;
    on for a full take-it-with-you archive. Bounded total size.
  - `certificates/` — verification certificates + RFC 3161 tokens already
    stored per uploaded document, where present.
- Two delivery shapes, tenant's choice on one page (`/record/export`):
  1. **Download** — stream the zip to the browser. Nothing is written to
     Semptify's disk or database; temp files live only inside the
     `read_remote`/request scope and are deleted in `finally`.
  2. **Refresh my archive** — write the same bundle to
     `Vault/exports/<YYYYMMDD-HHMMSS>/` inside the tenant's own storage.
- Page copy states plainly: the record already lives in the tenant's
  storage; the export is a portable copy for backup, moving, or sharing —
  plus the "what you can do today" path (open your storage →
  `Semptify5.0/.semptify/vault.db`).
- Explicit exclusion, stated on the page: identity/session/security
  metadata (`sessions`, `oauth_states`, encrypted tokens, R2 credentials,
  `user_capabilities`, `user_relationships`) is connection machinery, not
  the tenant's record — it is never included. No secrets ever leave in an
  export.
- Error contract: provider unreachable → plain-language message + "try
  again / reconnect storage" path; empty vault → still produces a valid
  manifest (zero counts), never a silent 404; partial document-pull
  failure → archive still delivers with a `warnings[]` list in
  `manifest.json`, never a corrupt zip presented as success.
- Register per the three-step rule: `_register(...)` in
  `product_manifest.py` (EXTENDED tier, `requires_gate="vault_initialized"`),
  `CAPABILITY_DEFAULTS["tenant"]` entry.

Does NOT:

- Read or include server-side `users`/`sessions`/`documents` SQLAlchemy
  tables as record sources — those are infrastructure/legacy index
  (Phase 2/3 decision items, see `handoffs/vault-phase3-identity-audit.md`).
- Write exports to server disk, keep an export-history table, or retain
  anything after the response closes. No seven-day server retention —
  retention is the tenant's storage or their own device.
- Offer "import" in this blueprint — the legacy `export_import` import
  path stays untouched; a vault-native import/restore is a separate
  blueprint (needs its own conflict/merge design).
- Touch `app/modules/onboarding/` (NO-TOUCH) or
  `app/core/data_export_import.py` — supersession note only; the old
  module is marked for retirement after the Phase 2 index decision
  removes the server tables it reads.
- Re-implement vault pull logic — uses `read_remote()` +
  `oauth_token_manager.get_valid_token_for_user()` +
  `services.storage.get_provider()` + `user_id.get_provider_from_user_id()`
  (the canonical provider-resolution pattern).

## Roles & capability defaults

Tenant only, gated by `vault_initialized` — export requires a connected
vault by definition. `CAPABILITY_DEFAULTS["tenant"]` gains the module.

## DB tables

None. Zero persistence holds end-to-end: source bytes come from the
tenant's storage, the archive is assembled in memory/temp, temp paths are
deleted in `finally`, nothing is logged beyond the standard request line.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /record/export | Export page — delivery choice + options (shell) |
| GET | /api/record-export/health | Module health check |
| POST | /api/record-export/download | Stream zip. Body: `{include_documents, format: "full"|"json-only"}` |
| POST | /api/record-export/to-vault | Write bundle to `Vault/exports/<ts>/` → returns path |

## Dependencies

- `app.sdk.vault.db.read_remote` — pull + read + discard vault.db.
- Canonical provider-resolution triple (oauth_token_manager /
  services.storage.get_provider / get_provider_from_user_id).
- `app.core.vault_paths` — `VAULT_DB_FILE`, `SYSTEM_FOLDER`, export dir
  naming convention.
- `zipfile` / `json` / `hashlib` / `tempfile` stdlib only — no new deps.

## Files

- `app/modules/record_export/` — `__init__.py`, `router.py`,
  `service.py` (`RecordExportService` — gather, dump JSON, zip,
  vault-write), `module_contract.json`, `README.md`
- `app/templates/pages/record_export.html` — export page (chronological:
  review what's included → choose shape → act)
- `app/core/product_manifest.py`, `app/core/capabilities.py` — registration
- `tests/` — service tests against a local vault.db fixture (temp SQLite
  built by `open_local` + migrations)

## Risk

- **Archive size:** document inclusion is opt-in + bounded; metadata-only
  export is small. Zip streams — no full-buffer hold.
- **Provider-call cost:** export is one vault.db pull (+ N document pulls
  when opted in) — per `manifest-reconcile`'s watch item, log the call
  count once so hot-path regressions stay visible.
- **PII boundary:** all content already belongs to the tenant and travels
  between their storage and their browser over TLS; the server is a
  conduit, never a store.
- **UPL risk:** none — it's the tenant's own data. `upl_risk_tier=LOW`.
- **fees_policy:** nothing priced.

## Verification plan

- `python -m py_compile` on all new files (venv311, Python 3.11.9)
- `pytest tests/module_health -q --no-cov`
- `python tools/guardrail_engine.py` — all checks pass
- Unit tests: fixture vault.db → export zip contains `record.db` +
  `manifest.json` with matching sha256 + per-domain JSON; empty vault →
  valid manifest with zero counts; `include_documents=false` → no
  `documents/` dir.
- Live check (IronBee backend): `request_http` on
  `/api/record-export/download` with a test session → 200 + zip
  content-type; log evidence that no export file remains server-side.
  Full provider E2E (real OAuth session) noted as a manual-verify gap —
  same limitation as `live-reads-retarget-sqlite`.
