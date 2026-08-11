---
description: Role definitions, legal sub-roles, and manager correction
---

# Roles and Identity

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
