# GitHub Sponsors — The Filing Fund ($345)

Canonical copy for the `1semptify-arch` GitHub Sponsors profile
(`https://github.com/sponsors/1semptify-arch`). Drafted 2026-11-05 under
queue task `github-sponsors-345-campaign`. When the live profile is edited,
edit this file in the same commit — this document is the source of truth for
what the profile says.

Sponsors account type: **personal** — GitHub charges no fee on sponsorships
to personal accounts, so every dollar reaches the fund.

## The math (sourced)

| Fee | Amount | Source |
|---|---|---|
| Minnesota nonprofit Articles of Incorporation (Chapter 317A), mail filing | $70 | MN Secretary of State fee schedule — <https://www.sos.mn.gov/media/1687/businessentityfees.pdf> ($90 online/in-person; $70 by mail) |
| IRS Form 1023-EZ user fee | $275 | IRS — <https://www.irs.gov/charities-non-profits/form-1023-and-1023-ez-amount-of-user-fee> |
| **Total** | **$345** | |

Using the mail filing keeps the goal at $345 instead of $365.

## Publish steps (GitHub Sponsors dashboard)

Dashboard: <https://github.com/sponsors/accounts> → profile for `1semptify-arch`.

1. **Profile / "Tell us about yourself"** — paste **Profile blurb** below.
   Markdown is supported.
2. **Goals → New goal** — one-time goal, target **$345**. Paste **Goal title**
   and **Goal description** below. This replaces the currently-live
   "$50 per month" recurring goal (only one goal is active at a time).
3. **Tiers** (optional) — the three suggested one-time tiers below. Skip
   entirely if the profile already has tiers it should keep.
4. Save, then update this file's **Live state** section with what shipped.

### Live state (verified 2026-11-06 via GraphQL `viewer.sponsorsListing` + public page)

- Sponsors listing: LIVE and public — <https://github.com/sponsors/1semptify-arch>
- Profile text currently live: **older copy, predates this doc**
  - short: "Building Semptify, a nonprofit tenant-rights platform — no fees to
    tenants, ever — mostly solo with AI coding agents. Sponsorship funds our
    nonprofit filing fees so this can grow beyond one person."
  - full: "Hi, I'm Brad — I'm building Semptify (semptify.org), a nonprofit
    tenant-rights platform with no fees to tenants, ever, largely on my own
    with the help of AI coding agents doing the heavy lifting on the codebase."
- Goal currently live: **"$50 per month" recurring**, 0% complete — NOT the
  canonical $345 one-time filing-fund goal below
- Tiers currently live: **none** — only GitHub's default custom-amount box
- `FUNDING.yml` in this repo already reads `github: [1semptify-arch]`, so the
  repo's Sponsor button points at the listing.

### Publish auth boundary (found 2026-11-06)

- Listing profile text and goals are **dashboard-only** — there is no public
  GraphQL/REST mutation for them. They need a browser signed in as
  `1semptify-arch`.
- Tiers ARE API-writable (`createSponsorsTier` with `publish: true`), but only
  with a token carrying the `user` (or `admin:org`) scope. The local `gh`
  token for `1semptify-arch` has `gist, read:org, repo, workflow` — confirmed
  `INSUFFICIENT_SCOPES` on a live call.
- So finishing the publish needs one of:
  a. Brad pastes the three sections below at <https://github.com/sponsors/accounts>
     (~2 min), or
  b. `gh auth refresh -s user` for `1semptify-arch`, after which an agent can
     run the tier mutations (profile text + goal still need the dashboard), or
  c. Brad signs the IronBee browser into GitHub and an agent drives the paste.
- Optional extra surface (needs Brad's OK — it is his personal profile):
  a `1semptify-arch/1semptify-arch` repo with the blurb below as
  `README.md` would put the campaign on the public GitHub profile page.

---

## Profile blurb — paste-ready

```markdown
**Semptify is an open-source tenant rights workspace — calm tools that help
renters keep a clear record, understand their rights, and take the next
right step.**

Tenants never pay for Semptify. No accounts, no advertising, no tracking.
Donations are the entire budget.

Right now every sponsorship goes to one concrete thing: the **$345 filing
fund** — the two government fees that turn Semptify into a legal nonprofit.

- **$70** — Minnesota nonprofit articles of incorporation (mail filing,
  Secretary of State)
- **$275** — IRS Form 1023-EZ, the streamlined 501(c)(3) application

When the fund clears, the paperwork gets filed and the receipts get posted.
That's the whole campaign — a small, specific unlock.

Everything we build stays open source and at no cost to tenants, always.
```

## Goal — paste-ready

- **Goal title:** `The filing fund`
- **Target amount:** `$345` (one-time)
- **Goal description:**

```markdown
Two government fees stand between Semptify and legal nonprofit status:

$70 — Minnesota nonprofit articles of incorporation (filed by mail with the
Secretary of State)

$275 — IRS Form 1023-EZ, the streamlined 501(c)(3) application

When this goal clears, both get filed and the receipts get posted. Nothing
else is in this fund — it exists for exactly these two filings.
```

## Suggested one-time tiers (optional)

- **$5 — Chip in.** Every bit of the filing fund is a fee somebody covered.
- **$25 — Half the state filing.** About half of the $70 Minnesota articles
  fee.
- **$70 — File the articles.** Covers the entire Minnesota filing by
  yourself.

(Do not create a tier framed as "cover the IRS fee" at $275 — a single-sponsor
tier that large reads as pressure, not invitation.)

## Voice check (semptify-voice, applied 2026-11-05)

- No "free", no business-model words applied to Semptify, no "evidence"/"proof",
  no adversarial framing.
- No urgency, no guilt, no scarcity — the goal is a fixed, factual number with
  named sources. Passes the banned-motivations test (fear / resentment /
  dishonesty / greed).
- All dollar claims sourced to the two official pages in the math table.
- "We'll post the receipts" is a standing commitment — when the filings
  happen, link the receipts from this file or the Sponsors profile.
