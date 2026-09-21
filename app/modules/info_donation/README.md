# Info Donation — "help the next tenant"

Post-resolution, opt-in, anonymized information donation. After a tenant's
housing situation resolves, they may voluntarily share anonymized answers
(how it ended, how long it took, what helped) so the next tenant in their
position gets a better path.

Spec: `docs/blueprints/info_donation_blueprint.md` and
`handoffs/info-donation-possibilities-2026-09-19.md` (Brad's decisions
2026-09-19: stable = issue resolved, event-based; server-side aggregate with
informed consent only; narrative review by Brad + beta users).

## Rules baked in

- **Gate:** nothing can be donated until the situation is resolved —
  `POST /api/info-donation/resolved` or any module publishing
  `EventType.ISSUE_RESOLVED`.
- **Consent:** versioned informed consent (`catalog.CONSENT_VERSION`) must
  be recorded before any item is accepted.
- **Per-item opt-in:** each catalog item is a separate yes; nothing bundled,
  nothing defaulted on.
- **Aggregate-only:** categorical items store immediately; free text lands
  in `moderation=pending` and is never served until a reviewer approves.
- **PII:** free text is screened for email/phone/SSN/street-address patterns
  before it is stored.
- **Revocable:** per-item withdraw or withdraw-all (hard delete + consent
  revoked).
- **Vault contents are never donated** — donations are answers to fixed
  questions, not document data.

## Files

| File | Responsibility |
| --- | --- |
| `catalog.py` | Item catalog + consent text/version (SSOT for what can be donated) |
| `models.py` | `InfoDonationProfile` + `InfoDonationItem` (Base, Postgres/SQLite) |
| `service.py` | Gate, consent, donate, withdraw, moderation |
| `router.py` | `/api/info-donation/*` JSON API (T2 tenant; review routes admin) |
| `register.py` | FunctionGroupContracts + `ISSUE_RESOLVED` subscriber |

Page surface: `GET /help-the-next-tenant` (main.py) →
`templates/pages/info_donation.html` + `static/js/info_donation.js`.
