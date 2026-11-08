# REMEDIATION — how each hole gets closed, with working precedents
*Researched 2026-10-23 as the answer-pass to HOLE_AUDIT_2026-10-23.md.
Every fix below is a mechanism that already runs somewhere — nothing here
requires inventing machinery. Decisions marked → who makes the call.*

## The two precedent systems that do most of the work

**UK Tenancy Deposit Protection (TDP)** — running since 2007, holds
billions of pounds across millions of deposits. Government-approved
custodial schemes hold the deposit **for the whole tenancy**; disputes
go to a free independent adjudication service (CIArb-qualified
adjudicators; ~16–20K disputes/yr at TDS alone; ~50% settle on the
negotiation platform before adjudication). Crucially: **the service
funds itself off custodial float and protection fees** — float-funds-
administration is proven at national scale, not a theory.

**Federal Advance Premium Tax Credit (APTC)** — the IRS pays an
*estimated* annual refundable credit to the insurer **monthly**, on the
household's election, then reconciles it on the tax return (Form 8962)
with defined recapture rules. This is the exact mechanism the M1PR leg
needs: a renter's credit advanced monthly to the pool and trued-up at
filing. "M1PR-A" is not a new invention — it's a federal design that's
run since 2014.

---

## TIER 1 fixes

### H1 — clean-year refund → adopt the UK custodial shape
UK precedent says: keep the deposit in escrow **for the tenancy**, not
one year. Brad's "renter gets something back" intent survives as a
**float dividend**: the tenant still gets statutory 1%, and a clean-year
household is paid an annual dividend from their deposit's share of pool
float (or a premium discount on the belongings leg). Deposit principal
returns at move-out like today — through adjudication, not a landlord's
itemization.
- Effect: damage security intact, claim frequency priced correctly,
  "refund after clean year" reframed as "your deposit starts paying
  you every year you stay clean."
- → **Brad decision** (amends the 10/19 locked clause). Recommend.

### H2 — M1PR coverage gap → three-part honest answer
- **Auto-enrollment via the CRP rail:** DOR already receives every
  CRP — it can flag credit-eligible non-claimants (the data exists;
  the 2024 reform moved claiming onto Form M1 and is projected to add
  ~119K claimants on its own). Election at lease signing via the pool,
  not discovery at tax time.
- **Advance-payment structure (APTC model):** the renter-side share is
  paid *by the state as an advance* against the credit, monthly — the
  household never sees a bill and the credit is never "taken"; it is
  applied on their behalf and reconciled on the return.
- **Honest residual:** over-cap renters (~$77,570+) pay the renter-side
  share directly (~$6/mo) — say it plainly. Roughly a third of renters
  sit above the cap; that's a real premium, disclose it.
- → drafting work; no Brad decision needed beyond approving the
  advance-payment structure.

### H3 — "rides the CRP rail" → corrected framing
Reword everywhere: the pool rides the **CRP data rail** (real,
mandatory since TY2024 — every landlord e-files unit-level rent data
annually) for eligibility and enrollment; the **payment** leg runs
through DOR's advance-and-reconcile mechanism (new build, modeled on
APTC/Form 8962, not on revenue recapture — assignment of a refundable
credit is an election, not a debt intercept). Straightens the claim
"no new reporting machinery" — true for reporting, honest about the
new payment plumbing being one form, not an agency.

### H4 — rating model → community base + experience surcharge
The standard reconciliation (workers-comp / ACA structure):
- **Flat community-rated base premium** on all landlords — prevents
  proxy-redlining (the whitepaper's correct concern).
- **Experience-rated surcharge/credit** on top — manufactured-claim
  history raises it, clean records discount it. Bounded band (e.g.,
  ±50% of base) keeps the modifier behavioral, not geographic.
- → **Brad decision** (concept sheet + fairness clause wording), then
  one line in each doc.

### H5 — repayment plan → precise one-line fix
The repayment plan covers **post-claim forward rent only** — the
claim-paid arrears are never repaid. Drafting line: "A paid claim is
not recoverable from the tenant; the repayment plan applies solely to
rent accruing after the coverage period and is a condition of
continued coverage, not of the claim itself."
- → language fix, no decision needed.

### H6 — median landlord → the honest value stack
Add a "what the landlord who never files actually buys" list:
adjudication that would cost ~$500–2,000 per dispute elsewhere, the
deposit-paperwork burden off their books (itemization exposure under
§504B.178 disappears — that statute is the #1 violation source), a
claims-history product replacing paid screening, and a **no-claim
dividend** (mutual-model: clean-book years return a share of their
matched premium — the SFM precedent makes this plausible, and it turns
the matched share from a tax into insurance-with-a-rebate).
- → drafting + **Brad sign-off on the dividend concept**.

## TIER 2 fixes

### H7 — year-one float ramp → named seed mechanism
Options in order of friction: (a) **coverage starts when escrow
crosses a threshold** (self-phasing, zero ask); (b) a repayable state
seed loan — UI trust-fund borrowing is the standing federal precedent
(states borrow against future premium revenue routinely); (c) an
initial premium surcharge for years 1–2. State in the whitepaper which
one; don't leave it implied.

### H8 — annual credit vs monthly premium → solved by H2's APTC shape
The advance-payment structure IS the fix: DOR advances monthly,
reconciles annually, defined recapture for over-advance (borrow the
8962 rules wholesale — repayment caps for lower-income households).

### H9 — "is hardship insurable" → reframe the product
Lead with the **guarantee-fund** frame, not the insurance frame:
Visale is a *caution* (guarantee), unemployment insurance is
experience-rated payroll-funded wage replacement — the Turnbuchalla
pool sits exactly at that junction. Statute drafts as a state
guarantee fund administered like insurance (SFM precedent for the
carrier), which also answers "Commerce vs MHFA": the fund lives at
MHFA, adjudication at an independent body, licensed-insurer
administration contracted out. "Hardship" becomes a *defined trigger
list* with documentary verification — same machinery UI uses weekly.

### H10 — SDR national lobby → convert, don't just fight
Give Rhino/Obligo a lane: licensed SDRs may operate **only** if
no-subrogation, refundable-principal, and claims-through-the-registry
— i.e., they become distributors of compliant products or they don't
sell in MN. The opposition research cuts our way (OR/WA/Philly killed
their bills; Baltimore vetoed; Blumenthal→FTC Oct 8; NCLC "Tenant
Insecurity" report May 2026) — cite it as the record that legislatures
already see through the product.

### H11 — docket diversion → honest fraction
Restate: "roughly a third to half of filings are collections-shaped —
serial nonpayment filings and deposit disputes the pool is designed
to absorb; holdover, breach, and conduct cases remain in court by
design." 7–12K diverted cases/yr is still the headline and it's
defensible.

### H12 — single-subject → drafting structure
One act, one subject: "residential rental risk." Insurance mechanics,
deposit escrow, adjudication, and the credit-assignment conforming
section all serve the pool — germaneness holds under Johnson v.
Harrison's liberal test if the credit language reads as *machinery*,
not separate tax policy. Flag for the Revisor's draft, don't redesign.

### H13 — small-landlord adverse selection → claims history follows
the unit, not the portfolio. Simplified-track pricing still reflects
the unit's claims record; the simplification is procedural (forms,
ombudsman), not actuarial.

## TIER 3 sharpening (already-acknowledged items)

- Backstop: borrow UI language — "advances repayable from future
  premiums with legislative appropriation backup," gives the fiscal
  note a precedent citation instead of a blank check.
- Admin adequacy: price adjudication like the UK ADR line-item — TDS
  funds ~20K disputes/yr off float + fees; our 40K claims needs its
  own budget line in the actuarial ask, not buried in 25%.
- Sunset → 5-year with mandatory year-3 report (avoids telling the
  administrator not to build past year 3).
- Belongings leg: stays opt-in pending actuarial; fire/habitability
  claims coordination drafted as one integrated claim.

## What changes in the docs if Brad approves the two decisions

1. Concept sheet "Deposits fund year one" → "Deposits move into
   bonded escrow for the tenancy and start paying you" (custodial
   model + float dividend).
2. "Premiums are experience-rated" → "community-rated base with an
   experience-rated surcharge — clean records earn discounts."
3. "Repayment plan" language per H5 one-liner (whitepaper mechanism
   table + concept sheet).
4. Honest-fraction restatement of docket diversion (H11) and the
   median-landlord paragraph (H6).
5. "Rides the CRP rail" → "CRP data rail + advance-payment mechanism"
   (H3/H8).
