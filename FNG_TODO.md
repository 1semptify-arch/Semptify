# FNG TODO — "Fix Next, Grunt-work" list
# (FNG = Fn New Guy. Mundane, bounded, non-urgent items. Pick one at a time.)

Last updated: 2026-07-02

---

## Design System — 3 parallel systems currently exist (found during audit)

Semptify currently has **three separate CSS systems** that were never reconciled.
This is why style changes don't always show up where expected. Do not add a
4th system — reconcile into one of the existing three instead.

### System 1 — `app/templates/base.html` inline `<style>` block
- Old dark-navy / card-with-border-radius theme
- Powers the Jinja2 `{% extends "base.html" %}` page templates
- Variables: `--color-bg-primary`, `--color-accent`, `--radius-md`, `--space-lg`, etc.
- **292 usages of these variable names across 27 template files** — DO NOT delete
  or rename these variables without a full visual QA pass (screenshots on every
  affected page). Breaking these silently makes text invisible (white-on-white
  or similar) across dozens of pages.

### System 2 — `static/css/ssot-design-system.css`
- The NEW flat / no-radius / no-shadow / tone-only system from the 2026-07-01
  design handoff (Inter font, `--tpl-1-header` through `--tpl-5-footer` tokens,
  dark mode via `[data-theme="dark"]`)
- Linked from `base.html` — 28 of 31 page templates already have `body_class`
  wired to `template-1` through `template-5` (verified 2026-07-02 — this part
  is actually DONE, contrary to earlier assumption)
- Fixed 2026-07-02: removed base.html's competing `.card` background/border/
  radius/shadow declarations so ssot's flat card style actually renders
  (cascade conflict — base.html loaded after the link tag, so it was winning
  on equal-specificity `.card` rules)

### System 3 — `static/css/main.css` + `static/css/themes/{ocean,forest,royal,crimson,slate}.css`
- A THIRD, older, gradient-based theme system using `data-theme="ocean"` etc.
- Used only by a handful of static (non-Jinja2) dashboard pages:
  `static/tenant/index.html`, `static/advocate/index.html`,
  `static/manager/index.html`, `static/legal/index.html`
- Completely separate token names from System 1 and System 2 — no shared vars
- **Decision needed from project owner:** migrate these 4 pages to the Jinja2
  `base.html` + System 2 approach, or keep them as intentionally separate
  static dashboards? Do not touch until decided.

### Remaining bounded design tasks (safe, one at a time)
- [x] Audit `.card--interactive:hover` and any other base.html rule for leftover
      `box-shadow` that still leaks through from `ssot-design-system.css`'s own
      `.card:hover { box-shadow: var(--shadow-md); }` — spec says zero shadows
- [ ] Replace emoji nav icons in `base.html:490-494` header nav
      (🏠 📚 🏢 🔧 🆘) with plain text or line icons per design handoff
      ("icons: single-color line icons only... never emoji") — cosmetic, low priority
- [ ] Visually verify (via Playwright `mcp3_browser_navigate` + screenshot) that
      each of the 5 template color sets actually renders correctly in production
      after a deploy — has not been visually confirmed yet, only verified by
      reading CSS source
- [x] Confirm nothing sets `document.documentElement.dataset.theme = 'dark'` or
      similar anywhere — searched `app/templates` and `static`, found ZERO JS
      that ever sets `data-theme="dark"`. Added `@media (prefers-color-scheme: dark)`
      fallback to `ssot-design-system.css` so dark mode is reachable without a
      toggle UI.

---

## Tenant Home Rebuild (carried over from BUILD_STATE.md)
- [ ] Fix broken emoji encoding in `tenant_home.html` (shows `?` instead of emoji)
- [ ] Fix `/tenant/journal` link → should point to `/tenant/timeline`
- [ ] Fix `/documents` link → non-existent route, needs correct target

---

## How to use this file
- Pick ONE item, do it, delete it from this file when done.
- If an item turns out to be bigger than expected, stop, ask the user before
  proceeding (per AGENTS.md root-cause-fix discipline).
- Do not let this file grow into a dumping ground — if something is urgent,
  it belongs in `BUILD_STATE.md` / `ACTIVE_CONTEXT.md`, not here.
