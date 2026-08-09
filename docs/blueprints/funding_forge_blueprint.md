# Funding Forge — Semptify Funding & Contact Manager

**Status:** APPROVED — approved 2026-07-25 (project owner request: build the GUI, contact manager, and full application process for all suggested funding entities)

**Type:** Standalone Add-on (can be mounted or run independently)

**Module path:** `funding_forge` (top-level package, not `app.modules`)

---

## Problem it solves

Semptify needs sustainable, mission-aligned funding, but the founder is solo and has no budget. There are dozens of potential funding channels (fiscal sponsors, crowdfunding platforms, foundations, grants, pro bono legal clinics, tech-for-good programs, local housing nonprofits, media outlets), each with its own contacts, deadlines, requirements, and follow-ups. Without a system, opportunities are forgotten, follow-ups fall through, and the nonprofit filing/funding pipeline stalls. Funding Forge is an ACT!-style contact and opportunity manager built specifically to track funding entities, their contacts, application processes, interactions, tasks, and documents in one calm, private, non-commercial workspace.

## Scope

### What it does

- Stores funding entities (funders, sponsors, platforms, clinics, orgs, media, etc.) with type, status, website, mission/focus, and notes.
- Stores contacts (people at those entities) with role, email, phone, and relationship status.
- Tracks opportunities / applications with stage pipeline, amount, deadline, and outcome.
- Tracks interactions (calls, emails, meetings, tasks, notes) linked to contacts and opportunities.
- Tracks tasks/reminders with due dates and completion status.
- Stores uploaded documents (applications, bylaws, letters, pitch decks) linked to funders/opportunities/contacts.
- Sends and records emails to contacts via Resend or SMTP, linked to contacts and opportunities.
- Provides a simple dashboard and list views for funders, contacts, opportunities, tasks, and interactions.
- Provides create/edit forms and detail pages for every entity.
- Exposes a JSON API for future automation.
- Ships with a pre-seeded catalog of suggested funding entities derived from the Semptify funding strategy.

### What it does NOT do

- Does NOT collect tenant data or connect to Semptify tenant accounts.
- Does NOT display ads, affiliate links, sponsored listings, or paid endorsements.
- Does NOT send SMS.
- Does NOT replace legal, accounting, or nonprofit filing advice.
- Does NOT integrate with tenant cloud storage auth.
- Does NOT store tenant PII; Funding Forge data is admin/system data only.

## User-facing or internal

Internal tool for Semptify administrators/fundraisers only. No tenant-facing pages.

## Roles

Admin-only access. Authentication uses username/password (with optional TOTP) from `FUNDING_FORGE_ADMIN_*` or the main Semptify `ADMIN_*` environment variables. After sign-in the browser receives a signed `funding_forge_admin` cookie and API clients may use the `x-admin-token` header.

## DB tables

- `funders` — funding entities
- `contacts` — people associated with funders
- `opportunities` — grants, sponsorships, campaigns, etc.
- `opportunity_steps` — checklist/steps inside an application process
- `interactions` — calls, emails, meetings, notes, tasks
- `tasks` — standalone or linked reminders
- `documents` — uploaded files and their metadata (storage type + storage key)
- `email_messages` — sent/drafted emails linked to contacts and opportunities
- `settings` — workspace state such as seed timestamp

## Routes

All routes are under `/` (server-rendered) and `/api` (JSON).

| Method | Path | Purpose |
| -------- | ------ | --------- |
| GET | `/` | SPA shell (redirects to `/login` when not authenticated) |
| GET | `/login` | Admin sign-in page |
| POST | `/login` | Admin sign-in |
| GET | `/logout` | Clear admin session |
| GET | `/funders` | List funding entities |
| GET | `/funders/new` | New funder form |
| GET | `/funders/{id}` | Funder detail |
| GET | `/funders/{id}/edit` | Edit funder form |
| GET | `/contacts` | List contacts |
| GET | `/contacts/new` | New contact form |
| GET | `/contacts/{id}` | Contact detail |
| GET | `/contacts/{id}/edit` | Edit contact form |
| GET | `/opportunities` | List opportunities |
| GET | `/opportunities/new` | New opportunity form |
| GET | `/opportunities/{id}` | Opportunity detail with steps/interactions |
| GET | `/opportunities/{id}/edit` | Edit opportunity form |
| GET | `/interactions` | List recent interactions |
| GET | `/tasks` | Task/reminder list |
| GET | `/documents` | Document list |
| GET | `/emails` | Email list |
| GET | `/emails/new` | Compose email form |
| GET | `/emails/{id}` | Email detail |
| GET | `/emails/{id}/edit` | Edit draft email |
| POST | `/api/funders` | Create funder |
| GET | `/api/funders` | List funders |
| GET | `/api/funders/{id}` | Get funder |
| PUT | `/api/funders/{id}` | Update funder |
| DELETE | `/api/funders/{id}` | Delete funder |
| POST | `/api/contacts` | Create contact |
| GET | `/api/contacts` | List contacts |
| GET | `/api/contacts/{id}` | Get contact |
| PUT | `/api/contacts/{id}` | Update contact |
| DELETE | `/api/contacts/{id}` | Delete contact |
| POST | `/api/opportunities` | Create opportunity |
| GET | `/api/opportunities` | List opportunities |
| GET | `/api/opportunities/{id}` | Get opportunity |
| PUT | `/api/opportunities/{id}` | Update opportunity |
| DELETE | `/api/opportunities/{id}` | Delete opportunity |
| POST | `/api/opportunities/{id}/steps` | Add application step |
| PUT | `/api/opportunities/{id}/steps/{step_id}` | Update step |
| DELETE | `/api/opportunities/{id}/steps/{step_id}` | Delete step |
| POST | `/api/interactions` | Create interaction |
| GET | `/api/interactions` | List interactions |
| PUT | `/api/interactions/{id}` | Update interaction |
| DELETE | `/api/interactions/{id}` | Delete interaction |
| POST | `/api/tasks` | Create task |
| GET | `/api/tasks` | List tasks |
| PUT | `/api/tasks/{id}` | Update task |
| DELETE | `/api/tasks/{id}` | Delete task |
| POST | `/api/documents` | Upload document |
| GET | `/api/documents` | List documents |
| GET | `/api/documents/{id}` | Download document |
| DELETE | `/api/documents/{id}` | Delete document |
| GET | `/api/emails` | List emails |
| POST | `/api/emails` | Send/create email |
| GET | `/api/emails/{id}` | Get email |
| PUT | `/api/emails/{id}` | Update email draft |
| DELETE | `/api/emails/{id}` | Delete email |
| POST | `/api/seed` | Reset and seed suggested entities |
| GET | `/api/admin/me` | Admin session check |
| GET | `/api/health` | Health check |

## Dependencies

- FastAPI
- Uvicorn
- SQLAlchemy 2.x (async) + aiosqlite
- Jinja2
- aiofiles (for file uploads)
- python-multipart
- Pydantic
- pyotp (optional TOTP support)
- aioboto3 (only when using R2 storage)
- httpx (only when using Resend email)
- Semptify design system CSS reused from `static/css/ssot-design-system.css` where possible, but no runtime dependency on `app` packages.

## Data flow

- Admin opens Funding Forge in browser.
- Browser submits server-rendered forms or JSON to FastAPI endpoints.
- SQLite database stores all records locally.
- File uploads go to the configured storage backend (`local` or `r2`).
  - `local`: `funding_forge/uploads/`
  - `r2`: Cloudflare R2 bucket under `funding_forge/<uuid>` keys
- Emails are sent via Resend API or SMTP when configured; otherwise saved as drafts.
- Pre-seed catalog populates funders and contacts from a bundled JSON file.

## What it does NOT touch

- `app/modules/*` tenant modules
- `app/core/*` Semptify core
- `app/main.py`
- Tenant cloud storage auth
- Semptify product manifest

## Capability tier

ADMIN / internal tool. Not exposed to tenant or advocate roles.

## Risk

- **Wrong scope creep:** could become a generic CRM. Mitigation: keep language and workflow focused on funding and nonprofit filing.
- **Data loss:** single SQLite file. Mitigation: include export button, document local backup path, and optional R2 document persistence.
- **Security:** internal tool with admin credentials. Mitigation: credentials from environment, signed admin token cookie/header, optional TOTP, no external network calls, no tenant PII.
- **Dependency drift:** standalone package must not introduce Python 3.12+ requirements. Mitigation: target 3.11.9, use same versioned dependencies as Semptify.

## Implementation

- Code: `funding_forge/__init__.py`, `auth.py`, `config.py`, `database.py`, `models.py`, `schemas.py`, `crud.py`, `api.py`, `storage.py`, `r2_client.py`, `email.py`, `main.py`, `seed_data.json`.
- GUI: `funding_forge/templates/index.html` and `login.html` plus `funding_forge/static/css/funding_forge.css` and `funding_forge/static/js/app.js`.
- Startup: `start_funding_forge.ps1` and `start_funding_forge.bat`.
- Tests: `funding_forge/tests/test_funding_forge.py`.
- Verification: `py_compile`, `ruff check`, `pytest` (5/5 passing), and a local uvicorn health + admin login + seed smoke test.
