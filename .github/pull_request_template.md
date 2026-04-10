## Description

<!-- Briefly describe what this PR changes and why. -->

## Related Issues

<!-- Link any relevant issues: Fixes #123, Closes #456 -->

---

## Sprint 1 Core Gate Checklist

All items below are **mandatory** before merge. The CI pipeline enforces these automatically, but reviewers must also confirm them manually.

### Gate 1 — End-to-End Filing Path

- [ ] Upload → Vault → Overlay emission → Workflow route → Legal evidence adapter chain is intact
- [ ] Every upload response includes a non-null `vault_id`
- [ ] Every upload response includes a non-empty `overlay_record_ids[]`
- [ ] Legal evidence resolves `vault_id` and `extracted_data` from overlay context
- [ ] No step in the chain depends on the old `document_id`-only identity path without an overlay fallback

### Gate 2 — Tenant Isolation

- [ ] Vault index queries are scoped to the requesting `user_id` — no cross-tenant leakage
- [ ] User role (`GU...` / `DU...` / `OU...`) receives HTTP 403 on overlay write endpoints
- [ ] Advocate, Manager, Legal, and Admin roles can write overlay records
- [ ] No new query, endpoint, or service method returns documents without a `user_id` scope filter

### Gate 3 — Workflow State Integrity

- [ ] Advancing from `welcome` with no `completed_actions` returns `status: blocked` with all 3 required actions listed
- [ ] Invalid role strings (e.g. `"not-a-real-role"`) return HTTP 422
- [ ] Invalid page strings (e.g. `"tenant_help"`) return HTTP 422
- [ ] `overlay_record_ids` presence is treated as `documents_present=True` in both `RouteRequest` and `AdvanceRequest`

---

## Vault Immutability Checklist

- [ ] None of the 11 immutable `VaultDocumentIndex` fields are written after initial upload:
  `vault_id`, `user_id`, `filename`, `safe_filename`, `sha256_hash`, `file_size`, `mime_type`, `storage_path`, `storage_provider`, `certificate_id`, `uploaded_at`
- [ ] Any code path that calls `VaultUploadService.update()` does not pass any of the above fields
- [ ] The `update()` method's `ValueError` guard is not bypassed or caught silently

---

## Overlay Adapter Checklist

- [ ] New upload flows call `_create_overlay_record()` (or equivalent) and do not swallow the result silently
- [ ] Overlay writes do not modify the source vault record
- [ ] Downstream resolvers (legal filing, timeline) call `_resolve_overlay_context()` before falling back to legacy fields

---

## Test Coverage

- [ ] `pytest tests/test_core_completion_gates.py -q` runs **6/6 PASS** locally
- [ ] `pytest tests/test_security_isolation_gates.py -q` runs **7/7 PASS** locally
- [ ] `pytest tests/test_action_router_gates.py -q` runs **8/8 PASS** locally
- [ ] No new logic in `vault_upload_service`, `document_overlay_service`, `workflow`, or `legal_filing` is untested
- [ ] No new test fixtures use direct protected attribute assignment (`obj._attr = ...`); use `setattr()` instead
- [ ] No test-generated artifacts are committed (`data/legal_filings/case_*.json`, `data/legal_filings/evidence/`)

---

## Security / Multi-Tenancy

- [ ] No new endpoint bypasses `get_current_user()` dependency
- [ ] No new endpoint performs a data query without a `user_id` / tenant scope parameter
- [ ] No secrets, tokens, or PII are logged or returned in error responses

---

## Reviewer Sign-off

| Area | Reviewer | Status |
|------|----------|--------|
| Core gates CI pass | | ⬜ |
| Vault immutability | | ⬜ |
| Overlay contract | | ⬜ |
| Tenant isolation | | ⬜ |
| Test coverage | | ⬜ |
