---
name: state-driven-ui
description: Build context-aware smart toolbars and adaptive navigation with a deterministic mode map (finite state machine) and static/js/state-ui.js — zero libraries, no click tracking
---

# Skill

## State-Driven UI — Smart Toolbars & Adaptive Navigation

Use this pattern whenever a toolbar, action bar, or navigation set must change
with context ("what's on screen"). It is a deterministic finite state machine:
the UI is a pure function of application state, driven by a declarative
**mode map**. No external libraries, no click tracking, no runtime AI.

### The pattern

1. **One mode map per surface.** A plain object maps each mode name to the
   actions/items that exist in that mode. Everything the UI can do is visible
   in one table — no hidden `if (x) btn.style.display` branches scattered
   through handlers.
2. **Actions only change state.** `dispatch('new')` sets `state.mode = 'form'`
   and re-renders. Clicks are inputs, not logic. Never mutate the DOM directly
   in an action handler.
3. **Modes come from passive signals.** Selection state, form completeness,
   current stage (`navigation.get_stage`), role, capability flags — never from
   tracked click history.
4. **Rules live in the map.** A button's `disabled: s => !s.draftTitle.trim()`
   is a rule evaluated every render — not a timer, listener, or ad-hoc check.

### The runtime — `static/js/state-ui.js`

Already in the repo. Vanilla JS, zero dependencies, ES5-safe. Three helpers:

```js
// toolbar surface: modes -> buttons
const ui = StateUI.mount({
  el: document.getElementById('toolbar'),
  state: { mode: 'default', selected: null, draftTitle: '' },
  modes: {
    default:  [{ id: 'home', label: 'Home' },
               { id: 'search', label: 'Search' },
               { id: 'new', label: 'New item', cls: 'btn-primary' }],
    selected: [{ id: 'edit', label: 'Edit', cls: 'btn-primary' },
               { id: 'move', label: 'Move' },
               { id: 'delete', label: 'Delete', cls: 'btn-danger' },
               { id: 'clear', label: 'Clear selection', cls: 'btn-ghost' }],
    form:     [{ id: 'save', label: 'Save', cls: 'btn-primary',
                 disabled: s => !s.draftTitle.trim() },
               { id: 'cancel', label: 'Cancel', cls: 'btn-ghost' }],
  },
  dispatch: (id, state, render) => { /* mutate state, then render() */ },
});

// adaptive nav: signal -> item set
StateUI.renderNav(navEl, NAV_MODES[context], activeId, onSelect);
```

Button entries: `{ id, label, cls?, title?, disabled?(state), hidden?(state) }`.
`label` may be a function of state.

### Styling

Component styles live in `design-system/components/state-ui.css` (imported by
`components/index.css`): `.mode-toolbar` (container), `.mode-status` (muted
mode/selection hint), `.mode-nav-item` (+`.active`). Actions reuse the existing
`.btn-*` variants — do not invent new button styles.

### Semptify rules that still apply

- **Signal sources:** stage ids via `app/core/navigation.py` SSOT registries
  (never hardcode paths — `get_stage()`), capability flags, document/item
  selection, form validity.
- **Chronological & spatial ordering** (`.cursor/rules/01-gui-*.mdc`) — the
  toolbar sits with the work it acts on; destructive actions (Delete) are last
  in the mode's button list and visually separated.
- **Calm CTAs** — mode maps use existing `.btn-*` semantics; at most one
  `btn-primary` per mode.
- **Mobile first** — `.mode-toolbar` wraps; verify at 375px and 1280px.
- **Error states** — every mode must still route to help; no dead ends.
- **Copy bans** — labels never say "free", "account", "log in", "sign up",
  "subscription", "premium", "pricing", "trial".

### When NOT to use it

- A static action row that never changes — plain markup is simpler.
- Anything that needs click tracking, heuristics, or runtime AI. This pattern
  is deliberately deterministic: the product runs rule-based and disconnected.
