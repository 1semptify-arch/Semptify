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
   - Verify the UI uses `/api/documents/upload` and passes `access_token` + `storage_provider`.
   - Verify error handling for invalid tokens, large files, and disallowed extensions.

## Priority 4 — Access scope and vault security

8. Review `VaultEngine` resource scopes
   - Audit `app/services/vault_engine.py` for OWN / SHARED / CASE / ORG / SYSTEM permissions.
   - Add tests for role-based access decisions on vault resources.

9. Audit document process docs
   - Review `docs/DOCUMENT_PROCESS_DEFINITIONS.md` and `docs/ID_REFERENCE.md` for alignment with code.
   - Update any gaps after the upload path decision.

## Optional improvement

10. Consider global document ID generation
    - If the app will run multiple workers, replace the in-memory sequential counter in `DocumentIDGenerator` with a durable or globally unique scheme.

---

### Suggested first implementation

- Start with task 1: move `DocumentRegistry` secret into config.
- Then add a small test for `DocumentIDGenerator` format validation.
