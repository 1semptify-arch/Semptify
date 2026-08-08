# Semptify — 5 GUI Design Proposals (Website + Webapp)

> Grounded in: `AGENTS.md`, `PROJECT_BIBLE.md`, `Semptify_Site_GUI_Framework.md`,
> `static/css/ssot-design-system.css`, `app/core/navigation.py`.
> Audience: stressed tenants, often on phones, low bandwidth, in a parking lot.
> Mission: public-service housing-rights tool — NOT a commercial product.

## Shared constraints (all 5 proposals honor these)

- **Forbidden words**: "free" (about Semptify), "accounts", "log in", "sign up",
  "subscription", "upgrade", "premium", "paid plan", "trial", "pricing".
- **Tenant-side stance**, lawful & factual, no victim-blaming, no false "both sides".
- **Calm, clear, trustworthy** — reduce panic to clarity.
- **Mobile-first, low-bandwidth** — design for a phone in a parking lot.
- **Privacy-first** — data lives in the user's own cloud storage, not on Semptify servers.
- **WCAG AA** — screen readers, keyboard nav, reduced motion, skip link.
- **No rounded corners** (per 2026-07-01 design handoff).
- **Four-pillar model** — RECORD, KNOW, ACT, GOVERN (RECORD is primary).
- **SSOT navigation** — all redirects via `navigation.get_stage(...)`.
- **No advertising, no tracking pixels, no affiliate links.**

Each proposal differs across **≥3 axes**: typography pairing, palette/mood, layout
structure, interaction style, density/composition, and primary persona served.

---

## Proposal 1 — "Courthouse Steps"

**One-line**: Civic legal authority — feels like walking into a legal aid clinic.

| Axis | Direction |
| ------ | ----------- |
| Primary persona | The Court-Bound (has a hearing date) |
| Typography | **Source Serif 4** (headings, body for legal text) + **Inter** (UI labels, nav) + **IBM Plex Mono** (citations, dates, case IDs) |
| Palette | Paper cream `#F6F1E7` · Ink black `#1A1A1A` · Oxblood `#7A1F1F` (urgency only) · Slate rule `#3A4A5A` |
| Layout | Columnar, legal-brief style. Two-column reading grid on desktop; single column on mobile. Visible rule lines between sections. |
| Interaction | Disclosed in chapters. "Next step" advances like turning a page. No infinite scroll. |
| Density | Medium-high — text-forward, citations visible, footnotes anchored. |
| Memorable thing | A **docket-style header strip** on every page: `Case: — · Stage: RECORD · Next deadline: —` that fills in as the user progresses. |
| Imagery | None. Typography and rule lines do the work. Optional subtle paper grain. |
| Why it fits | Tenants facing court need to feel they are in a serious, lawful, accountable place — not a startup. Serif + oxblood + columnar grid reads as "the law is real and on your side." |
| Risks | Can feel formal/cold for The Blindsided Tenant in acute panic. Mitigated by calm copy + a single persistent "What this means for you" plain-language box per page. |

---

## Proposal 2 — "The Calm Room"

**One-line**: Therapeutic breathing room — feels like sitting with a steady social worker.

| Axis | Direction |
| ------ | ----------- |
| Primary persona | The Blindsided Tenant (just got a notice, panicking) |
| Typography | **Inter** at large sizes, loose leading (1.7) + **IBM Plex Mono** only for metadata. Optional **Fraunces** for the single welcome headline. |
| Palette | Warm sand `#EDE6D6` · Sage `#5C6B5A` · Deep slate `#2B3340` · Single warm amber `#C98A2B` for the one next-action button per screen |
| Layout | Single-column reading flow, generous whitespace, max-width ~640px. Progressive disclosure: **one question at a time**, never a wall of options. |
| Interaction | One primary action per screen. "Continue" is always the obvious next breath. No menus with >5 items visible at once. |
| Density | Low — deliberately airy. Whitespace is the design. |
| Memorable thing | A **"Breathe. Here's your next step."** persistent card that always shows exactly one action — never a dashboard of 12 tiles. |
| Imagery | None. Soft CSS gradients only (sage→sand), no photos. |
| Why it fits | The framework doc literally says "Reduce panic to clarity." This proposal makes that the entire layout strategy, not just copy. Best for someone reading an eviction notice in their car. |
| Risks | Low density wastes screen on desktop power-users (The Builder). Mitigated by a deliberate "All steps" expandable index for repeat users. |

---

## Proposal 3 — "The Field Notebook"

**One-line**: Evidence-first utilitarian — feels like a detective's case binder.

| Axis | Direction |
| ------ | ----------- |
| Primary persona | The Builder (ongoing dispute, logging evidence over time) |
| Typography | **IBM Plex Mono** (metadata strips, timestamps, tags) + **Inter** (body) + **Source Serif 4** italic (handwritten-note quotes) |
| Palette | Kraft `#D9C7A3` · Ink `#232020` · Manila folder ochre `#B8862F` · Stamp red `#9E2B25` (only for "FILED" / deadline-stamped items) |
| Layout | Card grid of **evidence cards** — each card has a mono metadata strip (date · type · source · status) and a body. Timeline rendered as railroad tracks down the left rail. |
| Interaction | Drag-to-reorder evidence on desktop; long-press on mobile. Quick-capture bar pinned at bottom: "Add photo · Add note · Add communication." |
| Density | High — information-dense by design, but each card is self-contained and scannable. |
| Memorable thing | **Stamp marks** — a rotated mono "FILED · 2026-07-22" stamp on saved evidence, and a red "DEADLINE · 3 DAYS" stamp on time-sensitive items. |
| Imagery | Subtle paper/kraft texture (CSS, no external). No photos unless the user uploaded them. |
| Why it fits | The Builder's whole job is accumulating evidence. This proposal makes the vault feel like a physical case binder — tangible, organized, court-ready. |
| Risks | Aesthetic may read as "old-fashioned" to some. Mitigated by keeping Inter as the body face so it doesn't feel like a museum piece. |

---

## Proposal 4 — "The Beacon"

**One-line**: High-contrast emergency portal — maximum legibility on a phone in a parking lot.

| Axis | Direction |
| ------ | ----------- |
| Primary persona | The Blindsided Tenant + The Court-Bound (deadline-driven) |
| Typography | **Inter Display** (or Inter at 700/800) for headlines + **IBM Plex Sans** for body + **IBM Plex Mono** for deadlines. Large minimum type (18px body, 24px+ on mobile). |
| Palette | Pure black `#000` · Pure white `#FFF` · **One signal color**: amber `#F5A623` for deadlines, red `#D7263D` for emergencies only. Nothing else. |
| Layout | Deadline-forward dashboard. Top of every screen: **"Your next deadline: — days away"** in high contrast. Big tap targets (min 48×48px). 5-core nav as a thumb-reachable bottom bar on mobile. |
| Interaction | Everything reachable in ≤2 taps from home. High-contrast focus rings. Reduced-motion respected strictly. |
| Density | Medium — legible, not cramped. Large type limits density by design. |
| Memorable thing | A **deadline beacon** — a persistent high-contrast banner that counts down and turns amber→red as a hearing approaches. The single most important UI element on the site. |
| Imagery | None. Maximum contrast means no decorative imagery. Icons are solid, high-contrast, monochrome. |
| Why it fits | The framework doc: "Design for stress, low bandwidth, and possibly a phone screen in a parking lot." This proposal takes that literally — it's an emergency-services-grade UI. Best WCAG compliance of all 5. |
| Risks | Can feel stark/alarming. Mitigated by calm language in the beacon itself ("You have time. Here's what to do.") so the contrast conveys clarity, not panic. |

---

## Proposal 5 — "The Quiet Library"

**One-line**: Editorial research room — feels like a law library reading room.

| Axis | Direction |
| ------ | ----------- |
| Primary persona | The Preventer (no active dispute, educating) + The Court-Bound (studying) |
| Typography | **Source Serif 4** (headings + long-form law text) + **Inter** (UI) + **IBM Plex Mono** (citations, statute IDs). Heavy typographic hierarchy with horizontal rules. |
| Palette | Deep forest `#1F3A2E` · Parchment `#F2EAD3` · Brass `#A67C2E` · Ink `#1A1A1A`. Forest as primary brand color (distinct from current navy). |
| Layout | Multi-pane on desktop: left = library/law index, center = reading, right = "Your notes / related in your vault." Collapses to single column + drawer on mobile. |
| Interaction | Reading-first. Footnotes/citations are visible and clickable, jumping to the cited statute. "Save to my vault" is a persistent side action. |
| Density | Medium — text-rich but well-rhythm'd with rules and pull quotes. |
| Memorable thing | **Visible citations as first-class UI** — statute numbers (e.g., `Minn. Stat. § 504B.221`) are styled like library catalog cards, clickable, and link to the user's saved notes. |
| Imagery | None. Typography, rules, and a subtle parchment tint. Optional small brass section numerals. |
| Why it fits | The KNOW pillar (Library, State Laws, Context Engine) deserves a reading-room aesthetic, not a dashboard. Appeals to users who need to *understand* before they act. |
| Risks | Multi-pane layout is hard on small phones. Mitigated by a drawer pattern on mobile and a "focus reading mode" toggle that hides the panes. |

---

## Comparison at a glance

| # | Name | Persona | Type pair | Mood | Layout | Density | Memorable element |
| --- | ------ | --------- | ----------- | ------ | -------- | --------- | ------------------- |
| 1 | Courthouse Steps | Court-Bound | Source Serif + Inter + Mono | Civic / lawful | Columnar brief | Med-high | Docket header strip |
| 2 | The Calm Room | Blindsided | Inter (large) + Mono | Therapeutic | Single-column, progressive | Low | "Breathe. Next step." card |
| 3 | Field Notebook | Builder | Mono + Inter + Serif italic | Utilitarian / analog | Evidence-card grid + timeline rail | High | Stamp marks (FILED / DEADLINE) |
| 4 | The Beacon | Blindsided + Court-Bound | Inter Display + Plex Sans + Mono | Emergency / max-contrast | Deadline-forward dashboard | Medium | Deadline beacon banner |
| 5 | Quiet Library | Preventer + Court-Bound | Source Serif + Inter + Mono | Editorial / research | Multi-pane reading room | Medium | Citations as first-class UI |

## My recommendation

For **Semptify as a whole**, no single proposal wins — the product serves distinct
personas in distinct emotional states. The strongest overall direction is a
**hybrid of #2 (Calm Room) as the default shell + #4 (Beacon) as the deadline
system + #3 (Field Notebook) as the Vault/Office**:

- **Default chrome & onboarding** → Calm Room (reduce panic, one step at a time).
- **Deadline / hearing / emergency surfaces** → Beacon (high-contrast, persistent).
- **Vault, Office, Timeline, evidence capture** → Field Notebook (cards + stamps).
- **Library / State Laws / Context Engine** → Quiet Library (reading room).
- **Court Forms / Case Builder / Complaint Wizard** → Courthouse Steps (legal-brief).

This maps each proposal to the four-pillar stage where its aesthetic earns its place,
instead of forcing one mood across the whole product. It also keeps the existing
5-template color-token system meaningful (each pillar gets its own template).

If you want **one** unifying aesthetic for the whole site (simpler to build & maintain),
I recommend **#4 The Beacon** — it is the most accessible, the most mobile-honest, and
the most aligned with "design for a phone in a parking lot." Its risks (starkness) are
the easiest to mitigate with calm copy.
