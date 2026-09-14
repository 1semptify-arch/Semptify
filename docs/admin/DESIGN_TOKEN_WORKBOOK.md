# Semptify Design Token Workbook

**Purpose:** Review every active design token in `static/css/ssot-design-system.css` and decide what stays vs. what changes. This is the adjustment mechanism — the "Design Playground" referenced in the CSS comments was never committed; this workbook replaces it.

**How to use:**
- For each row, write one mark in **DECISION**: `K` = keep · `C` = change (write the new value in "Change to") · `?` = flag for discussion.
- Sections are ordered by leverage — **Section 1 (HSL dials) rethemes the whole app at once**. Most reviews only need Sections 1, 8, and 10.
- When done, hand the marked-up file back. Changes get applied to the `:root` block in `ssot-design-system.css`, then verified live at 375px and 1280px.

**Reviewer:** ____________  **Date:** ____________  **Scope:** ☐ full review ☐ palette only ☐ specific section: ______

---

## Section 1 — HSL Design Dials (highest leverage)

These four dials drive `--color-primary`, `--color-accent`, `--bg-page`, `--text-primary` and everything derived from them. Changing one dial rethemes the app globally.

| Token | Current | Renders as | Controls | DECISION | Change to / notes |
|---|---|---|---|---|---|
| `--h/s/l-primary` | `40 / 12% / 22%` | warm dark brown | primary buttons, headers gradient, links | | |
| `--h/s/l-accent` | `130 / 18% / 42%` | muted green | CTA accent, accent buttons | | |
| `--h/s/l-bg` | `43 / 10% / 97%` | warm paper ≈ `#f8f7f4` | page background + all surface steps | | |
| `--h/s/l-text` | `40 / 10% / 15%` | warm near-black | body text, border color (10% alpha) | | |

**⚠ Flag 1a — two competing "primary" colors.** The dial produces warm brown `hsl(40 12% 22%)`, but the tenant-facing `template-1` header is blue `#0C447C` (Section 7). These disagree — the app shows brown in some places and blue in others depending on which token a component uses. **Decision needed:** should the primary dial move toward the blue family (e.g. `h ≈ 210`), or should template-1 move toward the dial? ☐ dial→blue ☐ template→dial ☐ keep both, document why ☐ discuss

---

## Section 2 — Calm Ramp + Reserved Alarm

| Token | Current | Used for | DECISION | Change to |
|---|---|---|---|---|
| `--color-calm-50→900` | `#f0f4f8 · dce4ed · b8c8d9 · 94a8bf · 7a92a8 · 5c7a99 · 4a6582 · 3a4f66 · 2d3d4f · 1f2b38` | the "calm authority" slate ramp | | |
| `--color-alarm` | `#d97706` (hover `#b45309`) | **real deadlines only** — never emphasis | | |

---

## Section 3 — Semantic Colors (fixed, not dial-derived)

| Token | Current | 50 shade | 800 shade | DECISION | Change to |
|---|---|---|---|---|---|
| `--color-success` | `#10b981` | `#ecfdf5` | `#065f46` | | |
| `--color-warning` | `#f59e0b` | `#fffbeb` | `#92400e` | | |
| `--color-error` | `#ef4444` | `#fef2f2` | `#991b1b` | | |
| `--color-info` | `#3b82f6` | `#eff6ff` | `#1e40af` | | |
| `--color-gray-50→900` | Tailwind ramp `#f9fafb`→`#111827` | — | — | | |

---

## Section 4 — Text & Surfaces

| Token | Current | Controls | DECISION | Change to |
|---|---|---|---|---|
| `--text-secondary` | `#5b6470` | secondary text — **contrast-fixed 5.2:1 AA; don't change without re-verifying** | | |
| `--text-muted` | `#767d8a` | muted text — contrast-fixed | | |
| `--bg-card` | `#ffffff` | card/surface base | | |
| `--bg-surface/muted/field/sidebar/footer` | +1.5 / −3 / −1.5 / −5 / −8 %L steps off bg dial | zone shading ladder | | |
| `--tone-0→900` | `#fff · fafaf8 · f7f7f5 · f0f0ec · e8e3d4 · d8d6c8 · c8c8c0 · a0a098 · 6b6b63 · 4a4a4a · 1a1a1a` | warm-neutral ramp — zone separation instead of borders | | |

---

## Section 5 — Typography

| Token | Current | Controls | DECISION | Change to |
|---|---|---|---|---|
| `--font-sans` | `'Inter'/'IBM Plex Sans'` | body/UI text | | |
| `--font-head` | `'Playfair Display'`/Georgia | headings (not yet applied anywhere) | | |
| `--font-mono` | `'IBM Plex Mono'` | IDs, hashes, code | | |
| Type scale | H1 `22/600` · H2 `17/600` · H3 `15/500` · body `13/400` · label `11/500` | new scale — use this, not legacy rem scale | | |
| `--type-body-leading` | `1.45` | body line height | | |

---

## Section 6 — Space / Shape / Depth / Motion (usually keep)

| Token group | Current | DECISION | Change to |
|---|---|---|---|
| `--space-1→16` | 4·8·12·16·20·24·32·40·48·64 px | | |
| Radius | block `6` · block-lg `10` · input `4` · pill | | |
| Elevation | `--elevation-1→4` (4%→10% alpha) + sticky | | |
| Border | `1px` @ 10% text alpha — **not** the grouping mechanism | | |
| Max widths | 320 → 1280 (`--max-width-7xl`) | | |
| Easing/transitions | out/in/in-out/spring curves; 150/250/350ms | | |
| Z-index | dropdown 100 → tooltip 600 | | |

---

## Section 7 — Template-N Role Palettes

Five 3-color sets (dark header / light body / darker footer) applied via `<body class="template-N">`.

| Class | Role | Header | Body | Footer | DECISION | Change to |
|---|---|---|---|---|---|---|
| `template-1` | Tenants | `#0C447C` | `#f7f7f5` | `#042C53` | | |
| `template-2` | Legal | `#0F6E56` | `#E1F5EE` | `#04342C` | | |
| `template-3` | Advocates | `#534AB7` | `#EEEDFE` | `#26215C` | | |
| `template-4` | Tools/admin | `#5F5E5A` | `#F1EFE8` | `#2C2C2A` | | |
| `template-5` | Donors/public | `#993C1D` | `#FAECE7` | `#4A1B0C` | | |

**⚠ Flag 7a** — `template-5` is coral/CTA-warm. Check it still fits "calm authority, no urgency aesthetics" for public pages.

---

## Section 8 — Zone System ⚠ (known problem — review required)

| Token | Current | Issue | DECISION | Change to |
|---|---|---|---|---|
| `--zone-bg-primary` | `hsl(40 5% 12%)` — **dark** | Zone tokens were derived from the old dark GUI palette; v5 shell is paper-light. Zones may render near-black on a light page. | | |
| `--zone-bg-secondary/tertiary/inverse` | 17% / 23% / 10% L — all dark | same | | |
| `--zone-surface-1→3 / inverse` | card / gray-50 / gray-100 / gray-900 | light-oriented — inconsistent with `--zone-bg-*` | | |
| `--zone-corner-cut/soft` | `0` / `4px` | | | |
| `--zone-gap-tight/standard/loose` | `8` / `24` / `48` px | | | |

**Decision needed:** ☐ re-derive `--zone-bg-*` from the light bg dial (matching `--zone-surface-*`) ☐ keep dark zones intentionally (dark viewer areas) ☐ discuss

---

## Section 9 — Dark Mode Overrides

Applies via `prefers-color-scheme` and `[data-theme="dark"]`.

| Token | Dark value | DECISION | Change to |
|---|---|---|---|
| `--tpl-N-body` (all 5) | `#0a1a2a` / `#0a1a16` / `#100e1a` / `#161614` / `#1a0e0a` | | |
| text | `#f0f0f0` / `#c0c0c0` / `#909090` | | |
| `--bg-page` / `--bg-card` | `#0f172a` / `#1e293b` | | |
| `--zone-surface-*` | `#1e293b` / `#273344` / `#334155` / inv `#0f172a` | | |

---

## Section 10 — Pending Decisions (not tokens, same review pass)

| # | Question | Options | DECISION |
|---|---|---|---|
| 10.1 | Visual direction | ☐ adopt hybrid ☐ adopt Beacon ☐ keep v5 shell | **DECIDED 2026-09-14:** mock-site direction (`handoffs/mock-site`) is canonical — Site Shell v5 is its implementation. The 5 proposals in `mockups/gui-proposals/PROPOSALS.md` are reference-only for borrowable pieces (deadline beacon, FILED/DEADLINE stamps, citation cards). |
| 10.2 | `design-system/` directory — parallel token system, deprecated | ☐ fold needed parts into SSOT file + archive ☐ leave for now | |
| 10.3 | `static/css/themes/` 5-theme switcher (crimson/forest/ocean/royal/slate) — legacy, unrelated to template-N | ☐ retire ☐ keep ☐ wire into template-N | |
| 10.4 | Suspected CSS drift files: `static/design-system.css` (1KB @import shim), `static/css/main.css`, `static/css/semptify.css`, `app/static/css/{style,landing}.css` | ☐ audit which are linked → delete orphans ☐ leave | |
| 10.5 | `static/` chrome policy — ~150 standalone pages without base.html chrome | ~~reachable-via-nav pages get disclaimer footer~~ | **DECIDED 2026-09-14:** no footer retrofit — standalone statics get **rewritten as template pages** (inherit `base.html`/shell chrome for free) and the static versions retired. Deliberately-bare exceptions still stand: `static/911/` crisis page, print-only, admin-internal. |
| 10.6 | `page_router` mount question | ~~mount page_router ☐ migrate pages directly ☐ defer~~ | **DECIDED 2026-09-14:** salvage, don't mount. Keep `PAGE_MANIFEST` as the sitemap inventory (corrected to stop claiming live coverage), keep the contract-guard + placeholder auto-route pattern as the seed for the eventual PageEngine, retire the ~57 dormant pages the system already replaced. |

---

## Apply log

| Date | Applied by | Sections changed | Verified (375px / 1280px) | Commit |
|---|---|---|---|---|
| | | | | |

---

*Source of truth for values: `static/css/ssot-design-system.css` `:root` (lines 20–329) + dark-mode blocks (339–373). If this workbook and the CSS disagree, the CSS wins — update the workbook.*
