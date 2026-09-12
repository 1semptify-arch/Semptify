# Semptify — Build Parameters (Org / App / Site, One Building)

**Status:** Landed 2026-09-11. Companion to `docs/orchestration/vision-brief-for-opus.md`
(the *why*) and `docs/admin/SEMPTIFY_BUILD_CONTRACT.md` (the *what must ship*).
This document is the *how we decide*: the parameter set for organization, app,
and site decisions, applied as one picture.

**The single test every parameter must pass:**

> Does this make the tenant's path through the building shorter, clearer, and
> safer — or does it just make the building more impressive? Where a parameter
> serves the building more than the tenant, it is flagged, not silently built.

---

## Organization parameters

1. **No decision lives only in Brad's head.** Any parameter or ruling that would
   block work must be written into a doc or the orchestrator queue within the
   session it is decided. (Proof of need: the build contract cited "Layer 2/3"
   phasing that existed nowhere in the repo.) *Serves: shorter path — agents and
   future sessions don't stall on undocumented context.*

2. **Donor surfaces never touch crisis surfaces.** Funding asks live only in the
   Donor lens. Donation UI may not share a render path with tenant-facing pages.
   Already policy under the vocabulary rules; this makes it *structural*, so it
   cannot be violated by a well-meaning template edit. *Serves: safer path — a
   tenant in crisis never meets a fundraising ask.*

3. **Org growth is gated on the security split, not headcount.** Before any
   second decision-maker or employee exists, the four-piece token model
   (planned 5.1) lands — "no single entity can access everything" must remain
   true the moment Brad stops being the only entity. *Serves: safer path —
   authority-over-data never concentrates silently.*

4. **Nothing in the app may depend on the 501(c)(3) existing.** Formation is in
   process; no feature, integration, or copy may presume approval. *Serves:
   safer path — a delayed or denied filing cannot break the product.*

## App/product parameters — what belongs in the tenant's room

1. **The room test.** A feature belongs in Semptify 5.0 only if it operates on
   the tenant's own documents in *their* cloud storage. Public-facing knowledge
   (Law Library, resource directory) and multi-party surfaces (advocate/agency
   caseloads) are different rooms — hallway or lobby, not the tenant's private
   space. Agency OAuth never touches the tenant vault.

2. **Name the armor.** During 5.0 stabilization, every proposed feature must
   answer "what damage does this limit?" If it cannot name the harm it prevents,
   it waits for 5.1. This is "armor, not weapon" made mechanical.

3. **Post-resolution donation is its own room.** Opt-in only, after the tenant's
   dispute resolves, and never inside the active-case flow — separate intake,
   separate storage, separate consent record. Consent UI living inside the
   active vault invites scope creep on the zero-persistence promise.

4. **Documents are never the product.** Active case data cannot become the
   research dataset — not anonymized, not internal-only — without the explicit
   post-resolution donation above. *Flagged: currently policy-only; nothing in
   code enforces this separation yet.*

## Site/portal parameters

1. **The lobby does one thing.** Warm welcome, then route. Navigation complexity
   appearing on the landing page means portal work is being done in the wrong
   room. The "comforts of home" imagery is the parameter, not decoration — the
   lobby's job is emotional (a rental implies a home; a home implies safety),
   not informational.

2. **Every public room has its own door.** Any page a tenant might need must be
   reachable by direct URL — search result, bookmark, a caseworker's text
   message. The portal assists; it never sits in the path. A public page
   reachable *only* through the portal is a bug, per ADR-0002.

3. **Anonymous-first, permanently.** Anything reachable without OAuth stays that
   way. OAuth only ever guards the tenant's own storage. Authentication in
   front of information is a checkpoint on the road — the thing the Navigation
   Principle exists to prevent.

4. **One visible next action.** Every page answers "where does a person in
   crisis go from here?" A dead end is a defect, not a design choice — and per
   standing rule, errors must route to outside help, not a wall.

---

## Standing exceptions (known, tracked, awaiting Brad)

Parameters honest enough to name where the building currently fails its own
test:

- **`document_uploaded` gate** — a cookie-bearing tenant mid-onboarding cannot
  reach public knowledge until the vault proof passes. Its purpose is real
  (live end-to-end proof that the tenant's vault pipeline works — write,
  read-back, registry, certification), and the gates doc defines all three
  gates as intended. It remains the single standing checkpoint in the road.
  Tracked: `onboarding-third-gate-adr0002-2026-09-11` (blocked_on_decision).
- **Cold-start hang** — `python-magic`'s module-level `load()` spins on
  Windows, so the front door currently cannot open on the dev machine without
  a stub workaround. Armor that can't be entered isn't armor. Tracked:
  `bug-python-magic-startup-hang-2026-09-11`.

## How to use this document

When a parameter is proposed or a build decision is made, check it against the
test at the top. If it serves the building more than the tenant, flag it in the
queue rather than building it silently. When Brad rules on a flagged item, the
ruling gets written here or in the citing doc — not left in chat.
