# Evaluation — Attempt 1

## Overall Verdict: PASS

## Overall Assessment

The Calm Room design is a coherent, restrained one-column reading experience that faithfully translates the brief's warm-sand/sage/amber palette and "one step at a time" mood. The Fraunces welcome headline, the breathing-card CTA, and the generous section spacing all land the public-service, low-panic tone intended for a tenant in crisis. A few typographic and interaction details drift from the brief, but the foundation is solid and should be refined rather than pivoted.

Screenshots captured for this evaluation:

- Desktop (1440 px): `mockups/gui-proposals/eval/calm_room_desktop_1440.png`
- Tablet (768 px): `mockups/gui-proposals/eval/calm_room_tablet_768.png`
- Mobile (375 px): `mockups/gui-proposals/eval/calm_room_mobile_375.png`
- CTA hover state: `mockups/gui-proposals/eval/calm_room_cta_hover.png`
- CTA keyboard focus state: `mockups/gui-proposals/eval/calm_room_cta_focus.png`
- Console log: `mockups/gui-proposals/eval/calm_room_console.log`

## Scores

| Criterion | Score | Status | Weight | Notes |
| ----------- | ------- | -------- | -------- | ------- |
| Design Quality | 2/3 | PASS | HIGH | Clear "calm room" identity: sand field, sage accents, single centered column, CSS-only sage→sand gradient hero, one amber CTA. Slightly diluted by a second Fraunces headline and amber used on footer hover. |
| Originality | 2/3 | PASS | HIGH | Custom composition and pacing are visible (breathe card, left-sage borders, deliberate whitespace). It is a direct execution of the brief rather than a surprising invention, so it stops at 2. |
| Craft | 2/3 | PASS | MEDIUM | Strong type scale and spacing rhythm; body line-height 1.7, container maxes at 40rem, border-radius is 0 everywhere, responsive clamp sizes work. Close-inspection issues: Fraunces used twice, footer hover borrows CTA amber, and the "Who this is for" list adds unnecessary bottom-border separators. Contrast checks pass (sage on sand ≈4.56:1, sage-dark on sand-light ≈8.4:1). |
| Functionality | 2/3 | PASS | MEDIUM | Skip link works, `:focus-visible` rings are present on the CTA and footer links, hover/active states are clear, and the page is readable on desktop, tablet, and mobile. The CTA links to `/onboarding`, which 404s in the standalone mockup (expected once served by the app backend). |

## What's Working Well

- **Palette & mood**: `#EDE6D6` sand background, `#5C6B5A` sage top bar and borders, `#2B3340` slate text, and `#C98A2B` amber reserved for the single CTA create the intended therapeutic calm.
- **Breathe card**: The left sage border, soft shadow, and single "Begin" button give the memorable "calm hand on the shoulder" moment the brief asked for.
- **Single-column reading flow**: `max-width: 40rem` container is centered, padding scales from `1.25rem` to `1.5rem`, and section spacing stays airy (`3.5rem` mobile, `4.5rem` desktop).
- **Hard rules respected**: No `border-radius` anywhere, no photographs or external images, Google Fonts loaded, `prefers-reduced-motion` handled, `skip-link` and `:focus-visible` implemented.
- **Content fidelity**: All required sections and copy are present, forbidden commercial words ("free", "accounts", "log in", "sign up", "pricing", etc.) are absent, and the CTA label is exactly "Begin".

## Issues Found

### Issue 1: Fraunces is used for two headlines, not only the welcome H1

- **What**: `.breathe-card__lead` is set in `Fraunces`, Georgia, serif, but the brief specifies Fraunces for the "single welcome headline only."
- **Where**: `.breathe-card__lead` ("Breathe. Here's your next step.")
- **Why it matters**: Using the soft human serif in two places creates two competing "human" voices and weakens the typographic rule the brief set.
- **Suggested fix**: Set `.breathe-card__lead` in Inter (or a lighter-weight Inter) and reserve Fraunces solely for the H1.

### Issue 2: Footer hover uses the CTA amber

- **What**: `.footer__links a:hover` and `:focus-visible` change to `var(--amber)`. The brief reserves the single warm amber for the one primary action button per screen.
- **Where**: Footer links "About · Privacy · Contact".
- **Why it matters**: Amber on footer hover trains the eye to treat the footer as another action zone, diluting the uniqueness of the "Begin" button.
- **Suggested fix**: Use a non-amber hover state, e.g., remove the underline or shift to a subtle light-sage/white tint.

### Issue 3: "Who this is for" list adds bottom-border separators

- **What**: `.plain-list li` has a `border-bottom: 1px solid rgba(92, 107, 90, 0.12)` separator between items.
- **Where**: The "Who this is for" section list.
- **Why it matters**: The brief asked for "4 quiet lines (not cards, not tiles — just spaced lines)." The separators add visual density that contradicts the low-density request.
- **Suggested fix**: Remove `border-bottom` and rely on the en dash marker plus generous `line-height`/`padding` for spacing.

### Issue 4: CTA destination 404s in the standalone mockup

- **What**: The "Begin" button links to `/onboarding`. When the page is served as a single static file, that route does not exist.
- **Where**: `.cta-button` in the hero.
- **Why it matters**: The brief says the page leads into onboarding, but a self-contained mockup should not leave its primary action broken during review.
- **Suggested fix**: For the mockup, point to a local `onboarding/index.html` placeholder or use `href="#"` with a note that the real app route is `/onboarding`.

## Priority Fixes for Next Attempt

1. Remove bottom-border separators from `.plain-list li` to match "just spaced lines."
2. Reserve Fraunces for the welcome H1 only; switch `.breathe-card__lead` to Inter.
3. Change footer-link hover/focus color away from amber.
4. Provide a local placeholder for the `/onboarding` CTA or document that the link is app-relative.

## Should the next attempt REFINE or PIVOT

**REFINE.** The overall direction is working: the palette, single-column layout, content structure, and calm mood all align with the brief. The next attempt only needs to tighten typographic discipline and a few hover/interaction details.
