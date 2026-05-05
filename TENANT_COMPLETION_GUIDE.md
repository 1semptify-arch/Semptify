# Tenant Role Completion Guide
# Every promise made on the welcome page — what's needed to honor it.
# Source of truth: static/public/welcome.html
# Last updated: 2026-05-04

---

## THE PROMISE CHECKLIST

Each item below is a direct promise made to the user on the welcome page.
Nothing ships as "complete" until every checkbox is ticked.

---

## 1. 📓 Tenant Journal (Timeline)
> "Log rent payments, maintenance requests, communications with your landlord,
>  and anything important. Build a timeline of your rental life."

- [ ] Create journal entry (text, date, category)
- [ ] Categories: rent_payment, maintenance_request, landlord_communication, general_note
- [ ] Timeline view — chronological list of all entries
- [ ] Edit an entry
- [ ] Delete an entry
- [ ] Entry detail view (tap/click to expand)

**Route:** `/tenant/journal`
**File:** `static/tenant/journal.html` or served by router

---

## 2. 📚 Know Your Rights & Responsibilities
> "Access plain-language guides to tenant law in your state.
>  Understand what your landlord must do, and what you must do. Both matter equally."

- [ ] Rights content page — plain language, no jargon
- [ ] Responsibilities content page — equally prominent, not an afterthought
- [ ] Covers Minnesota law minimum (MNDES jurisdiction)
- [ ] Legal disclaimer on every content page
- [ ] Link to local legal aid (free legal services)
- [ ] Accessible from tenant dashboard (not buried)

**Route:** `/tenant/rights` or `/law-library`
**Note:** Must be two-sided — rights AND responsibilities, equal weight.

---

## 3. 📁 Document Storage (Vault)
> "Keep your lease, move-in photos, receipts, and communications organized
>  in your own cloud storage. We never store your documents on our servers."

- [ ] Upload a document to vault (Google Drive / Dropbox / OneDrive)
- [ ] Document categories: lease, move_in_photo, receipt, communication, other
- [ ] Document list — show all uploaded files
- [ ] Document viewer / download link
- [ ] Delete a document from vault
- [ ] Zero server-side storage — all files go to user's cloud only
- [ ] Upload confirmation with file name and location shown

**Route:** `/tenant/documents`
**File:** `static/tenant/documents.html`

---

## 4. 🛠️ Be Prepared (Just in Case)
> "Template letters, deadline trackers, and educational resources
>  about court procedures. We hope you never need them."

- [ ] Template letter: Maintenance request (written request to landlord)
- [ ] Template letter: Security deposit demand (after move-out)
- [ ] Deadline tracker: At least rent due date + lease end date
- [ ] Court procedure info: plain-language "what is eviction court" explainer
- [ ] All tools accessible from tenant dashboard
- [ ] Legal disclaimer on all template/court content

**Route:** `/tenant/tools` or separate pages per tool
**Note:** These are "just in case" — calm framing, not alarmist.

---

## 5. 💰 Free Forever
> "Free to use. Free Forever. No Ads."

- [ ] No paywall anywhere in tenant flow
- [ ] No upsell prompts
- [ ] No advertisements
- [ ] Footer displays "Free Forever • No Ads" as promised

**Enforcement:** Code review before any monetization feature is added.

---

## 6. 🔒 Data In Your Control
> "Your documents stay in your control. We never store your documents on our servers."

- [ ] All uploads go directly to user's own cloud vault (Drive/Dropbox/OneDrive)
- [ ] No document content stored in Semptify database
- [ ] Vault path shown to user so they can verify
- [ ] This is already architecturally enforced — must stay that way on every upload path

---

## 7. ⚖️ Tenant-First, Truth-Based
> We are on the side of tenants — always.
> We stand for what is lawful and factual. We do not mislead, balance-both-sides into silence, or soften the truth.
> The "two-way street" framing on the welcome page means: we won't help bad-faith tenants weaponize the app.
> It does NOT mean we treat landlords and tenants as equals when the law does not.

- [ ] Rights content is written FOR tenants, not "neutrally"
- [ ] When the law protects tenants, we say so clearly and directly
- [ ] When a landlord violates the law, we name it plainly
- [ ] Responsibilities section exists to help tenants protect themselves
  (a tenant who follows their lease removes every landlord excuse)
- [ ] No language that softens or excuses landlord violations
- [ ] No victim-blaming framing ("maybe you should have...")
- [ ] Legal facts are cited — not opinions, not hedged into uselessness
- [ ] Content passes: "Would a tenant facing eviction find this helpful and honest?"

---

## 8. 🏛️ Not Legal Advice
> "Semptify is an organizational tool and educational resource — not a law firm."

- [ ] Disclaimer shown on all rights/law content pages
- [ ] No language that implies legal advice ("you should sue", "you will win", etc.)
- [ ] Legal aid pointer visible (e.g., Minnesota Legal Aid link)
- [ ] About/disclaimer page exists at `/public/disclaimer.html`

---

## 9. 📄 Footer Links (Currently 404 — Must All Exist)

- [ ] `/public/privacy.html` — Privacy policy
- [ ] `/public/terms.html` — Terms of use
- [ ] `/public/disclaimer.html` — Legal disclaimer
- [ ] `/public/contact.html` — Contact information
- [ ] `/public/feedback.html` — Feedback form or link

---

## TENANT DASHBOARD — Must Surface All of the Above

The tenant dashboard (`/tenant/home` or `/tenant/dashboard`) must have
clear entry points to every promise:

- [ ] Journal link → `/tenant/journal`
- [ ] Documents link → `/tenant/documents`
- [ ] Rights & Responsibilities link → `/tenant/rights` or `/law-library`
- [ ] Tools link → template letters + deadline tracker
- [ ] Account/settings (storage provider, logout)

---

## COMPLETION STATUS

| Area | Status | Blocker |
|------|--------|---------|
| Journal / Timeline | ❓ Unknown | Need to verify route + UI |
| Rights & Responsibilities | ⚠️ Partial | Law library exists, two-sided framing TBD |
| Document Storage (upload) | ⚠️ Partial | Vault provisioned, upload UI TBD |
| Template Letters | ❌ Not verified | Needs check |
| Deadline Tracker | ❌ Not verified | Needs check |
| Court Procedure Info | ❌ Not verified | Needs check |
| Free Forever | ✅ Structural | No paywall in codebase |
| Data In Your Control | ✅ Structural | Vault architecture enforces this |
| Two-Way Street content | ⚠️ Partial | Welcome page is good, app content TBD |
| Legal Disclaimers | ⚠️ Partial | Disclaimer note exists, needs to be on content pages |
| Footer pages (5) | ❌ All 404 | Need to create |
| Tenant Dashboard | ⚠️ Partial | Exists but links TBD |

---

## NEXT SESSION PRIORITY ORDER

1. Verify tenant dashboard loads for logged-in user and has all nav links
2. Verify journal/timeline UI exists and works
3. Verify document upload works end-to-end
4. Create 5 footer pages (privacy, terms, disclaimer, contact, feedback)
5. Verify rights content is two-sided
6. Add template letters (maintenance request + deposit demand)
7. Add deadline tracker
8. Add legal disclaimers to content pages

---

## DEFINITION OF DONE

The tenant role is complete when:
- A brand new user can: sign up → connect storage → reach dashboard
- From the dashboard they can: write a journal entry, upload a document,
  read their rights, access a template letter, see a deadline tracker
- Every footer link works
- No broken links anywhere in the tenant flow
- Legal disclaimers present on all content
- Zero paywalls, zero ads, zero upsells
