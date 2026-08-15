# HANDOFF: Incorporate Fact-Check/Freshness System Into Standing Build Guides

**Why this exists:** The fact-check/freshness build plan (`HANDOFF_factcheck_freshness_buildnow.md`) specs the work itself. This handoff makes sure that work becomes a permanent, documented part of how Semptify is built and governed — not a one-off feature that lives only in a handoff doc and gets forgotten. Every doc listed below needs a specific, small addition. Do not skip any — a system this important to Information Integrity needs to be discoverable from every place a future agent or human would look for it.

---

## 1. ADR — write a new one, don't bury this in an existing ADR

Create `ADR-00XX-fact-check-freshness-system.md` (next available number) following the existing ADR format (see ADR-0008 as the template). Contents:

- **Context**: landing page rebuild required a sourced hero fact strip; audit found two partial, unscheduled systems (Context Engine Verifier, Data Freshness Manager) with no content-level supersession detection; a real drift was caught during this session (Calder-Wang/Kim study revised $25→$53/month between versions) before it shipped.
- **Decision**: extend existing `ContextFact` model + verifier + freshness manager rather than build a third system. Content-level comparison (not just link-liveness) is the core new capability. Scheduled via Render cron, not left as dead code.
- **Consequences**: landing page and future public-facing claims are now live-verified, not hardcoded. Adds a small maintenance surface (per-claim extraction patterns need updating if source pages restructure). Alerting must handle "couldn't verify" as its own state, never silently pass.
- **Status**: mark `Accepted` once Phase A–D of the build plan is merged; `Proposed` until then.
- **Link back** to `HANDOFF_factcheck_freshness_buildnow.md` for the phased implementation plan — the ADR is the permanent record of *why*, the handoff is the *how*.

---

## 2. AI_TEAM_OPERATING_PROTOCOL.md — add an operating rule

Add a short section (near wherever other standing system rules live, e.g. next to the `main` branch-protection note added in the last close-out):

> **Public-facing factual claims (landing page, marketing copy, hero stats) must be sourced through the fact-check/freshness system (ADR-00XX), never hardcoded.** Any new numeric or factual claim added to a public page requires: (1) a `ContextFact` row with `subject="landing"`, real `source_url` and `canonical_value`, (2) inclusion in the scheduled freshness check, (3) a citation/footnote rendered from the same data. No agent should hardcode a statistic into landing/marketing HTML going forward — this is how the Calder-Wang/Kim drift almost happened once and won't be allowed to happen silently again.

This makes it a binding rule for every future agent session, not just something this session happened to catch.

---

## 3. Information Integrity Standards doc (wherever "sourced, freshness-checked, opinion labeled" is currently documented — likely in the Motivations/standards doc referenced in memory)

Add: "Freshness-checked" is no longer aspirational language — link directly to ADR-00XX and state that as of [date], public-facing numeric claims are mechanically checked, not just policy-stated. If the existing doc has a "how this is enforced" gap (policy stated but no system behind it), close that gap explicitly here.

---

## 4. Build Bible — add this as a worked example

The Build Bible standard ("no band-aids, fix root causes") gets referenced a lot in this project's history but is mostly invoked reactively. Add this effort as a **positive worked example**: "landing page needed a stat → root cause was 'no system to keep any public claim current' → fixed the system, not just the stat" — a concrete illustration future sessions can point to when deciding whether they're patching a symptom or fixing a cause.

---

## 5. ACTIVE_CONTEXT.md / BUILD_STATE.md — standard close-out entry once built

Once Phases A–D are merged (per the build-plan handoff), add the standard session close-out entry, same pattern as every prior close-out in this project:
- What shipped (Phase A–D complete, landing page live-wired).
- What's deferred (Phase E admin panel, if not done same session; the five other stubbed `refresh_*` functions, explicitly noted as separate future work, not silently forgotten).
- The auto-hide vs. last-known-value decision (Brad's call, from the build-plan handoff section 6) — record whichever was chosen and why, so it's not re-litigated later.

---

## 6. Product manifest / tier registry (`product_manifest.py`)

Per the earlier audit: `data_freshness` is currently registered under `ProductTier.DEV`. Once this becomes load-bearing for a public page (the landing page), promote it to `ProductTier.CORE` alongside `context_engine` and `resource_directory` — a DEV-tier module shouldn't be the thing verifying what's shown to every visitor. Small change, but easy to forget since it's a one-line tier flag, not a feature — call it out explicitly so it doesn't get lost inside the larger Phase C work.

---

## 7. README / onboarding docs, if any exist for new contributors or agents

If there's a top-level "how Semptify is built" doc (README.md, CONTRIBUTING.md, or an onboarding doc referenced elsewhere), add one line pointing to ADR-00XX under whatever section covers data integrity / content standards — so a new agent or contributor encounters this rule early, not only if they happen to read AI_TEAM_OPERATING_PROTOCOL.md in full.

---

## 8. Sequencing — when to do this documentation pass

Do **not** wait until Phase A–D of the build plan are fully merged to start this. Split it:

- **Now (before/alongside Phase A):** write the ADR as `Proposed`, add the AI_TEAM_OPERATING_PROTOCOL.md rule, add the Information Integrity Standards link. These are cheap, and having the rule in place *before* the system is built means any other in-flight work (e.g., if another agent is touching landing/marketing copy concurrently) already knows not to hardcode claims.
- **After Phase D merges:** flip the ADR to `Accepted`, do the BUILD_STATE/ACTIVE_CONTEXT close-out entry, do the product manifest tier promotion, do the Build Bible worked-example addition.

---

## 9. Standing rules — apply throughout

- One task per commit. This documentation work can likely be 2 PRs (docs-now, docs-after-merge) rather than one per file — use judgment, but don't bundle doc changes into the same PR as the actual code changes from the build-plan handoff; keep them separable so a doc-only PR stays fast through CI (per the marker-split fix from earlier this session).
- `sync_orchestrator.py --check` after any PR touching tracker-adjacent files.
- Commit prefix `admin:`/`user:`/`help:`/`adr:` — the ADR-only commits should use the `adr:` prefix specifically, consistent with `ac1a9bf2 adr: Split CI Test job by markers` from earlier in this session.
