# HANDOFF: Context Loop vs. Information Orchestrator, and Page Composer vs. UI Composer

**Date:** 2026-08-18  
**Agent:** swe-1.7  
**Purpose:** Answer two architecture questions that keep coming up as the in-task guide / UI Composer work moves forward:

1. Is the older **Context Loop** a predecessor that the **Information Orchestrator (ADR-0008)** replaces, or are they coexisting systems?
2. Does the **Page Composer** bypass the **UI Composer** and build whole multi-pillar pages by itself, or does it feed the UI Composer content and let it produce components?

This is a read-only investigation. No code was changed.

---

## Bottom line up front

- **Context Loop and Information Orchestrator are coexisting, not a replacement chain.** Context Loop tracks the tenant's situation, events, intensity, and predictions. Information Orchestrator (the `context_engine` + envelopes + Experience Token) explains what each object and page means, and retrieves the right explanation variant for this tenant at this moment. They touch the same word — "context" — but they answer different questions.
- **Page Composer does not bypass UI Composer; it orchestrates above it.** Page Composer assembles a new `PageConfig` (the Page Shell / pillar-mixer layout) and then calls `app.services.ui_composer.compose_page()` to produce a legacy component list. UI Composer is still the component formatter; Page Composer is the page architect that decides which subject, blend, blocks, and GOVERN rules apply.
- The **in-task guide preview** (`/gui/record/journal/create`) is a third, lighter pattern: a Jinja template page (`journal_create_guide.html`) that uses the `components/ui_composer.html` macro library for the sync `process_indicator`. It does not call the `ui_composer` service, the Page Composer, or the Information Orchestrator. That is intentional for a one-function guide.

---

## 1. Context Loop vs. Information Orchestrator

### What the Context Loop does

- Location: `app/modules/context_loop/`, `app/services/context_loop.py`
- Core idea: ingest events, update a per-user `UserContext`, and calculate an `intensity_score` (0-100) for how urgent the tenant's situation is.
- Key pieces:
  - `ContextEvent` — a document upload, deadline, issue detected, action taken, etc.
  - `UserContext` — the running snapshot: documents, active issues, deadlines, laws, predictions, risk factors.
  - `IntensityEngine` — scores urgency based on document/issue type + deadlines + patterns.
- How it is used today:
  - `app/services/ui_composer.py` calls `context_loop.get_user_context()` when no explicit context is supplied, to decide which landing/timeline/library components to emit.
  - It is registered as its own module with `FunctionGroupContract`s (`context_loop_state`, `context_loop_intensity`, etc.).

### What the Information Orchestrator does

- Location: `app/core/context_envelope.py`, `app/core/page_envelope.py`, `app/core/experience_token.py`, `app/modules/context_engine/`, `app/services/emotion_engine.py`
- Core idea: every object and page carries structured metadata (Object Envelope / Page Envelope), the system retrieves a human-written explanation variant from a curated store, and it tailors that variant to how familiar the tenant is with this kind of object.
- Key pieces, per ADR-0008:
  - **Object Envelope** — per-object metadata: what it is, which pillar, why it exists, provenance, subject tags.
  - **Page Envelope** — page-level metadata: subject, objectives, actions, relations, state.
  - **Three-Layer Retrieval** — Layer 1 curated entries, Layer 2 metadata/embedding match, Layer 3 bounded rephrase.
  - **Familiarity Tapering** — which explanation variant to show based on exposure count.
  - **Momentum / Emotional Checkpoints** — warm, sparse milestone messages handled by the Emotion Engine.
  - **Experience Token** — privacy-safe familiarity state stored in the tenant's own cloud storage, not a Semptify-side tracker.
- How it is used today:
  - The ADR-0008 pilot surfaces are **Eviction Timeline** and **Vault upload flow** (per ADR and `tests/test_information_orchestrator_pilot.py`).
  - `app/modules/eviction_timeline/envelopes.py` and `app/modules/vault/envelopes.py` define real Object/Page Envelopes.
  - `context_engine.explanation_entries` and `context_engine.retrieval` are the Layer 1 + Layer 2 store.
  - `experience_token` has read/write wired to tenant storage.
  - Most pieces outside the two pilot surfaces are built but not yet wired into day-to-day pages (per `BACKLOG.md`).

### Verdict: coexisting, not superseded

| Question each answers | Context Loop | Information Orchestrator |
|---|---|---|
| What is the tenant's overall situation? | Yes — documents, deadlines, intensity, predictions. | No — it does not track user state. |
| What should this button/field/page say to this tenant right now? | No. | Yes — via Object/Page Envelopes + retrieval + tapering. |
| Where does the data come from? | Events emitted by modules and user actions. | Human-curated Layer 1 entries, object metadata, tenant-controlled Experience Token. |
| When should it run? | Continuously, event-driven. | At render time, when a page or object is displayed. |

They are **not a replacement chain**. The Information Orchestrator needs to know the tenant is in an "eviction" context, but it does not replace the Context Loop's intensity scoring or event processing. In the current code, `ui_composer.py` still reads from the Context Loop, while Page Composer leans on `context_engine` (facts/stories/case data). The two "context" systems are parallel tracks, and the honest path forward is to let them converge at the page level: Context Loop provides the *situation*, Information Orchestrator provides the *explanation*.

### One naming risk to watch

Both systems use the word "context" heavily. That is the main source of confusion. In conversation and code, it helps to say:

- "user context" or "situational context" for the Context Loop.
- "object context," "page context," or "explanation context" for the Information Orchestrator.

---

## 2. Page Composer vs. UI Composer

### What the UI Composer does

There are actually two things called "UI Composer" in the repo:

1. **`app/services/ui_composer.py` + `app/modules/ui_composer/router.py`** — a Python service that returns a JSON list of components (`welcome_message`, `fact_card`, `timeline_group`, `process_indicator`, etc.). `GET /api/ui/page/{intent}` renders them through `generic_page.html`.
2. **`app/templates/components/ui_composer.html`** — a Jinja macro library that knows how to render those same component types. It is imported by templates like the in-task guide body template.

The service is the *head waiter*: it picks a page intent (`landing`, `timeline`, `library`, `documents`, `tools`, `workflow_step`), asks the Context Loop for user context, and returns components. It does not know about subjects, blends, or GOVERN rules.

### What the Page Composer does

- Location: `app/modules/page_composer/`
- Core idea: take a `subject` + `jurisdiction` + user context, compute intensity, pick a major pillar and a blend, gather blocks from the Context Engine (facts/stories/case data), apply GOVERN floor/override rules, and produce a `PageConfig` for the Page Shell.
- In `app/modules/page_composer/assembly.py` (lines 85-178), the assembly formula does 9 steps:
  1. Resolve inputs
  2. Compute intensity
  3. Classify `major_pillar`
  4. Select blend
  5. Gather blocks
  6. Build `PageConfig`
  7. Apply capability filter
  8. Apply GOVERN rules
  9. **Emit legacy UI Composer components**

Step 9 is the key: it calls `app.services.ui_composer.compose_page()` with an intent derived from the major pillar and a context built from the Page Composer's own data:

```python
# assembly.py ~L152-162
ui_intent = _ui_intent_for(major_pillar)
ui_context = _build_ui_context(context, page_config, jurisdiction, page_data)
ui_page = ui_compose_page(
    user_id=user_id or "anonymous",
    page_intent=ui_intent,
    context=ui_context,
)
components = ui_page.get("components", [])
```

### Verdict: Page Composer is the orchestrator; UI Composer is still used

Page Composer **does not bypass** UI Composer. It:

- Decides the page architecture itself (subject → pillar → blend → blocks → Page Shell `PageConfig`).
- Then hands a pre-built content context to UI Composer so UI Composer can emit its familiar component list.
- Returns **both** the new `PageConfig` and the legacy `components` list in `PageAssemblyResult`.

The Page Shell (`app/modules/page_shell/`) is the newer rendering layer that turns `PageConfig` into HTML (`render_page_shell`). The UI Composer components are the older, parallel output. This is a migration-in-progress shape, not a bypass.

### Where the in-task guide fits

The `journal::journal_create` in-task guide at `/gui/record/journal/create` is **not** using the Page Composer or the `ui_composer` service. It is:

- A Jinja page (`app/templates/pages/journal_create_guide.html`) extending the RECORD pillar body template.
- A direct FastAPI route in `app/main.py` that pulls the `FunctionGroupContract` for `journal::journal_create`.
- A form that POSTs to the existing `/api/journal/` endpoint.
- The sync narration is rendered with `process_indicator` from `app/templates/components/ui_composer.html`.

That template macro reuse is the only connection to "UI Composer" in the preview. It is a deliberate, narrow scope: one function, one guide, no Page Composer, no Context Loop, no Information Orchestrator — just the contract, the form, and one shared component macro.

---

## 3. Recommendations

1. **Keep Context Loop and Information Orchestrator as separate but complementary systems.** Do not rewrite the Context Loop into the Information Orchestrator or vice versa. The right integration point is: Context Loop tells the page "how urgent / what phase," Information Orchestrator tells the page "what to say and how much."

2. **Page Composer is the right place to wire both context systems together.** It already pulls from `context_engine` (facts/stories/case) and emits a `PageConfig` for Page Shell. It can also consume Context Loop intensity/phase and pass it into the page/state metadata. That would let both systems influence the same rendered page without either one taking over the other.

3. **UI Composer is still a real layer, but it is a component formatter, not a page architect.** The in-task guide work should continue to use the `components/ui_composer.html` macros where appropriate, and should not be forced through `app/services/ui_composer.py` unless the page is intentionally intent-based (landing/timeline/library/etc.).

4. **If expanding ADR-0008 beyond the two pilot surfaces, the natural path is:**
   - Add Object Envelopes to the new surface's key objects.
   - Add a Page Envelope for the page.
   - Wire it through `page_composer.assemble_page` so Page Shell gets the layout and UI Composer gets the components.
   - Use the Experience Token read/write path for Familiarity Tapering.
   - Keep Live Event-Driven Narration as a separate build decision — it was never implemented and is not required for basic page-level explanation.

---

## 4. Key files referenced

- `app/modules/context_loop/service.py` and `router.py` — Context Loop core.
- `app/services/ui_composer.py` and `app/modules/ui_composer/router.py` — UI Composer service.
- `app/templates/components/ui_composer.html` — UI Composer Jinja macro library.
- `app/modules/page_composer/assembly.py` — Page Composer assembly formula.
- `app/modules/page_composer/service.py` — Page Composer fact/story/case gathering.
- `app/modules/page_composer/models.py` — `PageAssemblyResult` (PageConfig + components + GOVERN report).
- `app/modules/page_shell/models.py` and `renderer.py` — Page Shell config and rendering.
- `app/core/context_envelope.py`, `app/core/page_envelope.py`, `app/core/experience_token.py` — Information Orchestrator core schemas.
- `app/modules/context_engine/explanation_entries.py`, `retrieval.py`, `verifier.py` — Layer 1/2 store and fact-freshness checker.
- `docs/adr/0008-information-orchestrator.md` — canonical ADR-0008.
- `tests/test_information_orchestrator_pilot.py` — pilot test coverage.
- `BACKLOG.md` — current expansion status for ADR-0008.
