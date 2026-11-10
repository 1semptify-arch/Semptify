# Blueprint — Executive Administration (`executive_admin`)

> Status: BUILT — this blueprint documents the module as adopted and completed
> on 2026-11-08 (queue task `plan-20261108-nonprofit-office-module-mn-federal-501-c-df35`).
> The module was initially built in an IDE session as `nonprofit_office` and
> renamed `executive_admin` mid-build; Brad ratified the `executive_admin` name
> and the placement decision below on 2026-11-08.

## Module

- **Name:** Executive Administration — "Nonprofit Office"
- **module_path:** `app.modules.executive_admin.router`
- **Type:** Feature Module (admin-facing UI + API), GOVERN pillar
- **Mounted at:** `/admin/executive` (manifest prefix)

## Problem it solves

Semptify the organization is a Minnesota nonprofit corporation pursuing
501(c)(3) recognition. The formation path, the dated obligations that keep
the entity in good standing, board governance records, required policies,
the books of record, and grant readiness previously lived nowhere — scattered
notes at best. This module is the org's own back office: one private surface
that says what to do next and keeps the records the IRS, the Minnesota AG,
and funders ask for.

## Scope

**Does:**
- MN + federal formation roadmap: phased steps with per-step sources and
  verify dates, cost paths (DIY mail/online, full 1023, paid service, fiscal
  sponsorship).
- Compliance calendar computed from profile + ledger: MN annual renewal,
  IRS 990 class (N/EZ/full), 990-T at $1,000 UBI, AG annual report + audit
  threshold, 1023-EZ 27-month retroactivity deadline, AG registration
  trigger at $25,000 contributions, yearly board meeting, payroll forms
  when `has_employees`, custom deadlines, mark-filed records.
- Governance: board roster, quorum/notice/motion checks (Minn. Stat. ch.
  317A), agendas, minutes drafts, unanimous written actions.
- Policies: bylaws, COI, whistleblower, document retention, gift
  acceptance, financial controls — outlines + adoption status.
- Books of record: income/expense ledger in integer cents, IRS 990
  revenue categories + functional expense classes, restricted-fund
  tagging, fiscal-year summaries, donor acknowledgment letters ($250+ /
  quid-pro-quo $75+), CSV export.
- Grant readiness: 11-item checklist computed from live org state.
- Knowledge layer: every rule carries `source_ids` resolved to labeled
  statutes/IRS pages with `verified` flags and verify dates.

**Does NOT:**
- No tenant data — `exec_*` tables are org-level records only.
- No legal advice — content is organizational guidance for Semptify's own
  entity; unverified items carry `verified=False` and a confirm-on-source note.
- No filing/submission to any agency — it tracks and drafts, a human files.
- No grant-application tracking (that lives in Funding Forge — the
  readiness API points there).

## Roles

Admin only — `requires_role=("admin",)` in the manifest; not in
`CAPABILITY_DEFAULTS` for any role (admin gets `__all__`). Every route
requires the TOTP-verified admin elevation cookie or a valid admin token;
page `GET /` redirects to `/admin/login` otherwise, API answers 404.
`DEPLOY_TARGET=render_mvp` allow-lists it so it lives privately on
semptify.org (Brad, 2026-11-08).

## DB tables (Alembic `20261108_executive_admin`, revises `20261026_voice_posts`)

- `exec_ledger_entries` — one row per money movement (date, kind,
  amount_cents, 990 category, functional class, fund, counterparty,
  goods/services value, acknowledgment date, reference).
- `exec_records` — one JSON document per record keyed by `kind`:
  profile, step status, board member, meeting, written action, policy
  status, filed obligation, custom deadline.

## API endpoints

| Method + path | Purpose |
| --- | --- |
| `GET /admin/executive/` | Single-page admin UI (elevation → page; else → `/admin/login`) |
| `GET /admin/executive/health` | Module health ping |
| `GET /admin/executive/api/overview` | Objective, next action, warnings, progress, FY summary, readiness |
| `GET /admin/executive/api/knowledge` | Full sourced rules bundle (steps, costs, policies, agendas, categories, sources) |
| `GET|PUT /admin/executive/api/profile` | Org profile record |
| `PUT /admin/executive/api/steps/{id}` | Formation step status |
| `GET /admin/executive/api/calendar` | Computed obligation list |
| `POST /admin/executive/api/calendar/{id}/done` | Mark an obligation filed |
| `POST|DELETE /admin/executive/api/deadlines[/{id}]` | Custom deadlines |
| `GET|POST|PUT|DELETE /admin/executive/api/board[/{id}]` | Board roster |
| `GET|POST|PUT /admin/executive/api/meetings[/{id}]` | Meetings with compliance checks |
| `GET /admin/executive/api/meetings/{id}/agenda` | Draft agenda |
| `GET /admin/executive/api/meetings/{id}/minutes` | Draft minutes (plain text) |
| `GET|POST|PUT /admin/executive/api/written-actions[/{id}]` | Written actions + unanimity check |
| `GET /admin/executive/api/policies`; `PUT .../policies/{id}` | Policy list + status |
| `GET|POST|PUT|DELETE /admin/executive/api/ledger[/{id}]` | Ledger entries |
| `GET /admin/executive/api/ledger/summary` | Fiscal-year summary + 1023-EZ check |
| `GET /admin/executive/api/ledger/export.csv` | CSV export of the books |
| `GET /admin/executive/api/ledger/{id}/acknowledgment` | Donor acknowledgment letter |
| `GET /admin/executive/api/grant-readiness` | Readiness checklist |

## Dependencies

- `app.core.database` (`Base`, `get_db`) — SQLAlchemy async, shared Base.
- `app.core.admin_elevation` — elevation cookie verify.
- `app.core.security` — admin token + rate limiter (scripted access).
- `app.core.navigation` — `admin_login` stage for the unauthenticated redirect (SSOT).
- `app.core.config.get_settings` — admin rate-limit settings.
- Internal: `knowledge` (sourced rules), `compliance` (date/threshold math),
  `governance` (quorum/notice/votes), `ledger` (summaries/letters/CSV),
  `models` (tables).

## Capability tier

DEV tier, `lifecycle="dev_only"`, `requires_role=("admin",)` — plus an
explicit entry in `get_mvp_allowed_modules()` for the Render MVP build.

## Risk

- Wrong statutory content → mitigated by per-item `source_ids`, `verified`
  flags, and `VERIFIED_ON`/`FEES_VERIFIED_ON` dates in `knowledge.py`;
  unverified items say so on screen.
- Admin surface exposure → double-gated: storage middleware (session) +
  route-level elevation/token check returning 404; module health check
  verifies no unguarded public routes.
- Org financial data in Postgres → org records only, no tenant PII; table
  names and model docstrings make the boundary explicit.
