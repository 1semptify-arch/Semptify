---
description: How to use the canonical Vault SDK
---

# Vault SDK

Use `app.sdk.vault` for all vault operations.

```python
from app.sdk.vault import VaultClient, TENANT_VAULT
```

## Design

- Zero dependencies on FastAPI, SQLAlchemy, middleware, or navigation.
- All paths come from `app.core.vault_paths` (SSOT).
- `VaultClient(provider, access_token, user_id, folder_spec)` takes the token directly; no lookup.
- Methods: `create_folders()`, `health_check()`, `repair()`.
- Pre-built specs: `TENANT_VAULT`, `ADVOCATE_VAULT`, `LEGAL_VAULT`, `RESEARCH_VAULT`.
- Gate marking is the caller's responsibility — the SDK never touches gates or the DB.

## Pre-built specs

- `TENANT_VAULT` — base folders (documents, certificates).
- `ADVOCATE_VAULT` — adds client_files, case_notes, legal_filings.
- `LEGAL_VAULT` — adds court_exhibits, case_files, discovery.
- `RESEARCH_VAULT` — adds research, dossiers.

## Storage tiers

- **USER** — Google Drive / Dropbox / OneDrive (user owns).
- **SYSTEM** — Cloudflare R2 (system indexes).
- **LOCAL** — Server memory / token cache (ephemeral).
