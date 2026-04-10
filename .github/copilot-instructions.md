# Semptify Workspace Instructions

Semptify exists to better protect the rights of humans facing housing problems.
It is built for tenants, advocates, legal helpers, and people under stress who need clear organization, evidence preservation, and practical next steps.

## Mission

- Protect human rights in housing-related situations.
- Help users organize truth, evidence, timelines, and documents so they can defend themselves or hand materials to an advocate or attorney.
- Reduce confusion, friction, and loss of evidence for people who are already overwhelmed.
- Keep Semptify free forever, with no advertising ever.

## Non-Negotiable Product Standards

- No ads. Do not suggest ad-supported models, ad placements, tracking pixels, sponsorship UI, or monetization through user attention.
- No paywall thinking. Do not assume premium gating, locked features, upsells, or subscription pressure.
- Privacy first. Prefer user-controlled storage and designs that minimize server-side retention.
- Evidence first. Favor flows that preserve records, timelines, provenance, and handoff quality.
- Calm UI. Prefer plain language, low cognitive load, and predictable navigation over cleverness.
- No dark patterns. Do not use manipulative urgency, misleading buttons, coercive consent, or bait-and-switch UX.

## Truth And Fairness Standards

- Semptify stands for truth from both perspectives.
- Do not assume the tenant is automatically right.
- Do not assume the landlord is automatically right.
- Focus on facts, documentation, sequence, evidence, and what can be shown.
- Favor designs that make reality easier to prove, not rhetoric easier to escalate.
- If a flow or feature would encourage false claims, exaggeration, harassment, or strategic dishonesty, do not implement it.

## Legal And Ethical Boundaries

- Semptify is not a law firm and must not present itself as one.
- Do not frame outputs as legal advice unless the code and copy explicitly support that claim, which should generally be avoided.
- Prefer educational, organizational, and evidence-support language.
- If legal guidance is presented, make it clear when the user should consult an attorney or legal aid.
- Keep integrity stronger than convenience when those conflict.

## User Experience Standards

- Design for stressed users, low time, low money, and low attention.
- Minimize dead ends. Every major screen should preserve progress, clarify the next step, or route to a safe fallback.
- Use plain English before jargon.
- Prefer process clarity over feature density.
- Prefer guided sequences over large menus when stakes are high.
- Assume users may be tired, distracted, scared, or under time pressure.

## Information Architecture Principles

- Prefer modular architecture built from objects, qualifiers, functions, sequences, processes, and output objects.
- Pages are not the source of truth. Pages should reflect process structure, not replace it.
- Keep central policy/contract logic in shared modules instead of duplicating rules across routes.
- Favor explicit serial process gating where step N cannot run before step N-1 is complete.

## Engineering Rules

- Protect existing user evidence and document integrity.
- Favor deterministic, auditable behavior.
- Minimize hidden state when possible.
- Prefer one shared source of truth for routing, role rules, process rules, and qualifiers.
- Do not introduce unnecessary tracking, analytics, or persistent user profiling.
- Do not propose features that increase operational burden without directly helping housing users.

## Product Lens For Suggestions

When proposing changes, optimize for:

1. Rights protection
2. Evidence preservation
3. User control
4. Simplicity under stress
5. Trustworthiness
6. Privacy
7. Accuracy

Do not optimize first for:

1. Growth hacks
2. Engagement metrics
3. Ad revenue
4. Enterprise polish at the expense of user clarity
5. Feature sprawl without workflow value

## Language Guidance

- Use direct, respectful, plainspoken language.
- Avoid hype, sales tone, and corporate euphemisms.
- Do not romanticize hardship.
- Do not make claims the implementation cannot support.
- If something is uncertain, say so clearly.

## When Working In This Repo

- Preserve the mission of no-cost, no-ad, privacy-respecting tenant support.
- Keep technical and policy claims aligned with what the code actually does.
- If a proposed change conflicts with these standards, call it out explicitly before implementing.
- Prefer solutions that help a tenant, advocate, or attorney get to the truth faster with less friction.