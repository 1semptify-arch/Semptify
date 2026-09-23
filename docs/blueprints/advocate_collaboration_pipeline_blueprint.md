# Advocate / Attorney Collaboration Pipeline Blueprint

**Status:** DRAFT — pending Brad approval
**Module path:** extends `app/modules/advocate/` (+ new `case_session` function groups)
**Type:** Feature pipeline (multi-stage)
**Pillar:** GOVERN (crosses into ACT for document handoff)
**Tier:** DEV first
**Date:** 2026-09-23

## Problem

A tenant's real need is not "share a file" — it is *getting someone qualified to
work their case*. Today Semptify has scattered pieces (advocate role, invite
codes, share links, annotations, packet export) but they are not a pipeline.
Brad's framing (2026-09-23): invite → share → review → talk it through → grant
permissions → engage → represent. Each step should be visible, permissioned,
and revocable by the tenant.

**Design ruling (Brad, 2026-09-23):** communications must be secure and solid —
"no glitching or we wait." Voice stays on the phone; Semptify provides live
shared document viewing instead of in-app conferencing. No video/voice stack
is to be shipped until it can be self-hosted, encrypted, and reliable — a
crappy insecure conference is worse than none.

## What already exists (reuse, do not rebuild)

- **Advocate module** — 12 function groups: client list/detail, case queue,
  intake, client timeline, document annotate/list-overlays/delete-annotation,
  invite codes, tenant link/list/revoke advocate (`app/modules/advocate/`).
- **External share links** — token-gated, expiring, access-tracked
  (`app/services/document_share_store.py`, `/api/dc/shared/{token}`).
- **Packet export** — merged document bundles (`case_builder/packet_export.py`).
- **Live push plumbing** — SSE pattern already proven (transparency feed
  blueprint); `EventBus` exists for session state.

## The pipeline (stages)

1. **Invite** — tenant generates invite (code or link) scoped to a case or the
   whole vault; invite states what the recipient will be able to see before
   they accept. Optional email delivery.
2. **Review** — recipient opens the case: shared packet + timeline + documents
   (annotation exists). Tenant sees "advocate is reviewing" status.
3. **Live session** — phone call for voice + **live co-viewing** in-app:
   both parties open the same document; host-driven page/scroll sync and a
   shared highlight pointer ("look at paragraph 3"). Session log records who
   attended, when, and which documents were viewed — never recordings, never
   message content.
4. **Engage** — explicit scope-of-help record: what the advocate may view and
   do, shown to the tenant in plain language; grant/revoke already exists —
   surface it per-scope, not all-or-nothing.
5. **Represent** — status marker on the case ("represented by X since DATE");
   final packet export for handoff. Actual legal work happens off-platform —
   Semptify is not the law firm and never practices law (UPL boundary holds).

## Live co-viewing (the chosen comms layer)

- Voice: phone call — out of scope deliberately; free, secure, works.
- Co-view: short-lived session token; host and guest on the same document;
  host pushes page/scroll position and highlight markers; guest follows live.
  SSE for state push (proven pattern); WebSocket only if SSE proves lacking.
- Security bar: TLS via Cloudflare, expiring single-purpose tokens, no
  third-party media servers, nothing recorded, full audit log of what was
  viewed and when.
- **Non-negotiable:** ships only when it works solidly. If co-view can't be
  made reliable, the stage waits — phone alone is an acceptable fallback.

## Does NOT (v1)

- No video or voice conferencing of any kind.
- No e-signature / retainer / engagement-letter machinery.
- No chat or message inbox.
- No attorney-specific privilege tooling beyond session logging.
- No changes to `app/modules/onboarding/` (NO-TOUCH module).

## Decisions parked for Brad

- [ ] Advocate vs. attorney: one role with a "barred attorney" flag, or two
      separate roles? (Privilege handling differs.)
- [ ] Co-view MVP: page-sync only, or live annotations too?
- [ ] Who can start a session — tenant only, or advocate can request?
- [ ] Invite delivery: codes only, or in-app email sending?
- [ ] Stage-5 "represent" — a label on the case, or a fuller status lifecycle?
- [ ] Naming: keep "advocate" as the umbrella term for helpers/lawyers?

## Build order (each slice ships independently, behind flags)

1. Invite delivery + "what you'll see" consent screen
2. Status pipeline (invited → reviewing → engaged) on existing advocate links
3. Live co-view session MVP (the flagship piece)
4. Representation marker + handoff export polish

## Compliance notes

- Semptify facilitates sharing and collaboration; it does not give legal
  advice and does not create attorney-client relationships. The pipeline
  *documents* a relationship the parties form themselves.
- Tenant owns the data end to end: every grant visible, every access logged,
  every permission revocable.
