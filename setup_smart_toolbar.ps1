# setup_smart_toolbar.ps1 — install the state-driven Smart Toolbar kit
#
# Writes, idempotently:
#   app/core/smart_toolbar.py                  (the projection engine)
#   app/templates/components/smart_toolbar.html (the renderer partial)
#   .devin/rules/12-state-driven-actions.md    (the standing rule)
#   .devin/skills/smart-toolbar/SKILL.md       (the build/audit skill)
#   .github/prompts/smart-toolbar.prompt.md    (Copilot prompt mirror)
#   + appends the .smart-toolbar__* CSS block to static/css/ssot-design-system.css
#   + appends the [data-confirm] delegation to static/components/feedback.js
#
# Run from the module root:  powershell -File setup_smart_toolbar.ps1
# Or target another module:  powershell -File setup_smart_toolbar.ps1 -TargetRoot C:\path\to\module
#
# NOTE for other targets: the engine reads action.danger from each action —
# if the target's QuickAction-equivalent has no `danger` field, confirm falls
# back to the non-destructive style. Add `danger: bool = False` there if needed.

param(
    [string]$TargetRoot = $PSScriptRoot
)

$ErrorActionPreference = "Stop"

function Ensure-Dir($path) {
    if (-not (Test-Path $path)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
}

$engine = @'
"""
Smart Toolbar - state-driven action projection
================================================

Given an entity's current state and a per-state rule map, project exactly
which actions render - and in what role:

- one PRIMARY action (the next real step - rendered ``.btn--primary``)
- up to ``max_visible`` CONTEXTUAL actions inline (``.btn--ghost`` /
  ``.btn--danger``)
- the remainder behind the template's native ``<details>`` overflow menu

Actions that are not valid in the current state are never rendered - this
repo does not show disabled buttons. See
``.devin/rules/12-state-driven-actions.md``.

Actions are ``app.core.action_maps.QuickAction`` entries - or any mapping /
object exposing ``action_id`` (or ``id``), ``label``, ``target`` (or
``endpoint``), ``action_type``, ``confirmation_prompt`` (or ``confirm``),
and ``danger``. Rules map a state name to a ``StateRule``::

    DOCUMENT_RULES = {
        "DRAFT":   StateRule(primary="submit", contextual=("edit", "delete")),
        "PENDING": StateRule(primary="download", contextual=("share",)),
        "FILED":   StateRule(contextual=("download", "share")),
    }

In the route::

    return templates.TemplateResponse(
        "doc_detail.html",
        {
            "request": request,
            "doc": doc,
            "toolbar": project_toolbar(
                doc.status,
                actions=DOCUMENT_ACTIONS,
                rules=DOCUMENT_RULES,
                resolve=resolve_action_url,
            ),
        },
    )

``resolve`` is a callable ``action -> url`` that goes through the
navigation registry / module contract - URL strings are never hardcoded
here (.devin/rules/03-ssot-redirects.md). When ``resolve`` is omitted the
action's ``endpoint``/``target`` field is used verbatim.

Rendered by ``app/templates/components/smart_toolbar.html``, which expects::

    {"primary": entry|None, "visible": [entry, ...], "overflow": [entry, ...]}
    entry = {"id", "label", "endpoint", "method", "confirm", "danger"}
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

# Action types that render as plain links (GET). Anything else posts a form.
_LINK_TYPES = {"navigate", "download", "share", "external"}


@dataclass(frozen=True)
class StateRule:
    """Which actions are valid in one state, and which is the next step."""

    primary: str | None = None  # action_id promoted to the one main CTA
    contextual: tuple[str, ...] = ()  # ordered; first `max_visible` inline


def _field(action: Any, key: str, default: Any = None) -> Any:
    if isinstance(action, Mapping):
        return action.get(key, default)
    return getattr(action, key, default)


def _action_type(action: Any) -> str:
    raw = _field(action, "action_type", "") or ""
    return str(raw).rsplit(".", 1)[-1].lower()


def _entry(action: Any, resolve: Callable[[Any], str] | None) -> dict[str, Any]:
    return {
        "id": _field(action, "action_id") or _field(action, "id"),
        "label": _field(action, "label", ""),
        "endpoint": (
            resolve(action)
            if resolve
            else (_field(action, "endpoint") or _field(action, "target") or "#")
        ),
        "method": _field(action, "method")
        or ("GET" if _action_type(action) in _LINK_TYPES else "POST"),
        "confirm": _field(action, "confirmation_prompt") or _field(action, "confirm"),
        "danger": bool(_field(action, "danger", False)),
    }


def project_toolbar(
    state: str,
    *,
    actions: Mapping[str, Any],
    rules: Mapping[str, StateRule],
    max_visible: int = 3,
    resolve: Callable[[Any], str] | None = None,
) -> dict[str, Any]:
    """Project the toolbar contract for ``components/smart_toolbar.html``.

    ``rules`` maps state names (matched case-insensitively) to ``StateRule``.
    A state missing from ``rules`` projects an empty toolbar - nothing
    renders. Rule entries naming an action absent from ``actions`` are
    skipped silently: fewer buttons is a safe failure, a broken button is
    not.
    """
    rule = (
        rules.get(state)
        or rules.get(str(state).upper())
        or rules.get(str(state).lower())
    )
    if rule is None:
        return {"primary": None, "visible": [], "overflow": []}

    def entry(key: str | None) -> dict[str, Any] | None:
        action = actions.get(key) if key else None
        return _entry(action, resolve) if action is not None else None

    contextual = [e for key in rule.contextual if (e := entry(key)) is not None]
    return {
        "primary": entry(rule.primary),
        "visible": contextual[:max_visible],
        "overflow": contextual[max_visible:],
    }
'@

$template = @'
{#
  Smart toolbar - state-projected action row.

  Contract:
    Input:  toolbar - output of app.core.smart_toolbar.project_toolbar()
            {"primary": action|None, "visible": [action...], "overflow": [action...]}
            Each action: {id, label, endpoint, method ("GET"/"POST"),
                          confirm (str|None), danger (bool)}
    Renders ONLY valid actions - never disabled buttons
    (rule .devin/rules/12-state-driven-actions.md).
    One primary CTA + up to 3 contextual inline; extras sit behind the
    native <details> overflow. Zero page-level JavaScript - confirmations
    are handled globally by SemptifyFeedback via [data-confirm].

  Usage:  {% include "components/smart_toolbar.html" with context %}
#}
{% if toolbar and (toolbar.primary or toolbar.visible or toolbar.overflow) %}
{% macro _action(a, cls) %}
  {%- if a.method == "GET" -%}
  <a class="{{ cls }}" href="{{ a.endpoint }}"{% if a.confirm %} data-confirm="{{ a.confirm }}"{% if a.danger %} data-confirm-danger{% endif %}{% endif %}>{{ a.label }}</a>
  {%- else -%}
  <form class="smart-toolbar__form" action="{{ a.endpoint }}" method="post"{% if a.confirm %} data-confirm="{{ a.confirm }}"{% if a.danger %} data-confirm-danger{% endif %}{% endif %}>
    <button type="submit" class="{{ cls }}">{{ a.label }}</button>
  </form>
  {%- endif -%}
{% endmacro %}
<div class="smart-toolbar flex gap-3" role="toolbar" aria-label="Actions">
  {% if toolbar.primary %}{{ _action(toolbar.primary, "btn btn--primary") }}{% endif %}
  {% for a in toolbar.visible %}{{ _action(a, "btn btn--danger" if a.danger else "btn btn--ghost") }}{% endfor %}
  {% if toolbar.overflow %}
  <details class="smart-toolbar__overflow">
    <summary class="btn btn--ghost" aria-label="More actions">&#8942;</summary>
    <div class="smart-toolbar__menu">
      {% for a in toolbar.overflow %}{{ _action(a, "smart-toolbar__menu-item" ~ (" text-error" if a.danger else "")) }}{% endfor %}
    </div>
  </details>
  {% endif %}
</div>
{% endif %}
'@

$rule = @'
---
description: State-Driven Action Toolbars - the backend projects which actions render from entity state; never show disabled buttons; 1 primary + <=3 contextual + native <details> overflow
---

# State-Driven Action Toolbars

*(Standing rule, 2026-11-23. Companions: `10-progressive-disclosure.md` - what the
page shows at all; `11-zen-algorithms.md` - how much gets built; `03-ssot-redirects.md`
- where actions point.)*

## The rule

1. **Actions are projected from state - never gated by template `{% if %}` chains.**
   Given an entity's state, the backend decides which actions exist via
   `app.core.smart_toolbar.project_toolbar(state, actions=..., rules=...)`.
   Templates render the projected set verbatim - no state logic in Jinja.
2. **Never render disabled actions.** If an action isn't valid in the current
   state it is not in the DOM at all - no `disabled` buttons, no grayed-out
   "can't do this yet" affordances. Per progressive disclosure: availability
   follows situational need, so a *valid* action is never withheld either.
3. **One primary + at most 3 contextual.** Each state maps to at most one
   primary CTA (`.btn--primary`, the next real step) and at most three inline
   contextual actions (`.btn--ghost`; `.btn--danger` only for genuinely
   destructive actions). Anything beyond that goes in the native `<details>`
   overflow menu - never a fourth inline button.
4. **Native HTML before JavaScript.** Overflow = `<details>`/`<summary>`;
   confirmations = `SemptifyFeedback.confirm` via `data-confirm` attributes
   (delegated globally in `static/components/feedback.js`). Native
   `confirm()`/`alert()`/`prompt()` are banned repo-wide. Any additional JS
   must be vanilla and shared - never per-page inline handlers.
5. **Endpoints are SSOT-resolved.** `project_toolbar`'s `resolve` maps each
   action to its URL through the navigation registry / module contract - never
   hardcode URL strings (rule 03).
6. **Styling is design-system only.** `.btn--*` classes plus the
   `.smart-toolbar__*` block inside `static/css/ssot-design-system.css`. No new
   CSS files, no inline styles, no card borders - the overflow menu separates
   via background + elevation tokens.

## Where it binds

- Detail/action views that expose state-dependent operations (document status,
  filing status, request lifecycle).
- It is the **deterministic floor** - what *can* be done here, right now. It
  does not replace `next_step_path` (chronological "your path" sequencing) or
  `action_router` (AI-ranked suggestions).
- Workflow: `.devin/skills/smart-toolbar/SKILL.md` - mirrored as
  `.github/prompts/smart-toolbar.prompt.md`.
'@

$skill = @'
---
name: smart-toolbar
description: Add or audit state-driven action toolbars - project which actions render from entity state via app.core.smart_toolbar.project_toolbar + components/smart_toolbar.html. Never render disabled buttons; 1 primary + <=3 contextual + native <details> overflow. Use when a detail/action view needs state-dependent buttons, when converting template-side {% if %} button chains, or for a subtractive declutter pass on an action-heavy page.
---

# Skill

## Smart Toolbar - build & audit procedure

Canonical rule: `.devin/rules/12-state-driven-actions.md`.
Engine: `app/core/smart_toolbar.py` (`project_toolbar`, `StateRule`).
Renderer: `app/templates/components/smart_toolbar.html`.
Confirmations: `SemptifyFeedback.confirm` via `data-confirm` attributes,
delegated in `static/components/feedback.js` - native `confirm()` is banned.
The general subtractive pass belongs to the `zen-algorithms` skill - run it
first; this skill owns only the toolbar-specific checks.

## Build a state-driven toolbar

1. **Map states first.** List every entity state on the page and the actions
   valid in each, as a table, before touching code. If the states aren't
   clear, stop and ask - don't guess a lifecycle.
2. **Define rules beside the router that owns the page:**
   `RULES = {"DRAFT": StateRule(primary="submit", contextual=("edit", "delete")), ...}`
   Reuse an existing `QuickAction` map from `app/core/action_maps.py` where
   one covers the domain.
3. **Project in the route:** pass
   `toolbar=project_toolbar(entity.status, actions=..., rules=RULES, resolve=...)`
   in the `TemplateResponse` context. `resolve` maps each action to its URL
   through `navigation.get_stage` / contract routes - never hardcode URLs
   (rule 03).
4. **Render:** `{% include "components/smart_toolbar.html" with context %}`.
   Styling is `.btn--*` + `.smart-toolbar__*` from `ssot-design-system.css`
   only - no new CSS files, no inline styles.
5. **Confirmations:** set `confirmation_prompt` on the action - the template
   emits `data-confirm` and `SemptifyFeedback.confirm` handles the dialog.
   Set `danger=True` for destructive actions (`.btn--danger` + error-styled
   confirm dialog).
6. **Verify per the `gui` skill** when a live page changed: running app,
   375px + 1280px, eye-path audit.

## Audit an existing page (subtractive pass)

1. Zen pass first (`.devin/skills/zen-algorithms/SKILL.md`): goal -> minimum
   set -> justify rest -> subtract-first -> fewer parts.
2. Then toolbar checks - each hit is a finding:
   - `disabled` buttons or grayed-out actions in markup?
   - `{% if state == ... %}` / status / phase conditionals deciding button
     visibility inside the template?
   - More than 1 primary-styled or more than 3 inline contextual actions?
   - Native `confirm()` / `alert()` / `prompt()`, inline `onsubmit` /
     `onclick` handlers, or per-page JS that HTML/CSS or `data-confirm`
     could replace?
   - Hardcoded URL strings in template or Python?
   - Parallel CSS instead of `.btn--*` + `.smart-toolbar__*` classes?
3. Refactor: move state->action logic into `StateRule`s + `project_toolbar`,
   swap the button row for the include, delete what falls out.

## Output

Report in plain language: the state table extracted, what was deleted vs.
added, and verification evidence (`python -m py_compile`, Jinja parse, and a
running-app check per the `gui` skill if a live page changed).
'@

$prompt = @'
---
mode: agent
description: Add or audit state-driven action toolbars - project which actions render from entity state via app.core.smart_toolbar.project_toolbar + components/smart_toolbar.html. Never render disabled buttons; 1 primary + <=3 contextual + native <details> overflow. Use when a detail/action view needs state-dependent buttons, when converting template-side {% if %} button chains, or for a subtractive declutter pass on an action-heavy page.
---

<!-- Mirrors .devin/skills/smart-toolbar/SKILL.md - keep both in sync when editing. -->

## Smart Toolbar - build & audit procedure

Canonical rule: `.devin/rules/12-state-driven-actions.md`.
Engine: `app/core/smart_toolbar.py` (`project_toolbar`, `StateRule`).
Renderer: `app/templates/components/smart_toolbar.html`.
Confirmations: `SemptifyFeedback.confirm` via `data-confirm` attributes,
delegated in `static/components/feedback.js` - native `confirm()` is banned.
The general subtractive pass belongs to the `zen-algorithms` skill - run it
first; this skill owns only the toolbar-specific checks.

## Build a state-driven toolbar

1. **Map states first.** List every entity state on the page and the actions
   valid in each, as a table, before touching code. If the states aren't
   clear, stop and ask - don't guess a lifecycle.
2. **Define rules beside the router that owns the page:**
   `RULES = {"DRAFT": StateRule(primary="submit", contextual=("edit", "delete")), ...}`
   Reuse an existing `QuickAction` map from `app/core/action_maps.py` where
   one covers the domain.
3. **Project in the route:** pass
   `toolbar=project_toolbar(entity.status, actions=..., rules=RULES, resolve=...)`
   in the `TemplateResponse` context. `resolve` maps each action to its URL
   through `navigation.get_stage` / contract routes - never hardcode URLs
   (rule 03).
4. **Render:** `{% include "components/smart_toolbar.html" with context %}`.
   Styling is `.btn--*` + `.smart-toolbar__*` from `ssot-design-system.css`
   only - no new CSS files, no inline styles.
5. **Confirmations:** set `confirmation_prompt` on the action - the template
   emits `data-confirm` and `SemptifyFeedback.confirm` handles the dialog.
   Set `danger=True` for destructive actions (`.btn--danger` + error-styled
   confirm dialog).
6. **Verify per the `gui` skill** when a live page changed: running app,
   375px + 1280px, eye-path audit.

## Audit an existing page (subtractive pass)

1. Zen pass first (`.devin/skills/zen-algorithms/SKILL.md`): goal -> minimum
   set -> justify rest -> subtract-first -> fewer parts.
2. Then toolbar checks - each hit is a finding:
   - `disabled` buttons or grayed-out actions in markup?
   - `{% if state == ... %}` / status / phase conditionals deciding button
     visibility inside the template?
   - More than 1 primary-styled or more than 3 inline contextual actions?
   - Native `confirm()` / `alert()` / `prompt()`, inline `onsubmit` /
     `onclick` handlers, or per-page JS that HTML/CSS or `data-confirm`
     could replace?
   - Hardcoded URL strings in template or Python?
   - Parallel CSS instead of `.btn--*` + `.smart-toolbar__*` classes?
3. Refactor: move state->action logic into `StateRule`s + `project_toolbar`,
   swap the button row for the include, delete what falls out.

## Output

Report in plain language: the state table extracted, what was deleted vs.
added, and verification evidence (`python -m py_compile`, Jinja parse, and a
running-app check per the `gui` skill if a live page changed).
'@

$cssBlock = @'

/* ============================================================================
   SMART TOOLBAR - state-projected action row
   (.devin/rules/12-state-driven-actions.md - actions are projected by the
   backend; disabled actions are never rendered at all)
   ============================================================================ */
.smart-toolbar__form { margin: 0; }
.smart-toolbar__overflow { position: relative; }
.smart-toolbar__overflow > summary { list-style: none; user-select: none; }
.smart-toolbar__overflow > summary::-webkit-details-marker { display: none; }
.smart-toolbar__menu {
  position: absolute;
  right: 0;
  top: calc(100% + var(--space-1));
  min-width: 10rem;
  padding: var(--space-1);
  background: var(--bg-page);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  z-index: 30;
}
.smart-toolbar__menu form { margin: 0; }
.smart-toolbar__menu-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: var(--space-2) var(--space-3);
  color: var(--text-primary);
  text-decoration: none;
  background: none;
  border: 0;
  border-radius: var(--radius-md);
  cursor: pointer;
  font: inherit;
}
.smart-toolbar__menu-item:hover { background: var(--primary-50); }
'@

$jsBlock = @'

// ---- [data-confirm] delegation ---------------------------------------------
// Declarative confirmations for the smart toolbar (rule 12): any
// <form data-confirm="..."> or <a data-confirm="..."> routes through
// SemptifyFeedback.confirm - the canonical in-app dialog. Native confirm()
// is banned repo-wide. Add data-confirm-danger for the destructive style.
(function () {
    if (!window.SemptifyFeedback || !window.SemptifyFeedback.confirm) return;

    document.addEventListener('submit', function (e) {
        var f = e.target.closest('form[data-confirm]');
        if (!f) return;
        if (f.dataset.confirmed === '1') { delete f.dataset.confirmed; return; }
        e.preventDefault();
        window.SemptifyFeedback
            .confirm(f.dataset.confirm, { danger: f.hasAttribute('data-confirm-danger') })
            .then(function (ok) {
                if (!ok) return;
                f.dataset.confirmed = '1';
                if (f.requestSubmit) f.requestSubmit(); else f.submit();
            });
    });

    document.addEventListener('click', function (e) {
        var a = e.target.closest('a[data-confirm]');
        if (!a) return;
        if (a.dataset.confirmed === '1') { delete a.dataset.confirmed; return; }
        e.preventDefault();
        window.SemptifyFeedback
            .confirm(a.dataset.confirm, { danger: a.hasAttribute('data-confirm-danger') })
            .then(function (ok) {
                if (!ok) return;
                a.dataset.confirmed = '1';
                a.click();
            });
    });
})();
'@

$files = @{
    "app\core\smart_toolbar.py"                   = $engine
    "app\templates\components\smart_toolbar.html" = $template
    ".devin\rules\12-state-driven-actions.md"     = $rule
    ".devin\skills\smart-toolbar\SKILL.md"        = $skill
    ".github\prompts\smart-toolbar.prompt.md"     = $prompt
}

$written = 0; $skipped = 0
foreach ($rel in $files.Keys) {
    $dest = Join-Path $TargetRoot $rel
    Ensure-Dir (Split-Path $dest -Parent)
    if (Test-Path $dest) { Write-Host "exists, skipping: $rel"; $skipped++ }
    else { Set-Content -Path $dest -Value $files[$rel] -Encoding UTF8; Write-Host "wrote: $rel"; $written++ }
}

$cssPath = Join-Path $TargetRoot "static\css\ssot-design-system.css"
if (Test-Path $cssPath) {
    if ((Get-Content $cssPath -Raw) -match '\.smart-toolbar__menu') {
        Write-Host "exists, skipping: smart-toolbar CSS block"; $skipped++
    } else {
        Add-Content -Path $cssPath -Value $cssBlock -Encoding UTF8
        Write-Host "appended: smart-toolbar CSS block"; $written++
    }
} else { Write-Host "WARNING: $cssPath not found - CSS block not applied" }

$jsPath = Join-Path $TargetRoot "static\components\feedback.js"
if (Test-Path $jsPath) {
    if ((Get-Content $jsPath -Raw) -match 'data-confirm\] delegation') {
        Write-Host "exists, skipping: data-confirm delegation"; $skipped++
    } else {
        Add-Content -Path $jsPath -Value $jsBlock -Encoding UTF8
        Write-Host "appended: data-confirm delegation"; $written++
    }
} else { Write-Host "WARNING: $jsPath not found - data-confirm delegation not applied" }

Write-Host "`nDone. $written written/appended, $skipped already present."
Write-Host "Reminder: actions need a 'danger' field (added to QuickAction in this repo)."
