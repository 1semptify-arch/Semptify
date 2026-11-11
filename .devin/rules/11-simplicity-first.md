---
description: Simplicity-first directive — the 5-step algorithm for every build, design, and review decision (Brad, 2026-11-11)
---

# Simplicity-First — the 5-Step Algorithm

*(Standing rule from Brad, 2026-11-11. Applies to every build, design, and review decision — code, UI, copy, docs, process. Companion to `CORE_CONTEXT.md` "Calm over clever" and the pre-code question "Is this the simplest possible way to do this?")*

## Why

Every part is a cost: a thing a stressed user can trip on, a thing that can break, a thing someone must maintain. Complexity is guilty until proven innocent. The minimum that reaches the goal is the default — everything else earns its place or it goes.

## The algorithm — run it in order

1. **Goal.** State the goal in one sentence before touching anything. If you can't, stop — you're not designing, you're wandering.
2. **Minimum set.** Name the smallest set of parts that reaches the goal. "Parts" means whatever the medium is made of: files, functions, screens, sections, fields, rules, dependencies, words.
3. **Justify the rest.** Anything beyond the minimum set must carry its own stated justification tied to the goal. "Might need it later," "nice to have," and "it's what frameworks do" are not justifications.
4. **Subtract-first review.** Before adding to anything existing, look for what to remove. Review passes ask "what can come out?" before "what should go in?"
5. **Fewer-parts tie-break.** When two approaches are otherwise equal, the one with fewer parts wins.

## What this is not

- **Not minimalism for its own sake.** A justified part stays — the rule is that the justification is spoken and tied to the goal, never assumed.
- **Not a gate on access or function.** Per `.devin/rules/10-progressive-disclosure.md`, if a user's situation requires a function it is available, full stop. Simplicity governs *how much surrounds* a function, never whether it exists.
- **Not permission to ship incomplete.** "Minimum set" means the minimum that *reaches the goal* — including required states (error paths, a way out, mobile). A set that misses the goal is not the minimum set; it's a shortfall.

## Where it binds

- **GUI work** — enforced via the `gui` skill (`.devin/skills/gui/SKILL.md`): listed in the binding rules and checked in the verify pass.
- **Code review** — enforced via the `review` skill (`.devin/skills/review/SKILL.md`): unjustified parts are findings, same class as scope violations.
- **Everything else** — modules, public surfaces, copy, docs, process: same algorithm, same order.
