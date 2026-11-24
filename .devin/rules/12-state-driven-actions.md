---
description: State-Driven Action Toolbars — the backend projects which actions render from entity state; never show disabled buttons; 1 primary + <=3 contextual + native <details> overflow
---

# State-Driven Action Toolbars

*(Standing rule, 2026-11-23. Companions: `10-progressive-disclosure.md` — what the
page shows at all; `11-zen-algorithms.md` — how much gets built; `03-ssot-redirects.md`
— where actions point.)*

## The rule

1. **Actions are projected from state — never gated by template `{% if %}` chains.**
   Given an entity's state, the backend decides which actions exist via
   `app.core.smart_toolbar.project_toolbar(state, actions=..., rules=...)`.
   Templates render the projected set verbatim — no state logic in Jinja.
2. **Never render disabled actions.** If an action isn't valid in the current
   state it is not in the DOM at all — no `disabled` buttons, no grayed-out
   "can't do this yet" affordances. Per progressive disclosure: availability
   follows situational need, so a *valid* action is never withheld either.
3. **One primary + at most 3 contextual.** Each state maps to at most one
   primary CTA (`.btn--primary`, the next real step) and at most three inline
   contextual actions (`.btn--ghost`; `.btn--danger` only for genuinely
   destructive actions). Anything beyond that goes in the native `<details>`
   overflow menu — never a fourth inline button.
4. **Native HTML before JavaScript.** Overflow = `<details>`/`<summary>`;
   confirmations = `SemptifyFeedback.confirm` via `data-confirm` attributes
   (delegated globally in `static/components/feedback.js`). Native
   `confirm()`/`alert()`/`prompt()` are banned repo-wide. Any additional JS
   must be vanilla and shared — never per-page inline handlers.
5. **Endpoints are SSOT-resolved.** `project_toolbar`'s `resolve` maps each
   action to its URL through the navigation registry / module contract — never
   hardcode URL strings (rule 03).
6. **Styling is design-system only.** `.btn--*` classes plus the
   `.smart-toolbar__*` block inside `static/css/ssot-design-system.css`. No new
   CSS files, no inline styles, no card borders — the overflow menu separates
   via background + elevation tokens.

## Where it binds

- Detail/action views that expose state-dependent operations (document status,
  filing status, request lifecycle).
- It is the **deterministic floor** — what *can* be done here, right now. It
  does not replace `next_step_path` (chronological "your path" sequencing) or
  `action_router` (AI-ranked suggestions).
- Workflow: `.devin/skills/smart-toolbar/SKILL.md` — mirrored as
  `.github/prompts/smart-toolbar.prompt.md`.
