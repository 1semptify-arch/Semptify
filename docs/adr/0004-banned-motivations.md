# ADR 0004: Banned Motivations Standard

Date: 2026-08-06
Status: Accepted

## Decision

Semptify will never use **fear, resentment, dishonesty, or greed** as motivation in design, copy, or feature decisions.

If a proposed pattern only "works" because it exploits one of these four — urgency tactics, deceptive wording or images, anger-baiting, dark patterns, profit-first design — it does not ship, no matter how common that pattern is elsewhere.

This is a real standard every feature and wording choice gets checked against, not an abstract brand value.

## Why

Semptify exists to protect serenity of home, not to amplify crisis or manipulate users into engagement. Motivation rooted in fear or resentment teaches adversarial thinking that violates Language Rules (ADR 0005). Dishonesty and greed undermine the Information Integrity Standards in `docs/admin/MOTIVATIONS.md` §7.

## Consequences

- Copy MUST NOT use fear-based urgency ("act now or lose everything") unless citing a genuine legal deadline with source.
- UI MUST NOT use deceptive affordances (fake notifications, hidden costs, misleading progress).
- Features MUST NOT optimize for engagement metrics at the expense of Time to Real Help.
- Any design review MUST explicitly ask: "Does this exploit fear, resentment, dishonesty, or greed?" If yes, stop and redesign.
