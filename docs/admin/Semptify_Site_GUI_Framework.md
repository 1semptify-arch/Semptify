# Semptify — Website & GUI Framework
**Core Promise:** *Help tenants with tools and information to uphold tenant rights as a renter — in court if it goes that far, hopefully it won't.*

**The plain-language version — the actual problem being solved:** Semptify replaces the shoebox. Every renter has some version of it — a pile of receipts, notices, texts, and photos shoved in a drawer, impossible to find when it matters. When a landlord claims you owe money, or a case goes to court, a tenant needs to be able to hand over one organized record and say "this is what actually happened, here's my proof." That single sentence is the North Star test for every feature in this document: **does it help organize and keep track of tenancy records so they're ready the moment they're needed?** If not, it doesn't belong, no matter how useful it seems otherwise.

**This reorders the pillars, not just lists them.** RECORD is not one of four equal siblings — it is the reason Semptify exists. KNOW and ACT exist *in service of* RECORD: KNOW helps a tenant understand what's worth recording and why; ACT helps them put an organized record to use once they need to act on it. Neither pillar stands on its own the way RECORD does. If a future feature in KNOW or ACT doesn't ultimately trace back to making someone's records more organized, more complete, or more usable, it's drifting from the core mission.

**⚠ Stable Foundations — Do Not Modify:** The **onboarding/reconnect pipelines** and the **Vault** are proven, working systems. They are the airport hub every other pillar routes through — treated here as fixed infrastructure, not open questions. Every recommendation in this document builds *around* them, never *through* them.

This document defines the human-centered framework for Semptify's website and interface: who it's for, what it must do, how it should feel, and where the lines are.

---

## 1. Core Objectives

1. **Reduce panic to clarity.** Someone arriving at Semptify is often mid-crisis (eviction notice, landlord dispute, unsafe conditions). The #1 job of the site is to turn "I don't know what to do" into "here's my next step."
2. **Organize the evidence that wins cases.** Vault, timeline, and calendar exist so that when it matters — in front of a judge, a housing authority, or a landlord's lawyer — the tenant has a clean, dated, verifiable record.
3. **Never let a deadline get missed.** Court dates, response windows, and notice periods are unforgiving. The calendar/timeline system is a safety net, not a nice-to-have.
4. **Put ownership of data back in the tenant's hands.** Storage-based auth (their Drive/Dropbox/OneDrive) isn't just a technical choice — it's a trust statement: *we don't hold your life over our servers.*
5. **Make legal literacy accessible**, not legalese. The AI Copilot and legal_intel tools should translate law into "here's what this means for you" language.
6. **Prepare, don't just react.** Anticipate what's coming (a court date, a required response, a common landlord tactic) and surface it before the user has to ask.
7. **Level the playing field, not pick a side.** Housing court often moves too fast for anyone — represented or not — to keep up, and management companies with legal teams win largely on resource asymmetry and tenant unpreparedness, not always on the merits. Semptify's job is to make sure the facts can actually be seen and a case can actually be presented — not to presume any landlord or tenant is in the wrong. Right is right and wrong is wrong regardless of which side of the lease someone is on; Semptify's role is preparation and truth, not advocacy for a predetermined outcome. A judge or fact-finder decides — Semptify's job ends at making sure they have something real to decide with.

---

## 2. Who We Serve

| Persona | Situation | What they need most |
|---|---|---|
| **The Blindsided Tenant** | Just received a notice (late rent, eviction, non-renewal) | Immediate clarity: "What does this mean? What's my deadline?" |
| **The Builder** | Ongoing dispute (repairs ignored, harassment, unsafe conditions) | A place to log evidence over time — photos, dates, communications |
| **The Court-Bound** | Has a hearing date | Document packaging, timeline export, "what to expect" prep |
| **The Preventer** | No active dispute, but wants to be protected | Lightweight onboarding, passive document vaulting, education |
| **The Advocate/Helper** | Case worker, legal aid volunteer, family member assisting a tenant | Clear shared views, exportable records, trustworthy audit trail |

Common thread: **most users are here because something already went wrong, or they're afraid it will.** Design for stress, low bandwidth, and possibly a phone screen in a parking lot — not a leisurely desktop browsing session.

---

## 3. How We Serve — The Four Pillars

Every feature in Semptify belongs to one of four pillars. This is the navigation spine of the entire site — nothing decorative, no orphaned features.

| Pillar | Job | What lives here |
|---|---|---|
| **RECORD** | Capture and organize evidence | **Vault** (raw uploads — leases, notices, photos, texts, receipts), **Timeline** (auto-built chronological record), **Document Center** (processed *output* — organized packets, generated letters, exportable case files, certificates) |
| **KNOW** | Answer questions, build legal literacy | **Library** — all legal reference lives here (state-by-state tenant rights, statutes, guides). This is also where the **AI Copilot** operates from — it's the "ask a question, get an answer" surface, not a storage location |
| **ACT** | Take lawful action | Complaint wizard, court-prep toolkit, case builder, eviction defense tools, generated response letters |
| **GOVERN** | Keep the platform itself honest and running | Admin/onboarding, capability system, workflow engine, **AI Coder** — invisible scaffolding, not a user-facing menu item |

**Why this split matters:** RECORD and Document Center are easy to conflate but do different jobs — the Vault is *where things land*, the Document Center is *what comes out the other side* (a court-ready packet, a formatted letter, a shareable export). Keeping them distinct means a user always knows: "am I putting something in, or getting something out?"

The Library is deliberately kept separate from RECORD. Nobody's personal documents live there — it's the shared, jurisdiction-aware knowledge base that stays the same for every tenant, and it's the home base for the AI Copilot's answers. A user should always know: "if I have a question, I go to the Library; if I have a document, I go to the Vault or Document Center."

GOVERN is not something tenants click into day-to-day — it's the layer that makes the other three trustworthy (permissions, audit trail, platform integrity). It matters most for the nonprofit's own accountability, not for tenant navigation.

**AI Coder lives here, not in KNOW.** It's easy to lump it in with the AI Copilot since both are "AI," but they do fundamentally different jobs: the Copilot answers tenant questions from the Library (a KNOW-pillar, user-facing tool); the AI Coder — Claude, doing the actual development work — is a *building* tool that helps develop, maintain, and extend Semptify itself (new modules, fixes, admin tooling). It should be admin/dev-authenticated only, with zero visibility or access from any tenant-facing surface. That line matters even more now that Claude is your active build partner rather than a solo effort: the tooling you use to build Semptify and the product tenants use are two separate trust boundaries, and they should never blur.

### Mapped to specific features:

- **Connect Storage → Identity.** One clear action, plainly explained ("Your Google Drive becomes your Semptify account — no password to lose, no data stored on our servers").
- **Vault** (RECORD) → upload/organize leases, notices, photos, texts, receipts. Auto-classification and duplicate detection work quietly in the background. **This is the busy international airport of Semptify — every other pillar routes through or references it in some way.** It is stable and proven. Locked: no changes.
- **Timeline** (RECORD) → chronological record of everything that happened, in plain language, built automatically from vault activity where possible.
- **Document Center** (RECORD, output side) → one-click "package my case" for court, legal aid, or a housing authority; generated letters and complaint drafts land here too.
- **Calendar** (cross-pillar utility) → deadlines and hearing dates, with escalating reminders as a date approaches.
- **Library + AI Copilot** (KNOW) → "what does this mean," "what should I do next," "what are my rights in [state]" — framed as information, not legal representation. Publicly viewable without login as a trust/credibility surface.
- **Complaint Wizard / Court Prep / Case Builder** (ACT) → the tools that turn documentation and knowledge into a filed complaint, a court-ready packet, or a formal response.

### ACT Pillar — Detailed Breakdown

ACT is where Semptify carries the most legal exposure, because it's the pillar closest to *doing* something with legal consequence rather than just recording or explaining. One rule governs every tool in this pillar, without exception:

**ACT tools prepare and draft. They never submit, file, or represent.** The tenant (or their attorney) always takes the final action — clicking "file," printing and mailing, or walking into court. Semptify hands them something ready to use; it never acts on their behalf. This is the line that keeps Semptify a tool rather than an unlicensed legal practice.

**1. Complaint Wizard**
- **Trigger:** available to any tenant, but proactively surfaced when `case-active` flag is set.
- **Flow:** identify complaint type (HUD, state housing agency, local tenant rights office, state AG consumer protection) → pull relevant facts automatically from Timeline/Vault (dates, communications, photos) → generate a complaint draft using Library's jurisdiction-specific requirements → tenant reviews/edits every field → **output lands in Document Center** as a ready-to-submit draft, with plain-language instructions for where/how to actually file it themselves.
- **Writes back to RECORD:** once a tenant marks a complaint as filed, that becomes a Timeline event automatically — "Complaint filed with [agency] on [date]" — so the case history and the action history are never two separate things to maintain.

**2. Court Prep Toolkit**
- **Trigger:** auto-unlocks on the `court-bound` flag (a hearing date is added to Calendar). This is the clearest case of "unlock by situation, not by asking" from the capability model — nobody should have to know to look for this before they need it.
- **Contents:** a document packet assembled from Document Center + Vault (auto-suggested, tenant confirms what's included), a plain-language "what to expect in the courtroom" guide pulled from Library, a practice Q&A session with the AI Copilot, and the escalating deadline alerts already defined under Calendar (2 weeks out → gather documents, 3 days out → what to expect, day-of → packet ready).
- **Boundary:** this toolkit prepares a tenant to represent themselves or work with an attorney — it does not draft legal arguments framed as if from a licensed attorney, and every generated document carries the "not legal advice" microcopy already established as a site-wide rule.

**3. Case Builder**
- **What it actually is:** the connective tissue of the whole ACT pillar, not a separate silo. It assembles Timeline + Vault documents + relevant Library citations into one structured case file — the single artifact that feeds the Complaint Wizard, the Court Prep packet, and any Advocate/Legal Aid sharing.
- **Why it matters architecturally:** without Case Builder, RECORD and ACT would be disconnected — a tenant would have to manually re-gather evidence every time they used a different ACT tool. Case Builder is what makes "documentation" and "action" feel like one continuous process instead of two separate systems.

**4. Response Letter Generator**
- **Function:** template-based drafting for common tenant-to-landlord communication — repair requests, security deposit disputes, responses to a notice — using Library's state-specific requirements to get notice periods and statutory citations right.
- **Guardrail specific to this tool:** because these letters are tenant-to-landlord (not tenant-to-court/agency), it's tempting to let the AI Copilot be more "creative" here. Resist that — every generated letter should stick to facts and statutory rights, matching the "we will not use deception" and "facts, not assumptions" principles already established for the accountability database. A letter with an exaggerated or unverified claim is a liability for the tenant who signs it.

**5. Eviction Defense Tools**
- **Flow:** guided defense checklist (retaliation, discrimination, habitability failure, improper notice, rent paid but not credited) → tenant selects what applies → evidence auto-linked from Vault for each selected defense → generates a defense/counterclaim draft for Document Center.
- **This is the highest-stakes tool in the entire platform** — it's the one most likely to be used in an actual courtroom. It should get the most conservative treatment of the "not legal advice" disclaimer, and ideally a stronger prompt than elsewhere encouraging the tenant to have a legal aid attorney review it before use, given the toolkit itself already documented that legal aid organizations are usually willing to review even when they won't litigate offensively.

**6. Attorney / Legal Aid Intake Packet**
- **The problem it solves:** low-cost and legal aid attorneys operate under severe capacity constraints — every hour spent reconstructing a tenant's timeline from scattered texts, photos, and paper is an hour not spent on the next tenant in the same situation. A tenant showing up with a shoebox costs their attorney far more billable/pro-bono time than one showing up organized.
- **Function:** a one-click export from Case Builder, formatted specifically for fast attorney intake — chronological facts, clearly labeled evidence, dates that matter flagged up front, no editorializing. Not the same as the Document Center's court packet (which is for the court itself) — this one is optimized for a stranger-attorney's first 15 minutes with the case.
- **Why this matters beyond one case:** this is a force multiplier on the entire legal aid ecosystem's limited capacity. If Semptify shaves real time off intake across enough cases, that's capacity freed up for other tenants in the same position — the effect compounds well beyond any single user.
- **Also serves tenants who go it alone:** even a tenant who can't get an attorney and represents themselves benefits from the same organized packet — they walk into court informed instead of blind, which is the entire point of leveling the playing field rather than leaving anyone unprepared by default.


ACT is never self-contained — every tool in it reads from RECORD and KNOW, and writes back into RECORD:

```
RECORD (Vault, Timeline) ──┐
                            ├──> Case Builder ──> Complaint Wizard ──> Document Center (output) ──> Timeline (new event)
KNOW (Library) ─────────────┘                 └─> Court Prep ────────> Document Center (output)
                                               └─> Eviction Defense ──> Document Center (output)
```

No ACT tool should ever be designed as if it operates independently of the tenant's existing case record — that would recreate exactly the kind of duplication and fragmentation already found and fixed in the Vault (three competing systems, no shared source of truth). ACT succeeds specifically because it *pulls from* RECORD and KNOW rather than duplicating what they already hold.



---

## 4. What's Expected of Semptify (Our Commitments)

- **Radical clarity.** No dark patterns, no confusing legal jargon presented as if the user should already understand it.
- **Zero data exploitation.** We don't sell, mine, or leverage tenant data. Storage-based auth is the proof, not just the pitch.
- **Uptime when it counts.** A tenant on the way to court cannot have the vault go down.
- **Accuracy and jurisdiction-honesty.** If we don't know a state/local law confidently, we say so — we don't guess.
- **Emotional respect.** Copy, tone, and error states should never sound clinical, condescending, or bureaucratic to someone already under stress.
- **Accessibility by default.** Screen readers, keyboard navigation, plain-language reading level, mobile-first — not an afterthought.

## What We Expect of Users

- Users own the accuracy of what they upload (we organize, we don't fabricate or verify).
- Users understand Semptify is a tool for organization and information, not a replacement for a licensed attorney.
- Users are responsible for their own storage provider account and its security (2FA encouraged).

## What We Will Not Do

- **We will not provide individualized legal advice or represent anyone in court.** The Copilot and legal_intel content are informational — always framed as "this is general information, consult a licensed attorney for advice specific to your situation."
- **We will not guarantee outcomes.** No promises like "you will win your case."
- **We will not store tenant documents on Semptify's own servers** as primary storage — that's the entire point of storage-based identity.
- **We will not use urgency, fear, or guilt as growth/engagement tactics.** This is a vulnerable-user product; manipulative UX patterns are disqualifying.
- **We will not gatekeep critical safety information behind signup.** Basic "know your rights" content should be visible before someone even connects storage.

---

## 5. Site Structure & Navigation Flow

Principle: **one primary action per screen, always a visible "next step," never a dead end.**

```
Landing (public, no login required)
 ├── "What's your situation?" triage (notice received / ongoing issue / preparing / just learning)
 ├── Library preview (Know Your Rights — state-aware, always public, no login)
 └── Connect Storage → Get Started

Home Dashboard (post-connect)
 ├── Next Deadline (always the top of the page if one exists)
 ├── Case Timeline (RECORD — auto-built, scrollable, plain-language)
 ├── Ask the Library ("Ask a question" — AI Copilot, always one tap away)
 └── Prepare for Court (ACT — appears contextually when a hearing is set)

Top-Level Nav (the Four Pillars)
 ├── RECORD → Vault (raw uploads) + Timeline + Document Center (organized/exported output)
 ├── KNOW   → Library (legal reference + AI Copilot lives here)
 ├── ACT    → Complaint Wizard, Court Prep, Case Builder
 └── (GOVERN is not a nav item — it's the platform layer underneath, only visible to admins)

Secondary
 ├── Calendar (full view — cross-pillar utility)
 ├── Settings / Storage / Privacy
 └── Help & Legal Aid Directory (always accessible, never hidden)
```

**Navigation rules:**
- Top-level nav is the three tenant-facing pillars, plus Home: **Home, Record, Know, Act.** GOVERN never appears as a tenant nav item.
- The single most time-sensitive thing (a deadline) always surfaces at the top of the dashboard — never buried, regardless of which pillar it belongs to.
- No feature is more than 2 taps from Home.
- Every legal or AI-generated answer includes a visible "this isn't legal advice" microcopy — consistent, not naggy.
- A user should never be confused about whether they're *storing* something (Vault) or *retrieving* something they created (Document Center) — the two are visually and structurally distinct, even though both sit under RECORD.

---

## 6. Visual & Interaction Design Principles

- **Tone:** calm authority. Think "a knowledgeable friend who's done this before," not a government form and not a flashy startup.
- **Color:** a grounded, trustworthy palette (deep blue/slate + one warm accent for alerts/deadlines) — avoid alarm-red as a primary brand color since users already feel enough alarm.
- **Typography:** highly legible, generous line height, plain language at a ~7th–8th grade reading level for anything user-facing.
- **Motion:** subtle, purposeful — never playful or attention-grabbing for its own sake. Nothing that feels like it's wasting a stressed user's time.
- **Empty/error states:** always explain what happened and what to do next — never a bare "Error 404" or blank screen.
- **Mobile-first:** most first contact will likely be a phone. Every core flow (especially "upload a document" and "check my deadline") must work one-handed.

---

## 7. Preparing Users for What's Ahead (Scenario Readiness)

The product should proactively surface, not wait to be asked:

- **When a notice is uploaded** → immediately explain what type of notice it appears to be and what the response window typically is (with a jurisdiction caveat).
- **As a court date approaches** → escalating check-ins ("2 weeks out: here's what to gather," "3 days out: here's what to expect in the courtroom," "day of: here's your document packet").
- **If a user goes quiet mid-dispute** → a gentle, non-intrusive nudge to log recent communications before memory fades.
- **Always-visible fallback** → a legal aid / crisis housing resource directory, because Semptify is a tool, not a replacement for human help when things escalate.

---

## 8. Roles, Capability Levels & Cross-Pillar Mechanics

### The approach: capability flags, not paywalled tiers

Given the commitment not to gatekeep safety information, access should unlock based on **situation and verified relationship**, not payment. This is an *attribute-based access control* model: every user carries a set of capability flags, and every pillar checks those flags before showing a feature — rather than assigning someone to a fixed "plan."

**Core flags (auto-granted by situation, not purchased):**

| Flag | How it's granted | What it unlocks |
|---|---|---|
| `tenant-core` | Default on storage connect | Vault, Timeline, Library, Copilot, basic Document Center |
| `case-active` | Auto-set when a notice/dispute is logged | Full complaint wizard, case builder in ACT |
| `court-bound` | Auto-set when a hearing date is added to Calendar | Court Prep toolkit, escalating deadline alerts |
| `verified-advocate` | Tenant explicitly invites someone, invite accepted | Scoped read/comment access to *only* the documents that tenant shared |
| `verified-professional` | Identity/credential check (bar number, legal aid org affiliation) | Multi-case dashboard view, shared only where a tenant has explicitly granted access |
| `org-staff` | Internal onboarding (HR-side, not self-service) | GOVERN admin console access, scoped by role |
| `board-governance` | Appointed by the nonprofit's board process | Reporting/aggregate dashboards only — **no individual case-level data**, for privacy and liability reasons |
| `ai-coder` (system, not human) | Dev-environment authentication only | Code/module access in GOVERN; **never** live tenant PII — works against synthetic/test data |

### Role × Pillar capacity matrix

| Role | RECORD | KNOW | ACT | GOVERN |
|---|---|---|---|---|
| **Tenant (core)** | Full CRUD on own Vault/Timeline | Full access to Library + Copilot | Basic templates | No access |
| **Tenant (case-active/court-bound)** | Same + auto Document Center packet generation | Same, plus contextual proactive alerts | Full complaint wizard, case builder, court prep | No access |
| **Advocate/Helper** | View/comment only on *shared* items — no delete, no access to un-shared documents | Full access (they need it too) | Can co-draft with tenant; tenant retains final send/submit control | No access |
| **Legal Aid / Professional** | Read-only on explicitly shared case packets across multiple tenants | Full access, plus ability to flag Library content for review | Can review/approve before filing, if tenant grants that permission | No access |
| **Org Staff/Admin** | **No access to individual tenant records** — only anonymized, aggregated patterns for the accountability database | Curates/edits Library content through a review workflow | Sees aggregate outcome data only, not individual case content | Full — user management, audit logs, module toggles |
| **Board/Governance** | No access | No access | No access | Aggregate reporting dashboards only |
| **AI Coder (Claude)** | No access to production tenant data | Helps maintain Library structure/backend — not the legal content itself, which needs human/legal review | No access | Scoped dev access to build/extend modules |

The privacy-by-default rule running through this: **the organization itself should have less access to individual tenant data than the tenant's own invited helpers do.** That's an important trust signal — it proves the accountability mission (exposing bad landlords) never becomes surveillance of tenants.

### Mechanics for smooth cross-pillar interaction

1. **Single source of truth.** All capability flags live in GOVERN's capability system. Every pillar — RECORD, KNOW, ACT — checks against that one system before rendering a feature or granting an API call. No pillar maintains its own separate permission logic; that's how systems drift out of sync.
2. **Transparent locking, never silent hiding.** If a feature isn't unlocked yet, show it with a plain-language reason ("This unlocks once you add a court date") rather than hiding it entirely. Consistent with the "keep users well informed" principle — nobody should wonder if a feature exists.
3. **Consent is explicit and revocable.** Every Advocate/Legal Aid access grant is per-document or per-case, initiated by the tenant, and revocable at any time from one place (Settings). This mirrors the storage-based-auth trust model: the tenant owns the keys, always.
4. **Auto-elevation over manual requests.** Flags like `case-active` and `court-bound` should trigger automatically from what's already in RECORD (a notice uploaded, a hearing date added) — the user shouldn't have to "apply" for the tools they need in a crisis moment.
5. **Environment separation for the AI Coder.** Claude's dev access is architecturally isolated from the production tenant database — it builds and tests against synthetic data. This isn't just a policy, it should be a hard technical boundary, since it's the one role with the broadest system reach.
6. **Every access event is logged and visible to the tenant.** "Who has viewed my case" should be a real, checkable screen — not just an internal audit log. That's what makes the whole permission system trustworthy rather than just theoretical.

### Access model: polarity, not permission scopes

Semptify does not use conventional role-based permissions (scopes stacked on an identity). It uses a **connection-state gate**: the whole question is *are you connected* — positive polarity means the connection exists and current flows through it; negative polarity means the circuit is open and nothing passes. There's nothing to "revoke" in the traditional sense — disconnecting *is* the revocation, instantly and completely.

- Every relationship (Tenant↔Advocate, Tenant↔Legal Aid, Tenant↔Vault itself) is its own binary connection point.
- Downstream pillars (Timeline, Document Center, Library, ACT) don't carry separate permission logic — they inherit openness from the Vault's live connection state. No live connection upstream, nothing flows downstream.

### The Vault as keystone: the four-piece lock

The Vault only opens with an active, live OAuth connection to the tenant's own storage provider — this is the keystone the entire system routes through. Reconstructing full access requires **four separate token pieces**, governed by one hard rule: **no single entity may ever hold more than one piece — not the storage provider, not the tenant's device, not Semptify itself.**

1. **OAuth storage token** — held by the tenant's storage provider (Google/Dropbox/OneDrive), tenant-authorized
2. **Device/session token** — lives only on the tenant's own device, never synced to any server
3. **Semptify application-scoped token** — minimal, backend-held, isolated from the other pieces
4. **Self-referential piece** — known only to itself. Not persisted, not held by *any* party — generated and verified only in the moment of access, then gone. There is no copy anywhere to steal.

This is why the system self-heals without needing an admin to do anything: even if the first three pieces were somehow compromised together, completing access still requires regenerating the fourth piece fresh — and a stolen/static replay of the other three can never produce it. Compromise of any one holder (even a breach of Semptify's own backend) yields exactly one of four pieces, which is structurally worthless alone.

This is a stronger promise than "we don't store your files" — it's not a policy choice, it's architecturally enforced. A landlord's legal team, a subpoena aimed at the wrong party, or a breach anywhere in the chain still can't produce a complete key.

---

## 9. Open Questions to Resolve Next

- Which states/jurisdictions launch first (affects how much jurisdiction-specific content the Copilot/legal_intel need)?
- How much should the AI Copilot be allowed to draft (e.g., a response letter to a landlord) vs. purely explain?
- What's the offline/low-connectivity fallback for a user with an unstable phone plan?
- How is the "Advocate/Helper" persona (legal aid workers, case managers) supported — a distinct view, or just shared export?

---

## 10. Rendering Architecture — Module Manifest & Object Spaces (Phase 0 Spec)

**Status: SPEC ONLY — no code exists yet.** This section captures a decision made in a separate planning conversation, before it was lost. It is a content-first alternative to card-based UI: every module declares a data contract (what it needs, what it's doing, what it produces) completely separate from how that gets drawn on screen. The visual layer becomes one possible renderer of that contract, not baked into the module itself.

**Why "not cards":** cards hard-code a visual shape into every module. This spec instead defines a *data contract* per module — the same contract can later render as a card, a row, a panel, or anything else, without touching module code.

### 10.1 The Five Canonical Space Types

Every module/pipeline (Vault, Timeline, AI Planner, future ones) breaks into the same five space types, regardless of what it does:

| Space Type | Purpose | Example (Document Vault) |
|---|---|---|
| **INTAKE** | What the user/system must provide to activate this module | file upload, folder selector, provider token |
| **PROCESS** | What the module is doing / its current state while working | "scanning 12 files", progress bar, classification running |
| **OUTPUT** | The result the module produces | classified doc list, extracted evidence, generated packet |
| **CONTEXT** | Supporting info the user needs to understand the space (not data, but meaning) | disclaimer text, help copy, provider connection status |
| **META** | System-level state not shown as content but used for control | last_updated, error_state, permissions, sync_status |

Exactly 5 types, same meaning, every module. Renaming a type (e.g. `INTAKE` → `ENTRY`) is fine; adding a 6th type is not — if something doesn't fit one of these five, it's a sign the module boundary is wrong, not that the taxonomy needs to grow.

### 10.2 Naming Convention

Strict namespaced ID so the expediter (below) can resolve a space programmatically from any layer of the stack (Jinja2, JS, API response) with zero ambiguity:

```
{module}.{space_type}.{slot_index}

vault.intake.01
vault.process.01
vault.output.01
vault.context.01
vault.meta.01

timeline.output.01   # e.g. "maintenance" events
timeline.output.02   # e.g. "lease update" events
```

### 10.3 The Module Manifest

Each module declares its own space needs in a manifest file — **YAML files on disk, one per module, not Python dicts.** This was an explicit decision: dicts are the "fast now, rework later" option — not diffable, not validatable independent of the running app, and every module addition means touching Python. Files let the *shape* of the system be validated before a single line of rendering code runs.

```yaml
module: vault
label: "Document Vault"
spaces:
  - id: vault.context.01
    type: context
    order: 1
    source: static
    content: "Zero-knowledge storage. Files never leave your provider."

  - id: vault.intake.01
    type: intake
    order: 2
    source: endpoint
    endpoint: /api/vault/connection-status

  - id: vault.output.01
    type: output
    order: 3
    source: endpoint
    endpoint: /api/vault/folders
    depends_on: vault.intake.01
```

Key fields:
- **order** — explicit placement priority (lower = earlier). Default sort mechanism; sufficient for ~90% of cases.
- **depends_on** — for spaces that cannot populate until another space resolves (e.g. can't show folders until the connection is confirmed). If a dependency hasn't resolved, that space renders in a pending/placeholder state instead of blocking the whole page. No full dependency-graph engine needed yet — check `depends_on` before firing each space's data call; upgrade to real topological sort only if circular/multi-level dependencies actually appear.
- **source** — `static` (hardcoded), `endpoint` (calls a FastAPI route), or `computed` (derived from another space).

### 10.4 The System Expediter

The orchestrator. A single service that:

1. Loads every module manifest at startup (or from a registry file)
2. Resolves final render order using `order` + `depends_on`
3. Calls each space's data source (`endpoint` / `static` / `computed`)
4. Assembles a flat **render tree** — a list of resolved space objects, each with its id, type, and populated data
5. Hands that render tree to whatever template/renderer is chosen (Jinja2, JS component, anything)

The render tree is the contract boundary: modules never know or care how they're displayed; the renderer never has to know module internals — it just iterates the resolved list and draws each space by `type`.

```
Module Manifest (YAML) ──> Registry ──> System Expediter ──> Render Tree ──> Renderer
                                              │
                              (order + depends_on resolution,
                               calls static/endpoint/computed sources)
```

### 10.5 Applying It to Current Modules (worked example)

- **Document Vault** → `vault.context.01` (zero-knowledge disclaimer), `vault.intake.01` (connection status), `vault.output.01` (folder list, depends on intake)
- **Timeline** → `timeline.intake.01` (log entry form), `timeline.output.01` (maintenance events), `timeline.output.02` (lease update events)
- **AI Planner** (see naming rule in 10.6) → `ai_planner.intake.01` (query input), `ai_planner.process.01` (thinking/status), `ai_planner.output.01` (plan result)

### 10.6 Naming Rule — No Vendor Endorsement

Internally, calling the AI assistant "Copilot" or by any vendor's product name is fine in conversation. In code, manifests, and anything public-facing, it must be vendor-neutral: `ai_planner` module path / "AI Planning Assistant" in copy. This is not a style preference — it avoids implying endorsement of a specific AI vendor on a public-facing nonprofit site, which is a real liability line, not a cosmetic one.

### 10.7 Build Sequence (Phase 0 → Reference Module)

This order exists specifically to avoid rework — each phase only builds on a layer that's already been locked:

1. **Phase 0 — Naming & schema lock.** Decide every field name, required vs. optional, valid `type` values, and what happens when a `depends_on` target is missing (fail loud vs. render pending). This is a document/spec artifact, reviewed before any code — this section *is* that artifact, pending final sign-off.
2. **Manifest validator.** Fails loud on a malformed manifest at the door — never silently produces a broken page three layers downstream. This is the root-cause-vs-band-aid line: bad input dies at validation, not somewhere in the renderer.
3. **Registry.** Loads and holds all valid manifests at startup.
4. **System Expediter.** Resolves order + dependencies, calls data sources, builds the render tree.
5. **Renderer contract.** Locked before any visual work starts — this is what keeps the system "not cards": once the render tree format is fixed, swapping visual treatment later touches zero module code.
6. **One reference module, fully working, before scaling.** **Vault is the reference module** — it has all three data sources (static, endpoint, computed) and a real `depends_on` case (output waits on intake), making it a genuine end-to-end exercise of every mechanism the system will ever need. Get Vault's manifest fully validated, registered, expedited, and rendered — tested and reviewed — before touching Timeline or AI Planner. A flaw discovered on module 3 that requires redoing modules 1 and 2 is exactly the rework this sequence exists to prevent.

**Reminder — this is a spec, not a build order for right now.** Per `ACTIVE_CONTEXT.md`, this does not preempt the current priority queue (ZIP export, GUI screens 1–4, capability gate sweep). It is captured here so Phase 0 can be picked up deliberately, not accidentally half-started mid-session.

---

## 11. Execution Instructions — SWE-1.7 / GLM-5.2 (Handoff, Not Yet Started)

Per the Fast-Tag Routing System (`Semptify_AI_Orchestration_Blueprint.md`, Section 2), this work is tagged **[EI] — Execution / Isolated**: single-module scaffolding, no cross-module dependencies yet, no security/auth/migration surface. Routes to Windsurf house models (SWE-1.7) or GLM-5.2, per Section 3 of that document.

**Do not start this until the project owner explicitly says go.** Section 10 above is a spec for review, not a green light. If asked to execute, follow this exact order — do not skip ahead to the registry or expediter before the manifest schema for Vault is confirmed correct against Section 10.3.

### Task 1 — Manifest schema + validator (Vault only)
- **Target:** new file, path TBD by whoever's executing but must live under `app/core/` (e.g. `app/core/object_spaces.py` or similar — confirm naming with project owner before creating, per the "no new files without a reason" rule)
- **Input:** the YAML shape in Section 10.3
- **Output:** a function/class that loads a manifest YAML, validates every field against the rules in 10.1–10.3, and raises a clear error (not a silent failure) on anything malformed — missing `id`, invalid `type`, `depends_on` pointing at a nonexistent space, etc.
- **Verification:** a test manifest for `vault` (using the real Vault endpoints already live — `/api/vault/all`, `/api/vault/document/{vault_id}/content`, etc., per the Module Contract Template in the orchestration blueprint) validates cleanly; a deliberately broken manifest (bad `depends_on` target) fails loud with a specific error message naming the bad field.
- **Do not touch:** `app/modules/vault/router.py` or any live endpoint. This task only builds the manifest/validator layer — it does not wire anything into the running Vault module yet.

### Task 2 — Registry (loads all validated manifests)
- **Depends on:** Task 1 passing verification.
- **Output:** a startup-time loader that reads all manifest files from a designated folder (folder name TBD — propose one, confirm before creating), validates each via Task 1, and holds them in memory keyed by module name.
- **Verification:** registry loads the Vault manifest from Task 1 and exposes it by `module` name; loading a folder with one broken manifest fails loud and names which file broke, without crashing app startup silently.

### Task 3 — System Expediter (Vault only, read-only)
- **Depends on:** Task 2.
- **Output:** resolves `order` + `depends_on` for the Vault manifest's spaces, calls each space's declared `source` (for Vault: real `static` and `endpoint` calls against the already-working Vault API — no new endpoints), and produces the render tree structure described in Section 10.4.
- **Verification:** running the expediter against the Vault manifest produces a render tree where `vault.output.01` only resolves after `vault.intake.01` has resolved, and the tree can be printed/inspected as plain data (JSON-serializable) — no template rendering required yet.
- **Explicitly out of scope for this task:** wiring this render tree into any HTML template or replacing any existing Vault page. This task proves the mechanism works, nothing more.

### Rules for whoever executes this (SWE-1.7 or GLM-5.2)
- Follow `AGENTS.md` Known Failure Registry — especially #6 (imports at top of file only) and #13 (never create `_v2`/`_new` files; if a rewrite is needed, ask the project owner to rename the original first).
- No bare `except:` — specific exception types only.
- All new code targets Python 3.11.9 (`venv311`).
- Do not modify `app/modules/vault/router.py`, `app/main.py`, or any live/working route as part of Tasks 1–3. This is additive scaffolding beside the working system, not a replacement of it.
- If any part of the schema in Section 10 is ambiguous when actually writing code, stop and ask — do not guess a field name or behavior that isn't explicitly spelled out above.
- Report back per the Verification Step for each task before starting the next one.
