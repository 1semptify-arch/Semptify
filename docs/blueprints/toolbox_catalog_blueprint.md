# Blueprint — Toolbox Catalog (honest status for every promised service)

> Status: written 2026-11-01. Requested by Brad ("create stubs for non-fulfilled
> services depicted from the site pages ... and everything from the donate
> pages"). Built on branch `feat/toolbox-service-stubs`. Not shipped. Ship is
> Brad's call.

## Module
- **Name:** Toolbox Catalog. It extends the existing `portal` module and is not a
  new module.
- **module_path:** `app.modules.portal` (new file `toolbox.py`)
- **Type:** data registry plus public pages. It's a Pipeline-style read-only
  registry with no capability gate, because it's public and holds no user data.
- **Capability tier:** CORE (public)

## Problem it solves
The public site promises more than exists. Buttons for unbuilt services all go
to a generic `/preamble`, and some pages claim features that don't exist:
- blockchain timestamping on `/privacy`
- `/docs` on `/developers`
- "35 states" and "all 50 states" on `/donate`

A visitor who clicks a promise hits a dead end or a mismatch. That breaks the
Truth Standard and the Product Decision Filter item "honest representation of
system capabilities".

## Scope: what it does
- One registry (`ToolboxCatalog.ENTRIES`, 62 entries) holding every service
  mentioned on any public page. Each entry has an honest status
  (live / partial / planned / vision), a privacy level (L0–L4), an owning
  engine, what a person can do today, the pages that mention it, the existing
  modules behind it, and an honesty note wherever a page overclaims.
- `/toolbox` lists every entry by group with its status.
- `/toolbox/{id}` shows one entry: status → what you can do today (one action)
  → where it stands → details (collapsed) → get help now. Unknown ids render
  the full list with a 404 status, so there is no dead end.
- `GET /api/portal/toolbox` and `/api/portal/toolbox/{id}` give build agents
  the same data as JSON.
- Repoints the portal service-card buttons and `/tools` buttons for unbuilt
  services from `/preamble` to their toolbox entry.
- Fixes banned words in `portal/registry.py` ("Free", "No account required").

## Scope: what it does NOT do
- It doesn't build any of the services, and it doesn't fake them.
  No placeholder code paths exist, so `stub_detector` stays clean.
- It doesn't edit `/donate`, `/privacy`, or `/developers` copy. Those
  mismatches are recorded in entry notes and queued for a truth pass.
- It doesn't touch onboarding (NO-TOUCH module).
- It stores no user data and adds no tables.

## Roles
Public. No role gate.

## DB tables
None.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/toolbox` | Public list of every promised service + status |
| GET | `/toolbox/{entry_id}` | Public status page for one service |
| GET | `/api/portal/toolbox` | JSON catalog for agents |
| GET | `/api/portal/toolbox/{entry_id}` | JSON entry |

## Calls
`portal.pages` (page registry), the existing public-page loop in `app/main.py`,
and `body/public_shell.html`.

## Risks
- **The catalog goes stale as services ship.** Mitigation: flipping status is
  step 7 of the build loop (`SEMPTIFY_ORG_BUILD_SYSTEM.md` §4), and
  `tests/module_health/test_portal_toolbox.py` fails if a `backed_by` module
  disappears or a link points at a missing entry.
- **Statuses were set from code inspection and live checks on 2026-11-01, not a
  full functional test of every module.** Some "partial" ratings may be
  generous. The truth pass (phase P1) re-verifies each one.
