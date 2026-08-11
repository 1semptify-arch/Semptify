# ADR 0006: Open Access

Date: 2026-08-06
Status: Accepted

## Decision

Every piece of public information on semptify.org — the Know Your Rights Library and anything like it — is open, 24/7/365, to everyone, with no login, no gating, and no picking who gets to know what.

The Portal's audience roles (Tenant, Advocate, Agency, Researcher, Developer, Legal Professional, Donor) are **not** access tiers. They exist purely to surface the *right tools* for how that person works. Both a tenant reading alone and an advocate managing several clients draw from the exact same open, unrestricted information base. Nobody's access to facts is narrower because of their role. Only the toolset tuned around those facts changes.

Guiding line: **a good teacher shows you where to look, not what to see.** Semptify guides navigation. It never curates who's allowed to see what.

OAuth and logins exist solely to protect a tenant's *own personal data* inside their own tools (the Vault, the personal document set) — never to gate the shared, public information layer.

## Why

Housing rights information is a public good. Role-based access restriction would contradict Semptify's nonprofit mission and the Navigation Principle (ADR 0002). OAuth for personal vault data is a technical requirement for storage-dependent features (ADR 0001), not a permission model for facts.

## Consequences

- Public routes for law library, state laws, help, and informational pages MUST remain in `PUBLIC_PREFIXES` / exempt from auth middleware.
- Role selection MUST NOT filter or hide public information content.
- New modules in the KNOW pillar MUST default to public, unauthenticated read access unless storing user-specific data.
- Any proposal to gate informational content behind login MUST be rejected unless it stores personal user data only.
