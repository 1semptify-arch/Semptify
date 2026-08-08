# Semptify Core Context — Paste at the start of EVERY coding session

This is not optional background — it is the foundation every single decision is built on.

---

## What this is — say it out loud before you write a line of code

### This is a public utility. Not a product

It works like a library or a 911 service.
It is open to anyone. No account needed. No trace left behind. No promotion. No sign-up. No return visit goal.

The fastest someone gets from our site to real help — that is the only metric that matters.
We call it: **Time to Real Help.**

Not sessions. Not return visits. Not engagement. Not signups.
**Time to Real Help.** That is the north star. Every feature either reduces it or it doesn't belong here.

---

## Who we are

**Semptify.org** is a nonprofit. We exist for one reason: to help people in housing crisis navigate tenancy law, find real help, and not get lost in a system designed to confuse them.

We are not a business. We do not sell anything. We do not promote ourselves.
We optimize for one thing: **clarity under stress.**

We never want to profit from other people's desperation. If this site was not needed, that would be the best possible outcome. We build it anyway, because it is needed, and because it is the right thing to do.

---

## Who we are building for

Our users are in crisis. They may be:

- Facing eviction tonight
- Reading a notice they don't understand
- Terrified, overwhelmed, barely holding it together
- On a phone with a cracked screen and low battery
- Not tech-savvy
- English may not be their first language
- Dealing with this alone, with no one to call

### This changes everything about how we build

Every decision — layout, wording, color, flow — is made for this person in this moment.

---

## The one thing we tell people

We do not give legal advice. We say one thing:

> "Get legal advice from a qualified attorney."

Everything we build must make it easy to reach that message AND reach real outside help resources — even when our site breaks, even when a page errors, even when they are completely lost.

**There must never be a dead end.** Every error page, every broken flow, every moment of confusion must route the user toward real help. Not leave them hanging.

---

## What we NEVER build — no exceptions, no debate

If a feature serves Semptify, we do not build it.
If a feature serves the user in crisis, we build it.

When you are unsure, ask: **"Who does this serve?"**
If the answer is the organization — stop. Delete it. Start over.

### Never build these:

- User accounts of any kind
- Login or sign-up flows
- Email collection
- Newsletters or mailing lists
- Push notifications or re-engagement features
- "Follow us" links or social media promotion
- Analytics that track individual users
- Pop-ups of any kind — including cookie banners before help is shown
- Banners or pages promoting the site itself
- Waitlists
- Referral systems
- Donation asks on any crisis-facing page (wrong moment, wrong reason)
- Anything that makes people come back to US instead of getting help
- "Create an account to save your progress" — no. Just no.
- Any dark pattern. Any manipulation. Any guilt. Any pressure.

### Why this matters:

Every sign-up form, every pop-up, every "follow us" link is a door that closes in the face of someone who is scared and needs help right now. We do not close doors. We open them.

---

## Design principles — these override your defaults

### 1. Calm over clever

No animations that distract. No fancy interactions that confuse. Every screen should feel like a steady hand on a panicked shoulder. If it looks impressive, ask if it helps. If it doesn't help, remove it.

### 2. One thing at a time

Never show a user more than one decision at a time. No walls of text. No multiple columns of competing options. One clear next step. Always.

### 3. Always a way out — on every single page

Every page must have a clearly visible path to:

- Outside legal help resources (phone number minimum — always visible, never hidden)
- Back to the home page
- A human contact if one exists

This is not a footer feature. This is top-level, always visible, on every page including error pages.

### 4. Plain language only

- No legal jargon without an immediate plain English explanation right next to it
- No tech jargon
- Short sentences. Under 20 words where possible.
- If a stressed, distracted 10-year-old couldn't understand it in 10 seconds, rewrite it.

### 5. Mobile first, always

Most users are on phones. Build mobile first. Test at 375px width. Design for thumbs, not mice. If it works on mobile it will work on desktop. Not the other way around.

### 6. Build the error state first — not last

An error page that routes someone to a help line is better than a polished page that leaves them confused and alone. Build the failure states and fallbacks BEFORE the happy path. Always.

---

## What "done" means here

A feature is NOT done when it works. It is done when:

- [ ] It works on mobile (375px width minimum)
- [ ] It has an error state that routes to real help
- [ ] It uses plain language — no jargon without explanation
- [ ] It shows one decision at a time
- [ ] A stressed, distracted person could use it in under 30 seconds
- [ ] It does not dead-end anyone, ever
- [ ] The help line and legal aid link are still visible on this page
- [ ] It does not ask for any personal information that isn't absolutely required

---

## Tech principles

- **Accessibility is non-negotiable.** WCAG AA minimum. Screen reader compatible. This is not a nice-to-have.
- **Speed is non-negotiable.** Under 3 seconds on a 3G connection. No heavy frameworks without a clear reason.
- **Progressive enhancement.** If JavaScript fails, the core content and help links still show. A user should never get a blank screen.
- **Test on real devices.** Not just browser developer tools.
- **No third-party trackers** that send user data anywhere without explicit necessity.

---

## Before you write any code, stop and ask:

1. Does this make it easier or harder for someone in crisis to find real help?
2. What happens when this breaks? Does it route to help, or leave someone hanging?
3. Is this the simplest possible way to do this?
4. Would a stressed, scared person understand this in 10 seconds on a cracked phone screen?
5. Who does this serve — the user or the organization? If the organization, delete it.

---

## Our values — built into the code, not posted on a wall

We measure twice and cut once.
Quality over quantity.
Fact before fiction.
We do not act out of fear, greed, or the need for recognition.
We do things the right way because it is the right thing to do.
Every line of code either helps someone in crisis — or it shouldn't be there.
