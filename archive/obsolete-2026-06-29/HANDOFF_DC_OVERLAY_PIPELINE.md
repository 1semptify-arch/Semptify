# HANDOFF — Document Center Overlay Pipeline Compliance Review

**Prepared:** 2026-06-29  
**Status:** DO NOT CODE — review and plan first  
**Mandate:** Stateless. No user data on our servers. User cloud is the SSOT.

---

## The Core Violation

**Semptify's architectural rule** (`app/services/unified_overlay_manager.py:13-26`):
> "All overlays are stored in the USER's cloud storage — never on our servers."  
> "A document that has no overlay does not exist to Semptify processes."

**The user's directive (2026-06-29):**
> "No quick fixes. No band-aids. If it's done, we do it right."  
> "Fallback should not go to DB. Return 'process failed' or 'try again'."  
> "We store no user data on our system."

---

## What's Broken (4 violations)

### 1. DB Fallback in DC Right Panel
**File:** `app/modules/document_center/router.py`  
**What it does:** When no real overlays exist in cloud, `_build_overlay_progress()` falls back to `_synthesize_overlays()` which reads `doc.extracted_data` from our PostgreSQL.  
**Why it's wrong:** Serves user data from our DB. Violates "no overlay = doesn't exist."  
**What it should do:** Return `{"status": "processing_incomplete", "message": "Vaulted — awaiting processing."}`. Frontend shows "try again" state. No DB read, ever.

### 2. ✅ WIRED 2026-06-29 — Intake Now Creates Real Overlays
**What was fixed:**
- `mark_processed()` in `vault_upload_service.py` now only writes `processed=True` to DB (no `extracted_data` DB write)
- Added `parties` and `timeline_events` params to `mark_processed()`
- Creates `DOCUMENT_EXTRACTION` overlay (summary, dates, amounts), `PARTY_EXTRACTION` overlay (parties list), `TIMELINE_EXTRACTION` overlay (events from flow_result) — all in user cloud
- Intake router now passes full extraction payload (not the near-empty stub it used to)

**Remaining for GLM5.2:** The `VaultIndexDB.extracted_data_json` DB column still exists (no data written to it anymore, but column remains). Needs DB migration to drop column + remove from model.

### 3. `DocumentRegistryEntry` + `CertificationEvent` Tables Duplicate Cloud Data
**File:** `app/models/models.py` + `app/services/vault_upload_service.py`  
**What they do:** Store certification data (sha256, status, integrity, forgery_score, audit events) in our PostgreSQL — duplicating what's already in the certificate JSON in the user's cloud.  
**Why it's wrong:** Certificate JSON in `Vault/certificates/` is the SSOT. DB copy is redundant user data on our servers.  
**What should remain:** A minimal `vault_hash_index` table with ONLY `(sha256_hash, vault_id, user_id)` for fast dedup lookup. Everything else belongs in the certificate JSON in cloud.

### 4. DC List Shows Fabricated Overlay Count
**File:** `app/modules/document_center/router.py` — `dc_list_documents()`  
**What it does:** Computes `overlay_count` from DB flags (`processed`, `document_type`, `registry_id`) — it's a guess, not a real count.  
**Why it's wrong:** Fabricated from DB state. Not reality.  
**What it should do:** Remove `overlay_count` from the list endpoint entirely, or return `null`. Authoritative count only available when user opens a document and `dc_overlays` reads real overlays from cloud.

---

## Target Architecture (Lean + Compliant)

```
UPLOAD
  1. File → user cloud (Vault/documents/{uuid}.ext)
  2. Certificate JSON → user cloud (Vault/certificates/{cert_id}.json)
  3. DB index row → VaultIndexDB (lookup fields ONLY — see below)
  4. Hash index → vault_hash_index (sha256, vault_id, user_id — dedup only)

  ─── VAULTED GATE (registry_id issued, cert in cloud) ───

PROCESSING (after vault gate passes)
  5. OCR + classify + extract → transient, in memory only
  6. Create overlays → user cloud (Vault/overlays/)
     - VAULT_UPLOAD_MANIFEST
     - DOCUMENT_CLASSIFICATION
     - DOCUMENT_EXTRACTION  (dates, amounts, OCR text)
     - PARTY_EXTRACTION     (landlord, tenant, attorney)
     - TIMELINE_EXTRACTION  (events)

DC READS
  7. dc_get_overlays → reads overlays from user cloud ONLY
     No overlays exist? → return processing_incomplete
     No DB fallback. Ever.
```

**Our PostgreSQL after cleanup — VaultIndexDB stores ONLY:**
- `vault_id` (PK)
- `user_id`
- `storage_path`
- `storage_provider`
- `provider_file_id`
- `registry_id`
- `uploaded_at`
- `filename`
- `mime_type`
- `sha256_hash`

**Removed from VaultIndexDB:** `extracted_data_json`, `processed`, `document_type`, `description`, `tags`, `source_module`, `safe_filename` (safe_filename should be derivable from storage_path, not stored separately).

**Removed DB tables:** `DocumentRegistryEntry`, `CertificationEvent` — replaced by certificate JSON in user cloud.

---

## Files That Need Changing

| File | Change |
|------|--------|
| `app/modules/document_center/router.py` | Remove `_synthesize_overlays()` fallback, return `processing_incomplete` when no real overlays, remove fabricated overlay count from list |
| `app/modules/intake/router.py` | After vault gate passes, call `UnifiedOverlayManager.create_overlay()` instead of `mark_processed(extracted_data=...)` |
| `app/services/vault_upload_service.py` | Remove `DocumentRegistryEntry` DB write, remove `CertificationEvent` writes, simplify `mark_processed()` to not accept extracted_data |
| `app/models/models.py` | Remove `extracted_data_json`, `processed`, `document_type` from `VaultIndexDB`; remove `DocumentRegistryEntry` and `CertificationEvent` models |
| `app/templates/pages/documents.html` | Handle `processing_incomplete` status in right panel JS; remove overlay count badge from left panel |
| `app/modules/document_center/register.py` | Update contracts to reflect no fallback, `processing_incomplete` response |
| DB migration | Drop columns + tables |

---

## What's Already Correct (Do Not Touch)

- `vault_upload_service.upload()` — vault-first gate is solid
- `UnifiedOverlayManager` — correctly writes overlays to user cloud
- `_fetch_real_overlays()` + `_build_progress_from_real()` — correctly reads real overlays
- `dc_view` endpoint — correctly streams file from user cloud
- Immutability — no write path to original files
- Token fallback chain in intake router — keep as-is

---

## Session Note

The DB fallback in `_build_overlay_progress()` and `_synthesize_overlays()` was shipped 2026-06-28 as an interim measure. The user has rejected it. It must be removed cleanly, not patched. Fix the root (intake doesn't create overlays) and remove the symptom-masking fallback together in one pass.

Do not split this into two PRs. Do not remove the fallback without wiring overlay creation first — that would leave the DC showing nothing. Wire overlay creation in intake → verify overlays appear in DC → then remove fallback as one atomic change.
