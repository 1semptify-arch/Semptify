# ADR 0011: User Data Lives in the User's OAuth Storage — the appDataFolder File Contract Is the Module Link Layer

Date: 2026-11-18
Status: Accepted

## Decision

Across the Semptify ecosystem, user data lives in each user's own
OAuth-authorized cloud storage — never on Semptify servers. For
standalone/browser-side modules the concrete contract is the Google Drive
`appDataFolder` (hidden, app-scoped, invisible to other apps), holding
**one JSON array of rows per file**, namespaced
**`semptify.<module>.<collection>.json`**.

Because modules sharing the same OAuth client can read each other's
namespaced files, **the user's own Drive is the linking layer between
Semptify tools** — a second module resolves the first module's data by
reading its file directly, with no Semptify API or shared database in
between.

**Reference implementation:** `modules/app-crm/src/lib/driveStore.ts`,
with the file contract and rules of the road in
`modules/app-crm/docs/OAUTH-STORAGE.md`. It is the copy-paste starting
point for any future module.

**Brad's own setup stays god-mode/local.** The `dev-godmode-token` →
`LocalDiskProvider` path (`app/services/storage/local_disk.py`,
`app/services/storage/__init__.py`) plus direct case-side E: access is
the declared development/prototype environment — a carve-out by design,
not a security hole to fix.

## Why

- **Zero possession.** Nothing for Semptify to secure, breach, back up,
  or subpoena: the browser talks to `googleapis.com` directly and user
  content never transits our infrastructure. This is the concrete
  mechanism behind the three-layer model in
  `SECURITY_AND_PRIVACY_ARCHITECTURE.md`.
- **Cross-module linking with no backend.** Semptify tools share state
  through the user's Drive, not through a Semptify service — e.g. a
  module can read `semptify.crm.contacts.json` to resolve a contact
  without any API call to us.
- **Serverless and dependency-free.** GIS implicit tokens
  (`drive.appdata` — the narrowest Drive scope) + plain Drive REST v3
  fetch. No SDK, no server, no storage bill.
- **Proven.** app-crm already runs the full pattern: file-id caching,
  create-on-missing multipart upload, per-file write queues so rapid
  saves can't clobber read-modify-write, silent ~1h token re-auth with a
  single 401 retry.

## Consequences

- Any new Semptify module that needs persistence without the flagship
  backend MUST use this contract: `drive.appdata` scope only (never a
  broader Drive scope), `semptify.<module>.<collection>.json` naming,
  whole-array writes serialized per file.
- Modules MAY read other modules' namespaced files (that is the link
  layer); they MUST write only their own namespace.
- The flagship's provider-split vault (ADR-0001 — `Semptify5.0` across
  Drive/Dropbox/OneDrive) remains the canonical *document* pipeline.
  This ADR governs structured module state and the cross-module link
  layer; the two are complementary expressions of the same rule (user
  data in the user's own OAuth storage), not competing stores.
- OAuth *token* persistence is unchanged — ADR-0010 still governs
  (sessions table today, vault-first migration planned). This ADR covers
  user data, not tokens.
- God-mode/local is Brad's declared environment. Never "fix" it, never
  require OAuth storage for it, and never let its local-disk shortcuts
  leak into user-facing flows.
- Never add a Semptify-side proxy to this flow — user content must not
  transit our infrastructure.
- Whole-file replace is fine at personal scale (~a few MB per
  collection); beyond that, shard by id prefix per OAUTH-STORAGE.md.
