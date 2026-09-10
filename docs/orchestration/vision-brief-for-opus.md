# Semptify.org — Vision & Build Parameters
*A briefing document, written to bring another Claude model (Opus) fully into the vision before working on organizational, product, or web architecture decisions.*

---

## 1. What Semptify Is

Semptify is a nonprofit tenant-rights platform. Brad is the sole founder and director. It began roughly a year ago as a personal document organizer during Brad's own landlord dispute (Velair Property Management / Lexington Flats, Eagan, MN) and grew into a broader mission once it became clear the same tools that helped him would help any tenant.

**The foundational insight, stated plainly:** tenants cannot "win" against landlords in any meaningful sense. The legal and financial power is asymmetric and stays that way. The best realistic outcome is *damage limitation* — protecting a tenant's position, documentation, and options before and during a dispute. Semptify is not a weapon. It is **armor**.

**The Wisdom Principle:** the highest form of help is the instruction that prevents the dispute from happening at all. A tenant who knows their rights early, documents things early, and recognizes a red flag early may never need to fight anything.

**The Navigation Principle:** Semptify is engineered like a road system — always open, always navigable, no gates or checkpoints. Not like a building you need a badge to enter. This is enforced as both a design rule and a vocabulary rule throughout the codebase and the site.

Grounded legally in the implied warranty of habitability and the implied covenant of quiet enjoyment.

---

## 2. Who It's For

Tenants — full stop, no login required, nothing gated. All public information (rights, statutes, guidance) is open 24/7/365. The only place authentication exists at all is to protect a *tenant's own personal documents in their own cloud storage* (see Zero-Persistence, below) — never to gate access to knowledge.

Beyond tenants, the Portal (semptify.org/portal) recognizes several audience roles, but — critically — **these are not access tiers.** They only change which tools are surfaced to match how that person works:

- **Tenant** — the core user
- **Advocate**
- **Agency** (housing caseworkers / county caseworkers)
- **Researcher**
- **Developer**
- **Legal** (attorneys who eventually take over a real dispute)
- **Donor**

Semptify's job stops at handing a real attorney clean, organized documentation. It is not a law firm and doesn't pretend to be one.

---

## 3. Non-Negotiable Principles (already locked, not open for re-litigation)

These are structural commitments, not preferences:

1. **Zero-persistence / storage-as-identity.** Semptify never holds a tenant's documents. OAuth connects to the tenant's *own* cloud storage (Google Drive, OneDrive, Dropbox — iCloud not yet included). Semptify is the organizer, never the vault. No local/filesystem storage of tenant data anywhere, no exceptions, including for admins.
2. **Genuinely free infrastructure.** Every service Semptify depends on must be free-tier in reality, not just at first glance. Any ambiguity gets flagged before anyone builds on it.
3. **Know Your Rights is system logic, not a destination.** Rights information isn't a separate page tenants have to go find — it surfaces contextually wherever they're already working (the "Law Linker"), because a tenant mid-crisis won't go hunting through a library.
4. **Facts, not verdicts.** Anywhere Semptify presents information about landlords, property managers, or ownership structures, it stays neutral and sourced — comparing claimed vs. documented facts, never delivering conclusions or accusations.
5. **"Director, not repository."** A four-piece token/security model is planned (targeted for 5.1, not yet implemented) so that no single entity (including Brad, including any future admin) can unilaterally access everything.

---

## 4. The "One Building" Architecture — Org, App, and Site as a Single Picture

This is the mental model to hold all three pieces (organization, app, website) together instead of as separate projects:

- **semptify.org** is the whole building — the public-facing organization's presence in the world. It carries the mission, the trust, the legal nonprofit identity, the donor relationship, the "front door."
- **The Portal** (semptify.org/portal) is the building's concierge desk — it routes each visitor to the room suited to them, based on audience role, without ever locking a door behind them.
- **"Semptify 5.0"** (the FastAPI app, the Vault/Document Organizer) is **one room in the building** — the tenant's private workspace for organizing their own documents, using their own storage. It is not the whole building, and shouldn't be thought of as the whole product.
- **The landing page ("lobby")** stays deliberately narrow in scope: one warm welcome for tenants, built around "comforts of home" imagery (a yard with kids playing, a warm fireplace, a family library for learning and quiet reading, pets, a place to relax and rest, a dinner table, a bathtub and shower, a tree and sunshine, and a window with moon and starlight shining through) — evoking the emotional truth that a rental implies a home, and a home implies safety. It is not where audience-routing complexity lives; that's the Portal's job.
- **The organization** (the 501(c)(3) nonprofit, currently in formation in Minnesota) is the legal and financial structure that lets the building exist, be trusted, and be funded — grant-seeking and donor relationships are mission-first, funding-second in every piece of outward communication.

The unifying idea: **a tenant should be able to walk in the front door of any of these — the website, the app, a search engine, a caseworker's referral — and land somewhere useful without ever hitting a wall.** Every architectural decision (routing, OAuth, page structure, even code module boundaries) is a downstream expression of that one idea.

---

## 5. Current State Snapshot (so you're not starting from zero)

- Core Vault/Document Organizer app is live and under active stabilization (5.0). New feature surface area (5.1) is intentionally paused until 5.0 is solid.
- GUI has been migrated to a single SSOT (single-source-of-truth) design system; legacy/duplicate pages are being triaged and retired page by page.
- An "Information Orchestrator" and fact-checking pipeline exist so public claims (rights info, statistics) are sourced and auto-verified, with a VETTED/BETA gate so unverified content never reaches tenants.
- A Case Manager role is being designed for agency/county caseworkers, with strict separation from tenant-side data (agency OAuth never touches the tenant vault).
- A transparency/accountability module is planned to map corporate relationships between landlords, property managers, and contractors — neutral, sourced, facts-not-verdicts, never conclusory — and to connect tenants with outside resources, giving them a deliberate and louder voice.
- Nonprofit (501c3) formation is in process in Minnesota; GitHub Sponsors is live under `1semptify-arch`.

---

## 6. What This Conversation With You Is For

Brad wants to bring you (Opus) fully into this vision — not just the code, but the *why* — so that when we work together on:

- **organizational** decisions (nonprofit structure, governance, donor/grant positioning),
- **product/app** decisions (what Semptify 5.0 and future rooms in the building should and shouldn't do), and
- **web/site** decisions (how the public site, portal, and landing page work together)

...you're reasoning from the same first principles above (armor not weapon, roads not gates, facts not verdicts, zero-persistence, genuinely-free infra). In particular, any parameters we define together should be scoped around the tenant and what happens to a tenant's personal data — especially where persistent storage is concerned. One planned extension of this: once a tenant's own dispute has been resolved, Semptify intends to offer them the option to voluntarily donate whatever information they're willing to share, so future tenants can be better prepared to stand their ground. That donation is opt-in only, happens after resolution, and never changes the zero-persistence rule for a tenant's active case data — rather than defaulting to generic SaaS-startup instincts. The three pieces (org, app, site) are not separate workstreams to optimize independently — they're one building, and every parameter we define for one should be checked against how it serves the tenant standing at the front door.

---

## 7. The Ask

Help us define the build parameters for the organization, the app, and the website **together, as one picture** — not as three separate specs. Concretely:

- **Organization parameters:** what governance, decision rights, and donor/grant posture keep the nonprofit trustworthy and mission-first as it grows past a one-person operation.
- **App/product parameters:** what belongs in Semptify 5.0 (the tenant's private room) versus what belongs elsewhere in the building, and where the line sits between "tool that helps a tenant" and "feature creep that adds risk without adding armor."
- **Site/portal parameters:** how the public site, the portal, and the landing page divide responsibility so a visitor never has to know the internal structure to find their way to help.

For each of these three, we want the same test applied: does this parameter make the tenant's path through the building shorter, clearer, and safer — or does it just make the building more impressive? Where a parameter serves the building more than the tenant, flag it rather than silently building it in.

