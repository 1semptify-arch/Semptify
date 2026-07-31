# Brief — Proposal 4: "The Beacon"

## Objective
Design a **public welcome / public website** page for Semptify — a public-service
housing-rights and tenant-support tool. This page is the GUI entry point that gives
the public access to the Semptify webapp (it leads into onboarding). It is NOT a
marketing landing page and NOT a commercial product page.

## Target audience
Tenants facing housing problems — often stressed, often on a phone in a parking
lot, often low bandwidth. Primary personas: **The Blindsided Tenant** + **The
Court-Bound**. This is the most mobile-honest, most accessible of the 5 proposals.

## Aesthetic direction — "The Beacon"
High-contrast emergency-services portal. Maximum legibility on a phone in a parking
lot. Calm language inside a high-contrast frame — the contrast conveys clarity, not
panic. Best WCAG compliance of all 5 proposals.

- **Typography**: Inter Display (or Inter at 700/800 weight) for headlines + IBM
  Plex Sans for body + IBM Plex Mono for deadlines/metadata. LARGE minimum type:
  body 18px (24px+ on mobile), headlines 48px+. Load via Google Fonts.
- **Palette**: Pure black `#000` · Pure white `#FFF` · ONE signal color: amber
  `#F5A623` for deadlines, red `#D7263D` for emergencies only. Nothing else.
  Maximum contrast. WCAG AAA where feasible.
- **Layout**: Deadline-forward. Top of page: a high-contrast **deadline beacon**
   banner. Big tap targets (min 48×48px). 5-core nav as a thumb-reachable bottom
   bar on mobile; top bar on desktop.
- **Density**: Medium — large type limits density by design. Not cramped.
- **No rounded corners** (border-radius: 0 everywhere — hard rule).
- **No photographs of people.** Maximum contrast means no decorative imagery.
  Icons are solid, high-contrast, monochrome (inline SVG).

## Memorable element
A **deadline beacon** — a persistent high-contrast banner at the very top:
"YOUR NEXT DEADLINE: — · YOU HAVE TIME. HERE'S WHAT TO DO." It counts down and
turns amber → red as a hearing approaches. On the welcome page (no deadline yet),
it reads: "NO DEADLINE YET · BEGIN WHEN YOU'RE READY" in high contrast. This is
the single most important UI element on the site.

## Content structure (sections, top to bottom)
1. **Deadline beacon banner** (persistent, top) — black background, white text,
   amber accent. "NO DEADLINE YET · BEGIN WHEN YOU'RE READY" on the welcome page.
   Mono. High contrast.
2. **Top bar** — black, white text. Left: "SEMTIFY" bold. Right: mono
   "PUBLIC SERVICE · HOUSING RIGHTS". On desktop, a 5-link nav: HOME · LIBRARY ·
   OFFICE · TOOLS · HELP. On mobile, this collapses to a bottom bar.
3. **Hero** — Inter Display H1 (huge, bold, black on white): "Protect your
   housing rights." Subhead (Plex Sans, large): "Semptify is a public-service
   tool for tenants facing housing problems. Calm, lawful, one step at a time."
   Single high-contrast primary button: **"Begin"** (black bg, white text, big,
   min 48px tall). NOT "Sign up"/"Log in". Mono line under it: "No account
   needed. Your documents stay in your own cloud storage."
4. **The law is on your side** — high-contrast statement of the truth standard.
   Tenant-side, lawful, factual. Plain language. No hedging.
5. **Four pillars** — four high-contrast blocks (not soft cards). Each with a
   big mono numeral and a bold name:
   - **I. RECORD** — Capture & organize evidence.
   - **II. KNOW** — Facts only.
   - **III. ACT** — Lawful, guided action.
   - **IV. GOVERN** — Platform integrity.
6. **Who this is for** — a high-contrast list, large type:
   - You just got a notice.
   - You're in an ongoing dispute.
   - You have a hearing date.
   - You want to be ready.
   - You're helping someone.
7. **Your documents stay yours** — privacy promise, large type: documents live
   in your own Google Drive / Dropbox, not on Semptify servers.
8. **If you have a deadline right now** — a RED-bordered high-contrast box:
   "Eviction notice? Hearing date? Begin now. Deadlines matter." Links to Begin.
9. **Footer** — black bg, white mono text: ABOUT · PRIVACY · CONTACT. A line:
   "Semptify is a public-service housing-rights tool. No ads, ever."

## Forbidden words (HARD RULE — never use on the page)
"free" (about Semptify itself), "accounts", "log in", "sign up", "subscription",
"upgrade", "premium", "paid plan", "trial", "pricing". The CTA is "Begin".

## Technical requirements
- Single self-contained `index.html` + `assets/` if needed.
- Vanilla CSS (no Tailwind, no Bootstrap). Inline `<style>` fine for mockup.
- Google Fonts via `<link>` (Inter, IBM Plex Sans, IBM Plex Mono).
- Mobile-first responsive. Test at 375px and 1280px.
- WCAG AA (aim for AAA): skip link, focus-visible (thick high-contrast ring),
  `prefers-reduced-motion`, alt text, large type.
- `border-radius: 0` everywhere.
- Big tap targets (min 48×48px).
- No external image services. Icons as inline SVG only. No photos.

## Output path
`E:\master-repo\sources\app-semptify-fastapi\mockups\gui-proposals\beacon\index.html`

## Image needs
None. Solid high-contrast icons as inline SVG only. No photos, no external hosts.
