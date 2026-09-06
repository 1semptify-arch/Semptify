# Composer/Preview Shell — Module Contract Template

Every function page that uses `body/composer_preview_body.html` must fill out
this contract. It is the page's layout spec — fill it in before migrating a
page, keep it as a `{# ... #}` comment at the top of the page template, and
record the declared values in the `{% set %}` lines.

## Fill-in template

```text
Module:            <module>:<function_group>      (e.g. journal:journal_create)
Pillar tag:        [record | know | act | govern] (internal — never user-facing)
Function:          <one sentence: what the tenant DOES on this page>

Inputs:
  - <name>, <type>, [required | optional], <source>, <space: small | medium | large>
  (repeat per field)

Outputs (preview region):
  - <what renders> — [live-updating | submit-only]
  - empty state:   <what the tenant sees before any output>
  - error state:   <what the tenant sees on failure>

Actions:
  - <name> — placement [top-bar | composer-top | composer-bottom |
    preview-bottom | help-bottom], priority [primary | secondary]

Preview behavior:
  - empty state:  <required — a blank preview pane reads as broken>
  - error state:  <required>
  - live update trigger: <event that refreshes preview, or "none — submit only">

Layout:
  primary:           [composer | preview]
  ratio:             [3fr 2fr | 2fr 3fr | 1fr 1fr]      (constrained set only)
  control_placement: [top | bottom | side]
  mobile_order:      [composer, preview, help] or a permutation —
                     DOM order == visual order == this order (a11y, non-negotiable)
```

## Rules

1. **Only the declared option set.** If a page seems to need a new ratio or
   placement, stop — propose it as a shell change, don't hand-tune the page.
2. **DOM order = visual order.** Regions render in `shell_mobile_order`
   sequence on every viewport. Screen readers and keyboard follow the DOM.
3. **Help is a first-class region.** If the page has narration, contract
   I/O, or next-step guidance, it belongs in the help block, not squeezed
   into composer.
4. **Empty states are mandatory.** The preview region must never render
   blank.
5. **No new color, font, or spacing tokens.** The shell and all pages on it
   reuse `ssot-design-system.css` and Page Shell zone/block vocabulary only.
6. **Ordering follows the task.** First required action top/left, final
   action bottom/end, destructive or low-frequency actions last
   (`.cursor/rules/01-gui-chronological-spatial.mdc`).

## Worked example

See `app/templates/pages/journal_create_guide.html` — the contract comment at
the top of the file is the canonical example.
