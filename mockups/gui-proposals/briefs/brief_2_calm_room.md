# Brief — Proposal 2: "The Calm Room"

## Objective
Design a **public welcome / public website** page for Semptify — a public-service
housing-rights and tenant-support tool. This page is the GUI entry point that gives
the public access to the Semptify webapp (it leads into onboarding). It is NOT a
marketing landing page and NOT a commercial product page.

## Target audience
Tenants facing housing problems — often stressed, often on a phone, often low
bandwidth. Primary persona for this aesthetic: **The Blindsided Tenant** (just got
a notice, panicking, needs panic reduced to clarity).

## Aesthetic direction — "The Calm Room"
Therapeutic breathing room. Feels like sitting with a steady, kind social worker
who has done this a thousand times. Whitespace is the design. One step at a time.

- **Typography**: Inter at large sizes with loose leading (1.7) for body + IBM Plex
  Mono only for small metadata. Optional **Fraunces** (Google Font) for the single
  welcome headline only — soft, human serif. Load via Google Fonts.
- **Palette**: Warm sand `#EDE6D6` background · Sage `#5C6B5A` primary · Deep slate
  `#2B3340` text · Single warm amber `#C98A2B` reserved for the ONE primary action
  button per screen. Muted, calming, WCAG AA.
- **Layout**: Single-column reading flow, generous whitespace, max-width ~640px
  centered. Progressive disclosure feel — never a wall of options.
- **Density**: Low — deliberately airy. Big breathing room between sections.
- **No rounded corners** (border-radius: 0 everywhere — hard rule from the project).
- **No photographs of people.** Soft CSS gradients only (sage→sand). No external images.

## Memorable element
A **"Breathe. Here's your next step."** persistent card near the top that shows
exactly ONE action — the "Begin" button — never a dashboard of tiles. It should
feel like a calm hand on the shoulder.

## Content structure (sections, top to bottom)
1. **Top bar** — slim, sage. Left: "Semptify" in Inter. Right: small mono
   "Public service · Housing rights". Nothing else. No nav menu.
2. **Hero** — Fraunces H1 (large, soft): "You don't have to figure this out alone."
   Below, Inter subhead: "Semptify is a public-service tool that helps tenants
   protect their housing rights — calmly, lawfully, one step at a time."
   Then the memorable "Breathe. Here's your next step." card with a single amber
   button: **"Begin"** (NOT "Sign up"/"Log in"/"Get started free").
   Small mono line under it: "No account needed. Your documents stay in your
   own cloud storage."
3. **One step at a time** — a short serene section explaining the journey in 4
   quiet lines (not cards, not tiles — just spaced lines):
   - First, we connect your own cloud storage.
   - Then, we set up your private vault.
   - Then, you record what's happening.
   - Then, you know your rights and act on them.
4. **The law is on your side** — a calm serif/Inter statement of the truth
   standard. Tenant-side, lawful, factual. No hedging. No "both sides."
5. **Who this is for** — a gentle list:
   - You just got a notice.
   - You're in an ongoing dispute.
   - You have a hearing date.
   - You want to be ready, just in case.
   - You're helping someone who is.
6. **Your documents stay yours** — privacy promise in calm language: documents
   live in your own Google Drive or Dropbox, not on Semptify servers.
7. **If you're in a crisis right now** — a soft sage-bordered box (not alarming):
   "If you have a deadline — an eviction notice, a hearing date — begin now.
   You have time, and we'll go one step at a time."
8. **Footer** — minimal, mono, slim: About · Privacy · Contact. A line:
   "Semptify is a public-service housing-rights tool. No ads, ever."

## Forbidden words (HARD RULE — never use on the page)
"free" (about Semptify itself), "accounts", "log in", "sign up", "subscription",
"upgrade", "premium", "paid plan", "trial", "pricing". The CTA is "Begin".

## Technical requirements
- Single self-contained `index.html` + `assets/` if needed.
- Vanilla CSS (no Tailwind, no Bootstrap). Inline `<style>` fine for mockup.
- Google Fonts via `<link>` (Inter, IBM Plex Mono, Fraunces).
- Mobile-first responsive. Test at 375px and 1280px.
- WCAG AA: skip link, focus-visible, `prefers-reduced-motion`, alt text.
- `border-radius: 0` everywhere.
- No external image services. Generate any assets locally into `assets/`.

## Output path
`E:\master-repo\sources\app-semptify-fastapi\mockups\gui-proposals\calm_room\index.html`

## Image needs
None expected. Soft CSS gradients only. If you add any image, generate it locally
into `assets/` — never reference external hosts.
