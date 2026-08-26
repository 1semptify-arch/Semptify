# ADR 0005: Language Rules

Date: 2026-08-06
Status: Accepted

## Decision

Standing, non-negotiable language rules for all public copy and user-facing UI:

1. **No "evidence." No "proof."** Not until a court date is actually on the calendar. Before that point, use **"documentation of events,"** **"keeping records,"** or **"a paper trail."**
2. **No adversarial words in public copy** — no "fight," "battle," "enemy," "beat them," "take them down." These words do not live on the page.
3. **Composure over intensity, always.** The angrier the underlying situation, the calmer the page needs to sound.

This extends the UPL audit rule (avoid "evidence"/"proof" as legal terms of art broadly) — this is the sharper, standing version.

## Why

Courtroom-weight language before a court date escalates anxiety and implies legal conclusions users are not qualified to make. Adversarial framing contradicts the Wisdom Principle and serenity-of-home positioning in `docs/admin/MOTIVATIONS.md`. Calm language helps users stay proactive rather than reactive.

## Consequences

- Public templates, law library content, help pages, and marketing copy MUST be audited for banned terms before ship.
- Internal code identifiers MAY use technical terms (e.g., `is_evidence` in timeline metadata) but user-visible strings MUST follow these rules.
- AI-generated content MUST be reviewed against this ADR before publication.
- Violations found in audit or review MUST be fixed, not deferred.
