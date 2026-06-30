# Semptify ID Reference

This reference defines the key identifiers used by Semptify document and vault processes, including exact formats and how each ID is used.

## Document IDs

| Name | Format | Example | Source | Purpose |
|---|---|---|---|---|
| `document_id` | `SEM-YYYY-NNNNNN-XXXX` | `SEM-2026-000123-9A1B` | `app/services/document_registry.py` | Canonical registered document identity used by the registry, analysis, and case linkage |
| `vault_id` | UUID | `3fa85f64-5717-4562-b3fc-2c963f66afa6` | `app/services/vault_upload_service.py` | Primary identifier for the stored vault file and vault metadata |
| `certificate_id` | `cert_{YYYYMMDD_HHMMSS}_{vault_id_prefix}` | `cert_20260413_132501_ab12cd34` | `app/services/vault_upload_service.py` / `app/routers/vault.py` | Identifier for the upload certification record and audit artifact |
| `safe_filename` | `{vault_id}.{ext}` | `3fa85f64-5717-4562-b3fc-2c963f66afa6.pdf` | `app/services/vault_upload_service.py` | Filename used inside vault storage to avoid collisions and preserve extension |

## Hashes and integrity values

| Name | Format | Source | Purpose |
|---|---|---|---|
| `sha256_hash` | 64-character hex | `app/services/vault_upload_service.py` / `app/services/document_registry.py` | File content fingerprint used for deduplication and integrity |
| `content_hash` | 64-character hex | `app/services/document_registry.py` | SHA-256 of raw document bytes, used in registry integrity checks |
| `metadata_hash` | 64-character hex | `app/services/document_registry.py` | SHA-256 of sorted registration metadata, used in combined integrity check |
| `combined_hash` | 64-character hex | `app/services/document_registry.py` | HMAC-SHA256 over `doc_id:content_hash:metadata_hash`, used to detect tampering |

## OAuth and session identifiers

| Name | Format | Source | Purpose |
|---|---|---|---|
| `access_token` | provider-specific token | OAuth provider / `app/routers/storage.py` | Cloud storage access token for vault upload and download |
| `semptify_uid` | user ID string with provider/role prefix | Cookie/session | Identifies the authenticated user and their storage provider |
| function token | short-lived access token | `app/core/security.py` | Enables secure overlay or function-scoped operations without reusing OAuth tokens |

## Additional notes

- `document_id` is the user-visible registry ID and is the key identifier for document-level truth.
- `vault_id` is the vault storage identifier and is the key identifier for stored file artifacts.
- `certificate_id` ties the uploaded document to its certification record.
- `sha256_hash` is used in both vault and registry flows to verify that uploaded content has not changed.
- The secret used for document registry HMAC should be configured securely in production rather than hard-coded.

## Usage summary

- Use `document_id` when referring to the registered record inside Semptify.
- Use `vault_id` when referring to the actual stored file in the vault.
- Use `certificate_id` when referring to the proof/certification artifact.
- Use `safe_filename` when addressing storage paths in the vault.
- Use `access_token` only for cloud storage operations and never expose it in logs or UI.
