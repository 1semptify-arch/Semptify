# Brief — Proposal 1: "Courthouse Steps"

## Objective
Design a **public welcome / public website** page for Semptify — a public-service
housing-rights and tenant-support tool. This page is the GUI entry point that gives
the public access to the Semptify webapp (it leads into onboarding: role select →
storage connect → vault setup). It is NOT a marketing landing page and NOT a
commercial product page.

## Target audience
Tenants facing housing problems — often stressed, often on a phone, often low
bandwidth. Primary persona for this aesthetic: **The Court-Bound** (has a hearing
date, needs to feel the law is real and on their side).

## Aesthetic direction — "Courthouse Steps"
Civic legal authority. Feels like walking into a legal aid clinic or reading a
well-set legal brief. Serious, lawful, accountable — never a startup.

- **Typography**: Source Serif 4 (headings + legal/body text) + Inter (UI labels,
  nav, buttons) + IBM Plex Mono (citations, dates, case IDs, statute references).
  Load via Google Fonts.
- **Palette**: Paper cream `#F6F1E7` background · Ink black `#1A1A1A` text ·
  Oxblood `#7A1F1F` for urgency/emphasis only · Slate rule `#3A4A5A` for dividing
  lines. High contrast, WCAG AA.
- **Layout**: Columnar, legal-brief style. Two-column reading grid on desktop
  (main column + marginalia/sidebar for citations and "what this means" notes);
  single column on mobile. Visible horizontal rule lines between sections.
- **Density**: Medium-high, text-forward, citations visible.
- **No rounded corners** (border-radius: 0 everywhere — hard rule from the project).
- **No photographs of people.** Typography and rule lines do the work. Optional
  very subtle paper grain via CSS only.

## Memorable element
A **docket-style header strip** at the top of the page (and persistent on scroll):
`SEMTIFY · PUBLIC SERVICE · HOUSING RIGHTS` on the left, and on the right a
mono-set line like `Stage: WELCOME → RECORD → KNOW → ACT → GOVERN` showing the
user's place in the journey. Reads like the header of a court filing.

## Content structure (sections, top to bottom)
1. **Docket header strip** (persistent) — see memorable element.
2. **Hero** — Serif H1: "Semptify" with a one-line subhead in Inter:
   "A public-service tool to protect the rights of tenants facing housing problems."
   No emoji. A single primary button: **"Begin"** (NOT "Sign up", NOT "Log in",
   NOT "Get started free"). Below it, small mono text: "No account needed. Your
   documents stay in your own cloud storage."
3. **The law is on your side** — a short serif statement of the truth standard:
   Semptify stands with tenants, lawfully and factually. When the law protects a
   tenant, we say so clearly. Plain language, no hedging.
4. **Four pillars** — four columnar entries, each with a mono numeral (I–IV),
   a serif name, and an Inter gloss:
   - **I. RECORD** — Capture and organize evidence. Vault, timeline, calendar.
   - **II. KNOW** — Facts only. Library, state laws, context engine.
   - **III. ACT** — Lawful, guided action. Case builder, court forms, complaints.
   - **IV. GOVERN** — Platform integrity. Audit trail, transparency.
5. **Who this is for** — a compact list (not cards) of the personas:
   - The Blindsided Tenant — just got a notice.
   - The Builder — logging evidence over time.
   - The Court-Bound — has a hearing date.
   - The Preventer — wants to be protected before trouble.
   - The Advocate / Helper — assisting a tenant.
6. **Privacy promise** — serif statement: your documents live in your own cloud
   storage (Google Drive / Dropbox), not on Semptify servers. Semptify is a lens,
   not a vault-keeper.
7. **If you have an emergency** — an oxblood-bordered callout box: "Facing an
   eviction notice or a hearing date? Begin now. Deadlines matter." Links to Begin.
8. **Footer** — mono, slim: About · Privacy · Contact. No ads, no tracking pixels,
   no affiliate links. A line: "Semptify is a public-service housing-rights tool."

## Forbidden words (HARD RULE — never use on the page)
"free" (about Semptify itself), "accounts", "log in", "sign up", "subscription",
"upgrade", "premium", "paid plan", "trial", "pricing". The CTA is "Begin" — nothing else.

## Technical requirements
- Single self-contained `index.html` + an `assets/` folder if needed.
- Vanilla CSS (no Tailwind, no Bootstrap). Inline `<style>` is fine for a mockup.
- Google Fonts via `<link>`.
- Mobile-first responsive. Test at 375px and 1280px.
- WCAG AA: skip link, focus-visible, `prefers-reduced-motion`, alt text.
- `border-radius: 0` everywhere.
- No external image services (no Unsplash/Pexels). Generate any image assets
  locally into `assets/` if needed — but this design should need none.

## Output path
`C:\Semptify\Semptify-FastAPI\mockups\gui-proposals\courthouse_steps\index.html`
(and `assets/` subfolder if needed)

## Image needs
None expected. If you add any, they must be generated locally into `assets/` —
never reference external image hosts.
