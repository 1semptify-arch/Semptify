# Agency Connect + Partnerships Lane — Blueprint

**Status:** DRAFT — pending approval
**Type:** Small content/route improvement. No new module.
**Pillar:** HELP (routing to real humans) — L2-adjacent, public contact lane
**Date:** 2026-11-06
**Toolbox entries:** `agency_connect` (planned), `partnerships`
(planned) — both group=helpers, engine=help. Today-path for both:
write to `partnerships@semptify.org` via `/contact`.

## Audit finding: the lane exists and is honest — it's just thin

- `/contact` shows the partnerships mailbox as a `mailto:` link — that
  IS the agency/partnership lane today, and both catalog entries
  describe it accurately.
- `POST /api/public-forms/contact` exists and forwards to the support
  inbox via Resend (`public_forms/router.py:436`) — but **no public page
  renders a contact form**; `/contact` is mailto-only.
- `/advocacy` already carries the partner pitch correctly ("If they
  choose to share documents with you, they share them directly") with a
  "Partner With Us →" CTA to `/contact`.
- The portal services cards had wrong destinations (fixed in the P7
  pass): `advocate_affiliation`, `advocate_start_group`, and
  `agency_connect` all sent organizations to `/preamble` — the tenant
  onboarding flow — a dead end for an org. Now point to `/advocacy` /
  `/contact`.

## What's actually missing

Nothing structural. A housing agency or advocacy group can reach
Semptify today through a real mailbox. What `planned` honestly means
here is: no *structured* lane — no referral intake, no org profile, no
coordination surface. Those are partnership-program features, not
missing plumbing.

## Proposed shape (minimal, in order of value)

1. **Structured partnership inquiry on `/contact`** (optional, small):
   add a "partnership inquiry" option to the existing contact form
   machinery (`ContactRequest` gains an optional `org` + `kind` field,
   subject pre-set). Lets an agency say what it is and what it wants in
   one pass instead of composing a cold mailto. ~60 lines template +
   ~20 lines schema/route.
2. **Nothing else until there's demand.** A real "agencies connect"
   surface (referral intake, shared public info) is a partner-program
   design question that needs Brad + an actual partner conversation —
   it should not be invented speculatively. Both entries stay
   `planned` with the mailbox as the honest today-path.

## Decisions needed (Brad)

1. **Build the structured inquiry now or later?** Recommended: later —
   wait until the first real agency/partner inquiry shows what fields
   matter. The mailbox path is complete and honest; a form built before
   demand is a guess.
2. **Mailbox verification dependency.** The `contact_mailboxes` entry
   (P0 scope) still carries "not verified" — the partnerships lane's
   honesty rests on that mailbox actually being read. Confirm P0's
   mailbox verification covered `partnerships@` before any promotion.
3. **Referral-lane posture (pre-decision for the eventual design).**
   When an agency lane is built: agencies *receive* tenant-initiated
   referrals the same way reviewers receive shares — tenant consent,
   scoped content, no standing access (the CASE_SHARE pattern).
   Recommended: bake this constraint into the future spec now.

## Scope if approved

- Phase 1 only (if decision 1 is "now"): `ContactRequest` + contact
  form option + copy; nothing else.
- Toolbox: entries stay `planned`; no status flips.
