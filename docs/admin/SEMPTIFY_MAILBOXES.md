# Semptify Mailbox Log

Register of every `@semptify.org` email address — what it is for, how it
routes, and its status. Ordered by Brad 2026-11-19 as the compensating
control when the literal Email Routing rules decision landed as "stay on
catch-all" (queue: task-1c672c11).

**Routing posture:** Cloudflare Email Routing on zone `3afd2a548023104ce9d29c4e65848209`.
There are **no literal per-address rules** — every address below works
because the zone catch-all forwards to `1semptify@gmail.com`. If the
catch-all is ever disabled, every row marked `catch-all` stops receiving
mail silently. That fragility is accepted for now; this log is the
record that makes a future migration possible.

## Addresses

| Address | Purpose | Routing | Status | Notes |
|---|---|---|---|---|
| `support@semptify.org` | User-facing support contact | catch-all → `1semptify@gmail.com` | live | `SUPPORT_EMAIL` default in `config.py` / `email_service.py`; `.env.example` aligned 2026-11-14 (0d5fd1c4) |
| `brad@semptify.org` | Brad personal/ops | catch-all → `1semptify@gmail.com` | live | was the stale `.env.example` default until the alignment commit |
| `partnerships@semptify.org` | Agency/nonprofit partnership contact | catch-all → `1semptify@gmail.com` | live | relies on catch-all — no literal rule |
| `press@semptify.org` | Press/media contact | catch-all → `1semptify@gmail.com` | live | relies on catch-all — no literal rule |

## Rules for this log

- **Every new `@semptify.org` address gets a row the day it is minted** —
  whether in Cloudflare, Render env, code defaults, or printed copy.
- When a literal routing rule replaces catch-all for an address, update
  its `Routing` column the same day.
- If the catch-all is ever disabled or repointed, update every affected
  row and note it in this header.
- Destination mailboxes are external — if `1semptify@gmail.com` ever
  changes, that is a header-level change for the whole table.
