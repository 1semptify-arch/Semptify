# TODO: Document Upload, Vault, and Integrity Work

This task list captures the next concrete actions to complete document upload, registration, vault storage, integrity, and access control.

## Priority 1 — Fix production safety

1. Move registry HMAC secret into config
   - Update `app/services/document_registry.py` so `_SECRET_KEY` is loaded from settings instead of hard-coding.  ✅ done
   - Add a production validation in `app/core/config.py` / `app/core/security_config.py` to require `SECRET_KEY`.  ✅ done in `app/core/config.py`
   - Ensure tests cover missing/invalid `SECRET_KEY`.  ✅ done in `tests/test_document_registry.py`

2. Confirm canonical upload endpoint
   - ✅ Verified `POST /api/documents/upload` is the active upload path (unified endpoint with complete processing)
   - ✅ Removed redundant `app/routers/vault.py` router from `app/main.py` 
   - ✅ Documented `/api/documents/upload` as the canonical path (provides vault storage + full AI processing)

## Priority 2 — Strengthen ID and integrity coverage

3. Add `DocumentIDGenerator` tests
   - ✅ Test format validity for `SEM-YYYY-NNNNNN-XXXX`.
   - ✅ Test `.parse()` and `.is_valid()` behavior.
   - ✅ Add coverage around year reset behavior.

4. Add registry integrity tests
   - ✅ Test `content_hash`, `metadata_hash`, and `combined_hash` generation.
   - ✅ Test `HashGenerator.verify_integrity()` and registry verify logic.
   - ✅ Test duplicate detection and original/copy status.

5. Add upload/vault regression tests
   - ✅ Test `POST /api/documents/upload` happy path with a sample file.
   - ✅ Test vault deduplication by SHA-256.
   - ✅ Test certificate record creation and returned vault metadata.

## Priority 3 — Validate OAuth and storage auth

6. Add token encryption tests
   - ✅ Test `_encrypt_token()` and `_decrypt_token()` in `app/routers/storage.py`.
   - ✅ Test session recovery behavior when token decryption fails.
   - ✅ Test `require_user()` rejection for invalid storage sessions.

7. Confirm front-end upload integration
   - ✅ Verified briefcase.html uses /api/briefcase/document endpoint which calls vault_upload_service.upload() (same as /api/documents/upload)
   - ✅ Updated briefcase router to auto-detect user_id from X-User-ID header, derive storage_provider from user_id prefix, and retrieve access_token from session
   - ✅ Verified error handling for invalid tokens, large files, and disallowed extensions is handled by vault service

## Priority 4 — Access scope and vault security

8. Review `VaultEngine` resource scopes
   - ✅ Audited `app/services/vault_engine.py` for OWN/SHARED/CASE/ORG/SYSTEM permissions - access matrix correctly implemented with role-based permissions
   - ✅ Added comprehensive tests for role-based access decisions covering all roles (user, advocate, legal, manager, admin) and all scopes (OWN/SHARED/CASE/ORG/SYSTEM)

9. Audit document process docs
   - ✅ Reviewed `docs/DOCUMENT_PROCESS_DEFINITIONS.md` and `docs/ID_REFERENCE.md` - both are well-aligned with current code implementation
   - ✅ Document process definitions correctly describe vault upload service and document lifecycle stages
   - ✅ ID reference accurately defines all identifier formats (document_id, vault_id, certificate_id, etc.) and their purposes
   - ✅ No updates needed after upload path decisions - briefcase router uses same vault service as documents router

## Optional improvement

10. Consider global document ID generation
    - If the app will run multiple workers, replace the in-memory sequential counter in `DocumentIDGenerator` with a durable or globally unique scheme.

---

### Suggested first implementation

- Start with task 1: move `DocumentRegistry` secret into config.
- Then add a small test for `DocumentIDGenerator` format validation.
