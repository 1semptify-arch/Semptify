# Sample Letters L0 Blueprint

**Status:** DRAFT — pending approval
**Type:** Public page (PortalPage + `public_shell` template; content
derived from the existing in-app letters page)
**Pillar:** ACT
**Tier:** L0 public
**Date:** 2026-11-06
**Toolbox entry:** `letters` (planned, group=act, engine=action) —
"Plain sample letters: repair requests, deposit requests,
records-preservation requests."

## Problem

The catalog note says "Registered as response_letter_generator but not
built." That note is **stale** — real letter content exists:

- `/tenant/tools/letters` renders `pages/tenant_tools_letters.html`
  (893 lines): six letter cards — maintenance/repair request, security
  deposit return (cites MN Stat. 504B.178, 21-day deadline), habitability
  escalation (MN Stat. 504B), lease non-renewal response, eviction
  response (correctly warns "you must file an Answer with the court"),
  and housing-inspector request. Each has editable fields and print CSS.
- `letter_builder` page (`/letter-builder`, `pages/letter_builder.html`)
  — a compose surface, "served as static" per the page manifest.

But both are **role-gated inside app chrome**
(`_guard_role_page(request, {"tenant"})`) — a person who has not
connected storage never reaches them. The promise on public pages is an
L0 "copy a good letter" surface, not the in-app editor.

## Proposed shape

One public page, `public/sample_letters.html` extending
`body/public_shell.html`, plus one `PortalPage` line — same machinery as
`/credit-reports`. Read-only letter text the visitor reads, selects, and
copies (plus a print button per letter) — **no fill-in editor, no
fields, nothing sent anywhere**. The editable version stays where it is
inside the app; the L0 page links to `/preamble` for that.

### Which letters

Start with the three the catalog names, drawn from the existing six:

1. **Repair/maintenance request** — the universal first letter.
2. **Security deposit return request**.
3. **Records-preservation request** — asks the landlord to keep all
   records about the tenancy (the existing set doesn't have this one;
   it's the third letter the catalog promises, so it's the one piece of
   net-new writing).

The remaining three (habitability escalation, non-renewal, eviction
response) are good candidates for a second pass — they carry more
situation-specific risk and deserve their own review beat rather than
shipping in the same drop.

### Voice/UPL posture — the real decision

Each letter gets: when to use it (one line), the letter text, a "keep a
copy and note the date" line, and the standing not-legal-advice
disclaimer. Two honest options:

- **Option A — keep the Minnesota citations** (recommended). The
  existing letters cite MN statutes, which is what makes them genuinely
  useful — and the law library is MN-deep anyway. The page then says
  plainly: "These letters cite Minnesota law. If you rent elsewhere, the
  letter shape still works but check your own state's rules" and links
  `/law-library`. Risk: a non-MN tenant sends a letter citing MN
  statutes — mitigated by a per-letter jurisdiction line right at the
  top of each card, not just page-level.
- **Option B — strip citations, ship neutral letters.** Safer against
  misuse, but measurably less useful — a letter that asserts a deadline
  is what moves landlords; a vibes letter isn't worth the page.

Recommendation: **A**, with the jurisdiction line prominent per letter.

## Decision needed (Brad)

1. **MN-cited vs. neutral** — options above.
2. **Ship three now vs. all six.** Recommended: three (the catalog's own
   list) — the other three need more careful review.
3. **Copy vs. light edit of existing text.** Recommended: reuse the
   existing letter bodies verbatim where possible — they've already been
   through the in-app review path — rather than rewriting.

## Scope if approved

- `app/templates/public/sample_letters.html` (new): intro (what these
  are, paper-trail rationale), three letter sections, per-letter
  jurisdiction + disclaimer lines, copy/print affordance (clipboard +
  `window.print()` — no library), "want the fill-in version?" link to
  `/preamble`, Get-help-now CTA.
- One `PortalPage` line in `pages.py`.
- `toolbox.py` flip on the toolbox branch: `planned` → `partial`
  (three of an implied larger set) or `live` if Brad counts the catalog's
  three as the whole promise — his call; note updated either way.
  **Blocked until the toolbox branch merges.**

## Verification

- 375px/1280px render; copy button works; print output shows one clean
  letter (reuse the existing `printing` CSS pattern).
- Voice sweep: no banned terms; letters stay in "documentation of
  events" register — check the eviction-letter precedent for the right
  caution wording.
- No backend change → `py_compile` vacuous; guardrail run for
  completeness.
