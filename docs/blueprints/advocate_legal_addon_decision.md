# Advocate / Legal Add-On — Decision Brief

**Status:** DECISION DOC — Brad's call (build-system §7 decision #4)
**Type:** Architecture decision, not a build
**Date:** 2026-11-06
**Toolbox entries:** `advocate_portal` (planned), `legal_portal`
(planned) — both group=helpers, engine=help, L2.

## Where things stand (audited, not doc-claimed)

- **Tenant-only identity is shipped law.** `.devin/rules/04` (SUPERSEDED,
  kept "as add-on-repo reference"): PR #317 made the repo stateless
  tenant-only — no pro roles, no role gates, no elevation paths; access
  beyond the tenant's own surface comes only from tenant-granted
  sharing.
- **The dormant code is substantial, not stub.** `app/modules/advocate`
  (1,561-line router — dashboard, clients, queue, intake, link-requests,
  scope PUT, access log, document review/annotation, invite codes) and
  `app/modules/legal` (345-line router + 343-line service — legal
  workspace, matter/file surface) still exist and their registry entries
  still pass health checks. `app/templates/pages/advocate_*.html` +
  `tenant_my_advocate.html` survive; `/advocate/dashboard` and
  `/tenant/my-advocate` still render behind generic auth, but no role
  can authenticate *as* an advocate.
- **Public surfaces already honest.** Portal registry hid both role
  cards 2026-11-06 (`visible=False`, "kept dormant pending a retire
  decision"); `/advocacy` and `/legal-research` describe partnership and
  direct tenant-sharing without promising portals.
- **The flagship-side bridge already exists.** `legal_share` gives a
  tenant everything needed to work *with* a pro today — scoped,
  expiring, revocable `/r/{token}` access with Q&A — without any pro
  having an account in the flagship.

## Options

**A. Separate pro add-on repo (current documented direction).**
A second deployable holds the advocate/legal identity, caseload model,
and review surfaces. Flagship stays tenant-only; the add-on consumes
tenant-granted shares. The CASE_SHARE token model (see
`legal_share_promotion_blueprint.md`) is the consent bridge — a pro tool
would receive/honor `/r/{token}` grants, not hold standing access.
Dormant `advocate`/`legal` modules migrate out as the add-on's seed.

- Pros: preserves the tenant-only security boundary (no role-elevation
  attack surface in flagship); matches what the public pages and the
  rule file already say; add-on can carry bar-license checks, matter
  models, privileged-work-product handling the flagship shouldn't.
- Cons: two repos/deploys to maintain; the dormant code must still be
  carried (or retired) meanwhile; pro UX is cross-app (a share token
  per tenant, not a caseload dashboard inside one app).

**B. Bring pro roles back into the flagship.**
Reverses PR #317: re-introduce advocate/legal identities, role gates,
elevation.

- Pros: single app, caseload views are straightforward, dormant code
  reactivates in place.
- Cons: directly contradicts the tenant-only decision and every public
  statement made since; re-opens the role-elevation surface Brad closed
  on purpose; the toolbox notes would all have to be re-written. Not
  recommended.

**C. Retire the dormant code and stay token-share-only.**
Delete `advocate`/`legal` modules; `share_with_legal_aid` remains the
whole L2 story; toolbox entries move planned→vision with honest
today-paths.

- Pros: smallest surface, no second repo, zero ambiguity.
- Cons: abandons real, working caseload machinery (the advocate module
  is the most complete pro surface ever built here) and the "helped"
  level's longer-term promise.

## Recommendation

**A — separate add-on repo**, with CASE_SHARE as the consent bridge.
It is the documented direction everywhere it matters (rule 04, toolbox
notes, services-page hiding), it keeps the flagship's security story
simple, and it does not strand the dormant code — it relocates it. The
decision that actually matters for the flagship is already made:
**helpers get access only through tenant-granted shares.** Whether the
add-on ships this year or next changes nothing tenant-facing today.

Immediate mechanical asks if Brad picks A:

1. Leave the dormant modules in place but formally mark them
   `deprecated`/`internal` in the manifest (one-word lifecycle entries)
   so nothing accidentally revives them — or accept status quo
   (hidden cards already keep them invisible).
2. Toolbox `advocate_portal`/`legal_portal` stay `planned` with the
   existing "separate add-on" note until the add-on repo exists — no
   status change now.
3. When the add-on is built, its first feature is honoring
   `/r/{token}` grants — never direct vault access.

## Out of scope for this doc

Naming/hosting of the add-on repo, advocate invite-code mechanics, and
any UI for the pro side — all belong to the add-on's own blueprint once
Brad picks a direction.
