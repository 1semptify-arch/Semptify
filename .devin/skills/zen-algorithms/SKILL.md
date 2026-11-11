---
name: zen-algorithms
description: Run the Zen algorithm — the 5-step simplicity doctrine (goal → minimum set → justify rest → subtract-first → fewer-parts tie-break) — on any build, design, review, or refactor decision. Use before shipping any artifact, when asked to simplify or audit complexity, or as the subtract-first pass in review.
---

# Skill

## Zen Algorithms — the executable pass

The doctrine lives at `.devin/rules/11-zen-algorithms.md` (canonical text).
This skill is the runnable form: invoke it on a task, a diff, a page, or a
plan and it produces findings — not vibes.

### When to run

- Before building anything non-trivial
- Before marking any GUI / copy / docs task done
- When asked "is this too complicated?" or "simplify this"
- During review, as the subtract-first pass

### The pass — run in order, report each step

1. **Goal.** State it in one sentence. If you can't, STOP — report
   "no clear goal" and ask for one. Do not proceed.
2. **Minimum set.** List the smallest set of parts that reaches the goal.
   "Parts" = files, functions, screens, sections, fields, rules,
   dependencies, words — whatever the medium is made of.
3. **Justify the rest.** For every part beyond the minimum: state its
   justification tied to the goal, or flag it. "Might need it later,"
   "nice to have," and "that's what frameworks do" are NOT
   justifications — they are findings.
4. **Subtract-first.** In existing code or design, list what can be
   removed before what could be added. Every pass asks "what comes
   out?" before "what goes in?"
5. **Fewer-parts tie-break.** Two approaches otherwise equal → fewer
   parts wins. No debate — it is arithmetic, not taste.

### Guardrails (from the rule — do not violate)

- **Justified parts STAY.** The justification must be spoken and tied
  to the goal — never assumed.
- **Never gates access or function.** Progressive disclosure
  (`.devin/rules/10-progressive-disclosure.md`) governs whether
  something exists; Zen governs how much surrounds it.
- **"Minimum" means minimum that REACHES THE GOAL** — including error
  states, a way out, and mobile. A set that misses the goal is a
  shortfall, not the minimum.

### Output format

Report as:

```
GOAL: <one sentence>
MINIMUM SET: <list>
JUSTIFIED EXTRAS: <each part + its goal-tied justification>
SUBTRACTIONS: <what to remove>
VERDICT: ship | simplify-first | blocked-on-goal
```
