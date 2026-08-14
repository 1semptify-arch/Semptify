# ADR-0008 — Information Orchestrator: Context-Aware, Non-Static Object & Page Explanation

**Status:** Accepted
**Date:** 2026-08-10 (rev. 4 — core pilot surfaces landed on main, 2026-08-14)
**Author:** Brad (via planning session), drafted by Claude
**ADR number confirmed:** the OCR/semantic-reasoning privacy model ADR is **ADR-0007**, not ADR-0002 as originally guessed — confirmed via todo-068 preflight (2026-08-10). Still verify 0008 itself is the correct next open slot before final commit.
**Implementation scope:** The pilot surfaces (Eviction Timeline and Vault upload flow) are now on `main` as of merge `7c5b5733` (PR #65, 2026-08-14). This includes Object/Page Envelopes, Layer 1/2 retrieval, Familiarity Tapering, Momentum Checkpoints, and the Experience Token for those two flows. Full-platform rollout beyond the two pilot surfaces remains a separate future decision.

**Rev. 3 changes:** Status moved to Accepted. Decision #6 resolved: `token_version: 1` as the default field on the Experience Token schema. See `agent_orchestrator_tasks.json` todo-063 through todo-075 for the implementation task queue.

---

## 1. Context

Every module currently declares objects (fields, blocks, buttons, module outputs) in terms of mechanics only — input type, output type, where it renders. Nothing in that declaration tells the system, or an agent building against it, **why the object exists, who it's for, or what the tenant needs to understand to make a good decision about it.**

The result today is either:
- No explanation at all (a bare button with no context), or
- Static, hardcoded copy that never adapts to who's looking at it, how many times they've seen it, or where they are in their own case

This violates the spirit of Information Integrity (MOTIVATIONS.md) and the Wisdom Principle — the goal isn't to arm tenants for a fight, it's to give them what they need, when they need it, in a form proportional to how well they already understand it.

This ADR defines the **Information Orchestrator**: a system that gives every object *and every page* in Semptify structured context, and resolves that context into live, right-sized explanation using retrieval rather than hardcoded text or live LLM generation — without ever tracking a tenant in a way that would fail the Navigation Principle's vocabulary check.

## 2. Decision

Seven components. 2.1 (Object Envelope) and 2.6 (Page Envelope) are the two foundational schemas everything else reads from. They are designed to be built incrementally — each is independently useful.

### 2.1 Context Envelope — per-object metadata

Every object that can carry explanation declares a small structured envelope alongside its data. This is metadata, not content — cheap to declare, no runtime cost.

| Field | Type | Purpose |
|---|---|---|
| `object_id` | string | Unique identifier for this object type |
| `object_type` | enum | `field` \| `block` \| `button` \| `module_output` \| `page_zone` |
| `pillar` | enum | `RECORD` \| `KNOW` \| `ACT` \| `GOVERN` — sets tone/framing |
| `journey_stage` | enum | `orientation` \| `decision` \| `action` \| `reflection` — computed live per tenant, not fixed per object (see 2.1.1) |
| `who` | enum | `tenant` \| `advocate` \| `agency` \| `researcher` \| `legal` \| `donor` |
| `why` | string | One-line rationale for the object's existence — used by the orchestrator to query, not shown verbatim to the user |
| `provenance` | enum | `user_entered` \| `ocr_extracted` \| `system_computed` \| `semantically_retrieved` |
| `temporal_validity` | enum | `static` \| `time_bound` \| `event_triggered` |
| `subject_tags` | list[string] | Free-text tags for semantic matching (e.g. `["late fee", "MN", "lease clause"]`) |

**2.1.1 — Journey stage is computed, not fixed.** The same object type (e.g. `eviction_notice_date`) starts in `orientation` the first time a tenant sees it, and moves to `decision` once a derived deadline exists. The orchestrator computes this per tenant, per encounter — it is not a static property of the object definition.

### 2.2 Three-Layer Retrieval — how explanation gets filled in without hardcoding or live generation

This is the mechanism that keeps content dynamic without either (a) writing every explanation by hand for every situation, or (b) running a live LLM that could hallucinate a fact — which would be a UPL risk given the existing risk-tier framework.

**Layer 1 — Curated entries (human-written, versioned).**
Short explanation blocks, each tagged with subject, jurisdiction, UPL risk tier, Pillar, and **`review_status: beta | vetted`**. Functionally an extension of the Know Your Rights Library, granular enough to attach to individual page objects rather than only top-level articles. Each entry has multiple **variant slots** (see 2.4) rather than one fixed text. `beta` entries are eligible for retrieval and display but should carry a lighter-weight disclosure than `vetted` Library-grade content until a formal review baseline exists (see section 5, #4).

**Layer 2 — Semantic retrieval (PILOT REVISION 2026-08-10 — see below).**
Original design: retrieve best-matching Layer 1 entries via embedding similarity (all-MiniLM-L6-v2, offline), reusing an existing OCR semantic pipeline. **That pipeline does not exist yet** — ADR-0007 specifies it but it was never implemented (confirmed via todo-068 preflight). For the pilot, Layer 2 is implemented as **metadata-only matching**: exact/scored match on `subject_tags`, jurisdiction, `pillar`, and `review_status`, with the confidence concept preserved as a named config constant (`LAYER2_CONFIDENCE_THRESHOLD = 0.75`) for later replacement with real semantic scoring. The retrieval *interface* (query in, ranked Layer 1 entries out) stays the same either way, so upgrading to real embeddings later is a drop-in swap, not a rewrite. Building the actual embedding pipeline is tracked separately as todo-077 (completes ADR-0007), decoupled from the pilot's critical path.

**Layer 3 — Bounded local rephrasing (optional).**
A small local model may adjust *tone or length only* — trimming for a mobile card vs. expanding for a full page. It is never permitted to introduce a new fact or claim not present in the Layer 1 source. The source entry remains the attributable origin for Information Integrity disclosure purposes.

**Guardrail:** Layer 3 output must always be traceable to a specific Layer 1 entry ID. If no Layer 1 entry matches well enough (confidence threshold), the orchestrator shows nothing rather than guessing — silence is safer than a fabricated explanation.

### 2.3 Live Event-Driven Narration

When an object represents a process in motion (e.g. a document scan, an overlay build), the explanation shown must be tied to **real backend events**, not a decorative timer. This rides the existing WebSocket Events module (`/ws`, already active in CORE tier).

Sequence example (document upload → overlay):
1. Upload received → *"Got your document — starting the scan now."*
2. OCR pass running → *"Reading the text and finding key dates."*
3. Overlay build starts → *"Building your privacy overlay — this happens on your device. We never see the file itself."*
4. Overlay complete → *"Done. Your document's organized and nothing left your device."*

**Guardrail:** Each narration line must be triggered by the actual corresponding backend event firing. A line describing a step that hasn't started yet is a fabricated status and is not permitted, regardless of how much it improves perceived responsiveness.

### 2.4 Familiarity Tapering

Explanation depth is a function of how many times a tenant has encountered that *object type* (not that specific instance).

| Exposure | Behavior |
|---|---|
| 1st | Full explanation — trust/why-forward (e.g. the overlay privacy line above) |
| 2nd–3rd | A **different** angle each time — mechanics, then brief reinforcement. Never a verbatim repeat. |
| 4th+ | Collapses to minimal — real-time status only. Full explanation available on tap, never forced. |

This requires each Layer 1 entry to have multiple variant slots (trust/why, mechanics, short reinforcement, minimal/status) — the orchestrator selects by variant tier, driven by exposure count (see 2.7 for where that count actually lives).

**Rationale:** Repeating the full teaching routine past the point of need is friction for friction's sake, which conflicts with the existing banned-motivations standard as much as fear or urgency would. Right-sizing explanation *down* over time is as much a trust signal as providing it in the first place.

### 2.5 Momentum / Emotional Checkpoints

Distinct from 2.1–2.4: this operates at **milestone transitions** in the tenant's overall journey, not on individual objects. Two trigger moments:

- **After a task/phase completes** (complacency risk) — a warm, light acknowledgment that also names what's still ahead. E.g. *"Nice — that's the notice logged. We've still got the response letter and the timeline to build, but you've already got a start."*
- **Before a new phase starts** (overwhelm risk) — reframe scale honestly but gently. E.g. *"This next part looks like a lot. It's really three things, and you've already done harder ones."*

**This is momentum through warmth and honesty, not urgency or fear** — consistent with the existing banned-motivations rule (MOTIVATIONS.md), just applied to pacing rather than only to marketing copy. It must never imply false urgency, false difficulty, or false ease.

**Existing hook:** the module manifest already lists an Emotion Engine (`app.modules.emotion.router`, RESEARCH tier, `experimental`, tag "Emotion Engine"). This is very likely the intended home for 2.5 — check its current stub content before building fresh, rather than creating a parallel module.

**Guardrail — same tapering logic as 2.4 applies here too.** Firing this at every checkpoint, rather than only genuine phase boundaries, degrades it from a human moment into a script, which undermines the trust it's meant to build. Frequency is further governed by Intensity Level (2.8).

### 2.6 Page Envelope — grammar-parallel structure, one level above the Object Envelope

Where 2.1 gives individual objects context, the Page Envelope gives the *whole page* a consistent skeleton, modeled deliberately on English sentence structure — subject leads, objectives follow as predicate, actions are verb phrases carrying real weight, and prepositions/adjectives provide relational and descriptive support without leading.

| Grammar role | Field | Purpose |
|---|---|---|
| **Subject** (noun) | `page_subject` | The single clear topic that leads the page — "Your Lease," "March 3rd Notice." Same discipline as the lobby rule: one thing, not a menu. |
| **Objective(s)** (predicate) | `page_objectives` | What the page helps the tenant *do* — stated as goals ("understand your rights here," "decide how to respond"), not features. One or more. |
| **Actions** (verb phrases) | `page_actions` | The buttons/tasks on the page. Each action references its Object Envelope (2.1) and is backed by real supporting info via the Three-Layer Retrieval (2.2) — never a bare command. |
| **Prepositions** (relational) | `page_relations` | How the subject connects to everything else — *from* (the landlord), *since* (a date), *in response to* (another document). Ties this page into the tenant's larger timeline. |
| **Adjectives** (qualifiers) | `page_state` | Honest, factual state descriptors — "pending," "unread," "resolved," "time-sensitive." Descriptive only — must stay inside the banned-motivations rule; no alarmist language. |

The Page Envelope is declared once per page template; `page_actions` is populated at render time from whichever Object Envelopes are present on that page.

### 2.7 Experience Token — privacy-safe familiarity tracking (replaces rev. 1's server-side exposure table)

Rev. 1 proposed a `tenant_id + object_type → exposure_count` table. **This does not pass the Navigation Principle's vocabulary check** — a server-side table keyed to a persistent user ID is a tracker by definition, regardless of intent, and would be rejected on wording alone in SSOT review.

**Resolution:** the exposure count is never held by Semptify. It lives in a small preferences file — the **Experience Token** — stored using the *same storage-as-identity model already governing tenant documents*:

- For a tenant with connected storage: the token is a small JSON object written to their own connected cloud storage (same trust boundary as their documents). Semptify's servers never hold it, never see it, and it isn't keyed to anything Semptify assigns — the only "key" is the storage connection the tenant already controls.
- For a tenant without connected storage yet (early onboarding, pre-OAuth): falls back to session-local state only. Resets on a new device or session. Acceptable tradeoff — this only calibrates teaching depth, nothing load-bearing.
- **No new identifier is introduced anywhere.** Nothing about this token identifies the tenant to Semptify any more than storing a document already does.

**The formula:**

```
Experience Token = {
  object_type_A: amount (tally, incremented per exposure),
  object_type_B: amount,
  ...
  intensity_level: n   (see 2.8)
}

presentation = f(type, amount, intensity_level)
```

- **Type** = the object's `subject_tags` / category — which family of explanation this is
- **Amount** = a plain incrementing tally per type (informally: "notches") — no timestamps, no session history, just a count
- **Presentation** = selects the variant tier from Familiarity Tapering (2.4) and gates whether a Momentum Checkpoint (2.5) fires, scaled by Intensity Level (2.8)

### 2.8 Intensity Level — tenant-controlled multiplier

A single scalar stored inside the Experience Token (2.7), so it inherits the same privacy posture — never held server-side against an identity.

| Level | Behavior |
|---|---|
| 0 — Off | No momentum ticks (2.5). Minimal tone throughout. |
| 1 — Subtle | Rare, low-key. |
| 2 — Standard | Default behavior as designed in 2.5. |
| 3 — High | Warmer, more frequent. |

This is a genuine multiplier on both the frequency of Momentum Checkpoints and the general voice warmth of Layer 1 variant selection.

## 3. Non-goals / explicit guardrails

- No component in this ADR performs live, unbounded LLM reasoning that could generate a new legal claim, fact, or recommendation. Everything shown is either a Layer 1 human-authored entry, a bounded rephrase of one, or a real event narration.
- No fabricated progress or status narration (2.3 guardrail).
- No forced re-teaching past demonstrated familiarity (2.4).
- No urgency- or fear-based momentum tactics (2.5) — the emotional layer is opt-out-by-design (a tick, not a gate) and must never block progress.
- **No server-side tracking of any kind attached to a tenant identifier.** All familiarity/exposure state lives in tenant-controlled storage or session-local state (2.7). This is a hard constraint, not a preference — any implementation that introduces a Semptify-held table keyed to user ID for this purpose is out of spec and must be rejected in review.
- Nothing here changes the UPL risk tier of any existing module; retrieval only surfaces already-reviewed content at the tier it was authored for.

## 4. Dependencies on existing systems

- **WebSocket Events module** (`/ws`, CORE, active) — required for 2.3
- **OCR semantic embedding pipeline** (all-MiniLM-L6-v2, offline) — **CORRECTION (2026-08-10):** this does NOT exist as running code. ADR-0007 (OCR + Semantic Reasoning Privacy Model, status BETA) describes the intended design only. No `sentence-transformers`/`transformers`/embedding module found anywhere in the codebase (confirmed via todo-068 preflight). Section 2.2 Layer 2 has been revised accordingly — see below.
- **Know Your Rights Library** — primary source pool for Layer 1 entries
- **Emotion Engine module** (`app.modules.emotion.router`, RESEARCH, experimental) — likely home for 2.5; audit existing stub before building
- **Journal module** — potential secondary source for "reflection" stage context
- **Storage-as-identity architecture** (OAuth to tenant's own cloud) — required for 2.7; this ADR adds no new storage mechanism, it reuses the existing one

## 5. Open decisions — resolved 2026-08-10

1. ~~Where does `exposure_count` live~~ — **Resolved in rev. 2:** tenant's own connected storage via the Experience Token (2.7), session-local fallback pre-OAuth.
2. **Which object types get instrumented first — Resolved:** Eviction Timeline and Vault upload flow. Both already have real backend events (2.3) and real jurisdiction data to query against, making them the lowest-friction pilot surfaces.
3. **Confidence threshold for Layer 2 retrieval — Resolved (starting value, not permanent):** 0.75 cosine similarity. Conservative on purpose — per the 2.2 guardrail, showing nothing is safer than showing a weak match. This is a tuning parameter, not a fixed constant; see #4's beta process for how it gets calibrated.
4. **Who authors/reviews Layer 1 content — Resolved:** No formal Know Your Rights Library-grade review process until there's a baseline. Beta testers are the initial calibration signal — their confusion, corrections, and "that wasn't helpful" feedback is what the eventual formal review criteria gets built from. Until that baseline exists, Layer 1 entries get a **separate, lighter review pass** (Brad + informal check), not the full Library editorial process. New field added to Layer 1 entries: `review_status: beta | vetted` — beta entries are eligible for retrieval but should carry a lighter-weight disclosure than fully vetted Library content, and are the ones the Layer 2 threshold (#3) gets tuned against first.
5. **Default Intensity Level (2.8) — Resolved:** 2 (Standard), easy to lower.
6. **Format/schema versioning for the Experience Token — Resolved:** `token_version: 1` (integer, default), so future schema changes don't break tokens already sitting in tenant storage.

## 6. Consequences

**Positive:** Tenants get proportional, trustworthy explanation instead of either silence or static walls of text, at both the object and page level. Reuses existing infrastructure (embeddings, WebSocket, Emotion Engine stub, storage-as-identity) rather than requiring new heavy systems. Keeps UPL risk bounded because nothing is generated live. Familiarity/emotional state is fully privacy-safe by construction, not by policy — there's no tracker to misuse because there's no server-side table to begin with.

**Costs / risks:** Requires ongoing content authorship (Layer 1 entries with multiple variants is more writing than a single static blurb). Requires reading/writing a small file in tenant storage on relevant page loads — a new I/O pattern, though a lightweight one. Requires discipline to keep 2.3 narration tied to real events and 2.5 checkpoints genuinely sparse — both guardrails are easy to erode under deadline pressure and should be spot-checked in review, not just declared once. Session-local fallback (2.7) means a pre-OAuth tenant's familiarity state doesn't persist if they leave and come back before connecting storage — acceptable but worth tenant-facing awareness at some point.

---

*This ADR should be read alongside MOTIVATIONS.md (Wisdom Principle, Information Integrity Standards, banned motivations), the Navigation Principle ADR (vocabulary + design checks), and ADR-0007 (OCR/semantic-reasoning privacy model, currently BETA/unimplemented) — this document extends all three rather than replacing them.*
