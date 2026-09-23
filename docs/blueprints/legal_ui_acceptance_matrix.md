# Legal / Advocate UI — Acceptance Matrix (spec of record)

**Status:** ACTIVE SPEC — build slices are not done until their rows pass
**Module paths:** `app/modules/advocate/`, `app/modules/legal/`,
`app/modules/legal_trails/`, `app/modules/unified_overlays/`,
`app/templates/pages/{advocate*,legal*,tenant_my_advocate}.html`,
`app/main.py` page routes
**Companion docs:** `advocate_collaboration_pipeline_blueprint.md`
(pipeline stages + parked decisions), `document_color_key_blueprint.md`
(shipped)
**Date:** 2026-09-23
**Requested by:** Brad — "perfect, no shortcuts, no gaps, rock solid by
design, simple, easy to use, non-confusing, every process must pass all
attorney-client things, one chance — run it through all scenarios and
usage simulations."

## What "done" means

A row is **PASS** only when verified against the running application
(browser-driven via IronBee DevTools where it's UI; pytest for contract/
security rows) — never by code inspection alone. A slice is done only
when every row in its group passes at desktop ~1280px and mobile ~375px,
with console-error check. No row may be skipped silently; rows that
become obsolete are struck through with a reason, never deleted.

## Non-negotiable invariants (every row inherits these)

1. **Overlay-only.** Original document bytes are never modified. All
   highlights, notes, footnotes, color-key meanings, review marks, and
   collaboration state are overlays or metadata. Viewer rendering is
   DOM-only. The only way to produce a changed document is the gated
   release path (timestamp + certificate) producing a *new* artifact.
2. **Tenant owns the data.** Every grant visible to the tenant, every
   access logged (`vault_audit_logs` exists — wire it), every permission
   revocable by the tenant, revocation effective immediately.
3. **Legal role is read-only on tenant vaults** (`04-roles-and-identity`).
   Legal sub-roles — `attorney`, `judge`, `clerk`, `paralegal` — all
   require `bar_license_number`. Legal writes only through
   `overlay_create_legal` and `forms_share`, never `vault_write`.
4. **UPL boundary.** Semptify documents a relationship the parties form
   themselves. It never gives legal advice, never claims to create an
   attorney-client relationship, never practices law.
5. **No dead ends.** Every error, expired link, revoked access, or empty
   state routes the user toward a next step — never a blank wall.
6. **Voice = phone.** Co-viewing is eyes-only: shared document position
   and pointer, nothing recorded, no third-party media servers. Ships
   only when solid; phone alone is the acceptable fallback.
7. **Semptify voice.** Calm, plain, short. No "free", no business-model
   terms, no "evidence"/"proof" before a court date — "documentation",
   "records", "paper trail".
8. **Honest privilege labeling.** Advocate communications are NOT
   attorney-client privileged; attorney communications MAY be. The UI
   must never imply privilege where none exists — this is both an
   honesty requirement and a real legal-safety issue for tenants.
9. **Progressive disclosure.** A stressed non-technical tenant on a phone
   must be able to do every flow without instruction. Power features
   reveal as needed, never up front.
10. **Reasonable-efforts security baseline** (ABA Model Rule 1.6(c) /
    Formal Op. 477R): TLS in transit (Cloudflare), provider-side
    encryption at rest (tenant's own vault — Google/Dropbox), RBAC on
    every endpoint, immediate revocation, and an audit trail that is
    tamper-evident, complete, and not deletable by any user role. Where
    the sensitivity warrants ("higher degree of security" per 477R),
    prefer narrower scopes and shorter-lived tokens over broader ones.
11. **Chain of custody by construction.** Every document gets a content
    hash recorded at intake; the audit log records who/what/when for
    every access; released artifacts carry hash + timestamp/certificate.
    This aligns released records with FRE 902(13)/(14) self-authentication
    posture — certification language remains the qualified person's job,
    not the platform's claim.

## Actors

| ID | Actor | Notes |
|---|---|---|
| T | Tenant | Primary user; stressed, non-technical, often mobile |
| A | Advocate | Tenant-rights worker, multi-client caseload (`ADVOCACY` relationship) |
| AT | Attorney | Legal sub-role `attorney`, `bar_license_number`, read-only vault |
| PA | Paralegal/clerk | Legal sub-roles, narrower scope |
| X | External recipient | Share-link holder, no Semptify identity |
| ADV | Adversary | Landlord/PM/opposing party — must see nothing, ever |

## Current-state map (verified 2026-09-23 against live code)

**APIs (real):** `/api/advocate/*` 15 endpoints; `/api/legal/*` matters,
filings, discovery, exhibits, overlay; `/legal-trails/*` 22 endpoints
(violations, eviction threats, late-fee calc, broker oversight, claims,
filing windows, complaint generators, MN attorney directory);
`/api/unified-overlays/*` incl. `DOCUMENT_KEY` color key + footnotes.

**Pages:** `/advocate/clients/{id}` wired (docs/review/annotate/overlays);
`/tenant/my-advocate` and `/advocate/invite` partially wired;
`/advocate/dashboard`, `/legal/dashboard` static mockups;
`/legal/{subpage}` dead (no `static/legal/` files);
`legal_trails.html` orphaned (no route).

**Access model:** `UserRelationship` `ADVOCACY` rows, `is_active` flag;
`_check_client_link` per-request → revoke is immediate at the API.
Link is **tenant-initiated** via `link-request` with advocate's user_id;
scope is whole-client — **no per-case or per-document scoping today**.

## Scenario matrix

Verify methods: `API` = pytest/contract; `UI` = browser-driven live;
`SEC` = adversarial test; `COPY` = text/voice review.

### G1 — Identity, roles, boundaries

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G1.1 | T | Opens /legal or /advocate paths | Redirected or shown plain "not for you" with a real next step — never 403 wall | UI |
| G1.2 | A | Opens legal-only surfaces | Same — role separation enforced server-side, not just hidden links | SEC |
| G1.3 | AT | Has `legal_sub_role=attorney` + bar number | Attorney tools visible; paralegal/clerk get subset per role | API+UI |
| G1.4 | T+A | One user holds both roles | Both surfaces work; no state bleed between them | API |
| G1.5 | any | Forged/invalid session | Rejected; redirected to the real entry path, no partial render | SEC |
| G1.6 | ADV | Hits any tenant/advocate/legal route | Nothing tenant-specific leaks in body, headers, or error text | SEC |

### G2 — Invite & consent

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G2.1 | T | Starts "share my case" flow | Sees exactly what the advocate will be able to see BEFORE granting | UI |
| G2.2 | A | Receives link-request | Can accept/decline; sees tenant name + note; decline is clean | API+UI |
| G2.3 | T | Grants access | `ADVOCACY` row created; grant visible on tenant's "who can see my case" list | API+UI |
| G2.4 | T | Enters wrong/typo advocate ID | Clear error, no partial link, no dead end | UI |
| G2.5 | T | Advocate ID belongs to non-advocate | Rejected with plain explanation | API |
| G2.6 | A | Uses org invite code | Code validates, expiry/uses enforced, spent code rejected | API |
| G2.7 | T | Wants case-scoped (not whole-file) access | Either supported or UI honestly says access is whole-case | UI |
| G2.8 | T | Revokes before advocate ever views | `is_active=False`; advocate's next request 403s | API |

### G3 — Access, permission, revocation

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G3.1 | A | Lists clients | Only own `ADVOCACY` relationships appear — no other tenants | API |
| G3.2 | A | Opens non-client `client_id` directly | 403; nothing rendered | SEC |
| G3.3 | A | Revoked mid-session | Next API call 403s; open pages degrade to a clear "access ended" state | UI+API |
| G3.4 | A | Tries vault write on tenant doc | Denied — legal/advocate have no `vault_write` | SEC |
| G3.5 | A | Annotates client doc | Overlay created under advocate identity, original untouched | API |
| G3.6 | T | Views advocate's annotations | Visible with attribution; tenant sees who marked what | UI |
| G3.7 | A | Deletes own annotation | Deleted; cannot delete tenant's overlays | API |
| G3.8 | any | Every document access by A/AT | Written to `vault_audit_logs` (wire if missing) | API |
| G3.9 | T | "Who has seen my case" view | Tenant can see access history in plain language | UI |

### G4 — Document review & color key

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G4.1 | T | Opens doc, sets color meanings | DOCUMENT_KEY persists; reload shows same meanings | API+UI |
| G4.2 | T | Highlights + footnotes | Painted marks; original bytes unchanged (hash compare) | API |
| G4.3 | A | Opens same client doc | Sees tenant's color key + painted marks — shared vocabulary works | UI |
| G4.4 | A | Own annotations on shared doc | Rendered alongside tenant's, distinguishable by author | UI |
| G4.5 | T+A | Both annotate same doc concurrently | Both sets persist; no overwrite; legend counts merge | API |
| G4.6 | any | Doc deleted/archived with overlays | Overlays orphaned cleanly; UI says what happened, no crash | API |
| G4.7 | A | Clicks legend entry | Scrolls to + flashes the mark (same as tenant experience) | UI |
| G4.8 | any | Overlay fetch fails (storage down) | Doc still renders; honest "notes unavailable" state, not blank | UI |

### G5 — Privilege & confidentiality (attorney-client)

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G5.1 | AT | Attorney workspace materials | Attorney's own work product is not visible to advocate or tenant by default | API |
| G5.2 | A | Advocate materials labeled | UI never labels advocate comms "privileged" — honest wording | COPY |
| G5.3 | T | Shares doc with attorney vs advocate | Tenant sees the difference explained plainly before granting | UI+COPY |
| G5.4 | X | Opens share link | Sees only that document + tenant's message; no navigation into anything else | UI+SEC |
| G5.5 | X | Link expired / revoked | Clean "this link has ended" page with a real next step | UI |
| G5.6 | X | Forwards link to adversary | If link is live, ADV sees the doc — UI must warn tenant at share time that links can be forwarded | COPY |
| G5.7 | AT | Attorney overlays on tenant doc | Via `overlay_create_legal` only; no vault write | API |
| G5.8 | any | Error pages in shared/legal space | Never echo tenant data, paths, or IDs in error text | SEC |
| G5.9 | T+AT+A | Third party joins attorney comms (co-view, shared doc) | UI states plainly: a non-attorney present in attorney-client communications can affect privilege — parties choose who joins; no silent three-ways | UI+COPY |
| G5.10 | T | Shares privileged material via link | Share flow warns: forwarding can waive privilege; treat links like handing someone the paper | COPY |
| G5.11 | AT→PA | Paralegal/clerk accesses client matter | Access is delegated under a supervising attorney and visible to that attorney (Rule 5.3 — lawyer answers for nonlawyer conduct) | API |
| G5.12 | any | Export/release of a document | Metadata scrub considered: hidden metadata can carry privileged info even when visible text is redacted — release path documents what it emits | API |
| G5.13 | T | Tenant annotations/notes | Honest note where relevant: anything written on the platform may be discoverable in litigation — the tool never promises secrecy a court can't honor | COPY |

### G6 — Co-view session (eyes, not voice)

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G6.1 | T/A | Start session on a document | Short-lived token; both see same doc + color key | UI |
| G6.2 | A | Host scrolls/pages | Guest view follows; "look at paragraph 3" pointer lands | UI |
| G6.3 | T | Ends session | Guest tokens dead immediately; reload can't rejoin | SEC |
| G6.4 | T | Revokes advocate mid-session | Session terminates, not just future API calls | SEC |
| G6.5 | A | Guest network drops | Reconnects to current position or clean "session ended" — never stale view | UI |
| G6.6 | any | Session log | Records who/when/which docs — never content, never recording | API+COPY |
| G6.7 | any | Session under load/flaky | Degrades to "view the same doc separately" guidance — never frozen half-sync | UI |

### G7 — Matters, filings, representation

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G7.1 | AT | Creates matter | Persists; appears on legal dashboard (real data, not mockup) | API+UI |
| G7.2 | AT | Filings/discovery/exhibits | Each list renders real rows; empty states are honest | UI |
| G7.3 | AT | Matter overlay view | Tenant doc + overlays visible per granted scope | UI |
| G7.4 | T | Sees representation status | "Working with X since DATE" in plain words on tenant side | UI |
| G7.5 | AT | Handoff/packet export | Bundle includes legend page so highlights decode offline | UI |
| G7.6 | any | UPL check on all copy | Nothing implies Semptify practices law or creates the A-C relationship | COPY |

### G8 — Legal Trails wiring

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G8.1 | T | Legal Trails page reachable | Route serves `legal_trails.html`; not orphaned | UI |
| G8.2 | T | Log violation/threat/late fee | Persists via `/legal-trails/*`; appears in lists | API+UI |
| G8.3 | T | Filing windows view | Real deadlines render; empty state routes to logging one | UI |
| G8.4 | T | Generate complaint drafts | Output marked as draft; routes toward attorney/legal aid | UI+COPY |
| G8.5 | A | Sees client's trail data | Scoped to relationship; consistent with doc access rules | API |

### G9 — Release & timestamp

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G9.1 | T | Final release of a doc | Separate gated action; produces new artifact; original untouched | API |
| G9.2 | any | Released artifact | Carries timestamp/certificate; legend travels as metadata or legend page | API+UI |
| G9.3 | T | Understands the distinction | UI makes "original / marked-up view / released copy" unmistakable | UI+COPY |
| G9.4 | A | Tries to release on tenant's behalf | Denied or explicitly delegated — never silent | SEC |
| G9.5 | any | Document hash lifecycle | Hash recorded at intake; re-computable at any time; released artifact hash + timestamp + certificate travel together | API |
| G9.6 | any | Audit trail as custody record | Chronological access log per document is exportable and covers every view/share/annotate/release event | API |

### G10 — Failure, edge, accessibility

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G10.1 | any | Storage token expired | Honest reconnect prompt; doc list still readable; no crash | UI |
| G10.2 | any | Every empty list/state | Each has a next action; zero dead ends anywhere | UI |
| G10.3 | any | 375px mobile | All flows completable; no overflow; touch targets adequate | UI |
| G10.4 | any | Screen reader / keyboard | Panels, pickers, sessions operable without a mouse; ARIA sane | UI |
| G10.5 | T | Stressed-path walkthrough | Persona test: frightened tenant on phone can invite advocate + share a doc unaided | UI |
| G10.6 | any | Slow network | Loading states real; no half-rendered panels | UI |
| G10.7 | A | Concurrent edits to color meanings | Last-write wins with no corruption; both parties see final state | API |
| G10.8 | any | Idle session timeout | Inactivity expiry enforced (baseline ~30 min legal roles / ~60 min tenant); re-entry is clean, not a broken half-state | API+UI |
| G10.9 | T | Cognitive-load check (in-crisis heuristics) | Every tenant-facing flow: ≤3 decisions per screen, plain verbs, crucial info visually first — measured by walkthrough, not vibes | UI |
| G10.10 | T | Safety exit | If a tenant shares screens or is being watched, sensitive pages can be left quickly to a neutral page — sized appropriately to housing context, not a panic-button gimmick | UI |

### G11 — Adversarial / leak checks

| ID | Actor | Scenario | Pass criteria | Method |
|---|---|---|---|---|
| G11.1 | SEC | Enumerate client_ids / doc_ids / tokens | No oracle: 403 identical to 404 where appropriate; no timing leak | SEC |
| G11.2 | SEC | Replay expired invite/share/session tokens | Rejected; logged | SEC |
| G11.3 | SEC | Overlay payload injection (script in note/meaning) | Rendered as text, never executed; sanitized on paint | SEC |
| G11.4 | SEC | Cross-tenant overlay access | Tenant A's overlays never resolve under tenant B's doc | SEC |
| G11.5 | SEC | API-only access without UI | Same permission checks hold — UI is never the enforcement | SEC |
| G11.6 | SEC | Audit-log tampering | No user role can delete or alter audit rows; failed-access attempts are themselves logged | SEC |
| G11.7 | SEC | Brute-force on link/session tokens | Token entropy adequate; rate-limit or lockout on repeated invalid tokens | SEC |

## Build order (each slice = rows verified before next)

| Slice | Rows | Contents |
|---|---|---|
| 1 | G3.1–G3.2, G3.4–G3.5, G4.3–G4.4 | Wire advocate dashboard to real APIs; color key + painted marks in client detail; audit wiring check |
| 2 | G2.1–G2.8, G3.3, G3.9 | Invite/consent flow end-to-end; revoke behavior; "who can see my case" tenant view |
| 3 | G7.1–G7.3, G8.1–G8.5 | Wire legal dashboard to `/api/legal/matters`; route + wire legal_trails page; kill static mockups |
| 4 | G5.1–G5.8 | Privilege boundaries + share-link hardening pass |
| 5 | G6.1–G6.7 | Co-view session MVP (flagged; ships only when solid) |
| 6 | G7.4–G7.5, G9.1–G9.4 | Representation marker, packet legend, release gating |
| 7 | G10, G11 | Full failure + adversarial sweep, persona walkthroughs, final matrix sign-off |

## Research basis (external lenses consulted 2026-09-23)

- **ABA Model Rule 1.6(c) + Comment 18, Formal Opinion 477R** —
  "reasonable efforts" to prevent inadvertent/unauthorized disclosure;
  risk-based; higher-sensitivity info may require stronger precautions.
  → Invariant 10; session/token scoping choices.
- **ABA Model Rule 5.3 + Formal Opinion 506** — attorneys are
  responsible for nonlawyer conduct under their supervision; paralegal/
  clerk access must be delegated under and visible to a supervising
  attorney. → G5.11.
- **Privilege doctrine (third-party presence / waiver)** — comms in the
  presence of non-essential third parties can lose privilege; forwarding
  privileged comms waives it; the "agency exception" protects helpers
  *necessary* to the communication. → G5.9, G5.10. Design consequence:
  co-view sessions must show who's present and never silently add a
  third party to attorney-client review.
- **FRE 902(13)/(14), Sedona ESI Commentary, ETSI TS 103 643 (Digital
  Evidence Bag)** — self-authentication via hash + qualified-person
  certification; documented chain of custody (who/when/what) is the
  precondition. Our overlay-only + hash + timestamp design already
  aligns; the matrix makes it testable. → Invariant 11; G9.5–G9.6.
- **Client-portal security baselines** (Moxo/HubSecure/A bar guidance) —
  TLS 1.2+, AES-256 at rest, RBAC, immutable+exportable audit logs,
  session timeouts, per-document time-limited links, immediate
  revocation, unauthorized-attempt logging. → G3.8–G3.9, G10.8, G11.6–G11.7.
- **SAMHSA trauma-informed principles + i4J Ethical Tech Design
  Framework + in-crisis heuristics research** — safety, transparency,
  empowerment/choice; in-crisis users have impaired cognition → fewer
  decisions per screen, crucial info first, readable type. → Invariant 9;
  G10.9–G10.10.
- **Metadata-leak risk** (documented paralegal/ABA guidance) — hidden
  metadata can carry privileged content even when the visible text is
  redacted. → G5.12.
- **Discoverability honesty** — anything written on-platform (notes,
  annotations) may be discoverable; the UI must never promise secrecy a
  court can't honor. → G5.13.

## Decisions — settled by Brad (2026-09-23)

- **Scoping granularity → slice 2, before new invites.** Per-case /
  per-document sharing lands early; whole-file grants are the interim state.
- **Co-view MVP → page sync + shared pointer.** Plus an *anchored Q&A* lane
  (question pinned to a passage, answered in-session, persisted as overlays)
  — built in the session slice, not a chat inbox.
- **Session participants → visible** (G5.9 stands: an advocate present in an
  attorney-client session is shown and flagged as a possible waiver risk).
- **Representation status → simple marker** on the relationship, visible to
  both sides. No full lifecycle machinery in v1.
- **Invites → codes only for v1.** Brad's future idea logged: time-limited
  text-message verification with email fallback — revisit post-v1.
- **Pro-role security → idle session timeout; no extra 2FA layer.** Auth is
  delegated to provider OAuth (Google/Dropbox already enforce their own 2FA);
  an in-app second factor is friction without proportionate gain for v1.
- **Safety exit → quick-exit button** (DV-portal style): persistent discreet
  control that swaps to a neutral page instantly.
- **Co-view scope → role-agnostic (advocate AND legal).** One session
  system; per-role visibility enforced by the existing privilege filter.
- **Legal roles use OAuth storage like everyone else — no exceptions.**
  Same onboarding (provider connect → vault → role via invite code + bar
  number). No separate legal auth path. Consequence: an attorney's private
  work-product overlays live in the *attorney's own* vault — invisible to
  the tenant — which is the correct privilege boundary by construction.

## Still open

- Who can start a session — tenant-only vs. either side proposes (Brad asked
  whether sessions are advocate-only or include legal; settled above as
  role-agnostic, but the *initiator* question remains)
- Naming of the helper role ("advocate" umbrella vs. separate terms)
