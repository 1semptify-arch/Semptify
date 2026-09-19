# Transparency Feed Blueprint

**Status:** DRAFT — pending approval
**Module path:** `app.modules.transparency.router`
**Type:** Feature
**Pillar:** GOVERN
**Tier:** DEV
**Lifecycle:** dev_only
**Date:** 2026-09-19

## Problem

There is no way to watch what the running system is actually doing. Logs exist
(`RequestLoggingMiddleware`, `EventBus` history) but are not narrated, not live,
and not viewable anywhere. Brad asked for total runtime transparency — the live
backend and frontend narrating themselves in plain English as they run — for
user understanding and verification. This is also the groundwork for any future
tenant-facing transparency surface (extends ADR-0008 §2.3, which already accepts
"real backend events narrated live" as an approved pattern).

## Scope

Does:

- Provide an in-process `TransparencyFeed` — a bounded ring buffer (500 entries)
  of plain-English narration entries `{ts, source, level, text, request_id}`.
  In-memory only. No database, no disk writes.
- Emit narration at request-lifecycle checkpoints via a dedicated
  `TransparencyNarrationMiddleware` (request arrived → response sent with status
  and duration → error). Registered in `app/main.py` only when the feature is
  enabled; default state adds zero overhead.
- Mirror existing domain events from `EventBus` into the feed, reusing their
  already-resolved narration text where present (NARRATION_MESSAGES /
  contract narrator slots).
- Accept frontend echoes: a small browser script posts plain-English lines
  about what the client is doing (page loaded, fetch completed, narration
  received, JS error) so both sides narrate into one feed.
- Render a live view page `/transparency` (admin-only) streaming entries via
  SSE, with an initial history snapshot. Chronological order per the GUI rule.
- Provide a public `narrate()` API for future instrumentation of any code path
  (declared as a FunctionGroupContract so callers never invent the signature).
- Kill switch + verbosity: `TRANSPARENCY_FEED` env — `off` (default) |
  `summary` | `detailed`. `off` short-circuits everything.

Does NOT:

- Log every executed line of code (technically infeasible and unreadable —
  narrates meaningful checkpoints only).
- Store anything. No PII, no user IDs, no IPs, no query strings, no request
  bodies — T0 operational data only. Path parameters that look like tokens or
  IDs are masked before narrating.
- Change any tenant-facing page, flow, or narration-strip behavior.
- Touch `app/modules/onboarding/` (NO-TOUCH).
- Ship to production users — DEV tier keeps it off Render entirely until a
  separate promotion decision is made.

## Roles & capability defaults

Admin/dev only. No `CAPABILITY_DEFAULTS` entries (admins receive `__all__`).
Page + API additionally gated by `require_admin`.

## DB tables

None. PII boundary: nothing persisted anywhere; entries are T0 operational
metadata (method, normalized path, status, duration, event names).

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /api/transparency/health | Module health check |
| GET | /api/transparency/feed | JSON snapshot of recent entries (`since` cursor) |
| GET | /api/transparency/stream | SSE live stream of new entries |
| POST | /api/transparency/echo | Accept one narrated line from a browser client |
| GET | /transparency | Live transparency view page (`require_admin`) |

## Dependencies

- `app.core.event_bus` — subscribes to existing `EventType`s for mirroring
  (read-only; does not publish into the bus).
- `app.core.narrator.resolve_narration` — reuse contract narration resolution.
- `app.core.utc.utc_now` — timestamps.
- `app.core.security.require_admin` — page/API gating.
- `app.core.config.get_settings` — `TRANSPARENCY_FEED` flag.

New contract registered: `transparency::transparency_emit` (emit a narrated
line into the feed; inputs: `text`, `source?`, `level?`, `request_id?`;
output: `accepted`).

## Files

- `app/modules/transparency/` — `__init__.py`, `feed.py`, `middleware.py`,
  `router.py`, `register.py`, `module_contract.json`, `README.md`
- `app/templates/pages/transparency_feed.html` — live view (shell--solo)
- `static/js/transparency_feed.js` — EventSource renderer
- `static/js/transparency_echo.js` — opt-in browser narrator (loaded only when
  enabled, via `shell_base.html` conditional)
- `app/core/config.py` — `transparency_feed` setting
- `app/main.py` — conditional middleware registration + Jinja global
- `app/core/product_manifest.py` — one `_register(...)` line, DEV tier

## Risk

- **Overhead:** emit = string + deque append ≈ microseconds; no DB/disk I/O.
  Middleware no-ops when flag is `off` (single settings check per request).
  Main risk — narrating inside hot loops — is a documented rule: narrate once
  per operation, never per iteration.
- **PII leak:** mitigated by never narrating query strings, bodies, IPs, user
  IDs, or token-like path segments; DEV tier means it never runs in prod.
- **SSE connections:** bounded subscribers; disconnect cleans up queue.
- **UPL risk:** none — operational narration, no legal content.
- **fees_policy:** exempt_advanced irrelevant — admin/dev only, no "fee" text.

## Verification plan

- `python -m py_compile` on all changed/new files
- `pytest tests/module_health -q --no-cov` (module health suite incl. new module)
- `python tools/guardrail_engine.py` — all checks pass
- Live check on `:8001` (venv311): enable flag → `GET /transparency` 200 →
  exercise app pages → entries stream in real time via SSE → IronBee
  backend `request_http` + log evidence; flag off → feed endpoints still
  respond, zero entries emitted
