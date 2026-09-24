---
name: gui
description: Canonical procedure for any Semptify GUI/UI work — pages, templates, CSS, layout, styling. Use before building or editing any visual surface.
---

# Skill

## Semptify GUI Work — Canonical Procedure

Run this before building or editing any page, template, stylesheet, or visual component.
Skipping it is how the design system drifts and Known Failures repeat.

### Step 1: Read the canonical sources — in this order

1. `docs/admin/SSOT_DESIGN_SYSTEM.md` — the design system: ONE CSS file, tokens, utilities, component classes.
2. `GUI_VISUAL_BLUEPRINT.md` (master-repo root) — the visual blueprint.
3. `docs/admin/Semptify_Site_GUI_Framework.md` — site GUI framework.
4. `ACTIVE_CONTEXT.md` § Core Rules — current layout doctrine (shell variants, page models, tapering).
5. `BUILD_STATE.md` — last 2 entries (what chrome is live right now).

### Step 2: Read the binding rules

- `.cursor/rules/01-gui-chronological-spatial.mdc` — chronological task ordering + eye-path audit. **Mandatory before marking any GUI task done.**
- `.devin/rules/10-progressive-disclosure.md` — capability revelation / Familiarity Tapering.
- `.devin/rules/01-product-positioning.md` — pillars + positioning language.
- `.devin/rules/03-ssot-redirects.md` — no hardcoded URLs anywhere (Python or templates).

### Step 3: Use the canonical chrome — do not invent layout

Current canonical chrome is **Site Shell v5** (see BUILD_STATE.md 2026-09-12):

- `app/templates/shell_base.html` + `app/templates/body/*_shell.html` — asymmetric rail frame: **work zone left, supporting rail right** (Document Center is the exception: rail left, work right).
- Paper background, thin palette-colored header/footer, transparent regions, liquid root scaling, **no desktop page-scroll**.
- `.shell-side` rail: top-aligned, sticky, viewport-capped.
- `/tenant/start` solo variant — locked spec, don't generalize it.
- Header and footer are fixed universal templates — never vary per page. Footer is injected by `static/js/unified-footer-loader.js`.

Page models (two independent, never competing):

- **Page Composer + Page Shell** — blended multi-pillar pages (dashboards, Concierge, library browse). `static/templates/page-shell.html` and `component-examples.html` are the canonical markup patterns.
- **UI Composer body templates** — strict single-function pages: `app/templates/body/record_body.html`, `know_body.html`, `act_body.html`, `gui_shell.html`, `public_shell.html`, `composer_preview_shell.html`. One function, one page; one pillar per page. These reuse Page Shell CSS token vocabulary but not its grid/skeleton/blend logic.

Form-factor variants: **desktop-poster vs mobile-stacked-scroll** — apply both, every page.

### Step 4: Styling rules — non-negotiable

- `static/css/ssot-design-system.css` is the ONLY design-system file. Use its tokens, utility classes, and component classes.
- **No card borders.** Zone-based background separation to group controls.
- **Do not create new CSS files or inline styles** without checking the SSOT file first — `static/design-system.css`, `static/css/main.css`, `static/css/semptify.css`, and `app/static/css/` are suspected drift; confirm what's actually linked before extending or deleting anything (Known Failure #17: never delete a referenced static asset mid-migration).
- Themes live in `static/css/themes/` (crimson, forest, ocean, royal, slate) — extend there, not ad hoc.

### Step 5: Copy rules — non-negotiable

- **NEVER** "free", "account", "log in", "sign up", "subscription", "premium", "pricing", "trial" on user-facing surfaces (factual descriptions of external resources excepted).
- North star is **Time to Real Help** — no engagement mechanics, no urgency tactics, no dark patterns. Calm CTAs ("Get help now" pattern).
- No dead ends — every error/empty state routes toward real help.

### Step 6: Verify against the running app — required

Do not mark GUI work done on code review alone.

1. Start the app: `.\venv311\Scripts\Activate.ps1` then `python -m uvicorn app.main:fastapi_app --host 127.0.0.1 --port 8001 --reload`.
2. **IronBee browser tools only** (no other browser agents): `navigation_go-to` → exercise the change (click/fill/submit — don't just look) → `content_take-screenshot` and/or `a11y_take-aria-snapshot` → `o11y_get-console-messages` for errors.
3. Check **both viewports**: 375px (mobile-stacked-scroll) and 1280px (desktop-poster).
4. **Eye-path audit**: trace top-left → down/right through the page. Every earlier-step control must sit above/left of later-step controls. If not, rearrange before submitting.
5. Navigation changes: `python tests/test_ssot_architecture.py` must pass.

### Watch for

- `.html` static files can shadow Jinja routes (`/about.html` vs `/about`) — check `static/` before assuming a route renders your template.
- Contract copy is contract-shaped, not user-friendly — templates expose title/description override blocks; use them rather than editing contracts.
- Advocate/legal shell variants are CSS-wired but dormant — no pro roles exist in this repo (PR #317); they revive in the add-on repo.
- Mobile toolset is a separate deferred workstream — desktop shell is the rolled-out baseline.
