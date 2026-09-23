---
description: SUPERSEDED — tenant-only identity (PR #317). Kept as add-on-repo reference.
---

# Roles and Identity — SUPERSEDED (2026-09-23)

**This repo is stateless tenant-only (PR #317). There are no pro roles, no
role gates, and no elevation paths — every identity is a tenant and access
beyond the tenant's own surface comes only from tenant-granted sharing.
The definitions below are preserved for the separate pro-role add-on repo
(networked later) — do not implement, reference, or gate on them here.**

## Legal sub-roles

Judge is merged into Legal as a sub-role. Legal sub-roles are stored in the `legal_sub_role` field on the User model:

- `attorney` — full legal tools, court filing, privileged work product.
- `judge` — case review, oversight, judicial orders.
- `clerk` — filings processing, calendar, document review.
- `paralegal` — legal support, research, drafting, document organization.

All legal sub-roles require a `bar_license_number`. This is a public professional credential, not PII.

### Permissions

- Legal role has **read-only tenant vault access**. Do not grant `vault_write`.
- Legal can create legal overlays via `overlay_create_legal`.
- Legal can share forms via `forms_share`.
- `UserRole.JUDGE` enum is deprecated but kept for backward compatibility. Prefer `is_legal_sub_role(user_id, 'judge')`.

## Manager correction

- **Manager is a TENANT-RIGHTS ADVOCATE, not a property manager.**
- A worker with a multi-client caseload on the tenant side.
