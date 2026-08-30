# BACKLOG — Semptify Running Idea & Status Index

**Purpose:** Single running list so nothing discussed gets forgotten. Every idea, gap, or proposed feature gets at least one line here, at whatever stage it's actually at. Update this at the end of every session where something new comes up — same discipline as the `BUILD_STATE.md` close-out entry.

**State-doc map:**

- `BUILD_STATE.md` — what shipped, current build status, and known broken/pending.
- `ACTIVE_CONTEXT.md` — what is being worked on right now and open decisions.
- `BACKLOG.md` — new ideas, gaps, parked items, and future work at whatever stage it is in.

**Status tags:** `[considering]` → `[evaluated]` (passed scope/responsibility review) → `[accepted]` (has an ADR) → `[building]` → `[done]` → `[watching, not building]` → `[rejected]`

---

## Active / in progress

- `[building]` Fact-check / freshness system — ADR-0009 (Proposed). Phase A–D merged (PRs #90–#93). Confirmed separate from ADR-0008 per recap. Next: Phase B content-level verifier in production use. See `BUILD_STATE.md` for the close-out.
- `[considering]` Expand Information Orchestrator (ADR-0008) beyond pilot surfaces — see "New ideas" below.

## Landing page gap analysis

- `[considering]` Who Owns My Building — highest-leverage per research; check overlap with existing External Mappings module before evaluation. **Next Tier 1 item to run through scope/responsibility evaluation.**
- `[considering]` Habitability Rent-Abatement Calculator — Tier 1.
- `[considering]` Housing Discrimination Recorder — Tier 1.
- `[considering]` Algorithmic Screening Denial Assistant — Tier 2.
- `[considering]` Rent Increase Context Tool — Tier 2.
- `[considering]` Cross-Tenant Pattern Signal — Tier 2. **Do not evaluate via standard process — requires dedicated privacy-engineering review first per scope-evaluation checklist §3.**
- `[watching, not building]` Landlord surveillance-tech database — duplicates Anti-Eviction Mapping Project's existing work.
- `[watching, not building]` Proprietary eviction e-filing court integration — needs a court partnership Semptify doesn't have yet.
- `[done]` Landing page rebuild (fact-forward, typography-led concept, replacing "comforts of home") — planning complete, execution not yet started. Awaiting Brad's go + Phase 1 sourcing audit.

## Parked, needs a specific human/agent action

- `[considering]` `phase2-1a1341-055` — `services/eviction/case_builder` legal-output changes — **needs Brad's manual legal review**, not agent-actionable.
- `[considering]` `local/markdown-lint-pass` — 278-file lint pass, still unpushed, undecided (push+PR vs. merge vs. discard).

## Guardrail / build-hygiene backlog

- `[accepted]` **Add post-`create_app()` route scan for ad-hoc public routes.**
  Context: `/debug/*` routes were registered directly on `fastapi_app` in `app/main.py` and were invisible to `contract_route_check.py`, which only inspects module routers with `FunctionGroupContract`. `PUBLIC_PREFIXES` in `storage_middleware.py` is a runtime allowlist, not a build-time guardrail.
  Scope: after `create_app()` is called in the guardrail engine, walk `fastapi_app.routes` and flag any route whose path starts with an entry in `PUBLIC_PREFIXES` but is not in a registered module contract. This closes the gap that let `/debug/seed-test-user` become reachable without storage auth.
  Not urgent for the current handoff; do not build before CASE_DATA migration is complete.

## Security architecture — future work

- `[considering]` **Four-piece vault unlock scheme (Brad, 2026-08-26).** Not yet specced or implemented — recorded here so the shape isn't lost before it's ready to build.
  Concept: opening the vault requires four pieces combining in one specific order, at one instant:
  1. **Semptify's piece** — held server-side.
  2. **Provider's piece** — the OAuth-level connection/grant itself, held by the storage provider (Google Drive / Dropbox / OneDrive).
  3. **User's piece** — physically stored *inside the user's own cloud storage/vault*, but invisible to the user — they never see it, open it, or know it exists.
  4. **The fourth piece** — holds/stores nothing on its own, exists nowhere at rest. It is a *creation event*: the instant pieces 1–3 combine correctly, it creates the actual unlock key, completes its one job, and vanishes. Nothing to capture, because it never contained anything to begin with.
  Why it matters: no single party — not Semptify, not the provider, not the user, not any fourth store — ever holds the complete key at rest. The key exists only for an instant, in motion, when all three real pieces align. This extends the existing storage-as-identity model (see `docs/process_contracts/user_reconnect_v2.md`, `SECURITY_AND_PRIVACY_ARCHITECTURE.md`) one layer deeper: today the DB holds an encrypted OAuth token; this scheme would mean no persistent store anywhere holds a complete, usable key at all.
  Needs before building: a real spec (exact derivation order, what piece 4's creation function actually is, key-rotation/reconnect implications given piece 3 lives inside the user's own storage, and how this interacts with the existing `_derive_key(user_id, secret_key)` / AES-256-GCM token encryption already in `app/sdk/vault/encryption.py` and `app/core/auto_refresh.py`).

- `[considering]` **Versioned `SECRET_KEY` rotation for OAuth tokens (`ad-hoc-secretkey-rotation-2026-08-27`, resolved as design 2026-08-29).** Investigation-only; no token code changed.
  Context: full findings and a recommended approach are in `C:\master-repo\handoffs\ad-hoc-secretkey-rotation-2026-08-27-report.md`. The design adds a `sessions.key_version` column and a `SECRET_KEY_HISTORY` env/secret list, with lazy re-encryption on the next provider refresh and a defined grace period before old keys are removed.
  Why it matters: today a single `SECRET_KEY` change instantly invalidates every stored session and signed cookie, forcing all tenants through OAuth reconnect. A versioned scheme keeps Semptify's storage-as-identity model intact and requires no tenant action unless their token is stale.
  Needs before building: Brad's sign-off on the open design questions in the report (cookie HMAC versioning, grace period, `SECRET_KEY_HISTORY` storage, Alembic migration approach, one-shot bulk re-encryption job). The implementation must also reconcile the duplicate `_derive_key` in `app/modules/storage/router.py` and note that `app/sdk/vault/encryption.py` uses a separate key derivation (`:token:` salt) not covered by this scheme.

## New ideas / considering

- `[considering]` **Expand Information Orchestrator (ADR-0008) beyond pilot surfaces.**
  Context: the ADR-0008 recap found that most named components — Object Context Envelope, Page Envelope, Momentum/Emotional Checkpoints, Experience Token (read path) — are built and wired, but *only* for the two original pilot surfaces (Eviction Timeline, Vault upload flow). Several pieces are built but not wired at all: Three-Layer Retrieval Layer 3, Familiarity Tapering, Experience Token's save path. Live Event-Driven Narration was never built. The ADR itself states full-platform rollout was always meant to be a separate future decision — this is not a bug, it's an intentionally deferred scope boundary.
  Why it matters: right now, tenants using any page outside Eviction Timeline/Vault get none of the context-aware explanation system Semptify already built and paid the engineering cost for. That's real, already-built value sitting unused on most of the platform.
  Not yet evaluated. Needs to go through the scope & responsibility evaluation process before becoming a real ADR-0008 Phase 2 or its own handoff. Rough scope questions to answer during that evaluation: which additional pages/surfaces first, does Familiarity Tapering and the Experience Token save-path get wired as part of this or deferred further, and whether Live Event-Driven Narration (never built) is in scope for "expansion" or is really a separate net-new build.

- `[considering]` **Client-side plugin architecture design spec (`plugin-arch-design-spec-2026-08-28`, review 2026-08-29).** Design for browser extension, desktop app, and local script plugins that connect to Core via per-endpoint scoped tokens and zero-transfer document access. Spec at `C:\master-repo\handoffs\plugin-architecture-design-spec-2026-08-28-report.md`.
  Context: plugins run on the user's own machine, use existing storage-as-identity, never receive full tenant access, and never route document bytes through Core. Plugin directory location and build order (reference plugin vs API first) are explicitly open.
  Why it matters: lets the Semptify ecosystem extend without putting tenant documents on Semptify servers, in line with the no-PII / no-data-platform stance.
  Needs before building: Brad's decisions on directory location and build order; a separate prototype repo per the open `plugin-arch-repo-proposal-2026-08-28` task; no implementation should start until those are answered.

- `[considering]` **Plugin prototype repo proposal (`plugin-arch-repo-proposal-2026-08-28`, review 2026-08-29).** Proposed repo name and initial structure for the client-side plugin prototype.
  Context: repo should be decoupled from Semptify, mirroring the PMAS pattern: separate `1semptify-arch` repo, `apps.yaml` source of truth, standalone `mock_core/`, `browser_extension/`, `desktop_app/`, `local_script/`, and `plugin_api_spec/`. No code, credentials, or database shared with Semptify. Proposal at `C:\master-repo\handoffs\plugin-arch-repo-proposal-2026-08-28-report.md`.
  Why it matters: keeps the high-risk plugin build isolated from `master-repo` and the open ADR-0008 merge reconciliation, while giving reference implementations a place to live.
  Needs before building: Brad's explicit go-ahead to create the repo; the design spec (`plugin-arch-design-spec-2026-08-28`) to be accepted/resolved; and resolution of the directory/build-order open decisions.

## Recently closed

PRs #69–#93, the root-cause `protect-main` ruleset fix, and the Phase C/D fact-check/freshness close-out are recorded in `BUILD_STATE.md` and `ACTIVE_CONTEXT.md`. This section is intentionally brief; the canonical close-out lives in the state docs.
