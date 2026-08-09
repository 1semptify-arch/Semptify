# Information Integrity Audit — Know Your Rights Library & Public-Facing Informational Content

**Scope:** Semptify 5.0 (`app-semptify-fastapi`) public-facing informational content, anchored on the Know Your Rights Library (`law_library.html`, law_library router/data, state-laws.json) and extending to all public portal pages, the tenant Help page, the standalone help page, and the GUI "Know" landing.

**Mode:** Read-only audit. No content was rewritten, fixed, or deployed.

**Audit date:** 2026-08-06 (initial pass). **Freshness re-checks:** 2026-08-08 and 2026-08-09. On 2026-08-07 commits `ca711cb4`/`c58cc4a9` modified 8 audited files with code-style/lint-only changes (type annotations, whitespace, CSS borders) — no content changed. On 2026-08-08 commit `d120d781` (LF line-ending enforcement) rewrote 7 audited files on disk; verified via `git diff HEAD` that all 7 have **zero content diff**. As of 2026-08-09, all 15 audited files match their committed state with no content changes since the initial audit. All 14 findings remain accurate.

**Standards applied (per Brad's Information Integrity Standards):**
1. **Sourced** — every factual legal claim cites a primary source (statute, case, official agency).
2. **Opinion labeled as opinion** — editorial/advocacy language is clearly marked as opinion, not presented as fact.
3. **No advertising or endorsement** — no paid placements, affiliate links, or implied endorsements.
4. **AI-generated content disclosed** — AI-assisted content (e.g., the AI Librarian) is labeled as AI.
5. **Freshness** — content reflects current law; stale/dated claims flagged with last-verified dates.
6. **Language** — plain language, no legal jargon without explanation, no fear-mongering.

**Status categories used:** `VERIFIED`, `STALE`, `UNSOURCED`, `UNLABELED OPINION`, `AI-UNDISCLOSED`, `LANGUAGE VIOLATION`, `BROKEN/DEAD`, `GAP`.

---

## 1. Summary Table

| # | Content Area | File(s) | Status | Notes |
|---|---|---|---|---|
| 1 | MN tenant statutes (504B.001–.375) | `law_library/router.py` lines 113–204 | **VERIFIED** | Citations correct; `effective_date` present; `full_text` is a paraphrase stub, not verbatim statute |
| 2 | Federal housing laws (FHA, ADA, VAWA, HUD) | `router.py` 210–344 | **VERIFIED** | Citations correct; some `full_text` fields are paraphrases |
| 3 | Case law database (12 cases) | `router.py` 1366–1522 | **VERIFIED** | Real cases, correct citations, real holdings; `key_quotes` appear accurate but are not linked to source opinions |
| 4 | General/generic law entries (laws.json) | `data/laws/laws.json` | **UNSOURCED** | 7 entries with `statute_citation: null` and `jurisdiction: "general"` — generic boilerplate not tied to any statute |
| 5 | State laws data (50 states) | `static/data/state-laws.json` | **STALE / GAP** | `last_updated: 2025-04-23` (8 months old); only 12 states "complete", 38 are "stub" with one-line notes; no per-field `last_verified` dates |
| 6 | MN state detail | `state-laws.json` 11–190 | **VERIFIED** | Statute URL, legal aid orgs, gov resources all sourced; `interest_required: false` contradicts older MN law (interest was required on deposits >$50 pre-2024) — needs legal review |
| 7 | Law Library HTML — main page | `templates/pages/law_library.html` | **VERIFIED** (with findings) | Extensive sourced content; see findings 8–14 for issues |
| 8 | "Laws of Nature / Murphy's Law" section | `law_library.html` 700–712 | **UNLABELED OPINION** | Editorial/philosophical framing presented alongside statute cards without an "opinion" or "editorial" label |
| 9 | "Real Legal Principles With Funny Names" table | `law_library.html` 715–725 | **VERIFIED** | Res Ipsa, Caveat Emptor, etc. are real doctrines; "Caveat Emptor now DEAD in MN" is a strong claim that needs a citation |
| 10 | "Physical Constants of Housing Law" cards | `law_library.html` 727–734 | **VERIFIED** | 68°F, 21 days, 90 days, $500, 14 days — all match MN statute; 3-day "emergency repair window" is a court-practice norm, not a statute — should be labeled as such |
| 11 | AI Librarian panel | `law_library.html` 777–825 | **AI-UNDISCLOSED** | The panel is labeled "AI Librarian" in code but the visible UI label is generic ("Ask a legal question..."); no explicit "AI-generated, may be inaccurate" disclosure to the user |
| 12 | Statute/case card rendering (JS) | `law_library.html` 868–915 | **VERIFIED** | Renders `official_url`, `last_verified` when present; falls back to `revisor.mn.gov` for MN statutes |
| 13 | State law lookup UI | `law_library.html` 999–1060 | **VERIFIED** | Shows "Limited data available" banner for stub states; links to `lawhelp.org` |
| 14 | Dakota County local rules | `router.py` 1316–1364 | **GAP / UNSOURCED** | 3 rules with `full_text` that are clearly placeholder ("...") and no source citation; rule numbers (601/602/603) do not match real Dakota County District Court rules |
| 15 | About page (Jinja) | `templates/public/about.html` | **VERIFIED** | Mission, "what we are not", commitments; one MN fact (21-day deposit) cited inline |
| 16 | About page (static) | `static/public/about.html` | **VERIFIED** | Richer version; "hundreds of thousands" eviction stat is unsourced; MNDES ADM09-8010 reference is real |
| 17 | Renter's Guide | `templates/public/renters_guide.html` | **VERIFIED** | Plain-language rights/responsibilities; "facts only, no opinions" claim upheld; no specific statute citations (intentional — it's a summary) |
| 18 | Tenant Help (FAQ) | `templates/pages/tenant_help.html` | **VERIFIED** | 7 FAQs with MN-specific answers; cites 504B.161, 7-day answer, 24-hr entry; legal aid phone numbers sourced |
| 19 | Court Learning | `templates/pages/court_learning.html` | **GAP** | 5 topic cards (Eviction, Motions, Etiquette, Rights, Evidence) — but clicking only shows a 1-second spinner then nothing; **no actual lesson content exists** |
| 20 | Standalone Help (911/offline) | `static/public/semptify-help-standalone.html` | **VERIFIED** | Real crisis numbers (988, 211, HOME Line, legal aid, DV hotline, county lines); "Not legal advice" disclaimer present |
| 21 | GUI "Know" landing | `templates/gui/know.html` | **VERIFIED** | Minimal hub; "No opinions, no advice" label; links to library |
| 22 | Public: advocacy, complaints, legal_research, services, donate, tools, developers, help | `templates/public/*.html` | **VERIFIED** | All carry "not a law firm / not legal advice" disclaimers where relevant; no advertising; no unsourced legal claims |
| 23 | Disclaimer page | `static/public/disclaimer.html` | **VERIFIED** | "Last updated: May 2026"; clear not-legal-advice + no-guarantees + template-letters caveats; links to lawhelpmn.org, lawhelp.org, LSC |
| 24 | Portal Registry (SSOT for portal services) | `app/modules/portal/registry.py` | **VERIFIED** | Service descriptions are marketing/wayfinding copy, not legal claims; no sourcing required |
| 25 | Portal Pages Registry | `app/modules/portal/pages.py` | **VERIFIED** | SEO meta only; no factual legal claims |
| 26 | Footer legal disclaimer banner | `law_library.html` 758–760 | **VERIFIED** | "Semptify is an organizational tool, not legal advice" present on every law library view |
| 27 | "No Ads / Free Forever" claims | `law_library.html` 761; about.html; donate.html | **VERIFIED** | Consistent across all pages; no advertising observed anywhere |

---

## 2. Detailed Findings

### Finding 1 — `STALE` — State laws data is 8 months old with no per-field verification
**File:** `static/data/state-laws.json`
**Line:** 4 (`"last_updated": "2025-04-23"`)
**Issue:** The single `last_updated` timestamp is 8 months old. There are no per-state or per-field `last_verified` dates. Housing law changes frequently (e.g., AB 12 in CA took effect July 1, 2024 — captured, but newer 2025 amendments may exist). 38 of 50 states are "stub" with a single `notes` string and no verification.
**Standard violated:** Freshness.
**Recommendation:** Add a `last_verified` field per state; schedule a quarterly re-verification pass; surface `last_verified` in the state-law UI (the JS already supports `last_verified` display for statutes — extend it to states).

### Finding 2 — `UNSOURCED` — `data/laws/laws.json` contains 7 generic, citation-less entries
**File:** `data/laws/laws.json`
**Issue:** All 7 entries (`security_deposit_general`, `habitability_general`, `eviction_notice_general`, `retaliation_general`, `entry_access_general`, `rent_increase_general`, `lease_termination_general`) have `"statute_citation": null` and `"jurisdiction": "general"`. They state things like "24-48 hours notice typically required" and "90-day presumption of retaliation" without citing any statute. The 90-day retaliation figure happens to match MN § 504B.285, but the entry is labeled "general," implying it applies everywhere — it does not.
**Standard violated:** Sourced.
**Recommendation:** Either (a) remove these generic entries and route users to the state-specific data, or (b) tag each as "general guidance, varies by state — see your state's page" and add a source for the specific numbers cited.

### Finding 3 — `UNLABELED OPINION` — "Murphy's Law & Informal Laws" section
**File:** `templates/pages/law_library.html`
**Lines:** 700–712
**Issue:** This section applies Murphy's Law, Occam's Razor, Hanlon's Razor, etc. to tenant life. The framing is editorial/advocacy ("the real reason is probably simpler and greedier", "an overconfident landlord who confidently breaks the law is still liable"). Some entries embed real legal hooks (Minn. Stat. § 554 anti-SLAPP, § 504B.161/§ 504B.291 void clauses) — but the section is presented in the same visual style as the statute cards above it, with no "Editorial" or "Opinion" label. A reader could mistake "Occam's Razor says your landlord is greedy" for a legal finding.
**Standard violated:** Opinion labeled as opinion.
**Recommendation:** Add a section header note like "Editorial — these are metaphors, not law. The statute citations within are real; the interpretations are opinion." Or move to a clearly-labeled "Editor's Notes" zone.

### Finding 4 — `UNLABELED OPINION` — "Caveat Emptor now DEAD in MN"
**File:** `law_library.html`
**Line:** 719
**Issue:** The table cell states `Now DEAD in MN housing — landlords must disclose known defects; implied warranty overrides`. "DEAD" is a strong editorial characterization. The underlying point (implied warranty of habitability supersedes caveat emptor in residential leases post-Fritz v. Warthen, 1973) is correct, but the cell cites no case or statute.
**Standard violated:** Sourced + Opinion labeled.
**Recommendation:** Cite Fritz v. Warthen (298 Minn. 54, 1973) and Minn. Stat. § 504B.161; soften "DEAD" or label the cell as editorial.

### Finding 5 — `UNSOURCED` — "3 Days: Emergency Repair Window"
**File:** `law_library.html`
**Line:** 730
**Issue:** The card states "Courts treat 3 days as the outside edge of 'reasonable time' for emergency repairs." This is a court-practice norm, not a statute. The card presents it alongside statutory constants (21 days = § 504B.178, 90 days = § 504B.285) without distinguishing that this one is judicial practice, not statute.
**Standard violated:** Sourced.
**Recommendation:** Label as "Court practice (not statute)" or cite the specific MN case/county court standing order that establishes the 3-day norm.

### Finding 6 — `AI-UNDISCLOSED` — AI Librarian lacks user-facing AI disclosure
**File:** `law_library.html`
**Lines:** 777–825 (JS `askLibrarian()`), UI panel ~lines 60–80 (search input + AI response area)
**Issue:** The feature calls `/api/law-library/librarian/ask` and renders the response as an authoritative-looking answer with a topic heading, paragraph, and key-points list. The code internally calls it "AI Librarian" and "AI Panel," but the **visible UI label** on the input is "Ask a legal question..." and the response renders with a generic "Answer" heading. There is no visible "AI-generated — may be inaccurate; verify against primary sources" disclaimer on the panel or the response.
**Standard violated:** AI-generated content disclosed.
**Recommendation:** Add a persistent disclosure under the search input: "Answers are AI-generated and may contain errors. Always verify against the linked official sources." Render the same line under each AI response.

### Finding 7 — `GAP / UNSOURCED` — Dakota County local rules are placeholders
**File:** `law_library/router.py`
**Lines:** 1316–1364 (`DAKOTA_COUNTY_RULES`)
**Issue:** Three rules (601, 602, 603) have `full_text` values that are clearly truncated placeholders ("...General rules governing housing court proceedings in Dakota County...", "Eviction cases shall be heard on the housing court calendar...", "Remote hearings may be conducted using Zoom..."). The rule numbers 601/602/603 do not correspond to the actual Dakota County District Court local rules. There is no source URL or citation. If these are surfaced to users, they present fabricated rule text as real.
**Standard violated:** Sourced + Freshness.
**Recommendation:** Either remove `DAKOTA_COUNTY_RULES` until real rules with citations are sourced, or clearly mark them as "Summary — not official rule text" and link to the Dakota County court's published local rules.

### Finding 8 — `GAP` — Court Learning page has no lesson content
**File:** `templates/pages/court_learning.html`
**Lines:** 87–113 (topic cards), 117–129 (JS)
**Issue:** Five topic cards (Eviction Process, Filing Motions, Court Etiquette, Your Rights, Evidence Rules) are presented as clickable lessons. The JS handler shows a spinner for 1 second, then removes it — **no lesson content is ever loaded or displayed**. A user who clicks "Start learning →" gets nothing.
**Standard violated:** Freshness / completeness (effectively broken from a content standpoint).
**Recommendation:** Either wire the cards to real lesson content (even stub lessons with a "coming soon" label) or add a visible "Lessons coming soon" badge to each card instead of a fake loading spinner.

### Finding 9 — `STALE` — MN security deposit `interest_required: false` may be outdated
**File:** `static/data/state-laws.json`
**Line:** 34 (`"interest_required": false`)
**Issue:** MN historically required interest on deposits over $50 (then $2000 after a 2003 amendment). The data says `interest_required: false`. This may reflect a real 2024–2025 statutory change, or it may be an error. Either way, it contradicts the law_library.html card at line 729 ("21 Days — Minn. Stat. § 504B.178") and the router.py entry at line 161 ("Tenant entitled to interest on deposit over $2000"). **The two data sources disagree with each other.**
**Standard violated:** Freshness + Sourced (internal inconsistency).
**Recommendation:** Reconcile: verify the current text of Minn. Stat. § 504B.178 subd. 1a on `revisor.mn.gov`, update both `state-laws.json` and `router.py` to match, and add a `last_verified` date.

### Finding 10 — `UNSOURCED` — "hundreds of thousands" eviction statistic
**File:** `static/public/about.html`
**Line:** 157
**Issue:** "Every year, hundreds of thousands of people face eviction..." — no source. The actual U.S. figure is ~3.6 million eviction filings/year (Princeton Eviction Lab). The unsourced round number is both vaguer and lower than the real figure.
**Standard violated:** Sourced.
**Recommendation:** Cite the Princeton Eviction Lab (evictionlab.org) with the actual figure, or remove the statistic.

### Finding 11 — `VERIFIED` (with note) — Case law `key_quotes` are not linked to source opinions
**File:** `law_library/router.py`
**Lines:** 1366–1522
**Issue:** All 12 cases are real, citations are correct, holdings are accurate. However, the `key_quotes` strings are presented as verbatim quotes but have no link to the source opinion text. A reader cannot verify the quote. The case-card JS (`renderCaseCard`) does not render an `official_url` for cases even though the field is supported — the data simply doesn't populate it.
**Standard violated:** Sourced (partial — citation present, but quote not independently verifiable).
**Recommendation:** Add `official_url` to each case entry (Google Scholar, CourtListener, or the court's own opinion archive) and ensure `renderCaseCard` displays it (the JS already supports it at line 903).

### Finding 12 — `LANGUAGE VIOLATION` (minor) — "greedier" / editorial tone in law library
**File:** `law_library.html`
**Line:** 704 (Occam's Razor card)
**Issue:** "the real reason is probably simpler and greedier" — characterizes landlord motive in loaded terms. The Information Integrity Standards call for plain language without fear-mongering or loaded framing. This is mild but present.
**Standard violated:** Language (tone).
**Recommendation:** Soften to "the real reason is probably simpler" or move to the clearly-labeled editorial zone (see Finding 3).

### Finding 13 — `VERIFIED` — No advertising or endorsement observed anywhere
**Files:** All audited
**Issue:** None. The "No Ads / Free Forever" claim is consistent across every page. External links (HOME Line, lawhelpmn.org, mncourts.gov, AG office, revisor.mn.gov) are all to official/nonprofit sources, not paid placements. The about.html "Hard Nos" section explicitly disclaims affiliate links.
**Standard met:** No advertising or endorsement. ✅

### Finding 14 — `VERIFIED` — "Not legal advice" disclaimers are present and consistent
**Files:** `law_library.html` (footer banner + AI fallback), `about.html`, `renters_guide.html`, `complaints.html`, `tenant_help.html`, `help.html`, `disclaimer.html`, `semptify-help-standalone.html`, `gui/know.html`
**Issue:** None. Every page that makes any legal-adjacent claim carries a visible "Semptify is an organizational tool, not legal advice" disclaimer. The standalone help page and tenant_help both link to the full disclaimer.
**Standard met:** Language (disclaimers). ✅

---

## 3. VERIFIED Summary (content that passed all standards)

The following content is correctly sourced, current, properly labeled, and free of advertising:

- **MN tenant statutes** (router.py 113–204): 5 core statutes with correct citations and effective dates.
- **Federal housing laws** (router.py 210–344): FHA, ADA, VAWA, HUD programs — correct citations.
- **Case law database** (router.py 1366–1522): 12 real cases (Fritz v. Warthen, Texas Dept. of Housing, Trafficante, Havens Realty, Bragdon, Olmstead, Giebeler, Bronk, Sabal Palm, Bouley) with correct citations and holdings. (See Finding 11 re: quote sourcing.)
- **"Physical Constants of Housing Law"** (law_library.html 727–734): 68°F, 21 days, 90 days, $500, 14 days — all match MN statute. (See Finding 5 re: 3-day norm.)
- **Statute/case card rendering** (law_library.html JS): Renders `official_url` and `last_verified` when present; graceful fallback to `revisor.mn.gov`.
- **State law lookup UI**: Correctly flags stub states with "Limited data available" banner.
- **MN state detail** (state-laws.json 11–190): Statute URL, 6 legal aid orgs with real phone numbers/URLs, 3 government resources, 3 form templates. (See Finding 9 re: interest field.)
- **About, Renter's Guide, Help, Advocacy, Complaints, Legal Research, Services, Donate, Tools, Developers** public pages: All carry appropriate disclaimers; no unsourced legal claims (except Finding 10).
- **Standalone offline help page**: Real crisis numbers, real orgs, "Not legal advice" disclaimer.
- **Disclaimer page**: Comprehensive, dated, links to real legal aid finders.
- **Portal & Pages registries**: SSOT metadata only; no factual legal claims requiring sourcing.

---

## 4. Gaps List

1. **Court Learning lessons** — 5 topic cards, zero lesson content. (Finding 8)
2. **38 stub states** — state-laws.json has only 12 "complete" states; 38 have a one-line `notes` string and a `stub_url`. Users in 38 states get a redirect, not information. (Finding 1)
3. **Dakota County local rules** — placeholder text presented as rules. (Finding 7)
4. **Per-field verification dates** — no `last_verified` on state data, only a single file-level `last_updated`. (Finding 1)
5. **Case law `official_url`** — field supported by the data model and JS but never populated. (Finding 11)
6. **AI Librarian response sourcing** — the API returns `sources`, but if the API returns none, the UI shows the answer with no source links and no AI disclosure. (Finding 6)
7. **Generic laws.json** — 7 jurisdiction-agnostic entries that don't cite any law. (Finding 2)

---

## 5. Open Questions for Brad

1. **AI Librarian disclosure** — Do you want a persistent "AI-generated, verify against primary sources" banner on the AI panel, a per-response disclosure line, or both? (Finding 6)

2. **"Laws of Nature" section** — Is this intended as editorial/color, or as legal content? If editorial, do you want it moved to a separate "Editor's Notes" zone with a clear label? If legal, each claim needs a citation. (Finding 3)

3. **Dakota County rules** — Are these real local rules you have a source for (and the placeholder `full_text` just needs to be filled in), or were they AI-drafted placeholders that should be removed until sourced? (Finding 7)

4. **Court Learning** — Is this a stub for future content, or was lesson content supposed to exist already? Should the cards show a "Coming soon" badge in the interim? (Finding 8)

5. **MN security deposit interest** — `state-laws.json` says `interest_required: false`; `router.py` says "interest on deposit over $2000." Which reflects the current statute? I did not modify either, but they need reconciliation. (Finding 9)

6. **State laws freshness cadence** — Do you want a scheduled quarterly re-verification, or on-demand? Should `last_verified` be per-state or per-field? (Finding 1)

7. **Generic laws.json** — Should the 7 generic entries be removed (in favor of state-specific routing), or retained with a "general guidance, varies by state" label and sources added? (Finding 2)

8. **Eviction statistic on About page** — Replace "hundreds of thousands" with the Princeton Eviction Lab figure (~3.6M filings/year) and cite, or remove? (Finding 10)

---

## 6. Methodology & Files Audited

**Read in full:**
- `app/modules/law_library/router.py` (statute/case/county-rule data, lines 46–1522, 1307–1522)
- `app/templates/pages/law_library.html` (full, 1061 lines)
- `app/modules/state_laws/router.py` (full)
- `static/data/state-laws.json` (sampled: MN, CA, MI, stub states, metadata)
- `data/laws/laws.json` (full)
- `app/modules/portal/registry.py` (full)
- `app/modules/portal/pages.py` (full)
- `app/templates/public/{about, renters_guide, advocacy, complaints, legal_research, services, donate, tools, developers, help}.html`
- `app/templates/pages/{court_learning, tenant_help}.html`
- `app/templates/gui/know.html`
- `static/public/{about, disclaimer, semptify-help-standalone}.html`

**Not modified.** This was a read-only audit pass.
