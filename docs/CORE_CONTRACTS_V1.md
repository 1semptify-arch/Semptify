# Core Contracts v1 (Sprint 1)

This document defines non-negotiable contract and invariant rules for Semptify core modules.

## Scope

The v1 core contract applies to:

- `Documents` upload and processing adapters
- `Intake` upload and registration flow
- `Vault` immutable artifact storage
- `Document Overlays` mutable annotation/extraction layers
- `Workflow` deterministic routing and gating
- `Timeline` document-linked event modeling
- `Legal Filing` evidence intake and adapter resolution

## Identity Contract

Every core document flow MUST maintain explicit identity boundaries:

- `vault_id` identifies immutable vault artifact ownership and provenance.
- `overlay_record_ids[]` identifies mutable adapter records linked to a vault artifact.
- `document_id` in timeline/legal contexts may reference legacy document IDs, but when overlay IDs are supplied, resolution MUST prefer overlay-linked `vault_id`.

A payload is invalid if it returns conflicting identity references for the same artifact in one response.

## Vault Immutability Contract

Vault metadata fields listed below are immutable after creation and MUST NOT be mutated:

- `vault_id`
- `user_id`
- `filename`
- `safe_filename`
- `sha256_hash`
- `file_size`
- `mime_type`
- `storage_path`
- `storage_provider`
- `certificate_id`
- `uploaded_at`

Any mutation attempt MUST fail fast with a validation error.

## Overlay Adapter Contract

Overlay records provide mutable behavior without mutating vault originals.

- Upload MUST emit `vault_upload_manifest` overlay for traceability.
- Extraction/classification updates MUST emit corresponding overlay records.
- Downstream modules MUST resolve overlay context before fallback to legacy fields.
- Applying overlay context MUST preserve vault artifact immutability.

## Workflow Determinism Contract

Routing decisions are deterministic and must not be AI-dependent.

- `overlay_record_ids` presence MUST imply `documents_present=True` semantics for routing.
- Invalid role or storage-state inputs MUST produce `422` validation errors.
- Workflow advance from welcome MUST remain gate-based and reject missing prerequisites.

## Multi-Tenant Isolation Contract

Core operations must preserve tenant boundaries:

- Vault document queries MUST be scoped by requesting `user_id`.
- User-scoped timeline queries MUST never leak other users' manual events.
- Role-sensitive write APIs MUST reject insufficient privileges.

## Sprint 1 Mandatory Gate Suites

The following suites are required in CI:

- End-to-end filing gate:
  - upload -> vault -> overlay emission -> workflow route -> legal evidence adapter
- Tenant isolation gate:
  - user-scoped vault access and overlay write-role enforcement checks
- Workflow state integrity gate:
  - deterministic validation for blocked/invalid/advanced state transitions

## Enforcement

The executable enforcement for Sprint 1 is `tests/test_core_completion_gates.py` and must run as a mandatory CI check.
