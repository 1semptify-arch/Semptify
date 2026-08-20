---
description: Progressive Disclosure / Capability Revelation rule for Semptify frontends
---

# Progressive Disclosure / Capability Revelation

*(Companion to GUI Design Rule and Navigation Principle — include by reference in all frontend handoffs.)*

## The Premise

Semptify's users are triangulated at a 5th-grade reading/comprehension floor, using the app under real stress ("the gauntlet"), with no human help available. Success rate targets: 80% round 1 → 97% round 2 → 99.99% round 3.

That bar is **not achievable by better explanation.** No amount of Information Orchestrator narration can make a genuinely complex page simple. The only path that works: **the page itself must never present more than the user needs at this exact moment.**

## The Core Rule

**Do not delete functions. Do not gate access to a function on mastery.** If a user's situation requires a function, that function is available — full stop. What tapers is **how much is explained about it**, not whether it's there.

Every page/function is broken into the smallest usable piece, and the transparency layer (function description, backend narration, "what's next") scales in *verbosity* — not in *availability* — based on the user's demonstrated familiarity with that specific function. A first-time user sees "your document is now being prepared to be placed in your OAuth storage vault." A tenth-time user sees "Preparing your document..." Same function, same access, less narration.

## The Mechanism: Familiarity Tapering Governs Density, Not Access

ADR-0008's Familiarity Tapering / Experience Token already tracks per-user, per-function familiarity via an `intensity_level` field: **Off / Subtle / Standard / High.** This governs two things, and only these two:

1. **Narration verbosity** — how much the backstage/process narration explains ("your document is now being prepared to be placed in your OAuth storage vault" at High, "Preparing your document..." at Off)
2. **UI chrome density** — how much visual guidance/hand-holding surrounds the function (more prominent labels and help text at High, denser/quieter controls at Off)

**It never governs whether a function is shown.** Function/module availability is a separate, independent concern, resolved purely by situational need (Module Resolver: does this user's current situation call for this module right now). A user in crisis who needs an advanced function on day one gets it on day one — full explanation, but full access.

- **Round 1 (new to this function):** `intensity_level = High`. Full plain-language explanation, full narration, simpler-looking controls.
- **Round 2 (some familiarity):** `intensity_level = Standard`. Shorter explanation, lighter narration.
- **Round 3 (mastered):** `intensity_level = Off` or `Subtle`. Minimal narration, dense/quiet controls — the function looks and behaves like a power-user tool, without ever having been hidden.

This also collapses "CTA-simple mode vs. advanced mode" into the same dial — they're not a separate system, they're the High and Off ends of `intensity_level`. Form factor (mobile/desktop) is a fully separate, orthogonal axis — it changes layout shape only, never explanation density.

Backstage narration exists specifically to keep a user's attention and reduce anxiety **during real waiting** — it proves something is happening and passes the time honestly. It is not decoration. Once a function is instant and reliable, narrate less or not at all.

## What This Requires Before Build (open decisions — Brad's call)

1. Intensity-level advance trigger: does a function's tier advance on task-completion only, on explicit user request ("show me less"), or both?
2. Is `intensity_level` state per-function-per-page, or per-function app-wide? (Does progressing on Function X in one context carry over everywhere that function appears?)
3. How does a returning/experienced user start at the right tier instead of re-earning High→Off every session? (Likely: Experience Token already answers this — confirm it persists correctly in the tenant's own storage per ADR-0008.)

## What This Means for the Information Orchestrator (agent-buildable once above is decided)

- Orchestrator reads current `intensity_level` state to determine narration/chrome **verbosity only** — never which functions are rendered.
- Event contract needed: each function reports task-completion (not quiz-answer) back to the Experience Token to advance tier.
- Function/module *availability* is decided entirely separately, by the Module Resolver, based on situational relevance — not by the Orchestrator, and not by tier.

## Relationship to Existing Rules

- Complements the **GUI Design Rule** (chronological task-flow, spatial priority) — progressive disclosure decides *what's on the page*; the GUI rule decides *where it sits once shown*.
- Complements the **Navigation Principle** (road system, not gates) — hidden-until-needed is not a gate. Nothing is blocked; it's simply not surfaced until relevant. No verification checkpoint, no permission check — just relevance.
