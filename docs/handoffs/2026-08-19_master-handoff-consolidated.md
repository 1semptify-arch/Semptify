# Handoff: Progressive Disclosure Principle + Full Current State
*(Consolidated — both documents below had not yet been sent. Paste this whole file as one handoff.)*

---

# PART 1 — Standing Rule: Progressive Disclosure / Capability Revelation
*(Companion to GUI Design Rule and Navigation Principle — include by reference in all frontend handoffs)*

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

---

# PART 2 — Master Handoff: Everything, Current State
*(Supersedes any earlier standalone recap. This is current.)*

## Philosophy (why we're building it this way)
- **Motive:** get the user the answer to their problem as fast as possible — whether that answer comes from Semptify or from pointing them to another entity entirely. No cost to the user, ever. This is deliberate: keeping the product free removes the incentive structure that corrupts motive. If Semptify never profits from a user staying, engaging, or converting, there's no systemic pressure pushing decisions toward anything other than "what actually helps this person fastest."
- **Backstage narration exists for one reason: to keep a user's attention and reduce anxiety during real waiting.** "Your document is being prepared..." isn't decoration — it proves something is happening, passes the time honestly, and keeps the user subliminally aware of progress during a process that takes real seconds. It is NOT meant to explain mechanics for their own sake. Once something is instant and reliable, narrate less or not at all.
- **Users shouldn't have to think about how Semptify works.** Simple, easy, quick, painless. It should just work. Complexity is justified only by a real wait or a real decision point — never by a desire to be thorough.

## Sequencing — simplify first, add later (the actual current priority)
1. ~~Finish the single preview in progress (`journal_create`, RECORD pillar).~~ DONE — verified, polished, passed eye-judgment.
2. ~~Judge it by eye.~~ DONE — failed first pass, polished, passed second pass.
3. ~~Repeat the pattern for one more function, different pillar, to confirm generalization.~~ DONE — `law_library_get_statute` (KNOW pillar) passed clean on first try, no polish round needed. Pattern confirmed to generalize across write/save vs. read/lookup shapes.
4. ~~One more generalization test — ACT pillar.~~ DONE — `eviction_defense_calculate_deadlines` proved the pattern holds even with GOVERN/UPL risk-tier involvement (consequence notice + legal disclaimer on the same screen, no runtime suppression needed).
5. ~~Build the real tapering dial, wire Module Resolver, add form-factor layout variants.~~ DONE — Familiarity Tapering (`intensity_level`/`exposure_count`) live, Module Resolver wired (non-blocking notice pattern), desktop-poster/mobile-stacked-scroll variants applied to all three templates, Page Shell CSS/token vocabulary applied for visual consistency with Concierge pages. Verified at 375px and 1280px, all checks clean.
6. ~~Pause point + real-use pass.~~ DONE — dev auth bypass built, journal entry saved, statute lookup performed (fixed a real 404 endpoint bug in `law_library_get_statute.html` — it now calls `/api/law-library/statutes/{id}` and reads `data.statute`), deadline calculator run with real dates. Zero console errors, zero 4xx/5xx after the fix.
7. ~~Page Composer / Page Shell cleanup, prioritized by risk.~~ DONE — all six inventory gaps closed: capability filter wired to resolved module paths; `case_builder.get_cases_for_user` implemented; Page Shell manifest promoted to CORE with admin-only router; Page Composer + Page Shell contracts loaded by `contract_loader.py`; mobile CSS confirmed non-clipping; assembly formula blueprint promoted from DRAFT to APPROVED. PageEngine facade explicitly deferred.
8. **Next single-function guide page added — timeline create event.** Built `/gui/record/timeline/create-event` for `timeline::timeline_create_event` using the same pattern: `record_body.html`, Page Shell tokens, tapering, resolver notice, form-first layout, backstage narration, next-step CTA. Real-use verified with a live `POST /api/timeline/events` save (event ID `evt_xiG3qMKoRiHjEIGL`); 375px and desktop scroll both clean; zero console errors.
9. **Context Explanation Workbook + Loader created.** `context_explanation_entries` was empty; the embedding/retrieval pipeline is built but had no content. Wrote `docs/context_explanation_workbook.md` (content-author spec with the four variant slots, exposure mapping, writing rules, and 20-entry starter set), `data/explanation_workbook_template.csv`, `data/explanation_workbook_example.csv`, `data/context_explanation_workbook.csv` (full 56-row subject/jurisdiction/pillar workbook with placeholder prompts), and `tools/load_explanation_workbook.py` (skips placeholder rows and loads the rest). Loaded 3 example rows successfully.

## Current step

The pattern has now generalized across four functions and two pillars (RECORD: journal create, timeline create event; KNOW: law library get statute; ACT: eviction defense calculate deadlines). Next move is open: add a fifth function, do a real-use/demo pass across the proven pages, or return to the PageEngine facade only if a wrong-composer pick or third page-type pattern appears.

## Backlog (not urgent, tracked centrally — do not fix per-function)
- **Contract copy is too technical for user-facing display** (e.g., "Law Library Get Statute (SSOT)", "CANONICAL detailed view..."). Templates already expose title/description override blocks, so this is a copy pass, not a contract change — but it should happen once, centrally, across all functions, not patched ad hoc per page as it's noticed.

## Core Rules (current, corrected)
- **One function, one page — as the default, not an absolute mandate.** Applies whenever a user could reasonably arrive at that function on its own (menu, search, next-step link) — journal entry, statute lookup, deadline calculator, all correctly single-function pages, all proven.
- **Function GROUPS get their own page-flow when steps are strictly sequential and meaningless in isolation** — nobody looks up step 2 of onboarding without step 1. Test: would a user ever return to this step alone, out of sequence? If yes, separate function page. If no, it belongs in a group, still one decision per screen, just chained as one recognized task instead of scattered destinations. Onboarding (welcome → role select → storage OAuth → tenant home) is the clear first candidate for this pattern — not yet built, noted for when it's needed.
- **Header and footer are fixed, universal templates.** Never vary by page.
- **Four body layout types, one per pillar:** Record / Know / Act / Govern. Every single-function page uses exactly one.
- **Access is never gated by mastery.** If a user's situation requires a function, it's available — full stop.
- **Familiarity Tapering governs density only** — narration and UI chrome, not availability. Uses ADR-0008's `intensity_level`: Off / Subtle / Standard / High.
- **Two independent page models, not competing:**
  - Page Composer + Page Shell (existing, unchanged) — blended multi-pillar pages, owns Concierge/dashboard/landing/library-browse. Confirmed sound — matches existing code (`assembly.py`, `/gui/dashboard`, `/gui/page/{subject}`, `/tenant/library` subject pages).
  - UI Composer, extended — strict single-function pages, one pillar, no blend. Owns in-task guide pages. Confirmed sound — matches `/gui/record/journal/create` using `record_body.html`.
  - They share Context Loop, `module_contracts.py`, and will eventually share the Information Orchestrator, but never render the same kind of page.
- **`record_body.html` / `know_body.html` / `act_body.html` styling applied:** they reuse Page Shell's CSS tokens and class vocabulary (zone/block/block-input/output-trigger patterns) for visual consistency with Concierge pages — but not the 4-pillar grid, skeletons, channels, blends, or GOVERN logic. Verified at 375px and 1280px.

## Current Build Status
- **Verified and complete:**
  - Four single-function guide pages (`journal_create`, `law_library_get_statute`, `eviction_defense_calculate_deadlines`, `timeline_create_event`) verified responsive and working at 375px and 1280px.
  - Local dev tenant auth bypass implemented and used for real-use pass.
  - Page Composer / Page Shell prioritized cleanup completed (capability filter, Case Builder hook, mobile CSS, manifest, contracts, blueprint).
- **Confirmed via investigation, resolved, no action needed:**
  - Page Composer does not bypass UI Composer — orchestrates above it, calls it for legacy component output.
  - Context Loop ≠ Information Orchestrator — complementary (situation state vs. explanation layer), not duplicate. Information Orchestrator not wired into Page Composer yet; future integration work, not a conflict.
  - Two-page-model resolution — confirmed sound by the investigating agent.
- **Logged, not urgent, do not fix yet:**
  - `ui_composer.py`'s `_get_resolved_modules()` stub always returns `[]` — Module Resolver exists and works but isn't wired in. This is the actual wiring point for situational availability later.
  - ~25 modules missing `FunctionGroupContract` entirely; no contract has GUI fields yet. Not a blocker for `journal_create`, will block scaling past the first couple of previews.
  - Contract copy is too technical for user-facing display (e.g., "Law Library Get Statute (SSOT)", "CANONICAL detailed view..."). Templates expose title/description override blocks; this is a central copy pass, not a contract change.

- **Recently resolved (was logged, now done):**
  - Case Builder `get_cases_for_user` implemented in `app/modules/case_builder/case_builder.py` and used by Page Composer.
  - Page Shell manifest promoted to CORE in `app/core/product_manifest.py`; the `/api/page-shell` router remains admin-only, the renderer is used through Page Composer's tenant routes.
  - Page Composer and Page Shell contracts wired into `app/core/contract_loader.py`; `app/modules/page_shell/register.py` now registers real `FunctionGroupContract`s.

## Later: Page Engine Facade (reference only, not active work)
Once 2-3 functions are proven, the growing list of systems (Context Loop, Context Engine, Page Composer, Page Shell, UI Composer, Positronic Mesh, Module Resolver, Information Orchestrator) should sit behind one entry point — `PageEngine.render(user_id, request) → HTML` — so routes and future agents only ever call one thing. Don't build this now.

---

*This is the live reference doc. Update it, don't replace it, as things change.*
