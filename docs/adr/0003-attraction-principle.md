# ADR 0003: Attraction Principle

Date: 2026-08-06
Status: Accepted

## Decision

Semptify does not route or direct anyone. **It offers.**

Semptify's core job is narrow: **facilitate the tools used for storing and organizing documents.** Everything else — the Library, the Portal, role-tuned toolsets — exists only to make those tools easier to find and better fitted to how a given person works. Nothing is mandated. No feature requires engagement. No path is forced on anyone.

"Role" (Tenant, Advocate, Agency, Researcher, Developer, Legal, Donor) is not the system sorting or directing a person — it is a lens the **user** picks for themselves, purely to make the same open toolset feel more relevant. Semptify decides nothing about who someone is; it tunes what is shown if the person wants that tuning, and steps back otherwise.

Navigation (ADR 0002) rules out checkpoints *within* a path; Attraction rules out any mandate to be on a particular path *at all*. Together they describe a pull system, not a push system.

## Why

Mandatory flows and system-driven routing create the same abandonment and mistrust as physical gates. Users in crisis must always feel they chose their next step. Offering tools without requiring engagement respects composure and the Wisdom Principle in `docs/MOTIVATIONS.md`.

## Consequences

- Features MUST NOT require completion of unrelated steps (e.g., reading the Library before using the Vault).
- Role selection MUST remain optional and user-initiated; roles MUST NOT restrict access to public information (see ADR 0006).
- Onboarding MAY suggest paths but MUST allow bypass or deferral where storage is not yet connected.
- Dark patterns (forced continuations, hidden skip, engagement nags) MUST NOT ship regardless of industry convention.
