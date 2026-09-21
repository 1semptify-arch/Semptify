# Info Donation Blueprint

**Status:** APPROVED — approved 2026-09-19 (Brad's recorded decisions in
`handoffs/info-donation-possibilities-2026-09-19.md`; build dispatched
2026-09-21 as `info-donation-system`)
**Module path:** `app.modules.info_donation.router`
**Type:** Feature
**Pillar:** RECORD
**Tier:** CORE
**Date:** 2026-09-21

## Problem

After a tenant's housing situation resolves, what they learned — how it
ended, how long it took, what actually helped, which public resources
answered — is exactly what would help the next tenant in the same position.
Today that knowledge leaves with them. This module lets a tenant voluntarily
donate anonymized answers so the next person gets a better path. Serves the
"Be Heard" core function: putting experience on the record so it helps
someone else.

## Scope

Does:

- Gate all donation on resolution — the tenant marks their situation
  resolved (`POST /api/info-donation/resolved`) or any module publishes
  `EventType.ISSUE_RESOLVED`. No donation surface exists before that event.
- Informed consent, versioned (`CONSENT_VERSION`), recorded before any item
  is accepted. Consent covers the server-side aggregate only — the
  zero-persistence promise still applies to documents.
- Per-item opt-in from a fixed catalog (`catalog.py`) — each item is a
  separate yes, nothing bundled, nothing defaulted on.
- Review-before-submit: the page shows the tenant exactly what will be
  stored before it is sent.
- Revocation: withdraw one item or withdraw everything (hard-deletes the
  tenant's donation rows and revokes consent).
- Free-text items land in `moderation=pending` and are never served to
  anyone until a reviewer (Brad + beta users) approves them. Text is
  screened for email/phone/SSN/street-address patterns before it is stored.
- Admin-only review endpoints: list pending, approve, reject.
- Permanent dismiss: one control ends all donation asks for that tenant.

Does NOT:

- Does not touch vault contents — donated items are the tenant's answers to
  fixed questions, never document data.
- No PII, no addresses, no landlord names, no case numbers (screened).
- No prompting during an active situation — the resolved event is the only
  trigger. No urgency, no guilt framing, no repeat nags after dismiss.
- No public display of individual donations — aggregate only.
- No wiring of existing resolution paths (dispute status, tenancy-hub case
  close) in this pass — they can publish `ISSUE_RESOLVED` later; the
  subscriber is already live.

## Roles & capability defaults

- `tenant` — CAPABILITY_DEFAULTS entry (`app.modules.info_donation.router`).
- Admin gets it automatically (`__all__`); moderation endpoints additionally
  require the admin role.

## DB tables

Postgres/SQLite via `app.core.database.Base` — consented aggregate data is
server-side by explicit decision (Brad, 2026-09-19 dispatch note:
"zero-persistence promise applies to documents, not to this consented
aggregate"). Rows are keyed to `user_id` only so revocation works; nothing
individual is ever shown publicly.

- `info_donation_profiles` — user_id (PK), resolved_at, resolved_source,
  prompt_dismissed_at, consent_version, consented_at, consent_revoked_at,
  created_at, updated_at.
- `info_donation_items` — id (PK `idi_*`), user_id, item_key, value_json,
  moderation (none|pending|approved|rejected), moderated_by, moderated_at,
  created_at, updated_at. Unique (user_id, item_key) — re-answering
  replaces.

Alembic migration `20260921_add_info_donation_tables` (idempotent create;
`init_db` also auto-creates via `Base.metadata.create_all`).

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /api/info-donation/health | Health check |
| GET | /api/info-donation/status | Resolved/consent/dismiss/item state for this user |
| POST | /api/info-donation/resolved | Tenant marks situation resolved (publishes ISSUE_RESOLVED) |
| POST | /api/info-donation/dismiss | Permanently dismiss the donation ask |
| POST | /api/info-donation/consent | Record informed consent (version-checked) |
| POST | /api/info-donation/donate | Submit selected items (validated, PII-screened) |
| GET | /api/info-donation/mine | List the tenant's own donations |
| DELETE | /api/info-donation/mine/{item_id} | Withdraw one item |
| POST | /api/info-donation/withdraw-all | Revoke consent + delete all items |
| GET | /api/info-donation/review/pending | Admin: list pending free-text donations |
| POST | /api/info-donation/review/{item_id} | Admin: approve or reject a pending item |
| GET | /help-the-next-tenant | The donation page (main.py page route) |

## Dependencies

- `app.core.database` (Base, get_db) — server-side storage.
- `app.core.event_bus` (`ISSUE_RESOLVED`) — resolution event.
- `app.core.security` (`require_tier`), `app.core.capabilities`
  (`require_capability`), `app.core.user_context` (`UserContext`, `UserRole`).
- No module-to-module imports.

## Risk

- Consent/privacy-sensitive by design — mitigated: explicit versioned
  consent, per-item opt-in, PII screen on free text, moderation gate on
  narrative items, hard delete on withdrawal.
- UPL: none — collects experience data, gives no legal guidance.
  `upl_risk_tier=LOW`, `fees_policy=TENANT_NO_FEES`.
- Failure mode: module fails → `optional=True` keeps the app up; the page
  degrades to an explanation + link to `/help` (no dead end).

## Verification plan

- `python -m py_compile` on all changed/new files.
- `pytest tests/test_info_donation.py -q --no-cov` — service + endpoint
  coverage (gate enforcement, consent versioning, PII rejection, per-item
  opt-in, withdraw, moderation, no cross-user leakage).
- `pytest tests/module_health/test_info_donation.py -q --no-cov` and a
  `tools/module_registry.yaml` entry.
- `python tools/guardrail_engine.py`.
- Live check on :8001 (page 200, API 401 unauthenticated, end-to-end
  donate/withdraw with a seeded dev user).
