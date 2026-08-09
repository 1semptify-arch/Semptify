# Document Center (DC) — Handoff to Claude Sonnet 4.6

> **Purpose:** Give this to Sonnet 4.6 to do design + planning for the DC.
> **One-line invocation:** "Read `docs/planning/DC_HANDOFF_SONNET.md` and `docs/planning/DOCUMENT_CENTER_PLAN.md`, then produce a design + build plan for the Document Center."

---

## What You're Designing

The **Document Center (DC)** is Semptify's flagship product surface. Not a feature — the foundation. Nearly everything else in Semptify (Timeline, Journal, Contact Manager, Case Builder, Legal Prep) plugs into the DC and unlocks from it.

The DC is a single page where a tenant works with their documents alongside Semptify. It replaces fragmented UI (vault list, separate viewer, separate overlays, separate timeline) with one unified workspace.

## Read These First (in order)

1. `docs/planning/DOCUMENT_CENTER_PLAN.md` — the user's canonical vision (3-pane layout, 5 actions, viewer tools, unlock pattern)
2. `AGENTS.md` — Semptify rules: Python 3.11.9, Known Failure Registry, SSOT, no hardcoded URLs, fix root causes
3. `PROJECT_BIBLE.md` — governance hierarchy, onboarding gates, mission
4. `BUILD_GUIDE_SSOT.md` — what's actually shipped, what's broken, what's pending
5. `ACTIVE_CONTEXT.md` — current priority
6. `app/services/unified_overlay_manager.py` (bottom of file) — the overlay contracts. DC's right panel shows overlays, so you MUST use the real `FunctionGroupContract` signatures. Do not invent overlay fields.

## The DC in One Paragraph

A 3-pane desktop GUI page. Left: vault document list. Center: Semptify Viewer (the selected document renders here, user + Semptify walk through it together in real time). Right: overlays panel showing each document-process overlay with a completion % toward its stated goal. Top of viewer frame: tools for the selected item (highlights, notes, references, tied to a user key system — like the Briefcase was supposed to be). As verified metadata accumulates in the overlays, new Semptify features unlock (Timeline, Journal, Contact Manager, etc.). Tenant sees progress fill and understands why something unlocked.

## What Sonnet 4.6 Should Produce

A design + build plan covering:

### 1. Information Architecture

- The 3-pane layout — exact contents of each pane
- What "selected item options" live in the viewer top bar
- What an overlay row in the right panel looks like (name, %, status, goal, action)
- How the unlock pattern is communicated to the tenant (progress, "what's next", not gimmicky)

### 2. Viewer Design

- How the document renders (PDF.js for PDFs; image fallback for non-PDFs; what about .docx, .html, photos)
- How highlights, notes, references appear on the document
- How Semptify's extraction highlights appear (distinct from user highlights)
- How the user confirms/corrects an extracted field inline
- How "user + Semptify walk through together" actually feels (step mode? live mode? both?)

### 3. Overlay Panel Design

- Which overlays exist per document type (OCR, Parties, Dates, Addresses, Amounts, Signatures, References, ...)
- What "completion %" means per overlay — what counts as 100%
- How an overlay's "original goal" is defined and shown
- How verified vs unverified metadata is displayed
- How the user drills into an overlay from the panel

### 4. The Unlock Pattern

- Exact rules: how much verified metadata unlocks what
- First unlock = Timeline. Define the threshold.
- Second unlock = Journal. Define the threshold.
- Third unlock = Tenant Contact Manager. Define the threshold.
- How unlocks are surfaced (badge, toast, sidebar entry, progressive disclosure)
- How to avoid overwhelming a stressed tenant

### 5. Per-Document-Type Checklists

- Pick the first 5 document types to ship (suggest: Lease, Notice to Vacate, Repair Request, Rent Receipt, Move-in Inspection)
- For each: required fields, optional fields, what "Verified" means
- Where the checklist definition lives in code (suggest: `app/core/document_types.py` as SSOT)

### 6. Code Structure (respect Semptify conventions)

- New module: `app/modules/document_center/` (router, viewer, overlays, register)
- New SDK: `app/sdk/document_center/` if reusable
- New templates: `app/templates/pages/document_center.html` + partials for each pane
- New static: `static/js/dc/` (viewer, panel, unlock logic), `static/css/components/dc.css`
- Reuse: `app/sdk/vault/` for vault access, `app/services/unified_overlay_manager.py` for overlays, `app/core/navigation` for SSOT paths, `app/core/utc` for timestamps
- Contract: register `FunctionGroupContract` entries in `app/core/module_contracts.py` for any new DC APIs

### 7. Build Slices (smallest useful first)

- Slice 1: 3-pane shell + vault list + viewer renders one PDF + one overlay (OCR) with a fake %
- Slice 2: Real OCR overlay wired to a real extraction call
- Slice 3: One document type checklist (Lease) + inline confirm/correct
- Slice 4: Highlights + notes + references tied to user key
- Slice 5: First unlock (Timeline) triggered by verified metadata threshold
- Slice 6: Remaining 4 document types
- Slice 7: Journal unlock, Contact Manager unlock

Each slice must compile clean and be testable on its own. No slice breaks the previous.

### 8. Risks & Open Questions

- Performance: large PDFs in the viewer
- Storage: where do highlight/notes overlays live (R2? User's vault? Both?)
- Trust: how does the tenant know Semptify didn't misread a field
- Scope creep: how to stop DC from becoming a giant IDE
- Mobile: explicitly deferred — but design so it doesn't preclude it

## Hard Constraints (do NOT violate)

- Python 3.11.9 only
- No hardcoded URL strings — use `navigation.get_stage()`
- No `datetime.now()` — use `utc_now()` from `app.core.utc`
- No bare `except:` — use specific exception types
- No new `_v2` / `_new` / `_fixed` files — use the swap protocol if rewriting
- No workarounds downstream — fix root causes
- No inventing overlay API fields — read the contracts in `unified_overlay_manager.py`
- No black-box AI — the tenant sees what Semptify sees, always
- No feature unlocks without verified metadata — no free previews
- Desktop GUI first; mobile is a later problem
- Follow PEP 8, use async for I/O, use Pydantic for request/response models

## What Not to Do in This Pass

- Do not write production code yet — this is design + planning only
- Do not touch other modules — DC is additive
- Do not redesign onboarding, vault, or existing routes
- Do not propose new roles or permissions
- Do not introduce new dependencies without confirming Python 3.11.9 support

## Deliverable Format

Produce a single markdown doc: `docs/planning/DC_DESIGN_SONNET.md` with:

1. Executive summary (1 paragraph)
2. Information architecture (with a clean ASCII or mermaid diagram of the 3-pane layout)
3. Viewer design (with a wireframe description)
4. Overlay panel design (with a row template)
5. Unlock rules (as a table)
6. First 5 document type checklists
7. Code structure (file tree + responsibilities)
8. 7 build slices (each with: what's in it, what's testable, what dependencies)
9. Risks & mitigations
10. Open questions for the user to decide

Keep it dense, no fluff. The user types slowly and reads carefully.

---

## One-Line Invocation for Sonnet 4.6

> Read `docs/planning/DC_HANDOFF_SONNET.md` and `docs/planning/DOCUMENT_CENTER_PLAN.md`, then produce `docs/planning/DC_DESIGN_SONNET.md` following the deliverable format in the handoff doc. Do not write production code — this is design + planning only.
