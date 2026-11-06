# Tenant Group Finder — Blueprint

**Status:** DRAFT — pending approval
**Type:** Public L0 page over the existing resource directory + approved
listing seeding process. No new backend machinery.
**Pillar:** HELP (routing to real humans) — L0 read & learn
**Date:** 2026-11-06
**Toolbox entry:** `tenant_union_finder` (planned, group=together,
engine=help) — "Find a local tenants union or tenant organization."
Catalog note: "Every listing must be reviewed and approved before it
appears (listing rules)."

## Audit finding: the machinery already exists end-to-end

- **`app/modules/resource_directory`** (436-line router, registered
  stable): public `GET /api/resources` with category/subcategory/
  service_area/state/county/language filters; `GET /api/resources/{id}`.
  **The admission rule is the approved-listings rule**: `_visible()` lets
  a listing surface publicly only if `is_no_charge` OR
  `is_verified_nonprofit`; unverified rows are stored for admin review
  but never shown (model comment, Brad 2026-09-21). Admin create/
  update/CSV bulk-import sits behind `require_admin_network`
  (Tailscale-gated).
- **`tenant_union` is a named category example** on the `Resource`
  model (`models.py:1949`) alongside `legal_aid`, `housing_counseling`.
- **Staleness surfacing**: `last_verified` older than 365 days is
  flagged — an outdated phone number can actively harm someone.
- **Consumers already live**: `/tenant/resources` (app-side finder page
  with emergency-pin + tel: links), `law_library.html` (resource
  pop-out), `help.html`.
- **`resource_intake`** (209-line engine): the vetting pipeline —
  candidates → fact-check → human approval → released into the compiled
  resource pool. Approval provenance is recorded (`approved_by`,
  `fact_check_method`, `fact_check_date`).

What does **not** exist: any `tenant_union` listings (the directory is
near-empty — composer pool holds one statute seed), and a **public** L0
finder surface (`/tenant/resources` is app-gated; `/api/resources` is
public JSON but not a page a person can use).

## Proposed shape

1. **One public page** — `app/templates/public/find_tenant_group.html`
   extending `body/public_shell.html`, plus a `PortalPage` registry line
   (the `/credit-reports` pattern — no router, no backend). Suggested
   path `/find-a-tenant-group`. Thin JS calls the already-public
   `GET /api/resources?category=tenant_union&state=..&county=..`.
   Empty state is honest and useful: "No approved tenant groups are
   listed for your area yet — here is what you can do today" (211
   pointer + link to the start-a-group guide from the P4 blueprint).
2. **Listing admission stays exactly as coded.** New listings enter
   ONLY through the admin import path — each row reviewed and approved
   by Brad before `is_no_charge`/`is_verified_nonprofit` is set. This
   blueprint proposes the mechanism; it does not add a single listing
   (third-party listings are a standing stop-trigger — Brad approves
   each one).
3. **Sourcing rule for the first batch** (recommendation, Brad decides):
   start with organizations findable through official channels —
   state/national tenant-union federations, Legal Services Corporation
   grantee lists, HUD-approved counseling agencies — never scraped
   directories. `verified_source` records what the approval rests on
   (`"lsc-grantee"`, `"hud-approved"`, `"org-official-site"` — the model
   already names these).
4. **Donate-page companion fix** (shipped in the P7 pass, this commit):
   `/donate` claimed present-tense "Semptify connects renters with their
   local tenants unions" — softened to match `planned` status.

## Decisions needed (Brad)

1. **Approve the page shape** — one public page + one registry line,
   reusing `/api/resources` unchanged. Recommended: yes — smallest
   honest path to `live`.
2. **First-listings source.** Recommended: Brad hand-picks the seed set
   from official channels (even 3–5 national/statewide orgs makes the
   page real); agent prepares a CSV for `POST /admin/resources/import`
   but imports nothing unapproved.
3. **Category name.** `tenant_union` (model example) vs.
   `tenant_group` (plainer, matches the toolbox entry name).
   Recommended: `tenant_union` — already the coded convention; display
   label can say "tenant group" either way.
4. **Coverage honesty.** With a small seed list, most searches will
   hit the empty state. Recommended: launch anyway — the empty state
   carries the working today-path (211 + start-a-group guide), which is
   more honest than a padded directory.

## Scope if approved

- `app/templates/public/find_tenant_group.html` (new, ~150 lines).
- One `PortalPage` line in `app/modules/portal/pages.py`.
- Admin CSV import of Brad-approved listings (ops step, not code).
- Toolbox flip `tenant_union_finder` planned→live once ≥1 approved
  listing renders on the page; `backed_by` gains
  `resource_directory`, `resource_intake` (today lists only `campaign`).
- Verification: page at 375/1280, filters exercised, empty state
  verified, console clean.
