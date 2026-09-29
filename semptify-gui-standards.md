# Semptify GUI Standards

> Canonical log of reconciled UI/UX architecture decisions. Each entry below is a
> standing rule once logged — future GUI handoffs reference the entry instead of
> re-deriving it. New entries are appended, not edited in place; superseding a
> standard gets a new dated note on that entry.

---

## Guided Navigation Panel

*UI/UX Architecture Standard — reconciled. Supersedes the original hub-and-spoke draft. Logged 2026-09-26 from Brad's handoff.*

### 1. Target app structure

- **TIER 1 (Entry/Home):** Surfaces the tenant's current situation — active deadline, in-progress task, next logical destination. Categories appear only as live paths forward, gated by capability flags (unlock by situation, never purchase; transparent locking language, e.g. "unlocks once you add a court date").
- **TIER 2 (Waypoint):** Shows only tools relevant to the tenant's actual path when a category is entered. No static grid of everything available — if a tool doesn't apply to their situation, it isn't shown.
- **TIER 3 (Tool Focus Page):** One primary task per page. Progressive disclosure. No bundled multi-purpose screens.

### 2. Guided Navigation Panel

This is the existing `.shell-side` sticky rail (asymmetric work-zone-left/rail-right, top-aligned, viewport-capped) — not a new component.

**Layout**

- Main work area: forms/uploads/fields.
- Rail = the Guided Navigation Panel. No separate floating panel, no bottom action bar.

**Behavior**

1. **Primary Action Button** — one clear next step. Color: sage accent `#6B8E6B` from the Soft Neutrals palette. Never alarm color (`#d97706` stays reserved for real deadlines/eviction dates only).
2. **Alternative options** — max 2, collapsed behind an "other options" disclosure.
3. **Helper text** — one short line (7th–8th grade reading level) on the Primary Action only. No per-button explanations on alternatives.

**State mapping** — unchanged pattern: Empty → Upload; Uploaded → Configure, etc. Matches the standing "empty/error states explain what happened plus the next step" rule.

### 3. Frontend & accessibility

- **Styling:** `ssot-design-system.css` tokens only. No Tailwind, no ad hoc component libraries, no inline styles.
- **Color:** Primary action = sage accent. Alarm-red reserved for real deadlines only — never for emphasis.
- **Containers:** No card-style bordered/boxed containers. Zone separation via background-color/tone shift only.
- **Layout:** Desktop = no-scroll full-screen liquid layout. Mobile = stacked-scroll. Both required on every page.
- **Accessibility:** WCAG AA, tap targets ≥44px, ≤2 taps from Home, crisis-help reachable from every page, disclaimer footer present per static-chrome rule.
- **Validation:** Next Step stays inactive until the current step's minimum required action is complete.

---

## Placement & Order — Module Task Pattern + Visual Header

*Logged 2026-09-28 from Brad's directive. Applies to every module page and to the shared chrome.*

### 1. Module instructions

- Every module page carries short instructions on how to use the module to complete the task at hand.
- Layout and placement follow those instructions, in task order — do not complicate the UI.
- If a color code is ever used, it must relate elements to the module's task flow — never decorative.

### 2. Object → objective → actions (the work-zone model)

Before building or arranging a module page, answer in order:

1. **What module group is this?** (pillar: RECORD / KNOW / ACT / GOVERN)
2. **What is the objective of this configuration?**
3. **Is the object chosen?** (the thing the page acts on — a document, an entry, a statute…)
4. **What needs to be done with the object to complete the objective?**

- Each step shows only the function that serves the module's objective.
- The selected object determines the available actions — what can be done **to it, with it, for it**. Those are the actions shown.
- **Max three functions** visible in the work zone.

### 3. Visual header — always on top, fully visible

- The header is pinned and never scrolls out of view or collapses — every viewport, every page.
- Nav items in order **right to left**: **← Back arrow, Home, DC (Document Center), Library, Help & resources**.
- A way back home must always be present — the Back arrow and the Home button both satisfy this.
- Crisis help stays reachable from every page (Help & resources → `/help`; the "Get help now" pill where space allows).
- User time is valuable: nobody should hunt for the way to finish a task or to navigate. No extra UI beyond this.
