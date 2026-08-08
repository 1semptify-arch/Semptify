# Brief — Proposal 3: "The Field Notebook"

## Objective
Design a **public welcome / public website** page for Semptify — a public-service
housing-rights and tenant-support tool. This page is the GUI entry point that gives
the public access to the Semptify webapp (it leads into onboarding). It is NOT a
marketing landing page and NOT a commercial product page.

## Target audience
Tenants facing housing problems. Primary persona for this aesthetic: **The Builder**
(ongoing dispute, logging evidence over time — photos, dates, communications).
Wants the entry page to feel like opening a real, tangible case binder.

## Aesthetic direction — "The Field Notebook"
Evidence-first utilitarian, almost analog. Feels like a detective's case binder or
a journalist's field notebook. Tangible, organized, court-ready.

- **Typography**: IBM Plex Mono (metadata strips, timestamps, tags, captions) +
  Inter (body) + Source Serif 4 italic (for "handwritten-note" style pull quotes).
  Load via Google Fonts.
- **Palette**: Kraft `#D9C7A3` background · Ink `#232020` text · Manila folder
  ochre `#B8862F` accents · Stamp red `#9E2B25` reserved ONLY for "FILED" and
  deadline-stamped items. WCAG AA on text.
- **Layout**: Card-based. The page is a series of **evidence cards** — each card
  has a mono metadata strip at top (e.g. `DATE · TYPE · SOURCE · STATUS`) and a
  body below. A vertical "timeline rail" runs down the left side on desktop with
  dated entries. On mobile, cards stack single-column with the rail collapsed.
- **Density**: High but each card is self-contained and scannable.
- **No rounded corners** (border-radius: 0 everywhere — hard rule).
- **No photographs of people.** Subtle paper/kraft texture via CSS only. No external images.

## Memorable element
**Stamp marks** — rotated mono text stamps like `FILED · 2026-07-22` on saved
items, and a red `DEADLINE · — DAYS` stamp on the emergency callout. Stamps are
rotated ~-8deg, mono uppercase, with a thin double border. They should feel ink-stamped.

## Content structure (sections as "evidence cards", top to bottom)
1. **Cover card** — the page header as a case binder cover. Mono top strip:
   `CASE: — · OPENED: — · STATUS: WELCOME`. Big Inter/serif title: "Semptify".
   Subhead: "A public-service tool to protect the rights of tenants facing
   housing problems." A stamp mark: `PUBLIC SERVICE · HOUSING RIGHTS`.
   Single primary button: **"Begin"** (NOT "Sign up"/"Log in"). Mono line:
   "No account needed. Your documents stay in your own cloud storage."
2. **Card: THE LAW IS ON YOUR SIDE** — metadata strip `TYPE: STATEMENT · SOURCE: SEMPTIFY`.
   Body: the truth standard. Tenant-side, lawful, factual. A serif-italic pull
   quote: "When the law protects a tenant, we say so clearly."
3. **Card: THE FOUR PILLARS** — metadata strip `TYPE: STRUCTURE · REF: I–IV`.
   Four sub-entries, each with a mono numeral and a stamp:
   - I. RECORD — Capture & organize evidence. `STAMP: RECORD`
   - II. KNOW — Facts only. `STAMP: KNOW`
   - III. ACT — Lawful, guided action. `STAMP: ACT`
   - IV. GOVERN — Platform integrity. `STAMP: GOVERN`
4. **Card: WHO THIS IS FOR** — metadata strip `TYPE: PERSONAS · COUNT: 5`.
   Five entries, each one line, mono-tagged:
   - `01 · BLINDSIDED` — Just got a notice.
   - `02 · BUILDER` — Logging evidence over time.
   - `03 · COURT-BOUND` — Has a hearing date.
   - `04 · PREVENTER` — Wants to be ready.
   - `05 · ADVOCATE` — Helping a tenant.
5. **Card: YOUR DOCUMENTS STAY YOURS** — metadata strip `TYPE: PRIVACY · STORAGE: USER-OWNED`.
   Privacy promise: documents live in your own Google Drive / Dropbox, not on
   Semptify servers. Semptify is a lens, not a vault-keeper.
6. **Card: IF YOU HAVE A DEADLINE** — metadata strip `TYPE: URGENT · PRIORITY: HIGH`.
   A red stamp: `DEADLINE · BEGIN NOW`. Body: "Facing an eviction notice or a
   hearing date? Begin now. Deadlines matter." Links to Begin.
7. **Footer card** — mono, slim: `ABOUT · PRIVACY · CONTACT`. A line:
   "Semptify is a public-service housing-rights tool. No ads, ever."

## Forbidden words (HARD RULE — never use on the page)
"free" (about Semptify itself), "accounts", "log in", "sign up", "subscription",
"upgrade", "premium", "paid plan", "trial", "pricing". The CTA is "Begin".

## Technical requirements
- Single self-contained `index.html` + `assets/` if needed.
- Vanilla CSS (no Tailwind, no Bootstrap). Inline `<style>` fine for mockup.
- Google Fonts via `<link>` (Inter, IBM Plex Mono, Source Serif 4).
- Mobile-first responsive. Test at 375px and 1280px.
- WCAG AA: skip link, focus-visible, `prefers-reduced-motion`, alt text.
- `border-radius: 0` everywhere.
- No external image services. Generate any assets locally into `assets/`.

## Output path
`C:\Semptify\Semptify-FastAPI\mockups\gui-proposals\field_notebook\index.html`

## Image needs
None expected. Subtle kraft/paper texture via CSS only. If you add any image,
generate it locally into `assets/` — never reference external hosts.
