---
description: Professional roles revived (Brad, 2026-11-19) — legal/advocate/admin live alongside tenant.
---

# Roles and Identity — REVIVED (2026-11-19, supersedes the 2026-09-23 tenant-only note)

**Brad decided 2026-11-19 (task-b02e2f89): professional roles return in this
repo. `parse_user_id` decodes the real role letter; `/storage/connect?role=`
can mint `advocate`/`legal`; `admin` is NOT OAuth-mintable (server-minted
only). Onboarding stays tenant-only (`onboarding/oauth.py ALLOWED_ROLES`,
NO-TOUCH module) — pro accounts arrive via the storage connect path or admin
minting, not the public onboarding flow. Tenant-granted sharing
(ADVOCACY/CASE_SHARE) still governs what a professional sees of a tenant's
data — a role grants access to pro surfaces, never to tenant data directly.**

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
