# Document Process Definitions

This document defines the current Semptify document lifecycle, the responsible service for each stage, and the authoritative truth scope for each artifact.

## 1. Overview

Semptify treats document handling as a series of deterministic stages. Each stage has a clear source of truth and a defined scope of responsibility.

The high-level flow is:
1. Storage authentication and session identity
2. Vault upload
3. Document registration
4. Document processing / analytics
5. Document distribution and integration
6. Event emission and workflow gating
7. Access control and scope enforcement

## 2. Core document processes

### 2.1 Storage authentication and identity

- Responsible files:
  - `app/core/security.py`
  - `app/routers/storage.py`
  - `app/core/user_context.py`

- What it does:
  - Authenticates the user via storage OAuth
  - Validates that the user has a connected cloud storage provider
  - Decodes and reconstructs the active user context
  - Enforces storage-only access for real users (no demo/system accounts)

- Truth scope:
  - The user session and storage connection state are authoritative in the user context
  - `require_user()` is the gatekeeper for any document operation that touches vault or upload flows

### 2.2 Vault upload

- Responsible files:
  - `app/services/vault_upload_service.py`
  - `app/routers/documents.py`
  - `app/routers/vault.py` (currently not mounted in main)

- What it does:
  - Stores document bytes into the user's vault
  - Generates a stable vault identifier (`vault_id`)
  - Creates a safe storage filename
  - Creates a certification record for the stored document
  - Maintains a local index of vault documents for deduplication and lookup

- Truth scope:
  - The vault service is the source of truth for stored document metadata, storage path, and vault identity
  - The file content truth is the bytes stored in the user’s connected storage provider or local fallback
  - The certificate JSON record is the audit truth for the uploaded document

### 2.3 Document registration

- Responsible files:
  - `app/services/document_registry.py`
  - `app/routers/documents.py`

- What it does:
  - Generates a canonical registered document ID using `DocumentIDGenerator`
  - Computes `content_hash`, `metadata_hash`, and an HMAC-based `combined_hash`
  - Detects duplicates and marks copy/original status
  - Records custody metadata, version history, and integrity state
  - Persists the registry to disk

- Truth scope:
  - The registry is the authoritative truth for document identity and tamper-proof metadata
  - `DocumentIDGenerator` defines the document numbering scheme: `SEM-YYYY-NNNNNN-XXXX`

### 2.4 Document processing and analytics

- Responsible files:
  - `app/services/document_pipeline.py`
  - `app/services/document_intake.py`
  - `app/services/document_intelligence.py`
  - `app/services/law_engine.py`
  - `app/routers/documents.py`

- What it does:
  - Ingests and processes the uploaded document
  - Extracts text, metadata, and structured data
  - Classifies document type
  - Runs AI intelligence and urgency scoring
  - Matches documents against applicable tenant/legal laws
  - Marks documents as processed and updates extracted metadata

- Truth scope:
  - The pipeline is the truth for processing state and extracted analytics
  - Document content remains immutable in the vault; processed metadata is separate and derived

### 2.5 Document distribution / module integration

- Responsible files:
  - `app/services/document_distributor.py`
  - `app/services/document_flow_orchestrator.py`
  - `app/services/case_auto_creation.py`

- What it does:
  - Routes a newly processed document to dependent modules (briefcase, form data, court packet, timeline, etc.)
  - Ensures processed documents are visible across feature modules
  - Creates higher-level artifacts like cases, timeline events, and evidence records

- Truth scope:
  - The distributor is the authoritative truth for which modules have received document data
  - Document source remains the vault; module outputs are derived, not authoritative over source content

### 2.6 Event emission and workflow gating

- Responsible files:
  - `app/core/workflow_engine.py`
  - `app/routers/workflow.py`
  - `app/core/positronic_mesh.py`

- What it does:
  - Determines the next allowed user action based on workflow state
  - Enforces serial gating for storage, vault activation, and client activation
  - Exposes deterministic workflow decisions for tenant and professional roles

- Truth scope:
  - The workflow engine is the truth for routing decisions and allowed next actions
  - It is not the source of document content; it is the source of process eligibility

### 2.7 Access control and document scope

- Responsible files:
  - `app/services/vault_engine.py`
  - `app/routers/vault_engine.py`

- What it does:
  - Determines resource scope for documents: OWN, SHARED, CASE, ORG, SYSTEM
  - Grants or denies read/write/delete/admin actions based on role and resource context

- Truth scope:
  - `VaultEngine` is the authoritative truth for document access scope and permissions
  - It is the security boundary for all vault document access operations

## 3. Key artifacts and their authoritative truth

| Artifact | Source of Truth | Stored Where | Notes |
|---|---|---|---|
| `vault_id` | `VaultUploadService` | local vault index + certificate file | Unique vault artifact ID for stored file |
| document registry ID | `DocumentRegistry` | `registry.json` | Canonical system document identity |
| file hash | `DocumentRegistry` / vault upload service | registry and certificate | SHA-256 content fingerprint |
| metadata hash | `DocumentRegistry` | registry | Sorted metadata fingerprint |
| combined hash | `DocumentRegistry` | registry | HMAC-based tamper detection |
| certificate record | `VaultUploadService` | `.semptify/vault/certificates/` | Upload certification proof |
| workflow decision | `WorkflowEngine` | runtime evaluation | route/action gating |
| access scope | `VaultEngine` | runtime | OWN / SHARED / CASE / ORG / SYSTEM |

## 4. Endpoint truth surfaces

- `POST /api/documents/upload` — active document upload entry point
- `POST /api/documents/upload/simple` — legacy upload fallback
- `GET /api/workflow/route` — deterministic next-process routing
- `POST /api/vault-engine/check-access` — access control lookup
- `POST /api/vault-engine/read` / `write` / `delete` — secure resource operations

## 5. Encryption and OAuth truth

- Access tokens are encrypted with AES-GCM using a key derived from:
  - `SECRET_KEY` + `user_id`
  - Implemented in `app/routers/storage.py`
- Token encryption is the truth for storage session recovery and auth integrity
- A corrupted session record is rejected and forces re-authentication

## 6. Gaps and important constraints

- `DocumentIDGenerator` uses an in-memory yearly counter. If running multiple processes, this is a weak point for global uniqueness.
- `DocumentRegistry` currently uses a hard-coded `_SECRET_KEY` for HMAC integrity; production should source it from config.
- The dedicated `/api/vault` router exists in code but is not mounted in `app/main.py`.
- `POST /api/documents/upload` is the truth path for document intake today.

## 7. How this should behave under every scenario

1. User authenticates successfully with storage OAuth
2. `require_user()` validates storage identity and session integrity
3. Document upload is accepted only if file and extension are valid
4. Vault service stores the file and issues a vault ID
5. Registry service issues a canonical document ID and integrity hashes
6. Certificate artifacts are written and traceable
7. Processing is queued or executed, with extracted metadata appended
8. Access rules are applied on every subsequent read/write/delete
9. Any tampering or integrity mismatch is detectable via hashes
10. Any session or token corruption triggers re-authentication

## 8. Recommendation for full truth enforcement

- Make `DocumentRegistry._SECRET_KEY` configurable from `Settings`
- Persist `DocumentIDGenerator` state in durable storage if running multiple workers
- Mount `app/routers/vault.py` only if expected endpoints are used
- Add explicit tests for:
  - `POST /api/documents/upload` happy path
  - `DocumentIDGenerator.is_valid()` format
  - registry integrity verification
  - storage token decryption and invalid token rejection
  - workflow gating for upload/vault activation

---

### Implementation note

This document is intended to be the single source of truth for Semptify document lifecycle design and the truth scope of each stage.
