# Semptify — Motivations & Foundational Reference

*Living document. Read this in full at the start of every AI agent, collaborator, or coding session before other work begins.*

Permanent decisions extracted from this doc live in numbered ADRs under `docs/adr/` (0001–0006). Major changes to standing principles get new ADRs; this file may evolve for context and open threads.

---

## 1. What Semptify Is — and Is Not

Semptify is **not** a legal battleground. It is **not** a business. It is not built to fight, beat, or take anyone down a level — even though it exists because someone got run over and had no way to prove it.

Semptify **is** a proactive insight tool. Its job is to help someone see the traps, pitfalls, and obstacles *before* they step in them — so a disagreement with a landlord never has to become a crisis in the first place. Where a crisis has already started, Semptify helps someone get through it with composure, clarity, and a record they can trust.

The word that describes what Semptify protects is **serenity of home.** Not "wins." Not "cases." Serenity — the basic, ordinary peace of living somewhere without fear.

**Guiding sentence for any new feature, page, or piece of copy:**
*"Does this help someone stay proactive and see clearly — or does it drag them into a fight?"* If it's the second, rewrite it.

### The Wisdom Principle

Semptify does not exist to turn tenants into amateur lawyers. It exists so that, with the right instruction at the right time, most people avoid the dispute entirely — because they knew what to do before it became a problem. That's the actual win condition: not "the tenant wins the legal fight," but **the fight mostly never needs to happen.**

When it does happen anyway, the win condition shifts to something just as calm: the documentation is already clean, in order, and complete — so a real attorney can pick it up quickly, argue it, and the tenant gets to go back to living their life instead of carrying a case in their head. Semptify's job stops at "here's your record, organized." It was never meant to be the thing that argues the case.

This is also the legal backbone underneath "serenity of home," not just a nice phrase: nearly every U.S. residential lease carries an **implied warranty of habitability** (the home must actually be livable) and an **implied covenant of quiet enjoyment** (the tenant has a right to peaceful use of the home, free from landlord interference) — whether or not the lease text says so. Semptify isn't inventing the idea that a lease means "your home, your safety." That's already the law. Semptify just makes it visible and actionable.

### Why Semptify Doesn't Look Away

A problem exists because it was allowed to happen. Staying proactive and avoiding unnecessary battles (the Wisdom Principle above) is not the same thing as staying silent — silence is not peace. Choose your battles and your reactions, but don't just let it be. Nudge it, push it, poke it, talk to it — but don't ignore it. Do something, no matter how small the effort. Doing nothing makes you part of the problem.

---

## 2. Language Rules (Standing, Non-Negotiable)

See **ADR 0005** for the permanent record. Summary:

- **No "evidence." No "proof."** Not until a court date is actually on the calendar. Before that point, everything is **"documentation of events,"** **"keeping records,"** or **"a paper trail."**
- **No adversarial words in public copy** — no "fight," "battle," "enemy," "beat them," "take them down."
- **Composure over intensity, always.**

---

## 3. The Six Core Functions

Semptify's entire feature set should trace back to one of these. If a proposed feature doesn't serve one of these six, it's probably out of scope — or it's actually a new function that needs its own justification.

1. **Information** — accurate, current, plain-language knowledge about tenant rights and process.
2. **Research** — helping someone go deeper on their specific situation, not just the general rules.
3. **Documentation** — organizing the paper trail of what actually happened, in order, without embellishment.
4. **Organize** — turning scattered receipts, texts, and photos into something a person (or a court) can actually follow.
5. **Collaborate** — helping people find each other. If a tenants union or association already exists nearby, point to it. If one doesn't exist yet, this is where Semptify says: *it might be time to start one — there's power in numbers.*
6. **Be Heard** — giving someone a way to put their story on the record and pass it on, to whoever will listen — a neighbor, an advocacy group, a legislator. Also the practical side: the tools to file a legitimate complaint when something is actually wrong.

---

## 4. Where Semptify Stands Today

Worst-case-scenario coverage — the panic moments, the eviction-tomorrow questions, the crisis triage — is in decent shape. That work is largely done.

**The next frontier is the Information layer**, and it currently underperforms the rest of the platform. The ambition going forward is explicit: **Semptify should be elite-class among housing information advocacy platforms** — the best-organized, best-presented, most trustworthy source a renter finds when they start looking.

This means the next major body of work is **front-end information architecture** — how content is structured, surfaced, kept fresh, and made genuinely easy to act on.

---

## 5. Landing Page Visual Philosophy

The public landing page should **not** organize itself by topic or category — categorization feels institutional and impersonal, which works against the whole point.

Instead: a rich, varied field of the **comforts of home** — house with a chimney, washer, bathtub, tree, pets, school bus, outlines of people, furniture, and more. The list is intentionally open-ended and non-systematic. The feeling being targeted is bigger than "objects" — it's the reminder that a rental was never supposed to be just a transaction. A lease implies a home, and a home implies safety.

(Size, color, and animation pacing by urgency tier — crisis vs. everyday — still apply from prior design work.)

---

## 6. Site Scope — semptify.org vs. Semptify 5.0

Everything built in this repo (Vault, Document Organizer, tenant GUI, FastAPI backend) is **Semptify 5.0 — the tenant document/vault web app.** That's one room in a much bigger building.

**semptify.org is the whole building:**

- **Lobby** — the public landing page (warm, human, no login, the home-object question field). Emotional, not organizational.
- **Concierge (Portal)** — `semptify.org/portal`. Structured routing: Tenants, Advocates, Agencies, Researchers, Developers, Legal Professionals, Donors, plus standalone tools.
- **Upper floors** — the actual tools per audience: Vault, Advocate Portal, Know Your Rights Library, etc.

See **ADR 0002** (Navigation Principle), **ADR 0003** (Attraction Principle), **ADR 0004** (Banned Motivations), and **ADR 0006** (Open Access) for permanent design standards governing this scope.

### Storage Architecture

See **ADR 0001** (Storage Architecture Split). User documents live in the tenant's own cloud via OAuth; system metadata lives in Cloudflare R2 and Neon PostgreSQL. OAuth is a merge-lane for personal tools, not a perimeter around public information.

---

## 7. Information Integrity Standards (New Priority)

Standing rules going forward:

- **Show sources.** Factual claims get a visible citation or link.
- **Label opinion as opinion.** No blending Semptify's read with settled fact.
- **No advertising, no endorsing.**
- **Disclose AI-generated content.**
- **Fact-check as a standing process, not a one-time pass.**

This standard applies hardest to the Know Your Rights Library and any Research/Information tooling.

---

## 8. Open Threads to Revisit

- **Content freshness pipeline** — see `docs/README.md` (staleness check + weekly report).
- **Sourcing standard for Law Library content**
- **Collaborate & Be Heard as features, not just values**
- **Comfort-of-home shape library** — intentionally open-ended
- **Information sourcing system** — queued after Know Your Rights Library audit remediation
