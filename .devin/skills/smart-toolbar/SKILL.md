---
name: smart-toolbar
description: Add or audit state-driven action toolbars — project which actions render from entity state via app.core.smart_toolbar.project_toolbar + components/smart_toolbar.html. Never render disabled buttons; 1 primary + <=3 contextual + native <details> overflow. Use when a detail/action view needs state-dependent buttons, when converting template-side {% if %} button chains, or for a subtractive declutter pass on an action-heavy page.
---

# Skill

## Smart Toolbar — build & audit procedure

Canonical rule: `.devin/rules/12-state-driven-actions.md`.
Engine: `app/core/smart_toolbar.py` (`project_toolbar`, `StateRule`).
Renderer: `app/templates/components/smart_toolbar.html`.
Confirmations: `SemptifyFeedback.confirm` via `data-confirm` attributes,
delegated in `static/components/feedback.js` — native `confirm()` is banned.
The general subtractive pass belongs to the `zen-algorithms` skill — run it
first; this skill owns only the toolbar-specific checks.

## Build a state-driven toolbar

1. **Map states first.** List every entity state on the page and the actions
   valid in each, as a table, before touching code. If the states aren't
   clear, stop and ask — don't guess a lifecycle.
2. **Define rules beside the router that owns the page:**
   `RULES = {"DRAFT": StateRule(primary="submit", contextual=("edit", "delete")), ...}`
   Reuse an existing `QuickAction` map from `app/core/action_maps.py` where
   one covers the domain.
3. **Project in the route:** pass
   `toolbar=project_toolbar(entity.status, actions=..., rules=RULES, resolve=...)`
   in the `TemplateResponse` context. `resolve` maps each action to its URL
   through `navigation.get_stage` / contract routes — never hardcode URLs
   (rule 03).
4. **Render:** `{% include "components/smart_toolbar.html" with context %}`.
   Styling is `.btn--*` + `.smart-toolbar__*` from `ssot-design-system.css`
   only — no new CSS files, no inline styles.
5. **Confirmations:** set `confirmation_prompt` on the action — the template
   emits `data-confirm` and `SemptifyFeedback.confirm` handles the dialog.
   Set `danger=True` for destructive actions (`.btn--danger` + error-styled
   confirm dialog).
6. **Verify per the `gui` skill** when a live page changed: running app,
   375px + 1280px, eye-path audit.

## Audit an existing page (subtractive pass)

1. Zen pass first (`.devin/skills/zen-algorithms/SKILL.md`): goal → minimum
   set → justify rest → subtract-first → fewer parts.
2. Then toolbar checks — each hit is a finding:
   - `disabled` buttons or grayed-out actions in markup?
   - `{% if state == ... %}` / status / phase conditionals deciding button
     visibility inside the template?
   - More than 1 primary-styled or more than 3 inline contextual actions?
   - Native `confirm()` / `alert()` / `prompt()`, inline `onsubmit` /
     `onclick` handlers, or per-page JS that HTML/CSS or `data-confirm`
     could replace?
   - Hardcoded URL strings in template or Python?
   - Parallel CSS instead of `.btn--*` + `.smart-toolbar__*` classes?
3. Refactor: move state→action logic into `StateRule`s + `project_toolbar`,
   swap the button row for the include, delete what falls out.

## Output

Report in plain language: the state table extracted, what was deleted vs.
added, and verification evidence (`python -m py_compile`, Jinja parse, and a
running-app check per the `gui` skill if a live page changed).
