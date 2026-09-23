# Shell Visual Quieting — Spec for Sign-off

**Date:** 2026-09-23 · **Author:** devin · **Status:** awaiting Brad sign-off (spec-first per his instruction)
**Origin:** `task-56efbbd3` — Brad's prod eyeball of `/tenant/start`: "card backgrounds too bold,
separations need to be subtle, button text consistent, no-scroll desktop."

> This spec proposes changes to shared shell primitives. The tenant flagship page
> (`tenant_home_next.html`) is spec-locked; the primitives it uses are shared by every
> Site Shell v5 page. Scope options are called out so the blast radius is explicit.

## What Brad actually saw — diagnosis

| Complaint | Root cause in code | Where |
|---|---|---|
| "Very dark colors" | `@media (prefers-color-scheme: dark)` auto-flips the whole shell to dark paper (`#1e1c18`) when the OS/browser is in dark mode — no user toggle involved | `static/css/ssot-design-system.css` ~L339–371, plus `[data-theme="dark"] body.shell` ~L390 |
| "Cards with buttons" / "backgrounds too bold" | `.shell-btn` is a filled rounded box: `background: var(--bg-card)` + `border` + `border-radius` + `min-width: 7rem` — reads as a card, especially in dark mode where `--bg-card` = `#1e293b` | same file, ~L2086–2135 |
| "Separations need to be subtle" | Zone separators use `--bg-muted` hairlines (subtle in light, `#3b3833` in dark); `.shell-panel` and `.shell-btn` add boxed backgrounds on top | ~L2380, L2249 |
| "Button text changes" | `:hover` inverts the button — background goes `--color-primary`, text flips to `--bg-card`, plus `translateY(-2px)` lift | ~L2105 |
| "Scrolling" | Shell is viewport-locked (`100dvh`, `overflow:hidden`); the solo column is taller than the zone so `.shell-main` scrolls internally — feels like page scroll | ~L1830, L1915 |

## Which UI surfaces this touches (the "discern the UIs" step)

Per `docs/planning/B_SIDE_DISPLAY_WINDOW_MAP.md`, the live surfaces are:

1. **Site Shell v5** (`body.shell`) — header/footer chrome + work zone + rail.
   Variants: standard (work-left/rail-right), `shell--solo` (tenant flagship, no rail),
   `shell--dc` (Document Center, rail-left/work-right). All variants share the same
   primitives — a change to `.shell-btn` hits every shell page.
2. **Page Composer / Page Shell pages** — dashboard/library pages; different template
   family, own token vocabulary (partially shared).
3. **UI Composer single-function bodies** (`record_body`, `know_body`, `act_body`) —
   reuse shell tokens, not the grid.
4. **Public pages** (`public_shell` → `shell_base` — also `body.shell`) and **static
   pages** (JS-injected footer; largely outside this change).

**Recommendation:** scope the primitive changes to `body.shell` (all variants) — the
complaints are about the shared primitives, not the tenant page's markup. The tenant
flagship's *content order* stays untouched (locked spec preserved).

## Proposed changes

### 1. Palette — pin shell pages to light paper

Remove the two dark overrides for `body.shell` (the `@media (prefers-color-scheme: dark)`
`html body.shell` block and the `[data-theme="dark"] body.shell` block). The warm-paper
palette is the designed look; dark mode produced the "very dark, in-your-face" rendering.
Non-shell pages keep their existing dark handling.

**Alternative if dark mode must stay:** redesign the dark palette as a separate pass —
do not land both at once.

### 2. De-card the buttons (`.shell-btn`)

- `background: transparent` (was `--bg-card`); keep the hairline `--shell-line` border.
- Drop `min-width: 7rem`; keep `min-height: 2.5rem` for hit target.
- Reduce padding `0.5rem 1.25rem` → `0.375rem 1rem`.
- `.shell-btn--accent` / `--primary`: keep a quiet filled accent for the single primary
  action (filled ≠ card — it's the one "do this" affordance, consistent with the calm
  "Get help now" pattern). Secondary buttons are flat outlines.

### 3. Consistent button text (hover behavior)

- Remove the hover inversion: no background→primary / text→bg-card swap, no `translateY` lift.
- Hover = subtle border-color shift to accent + faint background tint
  (`color-mix(in srgb, var(--color-accent) 8%, transparent)` or a new `--role-tint`-level
  token). Text color never changes.
- Temporary action feedback (e.g., pressed/saving state) is allowed to differ — briefly,
  then returns to consistent text. Matches Brad's instruction exactly.

### 4. Subtle separation

- Zone separators stay hairlines; in dark mode they were `#3b3833` — moot if pinned light.
- `.shell-panel`: border only, `background: transparent` (was `--bg-page` fill + border).
- `.shell-chip`: keep pill outline, drop any fill; padding `0.3rem 0.875rem` → `0.25rem 0.75rem`.
- `.shell-rows a` padding `0.75rem` → `0.5rem 0.25rem`; row hover stays a whisper (`--bg-page`).

### 5. No-scroll desktop

- Tighten vertical rhythm on `shell--solo`: zone margin/padding `1.75rem` → `1.125rem`,
  lede margin `1.75rem` → `1rem`, hero block trims.
- Target: full page fits `100dvh − header − footer` at a 900px-tall desktop viewport with
  typical content (vault disconnected state is the shortest; fully-provisioned is tallest).
- If a fully-loaded page still exceeds the viewport, the internal `.shell-main` scroll
  remains as overflow-only fallback — never a designed interaction. (Flagged, not hidden:
  exact fit depends on `surfacing.sections` count and `path_steps` length.)

### 6. Explicitly NOT changing

- Zone/section **order** (locked spec, chronological rule already satisfied).
- Header/footer chrome, role accents, typography (`Playfair` display font).
- Mobile (`<900px`) stacked-scroll variant — untouched, separate deferred toolset.
- Non-shell surfaces.

## Verification

- `py_compile` n/a (CSS/template only); visual check per GUI skill Step 6 at 1280px and
  375px once Brad approves (IronBee browser tools).
- Eye-path audit per `.cursor/rules/01-gui-chronological-spatial.mdc`.
- Confirm `/tenant/start` fits `100dvh` at 1280×900 with representative content.

## Decision points for Brad

- [ ] Approve pin-to-light for `body.shell` pages (§1)
- [ ] Approve de-carded buttons + consistent text + subtle separators (§2–4)
- [ ] Approve tightened rhythm for no-scroll desktop (§5)
- [ ] Scope: all `body.shell` pages (recommended) vs. `shell--solo` only
