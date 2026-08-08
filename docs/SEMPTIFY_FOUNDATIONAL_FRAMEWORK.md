# Semptify Foundational Framework — Canonical

**Status:** APPROVED 2026-06-28
**Sources:** Claude first pass + Gemini cross-check (8-document bundle review)
**Authority:** This is the SSOT for all structural decisions going forward

---

## I. The Four Pillars of Semptify

### 1. RECORD (The Armour)

Capture and preserve. Forensic-grade evidence.

- **Focus:** Vault, FEMS, Timeline, Journal, Document Certification
- **Modules:** documents, vault, timeline, briefcase, fems, journal

### 2. KNOW (The Fact-Base)

Education without advice.

- **Focus:** Law Library, State Statutes, CCL (Court Case Lookup), RISC
- **Modules:** law_library, state_laws, risc, free_api, search

### 3. ACT (The Sword)

Lawful exercise of rights.

- **Focus:** Case Builder, Eviction Defense, MNDES Exhibits, Complaint Wizards
- **Modules:** mndes, case_builder, eviction_defense, court_forms, complaints

### 4. INTEGRITY (The Foundation)

Platform governance.

- **Focus:** The Forge (Dev), Capability System, Conductor (SSOT Nav), SSOT Metrics
- **Modules:** onboarding, capabilities, development (Forge), setup

---

## II. Non-Profit Org Structure (501(c)(3))

### Board of Directors (7 Seats)

1. **Tenant Representative** — lived experience
2. **Housing Attorney** — legal integrity
3. **Data Privacy Expert** — oversees privacy-first promise
4. **Forensic Document Expert** — oversees evidence standards (MNDES/FEMS)
5-7. **Community/Non-Profit Leaders** — fundraising and outreach

### Staff (Phase 1)

- **Executive Director** — mission & fundraising
- **CTO** — guardian of PROJECT_BIBLE and AGENTS.md
- **Programs Manager (Law Library)** — curates 50-state fact-base
- **Advocacy Liaison** — manages tenant union and legal aid relationships

---

## III. Website Map (SSOT Compliant)

### Public Site (Unauthenticated)

- `/` — Welcome (the journaling pitch)
- `/about` — the dissertation in public form (the cause)
- `/library` — public preview (search-friendly KNOW content)
- `/transparency` — real-time integrity stats (uptime, no-tracking proof)

### The Conductor (Middleware)

All `/login` or `/start` requests hit onboarding router to check gates:
`[nothing] → storage_connected → vault_initialized`

### App Portals (Role-Based)

- `/tenant/home` — the journal + timeline
- `/advocate/home` — caseload management (shared vaults)
- `/legal/home` — case building & MNDES exhibit generation
- `/manager/home` — compliance checklist (privacy-locked)
- `/admin` — the Forge, module console, user management

---

## IV. Role-Based GUIs

| Role | Primary Device | Philosophy |
| ------ | --------------- | ------------ |
| **Tenant** | **Mobile** | "Calm in the Storm." One-tap journaling. Fast upload. |
| **Advocate** | **Tablet/Laptop** | "Bridge-builder." Scanning multiple clients. Document delivery. |
| **Legal** | **Desktop** | "The Precision Tool." MNDES formatting. Case chronology. |
| **Manager** | **Desktop** | "Compliance Officer." Rent ledgers and notice logs. |
| **Admin** | **Desktop** | "The Architect." Toggling flags in the Forge. |

---

## V. Module-to-Pillar Mapping

### RECORD (Core 5.0)

- `app.modules.documents.router`
- `app.modules.vault.router` / `vault_engine.router`
- `app.modules.timeline.router`
- `app.modules.briefcase.router`
- `app.modules.fems` (Extended)
- `app.modules.journal` (implicit in Core)

### KNOW (Core 5.0)

- `app.modules.law_library.router`
- `app.modules.state_laws.router`
- `app.modules.risc.router`
- `app.modules.free_api.router` (property/landlord lookup)
- `app.modules.search.router`

### ACT (Extended — disabled by default)

- `app.modules.mndes.router` (CORE — always ready for MN)
- `app.modules.case_builder.router`
- `app.modules.eviction_defense.router`
- `app.modules.court_forms.router`
- `app.modules.complaints.router`

### INTEGRITY (Dev/Admin)

- `app.modules.onboarding`
- `app.modules.capabilities.router`
- `app.modules.development.router` (the Forge)
- `app.modules.setup.router`

---

## VI. Tenant Home Page — The Launchpad

**Design principle:** "Calm dashboard." Not overwhelming. A stressed tenant at midnight should know exactly what to do.

### Top Section (Status)

- Greeting: "Hello, [Name]."
- Health badges: `[Vault: Connected ✓] [Jurisdiction: MN] [Role: Tenant]`

### The Big Three (Quick Actions — Mobile Optimized)

1. **📝 Write in Journal** — PRIMARY action (dissertation logic: Semptify IS the journal)
2. **📄 Add Document/Photo** — secondary (record logic)
3. **⚖️ Check a Right** — tertiary (KNOW logic)

### Middle Section (The Pulse)

- Recent timeline feed (last 3 entries)
- **Direct navigation buttons:**
  - `[📁 Document Center]` — vault access
  - `[📖 Law Library]` — KNOW pillar
  - `[🔎 Court Case Lookup (CCL)]` — the "sword" of KNOW

### Bottom Section (Progress)

- Onboarding/vault status — if `vault_initialized` is false, show massive "Setup your Vault" button
- Next steps — "You have a hearing in 12 days" (if timeline detects court date)

---

## VII. Key Corrections from Gemini Cross-Check

1. **Journaling is #1 action** — not upload. Semptify is "The Tenant's Journal"
2. **MNDES is CORE** — Minnesota court exhibit system, always ready
3. **FEMS is forensic** — not just document ingestion, it's Forensic Evidence Management
4. **Judge is distinct** — higher standard of evidence integrity
5. **Conductor handles escape hatches + TTL** — SSOT navigation with time-to-live rules
6. **Storage gate is mandatory** — non-skippable for Core 5.0
