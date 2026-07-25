# Funding Forge

A standalone funding and contact manager for Semptify.

Built to track funding entities, contacts, grant/application pipelines, interactions, tasks, and documents in one calm, private, non-commercial workspace.

## Quick start

1. Ensure Python 3.11.9 and the Semptify `venv311` environment exist in the repo root.
2. Copy the environment template:
   ```powershell
   Copy-Item .env.template .env
   ```
3. Edit `.env` and set `FUNDING_FORGE_ADMIN_USERNAME` and `FUNDING_FORGE_ADMIN_PASSWORD`.
4. (Optional) Add Cloudflare R2 credentials and set `FUNDING_FORGE_STORAGE_BACKEND=r2` to persist uploads in R2.
5. Run:
   ```powershell
   .\start_funding_forge.ps1
   ```
6. Open http://127.0.0.1:8001 and sign in with the admin credentials.

## Features

- **Admin-only access** — username/password (and optional TOTP) gate. Falls back to `ADMIN_USERNAME`/`ADMIN_PASSWORD` so it can reuse the same admin credentials as the main Semptify app.
- **Funders** — organizations, platforms, foundations, clinics, media, and partners.
- **Contacts** — people at those entities with role, email, phone, and status.
- **Opportunities** — grants, fiscal sponsorships, crowdfunding campaigns, etc.
- **Application steps** — per-opportunity checklist with status and due dates.
- **Interactions** — calls, emails, meetings, notes tied to contacts and opportunities.
- **Tasks** — reminders linked to any record type.
- **Documents** — file uploads linked to opportunities or other records.
- **Persistent storage** — documents can be stored on Cloudflare R2 system storage instead of the local filesystem.
- **Seed catalog** — one-click load of suggested funding entities.

## API

All data is available under `/api`. See `/api/docs` for interactive documentation when running.

Programmatic access uses the admin token cookie or the `x-admin-token` header.

## Notes

- This is an internal admin tool, not a tenant-facing feature.
- No ads, no tracking, no endorsements — only neutral listings.
- No email or payment processing is performed.
- Funding Forge data is admin/system data and does not contain tenant PII.
