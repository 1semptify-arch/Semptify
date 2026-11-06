# Legal Share — Consent Model + Promotion Blueprint

**Status:** DRAFT — pending approval
**Type:** Lifecycle promotion (dev_only → beta) + canonical consent-model
documentation. No new module; one manifest line + verification.
**Pillar:** HELP (L2 — shared with a helper, only with consent)
**Date:** 2026-11-06
**Toolbox entry:** `share_with_legal_aid` (partial, group=helpers,
engine=help) — "Let a legal aid office or attorney see your record, with
your consent, and take it back any time."
**Queue:** sorg-p7-helped ("merge legal-share, consent model")

## Audit finding: the merge already happened

`feat/legal-share-portal` is an ancestor of the working line — the whole
branch (Phases 1–5: CASE_SHARE backend, REVIEW_THREAD Q&A, `/r/{token}`
reviewer portal, `/legal-share` tenant page, counsel-packet importer)
landed on `chore/remove-dead-css-system3`. The toolbox note "Built on a
branch that is waiting for review" is stale — what is actually pending
is **lifecycle promotion**, not merge.

What exists on disk today (`app/modules/legal_share/`):

- `service.py` (485 lines) — CASE_SHARE + REVIEW_THREAD overlay stores.
- `router.py` (556 lines) — API at `/api/legal-share` + `pages_router`
  (`/legal-share` tenant page, `/r/{token}` anonymous reviewer page).
- `register.py` + `module_contract.json` — 5 function groups registered;
  `app/core/contract_loader.py` loads them.
- `tests/test_legal_share.py` — vault-persistence tests with a fake
  provider (token resolution, expiry/revoke, scope enforcement, unread
  flags, "nothing certified / reviewer has no identity" invariants).
- Templates: `pages/legal_share.html`, `pages/reviewer_share.html`,
  `pages/reviewer_unavailable.html`.
- Manifest: both routers registered at `ProductTier.EXTENDED`,
  `lifecycle="dev_only"` — mounted but admin-gated in production
  (`dev_mode_middleware` checks `module_overlay.is_module_in_dev_mode`).
- `/api/legal-share/r/` is already in `PUBLIC_PREFIXES`
  (`storage_middleware.py:187`) — the reviewer lane needs no storage
  session.

## The consent model (already implemented — document as canonical)

This is the L2 pattern the whole HELP engine should reuse. Its
invariants, all enforced in code:

1. **Tenant-initiated only.** A share is created by the tenant's own
   session (`yellow_access`); nobody can request one on their behalf.
2. **Scoped slice, not the vault.** The grant carries an explicit
   `documents` id list; `shared_document_ids()` is the enforcement set
   on every reviewer read (metadata, content stream, thread binding).
   Notes/deadlines/summary are separate opt-ins (`include_notes`,
   `include_summary`, `deadline_ids`).
3. **Expiring by construction.** `expires_days ∈ {7, 30, 90}` — no
   open-ended grants; expired shares 410.
4. **Revocable instantly.** `POST /shares/{id}/revoke` stamps
   `revoked_at`; the reviewer sees a calm "no longer available" page,
   never an error.
5. **Reviewer has no identity.** The owner-scoped token
   (`{effective_user_id}:{urlsafe32}`) is the entire credential — no
   account, no cookie, no server-side token index (resolution reads the
   owner's own vault overlays).
6. **Nothing leaves the tenant's storage.** Shares and Q&A threads are
   overlays in the tenant's vault (`VAULT_RECORDS_FILE`,
   `VAULT_CASE_REVIEW_FILE`), `created_by = tenant`, `certified=False`,
   originals immutable. Semptify stores no case content server-side.
7. **No generated content.** Reviewer questions and tenant answers are
   stored verbatim — the system never drafts legal text (UPL posture).
8. **Tenant visibility.** `access_count`/`accessed_at` on every share +
   `unread_by_tenant` flags surface in `GET /shares` and `/questions`.

## What promotion still needs

- [ ] **Lifecycle flip:** `lifecycle="dev_only"` → `"beta"` (or
  `"experimental"`) on both manifest entries in
  `app/core/product_manifest.py` (lines ~813–837). One-word change;
  dev_mode_middleware then stops admin-gating the routes.
- [ ] **Live dev-profile verification** (not yet done — module merged
  but never exercised end-to-end on a running server): create share →
  open `/r/{token}` anonymously → reviewer question → tenant reply →
  revoke → confirm 410.
- [ ] **Tenant notification gap (decision #2):** today the tenant only
  learns of reviewer questions by opening `/legal-share` or calling
  `/questions`. No badge/email/digest exists. Decide: accept passive
  discovery for beta, or require a notification affordance first.
- [ ] **Entry copy for the tenant page:** `/legal-share` is reachable
  only by URL — no nav entry exists (progressive-disclosure rule:
  surface it from the tenant home once beta).
- [ ] **Toolbox flip after promotion:** `share_with_legal_aid`
  partial→live only after the live verification above passes on the
  deployed profile.

## Decisions needed (Brad)

1. **Promote to `beta` now or hold?** Recommended: promote after the
   live dev-profile pass — the code is complete and tested, the only
   unproven surface is runtime, and `beta` matches how the catalog reads
   ("some of it works today").
2. **Notification affordance:** passive (beta) vs. build a
   questions-badge on tenant home first. Recommended: passive for beta —
   tenants who create a share know to check back; a badge is a P8-era
   polish item, not a consent blocker.
3. **Reuse as the canonical L2 consent pattern:** adopt CASE_SHARE as
   the model all future helper-sharing (advocate add-on, agency
   referrals) builds on — i.e., pro-role add-ons *consume* tenant-granted
   shares rather than holding standing access. Recommended: yes — it is
   the only model compatible with tenant-only identity (PR #317).
4. **Counsel-packet importer** (`case_review` vault importer, branch
   commits `9a62cb6d`/`09687c18`): internal tooling, admin-side. Confirm
   it stays internal — never a tenant surface.

## Scope if approved

- `app/core/product_manifest.py`: two `lifecycle=` flips + dev_notes.
- Optional small template/nav additions per decision #2/#3.
- No service/router changes required for promotion itself.
- Verification: module test file + live reviewer-flow pass at 375/1280.
