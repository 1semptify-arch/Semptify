# Semptify Page Shell

Implementation of the pillar-mixer backbone spec
(`temp/semptify_pillar_mixer_backbone.md`) — **shell + rendering engine
only**. Does not pick blends, compute intensity, or gather case data.
Feed it a validated `PageConfig`, get back rendered HTML for the shell.

## Scope

Built per the task brief:

- **Page config loader** (`loader.py`) — validates §4 schema, rejects
  configs missing `major_pillar` or with an unrecognized `blend` name.
- **Skeleton selector** (`skeletons.py`) — four skeletons from §10 as
  grid-template-areas. `major_pillar` selects the skeleton; no other
  logic overrides this.
- **Zone + Block rendering** (`renderer.py`) — `Zone` + three `Block`
  kinds (`InputBlock`, `InfoBlock`, `OutputBlock`) per §8. One renderer
  per block kind, not per page.
- **Level → prominence** (`zones.py`) — single configurable function
  `level_to_prominence()` implementing the 0–25 / 26–60 / 61–100
  threshold rule. Hand-tunable in one place.
- **Level → visual weight** (`zones.py`) — single configurable function
  `level_to_visual_weight()` implementing the §11 shade-depth rule
  (0–30 low / 31–70 moderate / 71–100 deep). Drives background-color
  shifts and gradients only — never borders, shadows, or alert styling.
  Applied to all four zones; no per-skeleton special cases.
- **Layout mechanics** (`page_shell.css`) — `.page-shell` is
  `height: 100vh; overflow: hidden;` CSS Grid. `clamp()` for
  spacing/typography. Zones scale via `fr` units. Individual zones get
  `overflow-y: auto` only when their own content overflows. Visual
  language per §11: no cards, no borders, no shadows — zone separation
  via background-color shifts, gradients, and shape only.
- **Mobile renderer** (`page_shell.css`, media query ≤1024px) — §12:
  one config, two renderers. Below 1024px the same `PageConfig` renders
  as a single-column scrolling document (not the desktop poster
  behavior). Zone stack order: `major_pillar` first, then remaining
  non-GOVERN zones in fixed default order (KNOW → RECORD → ACT,
  skipping the major_pillar). GOVERN is NOT in the scroll stack — it
  renders as a pinned band at the bottom of the viewport
  (`position: sticky; bottom: 0;`), staying visible regardless of
  scroll. Breakpoints: `<768px` mobile, `768–1024px` mobile with wider
  padding (via existing `clamp()` vw scaling — no separate query),
  `>1024px` desktop skeleton renderer (§10). CSS-only implementation
  via media queries + `order` property — no JS viewport detection, no
  renderer-side branching (the skeleton class already encodes
  major_pillar, so CSS can order zones without Python changes). §11
  visual language applies identically on mobile — same
  `visual-weight-{low|moderate|deep}` classes, same
  `level_to_visual_weight()` helper, device-agnostic.
- **GOVERN hard rules** (`govern.py`) — floor by risk_tier + override
  authority (GOVERN `suppresses_act_block` filters ACT blocks). GOVERN
  always has its own dedicated grid area in all four skeletons.

## Files

```text
app/modules/page_shell/
  __init__.py
  models.py          # Pydantic: PageConfig, Zone, InputBlock, InfoBlock, OutputBlock
  blends.py          # §2 named blend presets
  skeletons.py       # §10 four skeletons (grid-template-areas)
  govern.py          # §3 GOVERN floor + override rules
  zones.py           # §8 level → prominence + §11 level → visual weight
  renderer.py        # data-driven zone + three block-kind renderers → HTML
  loader.py          # config loader/validator
  router.py          # /api/page-shell/* endpoints
  register.py        # registration helper
  sample_configs/
    record_focus_demo.json   # major_pillar=record (wide skeleton)
    govern_focus_demo.json   # major_pillar=govern (structurally different + GOVERN override demo)

static/page_shell/page_shell.css        # §9 layout + four skeletons + mobile breakpoint
static/admin/page_shell_demo.html       # working demo (two sample configs)
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/page-shell/health` | Health check |
| GET | `/api/page-shell/skeletons` | List the four skeletons (§10) |
| GET | `/api/page-shell/blends` | List named blend presets (§2) |
| POST | `/api/page-shell/render` | Render a posted page config to HTML |
| GET | `/api/page-shell/demo` | Render both sample configs |

**Demo UI:** `/admin/page_shell_demo.html` — toggle between `record_focus`
and `govern_focus` sample configs, see the rendered shell + the GOVERN
report (clamping + suppressed ACT blocks).

## Demo configs

Two sample configs exercise visibly different skeletons:

- **`record_focus_demo.json`** — `major_pillar: "record"`, blend
  `first_contact`. Wide skeleton: RECORD spans 2/3 width across two
  rows. GOVERN is a full-width bottom strip. Shows a 3-block RECORD zone
  (file upload, date, text) and a 2-block KNOW zone.
- **`govern_focus_demo.json`** — `major_pillar: "govern"`, blend
  `high_stakes_review`. Structurally different: GOVERN is a full-width
  top strip, three secondary zones share a single row underneath.
  Demonstrates the GOVERN override: the `blk_escalate_to_attorney`
  OutputBlock in the GOVERN zone sets
  `suppresses_act_block: "blk_file_with_court"`, so the ACT "File with
  court" button is filtered out of the rendered ACT zone — regardless of
  ACT's level. The demo UI surfaces this in the report bar.

## Assumptions (where the spec was ambiguous)

1. **Row sizing by level (§9 "high-level zone gets 2fr")** — NOT
   implemented. The spec says "when `level` is high for a zone, that
   zone's row can request more `fr` share dynamically (e.g. ACT at level
   90 gets `2fr` instead of `1fr`)." But §7 says the shell shape is
   sacred and §8 says level drives block count/prominence WITHIN a zone.
   I read "shape is sacred" as the stronger rule and kept row sizes
   fixed per skeleton (1fr 1fr auto for focus skeletons, auto 1fr for
   govern_focus). Level drives block count + emphasis styling, not row
   size. If you want dynamic `fr` by level, that's a one-line change in
   `skeletons.py:grid_template_rows()` — flag it and I'll wire it.

2. **Risk tier inference** — the spec's §4 schema puts `risk_tier` on
   the GOVERN channel, but the codebase's canonical `UPLRiskTier` enum
   (`app.core.upl_guardrails`) uses a 6-step monotonic scale (low →
   very_high_do_not_build) rather than the spec's informal red/yellow/green.
   I mapped the 6-step scale to GOVERN floors in `govern.py` and infer
   the page's risk tier by scanning OutputBlocks for the highest
   declared `risk_tier`. The real context engine (out of scope) will
   compute this from case state.

3. **`very_high_do_not_build`** — spec-confirmed permanent rule (§3/§11),
   not an assumption. The loader hard-rejects configs inferred to this
   tier rather than clamping GOVERN. Matches the codebase's UPL policy.

4. **Zone derivation** — if a config omits `zones`, the loader derives
   empty zones from `channels` so the grid still renders all four areas
   (§7: all four zones always exist). Real configs will include `zones`
   explicitly with their blocks.

5. **InfoBlock content** — spec-confirmed field (§8). The shell renders
   a container with `data-content-ref` but does NOT load the referenced
   markdown. Content loading is the composer's job (out of scope per
   task brief). The demo shows the `summary` field in the collapsed view.

6. **Block ordering when capped by prominence** — when
   `level_to_prominence` caps `block_count` below the number of blocks
   in a zone, the renderer takes the FIRST N blocks (spec says a zone is
   an "ordered list" so order is meaningful). No ranking/sorting — that
   would require blend-specific logic (out of scope).

7. **GOVERN visual weight** — §11 deletes the earlier §10 open question
   ("GOVERN strip may get visually heavier in `act_focus`"). GOVERN
   weight is now level-driven via `level_to_visual_weight()` like every
   other zone — no per-skeleton special cases. GOVERN at level ≥71 gets
   the deepest shade on the page; GOVERN at level ≤30 gets the lightest.
   No alert/banner styling anywhere in the shell.

8. **No 5th zone, no deviation from the four skeleton shapes.** Confirmed
   not needed.

9. **`color-mix()` browser support** — **CLOSED.** `color-mix()` browser
   support checked (caniuse, July 2026): 91.2% global, Safari/iOS Safari
   supported since 16.2 (Dec 2022). No fallback needed — confirmed safe,
   no action taken.

10. **Mobile GOVERN pin position for `govern_focus`** — **RESOLVED.** §12
    says "pick bottom unless you hit a reason not to." `govern_focus` is
    that reason: it exists specifically for high-stakes/red-tier pages
    where the disclaimer must be read first (§10). Bottom-pinning it on
    mobile would undo the one thing that skeleton is for, on the pages
    where it matters most. So: `govern_focus` pins GOVERN at the TOP on
    mobile (matches its desktop top-dominant layout and the skeleton's
    high-stakes purpose); the other three skeletons pin bottom (keeps
    major_pillar content visible first on load). Implemented as a one-
    line CSS override in the mobile media query block.

## New ambiguities surfaced this pass

None. All §12 mobile renderer decisions (breakpoints, stack order,
GOVERN pin position) came directly from the spec. The one judgment call
(GOVERN pin position for `govern_focus` on mobile) is documented in
assumption #10 above and resolved — `govern_focus` pins top, the other
three skeletons pin bottom.

## Out of scope (per task brief)

- Context engine (case stage, deadline proximity, risk tier computation)
- Blend selection logic (which blend to pick for a given situation)
- Real content loading (InfoBlock `content_ref` resolution)
- Audit hook firing (logged via GOVERN — wiring is a separate task)
- Case data binding (InputBlock `writes_to` field is captured but not wired)

## Verification

```powershell
cd c:\Semptify\Semptify-FastAPI
python -m py_compile app/modules/page_shell\models.py app/modules/page_shell\blends.py app/modules/page_shell\skeletons.py app/modules/page_shell\govern.py app/modules/page_shell\zones.py app/modules/page_shell\renderer.py app/modules/page_shell\loader.py app/modules/page_shell\router.py app/modules/page_shell\register.py
```

Then visit `/admin/page_shell_demo.html` for the live demo.
