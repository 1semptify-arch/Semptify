# Start a Tenant Group — Guide Blueprint

**Status:** DRAFT — pending approval
**Type:** Public guide page (PortalPage + `public_shell` template — the
`/credit-reports` pattern, no new module)
**Pillar:** KNOW (education) — links out to ACT/record tools
**Tier:** L0 public
**Date:** 2026-11-06
**Toolbox entry:** `start_a_group` (planned, group=together,
engine=content) — "A plain guide to forming a tenant group: structure,
outreach, funding, limits."

## Problem

`promised_on` lists `/advocacy`, `/services`, `/donate`. The advocacy
page today is a 62-line template whose "Start an Advocacy Group" section
is only a five-bullet topic list (legal structure, outreach, funding,
tools, boundaries) followed by an "Ask us →" contact CTA. The catalog
note is accurate: the topics are listed, the guide is not written.

## Proposed shape

One public page, `public/start_a_group.html` extending
`body/public_shell.html`, plus one `PortalPage` registry line in
`app/modules/portal/pages.py` — identical machinery to
`/credit-reports` (registry line + shell template, no router, no
backend). Suggested path `/start-a-tenant-group`; `/advocacy` keeps its
partner-with-us role and links to the guide.

### Guide outline (content to be written in the build pass)

Ordered as a person actually does it (chronological/spatial rule):

1. **What a tenant group is (and isn't)** — a few neighbors who agree to
   compare notes and speak together; not a lawsuit, not a union card on
   day one. Right to organize exists under federal labor law analogues
   and many state tenant-protection laws — keep it honest: protections
   vary by state, retaliation for organizing is illegal in many places
   but happens; document everything.
2. **Start with two or three neighbors** — how to have the first
   conversation; building/common-area and off-site options; what not to
   put in writing casually.
3. **Agree on the ask** — repairs, deposits, a policy change; one clear
   ask beats ten grievances.
4. **Put it in writing together** — a joint letter or petition; link to
   the sample-letters page (P4 sibling blueprint) as the "today" path.
5. **Know the limits** — a tenant group is not a law firm; when the issue
   is bigger than the building, legal aid and tenant unions exist (link
   `/help`, neutral 211 pointer).
6. **Structure only if it grows** — informal group vs. nonprofit is a
   later question; name official starting points (state secretary of
   state, Legal Aid) rather than advising a structure — UPL-safe.

Voice rules that apply on this page specifically: no adversarial
framing (ADR-0005 — no "fight," "battle," "take them down"); the guide
teaches calm organizing, not conflict; "documenting events / keeping
records," not "evidence"; no urgency. Funding mentions stay factual and
generic (no grant-search promises, no donation solicitation for groups —
Semptify's own donate page is a separate surface).

## Decision needed (Brad)

1. **Own page vs. expand `/advocacy` in place.** Recommended: own page —
   `/advocacy` is aimed at existing organizations ("Partner With Us"),
   the guide is aimed at a tenant starting from zero; different reader,
   different spine. `/advocacy`'s five-bullet list becomes a link to the
   guide.
2. **How far into legal-structure detail.** Recommended: stop at "informal
   first; structure later, here are the official places that answer it" —
   advising nonprofit-vs-collective specifics drifts toward legal advice.
3. **Name.** "Start a tenant group" (catalog name) vs. "start an advocacy
   group" (current advocacy-page phrase). Recommended: tenant group —
   plainer, matches the toolbox entry.

## Scope if approved

- `app/templates/public/start_a_group.html` (new, ~120–160 lines, same
  section rhythm as `credit_reports.html`).
- One `PortalPage` line in `pages.py` (sitemap + optional footer).
- `/advocacy` edit: replace the bullet list with a short paragraph +
  link (one template, ~10 lines).
- `toolbox.py` flip on the toolbox branch: `planned` → `live`,
  `today`/`today_path` → the guide, `note` cleared, `promised_on`
  unchanged. **Blocked until `feat/toolbox-service-stubs` merges** —
  same blocker as P2/P3.

## Verification

- Page renders at 375px and 1280px; eye-path top→down follows steps 1–6.
- Voice sweep: no banned terms (ADR-0005), no "free"/account language,
  disclaimer line present, "Get help now" reachable.
- Banned-motivation check: organizing page gets an extra read for
  adversarial framing — this is the page most at risk of it.
- No console errors; all links resolve.
