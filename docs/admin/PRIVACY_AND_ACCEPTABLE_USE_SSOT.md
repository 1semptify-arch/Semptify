# Privacy & Acceptable Use — SSOT

> **Status:** Canonical. This document + `app/core/privacy_aup.py` are the single
> source of truth for (a) what each role may store where, (b) the defined list of
> disclaimers for all modules and roles, and (c) what Semptify will and will not do.
> It extends — does not replace — the Role-Scoped Data Privacy Policy in
> `SECURITY_AND_PRIVACY_ARCHITECTURE.md` and the UPL tier system in
> `app/core/upl_guardrails.py`.
>
> **For AI agents:** before building any module that stores data or produces
> user-facing output, check `privacy_aup.py`. Unknown roles and unlisted
> fields fail closed.

---

## 1. The four storage buckets

Every field a module might touch falls into exactly one bucket **per role**:

| Bucket | Meaning |
|---|---|
| `server_allowed` | May be written to Semptify's database for this role |
| `vault_only` | May exist only in the user's own cloud vault (their Google Drive / Dropbox / OneDrive) |
| `vault_forbidden` | May NOT be written into a user's vault either (other users' data, server secrets, tracking artifacts) |
| `never_collected` | Must not exist anywhere in the system |

Enforcement helper: `privacy_aup.may_store_on_server(role, field_name)` returns
`True` only for fields explicitly in `server_allowed`. Anything not listed is
treated as vault-only — **fail closed**. A module needing a non-listed field
must implement the consent gate first (see §4).

## 2. Rule by role

### TENANT — zero PII on servers (hard rule)

- **Server allowed:** anonymous user ID, storage provider name, opaque provider
  subject ID, onboarding gate flags, role preference, timestamps, jurisdiction
  state code, encrypted OAuth tokens (session-scoped), tenant-created landlord
  contact records.
- **Vault only:** name, email, address, phone, DOB, case details, all document
  content, timeline, journal, evidence files, retaliation events, contacts,
  correspondence, court-form drafts, consent records.
- **Vault forbidden:** other users' data, server secrets/keys, server logs,
  executable code, tracking beacons, scraped opinion text, AI training data,
  other tenants' case data.
- **Never collected:** activity logs, click tracking, page-view history, IP logs,
  device fingerprints, location tracking, analytics, behavioral profiles, ad IDs.

### MANAGER — tenant-rights advocate (NOT a property manager)

- **Server allowed:** own operational case metadata, relationship records
  (advocacy links), provider/subject IDs, timestamps.
- **Vault only:** own notes/drafts, client-consented shared records.
- **Vault forbidden:** client PII without documented consent, other clients'
  case data.
- **Never collected:** platform never-collected list **+ tenant PII without consent.**

### ADVOCATE — consent-gated coordination

- Same shape as manager until the dedicated advocate data policy is written:
  case-coordination metadata on server, client records only with documented
  consent, no client PII in the advocate's own vault.

### LEGAL — sub-roles: attorney / judge / clerk / paralegal

- **Server allowed:** legal sub-role, hashed bar-license number (public
  credential, not PII), engagement/relationship records, timestamps.
- **Vault only:** work-product drafts and legal overlays in the legal user's
  OWN vault. **Read-only access to tenant vaults — `vault_write` is never
  granted** (04-roles-and-identity.md).
- **Never collected:** privileged content without an engagement record.

### ADMIN

- Internal operational data only. Audit events anonymized where possible.
  No tenant PII, no user document content — even for admins.

### RESEARCH

- Aggregated, anonymized data only. No individual-level data without explicit
  consent. Most restrictive rule — `storage_rule_for` falls back to it for
  unknown roles.

## 3. Disclaimer registry — the defined list

All disclaimers live in `privacy_aup.DISCLAIMERS` keyed by stable ID. Modules
**must not** define their own `LEGAL_DISCLAIMER`-style constants — three
divergent variants already existed (`law_library`, `eviction_defense`,
`role_ui`) and are being unified to this registry.

| ID | Use |
|---|---|
| `not_legal_advice` | Short UPL notice (canonical, from `upl_guardrails.py`) |
| `not_legal_advice_long` | Long UPL notice for banners/footers |
| `educational_info` | "Education only, not legal advice; verify with official sources" |
| `tenant_zero_pii` | Tenant data-promise notice on RECORD surfaces |
| `consent_gate` | Shown before any module stores tenant data server-side |
| `ai_generated` | AI output may contain errors — verify |
| `public_content_opinion` | Third-party/public content is opinion, not verified |
| `external_resource` | Outside orgs — Semptify doesn't run them, details change |
| `ephemeral_processing` | Documents processed in memory, never stored |
| `shared_access` | Shared records visible to the person shared with; revocable |
| `emergency_redirect` | Semptify is not an emergency service — 911/211 |

**Assignment:** `MODULE_DISCLAIMERS` maps every module to its required IDs;
`"*"` is the floor applied to everything. `ROLE_DISCLAIMERS` maps role-level
surfaces. Helpers: `disclaimers_for_module(name)`, `disclaimers_for_role(role)`.
A module not in the map ships no user-facing output until it is added.

## 4. The consent gate

Any module that wants to store tenant data server-side must, before writing:

1. Explain in plain language what data, where, and why.
2. Name the specific fields.
3. State retention period and deletion mechanism.
4. Obtain explicit opt-in — no pre-checked boxes.
5. Be skippable — core Semptify works without consent.
6. Record timestamped consent **in the user's vault**, not only on the server.
7. Display the `consent_gate` disclaimer at the decision point.

## 5. Acceptable use — what Semptify will and will not do

### Semptify WILL

- Organize the user's own documents, timeline, and records.
- Show verified facts — statutes, court rules, public records — with sources.
- Explain legal concepts in plain language (education, not advice).
- Track deadlines computed from the user's own events.
- Connect users to real outside help (legal aid, hotlines, agencies).
- Generate organizational documents from the user's own facts.
- Keep tenant data in the tenant's vault; delete everything on request.

### Semptify WILL NOT

- Give legal advice, predict outcomes, or represent anyone (UPL hard stop).
- File documents without attorney review.
- Contact landlords, agencies, or officials on a user's behalf.
- Store tenant PII without consent.
- Sell or share user data; run ads or tracking; require registration.
- Use urgency tactics, dark patterns, or act from fear, resentment,
  dishonesty, or greed — standing motivation rule.

### Users MAY

- Organize their own records; share them with helpers (revocable); export
  anytime; use Semptify for any lawful housing purpose.

### Users MAY NOT

- Upload other people's private data without the right to hold it.
- Use Semptify for harassment, doxxing, or dossiers on private individuals.
- Represent Semptify output as legal advice.
- Probe or attack the service, or scrape private individuals (companies only,
  per `pmas_foundation` rules).

---

## Cross-references

- `app/core/privacy_aup.py` — machine-readable twin of this document.
- `app/core/upl_guardrails.py` — UPL risk tiers, banned phrases, referral block.
- `SECURITY_AND_PRIVACY_ARCHITECTURE.md` §"Role-Scoped Data Privacy Policy" —
  the canonical policy this SSOT operationalizes.
- `docs/admin/MOTIVATIONS.md` — banned motivations and language rules.
- `app-pmas/pmas_foundation/AGENTS.md` — Tier A/Tier B data sensitivity
  (PMAS-side; the `public_content_opinion` and scrape rules align with it).

**Last updated:** 2026-09-19 — created per Brad's directive (per-role/module
not-allowed lists, defined disclaimer registry, will/won't-do SSOT).
