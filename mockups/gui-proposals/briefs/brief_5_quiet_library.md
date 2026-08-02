# Brief — Proposal 5: "The Quiet Library"

## Objective

Design a **public welcome / public website** page for Semptify — a public-service
housing-rights and tenant-support tool. This page is the GUI entry point that gives
the public access to the Semptify webapp (it leads into onboarding). It is NOT a
marketing landing page and NOT a commercial product page.

## Target audience

Tenants facing housing problems. Primary personas for this aesthetic: **The
Preventer** (no active dispute, educating themselves) + **The Court-Bound**
(studying before a hearing). Wants the entry page to feel like entering a law
library reading room — a place to understand before acting.

## Aesthetic direction — "The Quiet Library"

Editorial research room. Feels like a law library reading room — quiet, deep,
orderly. Reading-first. Citations are first-class UI, not afterthoughts.

- **Typography**: Source Serif 4 (headings + long-form text) + Inter (UI labels,
  nav, buttons) + IBM Plex Mono (citations, statute IDs, metadata). Heavy
  typographic hierarchy with horizontal rules between sections. Load via Google
  Fonts.
- **Palette**: Deep forest `#1F3A2E` primary brand · Parchment `#F2EAD3`
  background · Brass `#A67C2E` accents · Ink `#1A1A1A` text. Forest as the
  primary brand color (distinct from the current navy). WCAG AA.
- **Layout**: Multi-pane on desktop: left = library/law index (a slim index of
  the four pillars + key statutes), center = reading column (the welcome
  content), right = "Your notes / related" rail (on the welcome page, this holds
  the "Begin" CTA + privacy promise + emergency callout). Collapses to single
  column + a drawer pattern on mobile. Max reading width ~680px in the center.
- **Density**: Medium — text-rich but well-rhythm'd with rules, pull quotes,
  and section numerals.
- **No rounded corners** (border-radius: 0 everywhere — hard rule).
- **No photographs of people.** Typography, rules, and a subtle parchment tint.
  Optional small brass section numerals. No external images.

## Memorable element

**Visible citations as first-class UI** — statute-style references (e.g.
`Minn. Stat. § 504B.221`) are styled like library catalog cards: mono, brass-
ruled, clickable-looking, with a small "catalog card" frame. On the welcome page,
the four pillars are presented as catalog-card entries with citation-style
metadata strips. This signals "this is a place where the law is real and
looked-up, not invented."

## Content structure (sections, top to bottom in the center reading column)

1. **Masthead** — slim, forest green band. Left: "SEMTIFY" in Source Serif.
   Right: mono "PUBLIC SERVICE · HOUSING RIGHTS · EST. 2026". A horizontal brass
   rule beneath.
2. **Hero** — Source Serif H1: "A quiet place to learn your rights — and act on
   them." Inter subhead: "Semptify is a public-service tool that helps tenants
   protect their housing rights. Calm, lawful, evidence-first."
3. **The law is on your side** — a serif statement of the truth standard with a
   pull quote: "When the law protects a tenant, we say so clearly. We do not
   soften it."
4. **The four pillars (as catalog cards)** — four entries, each framed like a
   library catalog card with a mono metadata strip and a brass rule:
   - `I · RECORD · EVIDENCE` — Capture and organize evidence. Vault, timeline,
     calendar.
   - `II · KNOW · FACTS` — Facts only. Library, state laws, context engine.
   - `III · ACT · LAWFUL ACTION` — Case builder, court forms, complaints.
   - `IV · GOVERN · INTEGRITY` — Audit trail, transparency.
5. **Who this is for** — a quiet list with small mono labels:
   - The Blindsided Tenant.
   - The Builder.
   - The Court-Bound.
   - The Preventer.
   - The Advocate / Helper.
6. **Your documents stay yours** — serif privacy promise: documents live in your
   own Google Drive / Dropbox, not on Semptify servers.
7. **If you have a deadline** — a forest-bordered callout: "Facing an eviction
   notice or a hearing date? Begin now. Deadlines matter."
8. **Footer** — parchment, ink mono: ABOUT · PRIVACY · CONTACT. A line:
   "Semptify is a public-service housing-rights tool. No ads, ever."

## Left index pane (desktop only)

A slim forest-tinted index titled "INDEX" in mono, listing:

- I. RECORD
- II. KNOW
- III. ACT
- IV. GOVERN
- PRIVACY
- BEGIN
Each is a quiet text link (no buttons in the index). On mobile this becomes a
disclosure drawer toggled by an "INDEX" button.

## Right rail (desktop only)

Holds the primary **"Begin"** button (forest bg, parchment text — NOT "Sign
up"/"Log in"), a mono note "No account needed. Your documents stay in your own
cloud storage.", and the emergency callout. On mobile these move into the center
column flow.

## Forbidden words (HARD RULE — never use on the page)

"free" (about Semptify itself), "accounts", "log in", "sign up", "subscription",
"upgrade", "premium", "paid plan", "trial", "pricing". The CTA is "Begin".

## Technical requirements

- Single self-contained `index.html` + `assets/` if needed.
- Vanilla CSS (no Tailwind, no Bootstrap). Inline `<style>` fine for mockup.
- Google Fonts via `<link>` (Source Serif 4, Inter, IBM Plex Mono).
- Mobile-first responsive. Test at 375px and 1280px. Multi-pane on desktop,
  single column + drawer on mobile.
- WCAG AA: skip link, focus-visible, `prefers-reduced-motion`, alt text.
- `border-radius: 0` everywhere.
- No external image services. Generate any assets locally into `assets/`.

## Output path

`E:\master-repo\sources\app-semptify-fastapi\mockups\gui-proposals\quiet_library\index.html`

## Image needs

None expected. Typography, rules, parchment tint. If you add any image, generate
it locally into `assets/` — never reference external hosts.
