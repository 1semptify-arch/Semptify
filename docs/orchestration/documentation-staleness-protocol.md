# Semptify — Documentation Staleness Protocol

## The Problem, in Brad's Own Words
When working through a problem, old attempts and references carry over. Even after something is fixed, remnants of the old approach can still be found later and get blended with the new fix — producing confused, inconsistent output the next time someone (human or agent) touches that area.

## Standing Rule
Stale content never gets left "just in case." Once something is superseded, it is either:
1. **Deleted outright**, if it's genuinely dead or a duplicate, or
2. **Explicitly archived** to a clearly labeled location, with a one-line reason and date logged in `BUILD_STATE.md`.

Nothing stale should be discoverable by a normal repo search without also surfacing that it's been superseded.

## Recurring Agent Task: Documentation Reconciliation Pass
Assign to SWE-1.7 (trusted tier), on a recurring cadence:

1. Pull the canonical source-of-truth docs: `NAMING_SSOT_DICTIONARY.md`, `SEMPTIFY_REFERENCE_LIBRARY.md`, `BUILD_STATE.md`.
2. Context-search the rest of the repo (docs, comments, READMEs, handoff files) for anything that contradicts or duplicates what the SSOT says.
3. For each contradiction found:
   - If the SSOT is correct and the other reference is simply outdated → archive or delete the outdated reference, log it in `BUILD_STATE.md`.
   - If the SSOT itself looks outdated → **STOP.** Flag it. Do not resolve unilaterally — this routes back to Brad.
4. Never silently merge old and new content. If it's ambiguous which version is current, flag it rather than guessing.

## Known Existing Risk Areas (feed these in first, don't start from scratch)
- The footer has three parallel implementations (`base.html` block, `unified-footer-loader.js`, `components/` partial) — disclaimer wording can drift out of sync across them.
- `gap_report.py` may be lagging behind actual repo state — it already caught this once (a flagged "gap" turned out to be stale; the real fix had already landed).
- The legacy pages audit still has roughly 57 files pending a mount decision.
- Two loose-end triage items are still open from the last board reconciliation pass.

## Handoff Folder Sweep (standing rule)
Brad drops new handoff files into `C:\master-repo\hand offs and temp` as a temporary staging area — it is not a permanent home for anything. As part of every reconciliation pass:

1. Check `C:\master-repo\hand offs and temp` for any files that have landed there.
2. Move each file to its correct home in the repo (see the Information Package Index for where orchestration docs belong; other file types follow their own established locations).
3. Once a file is moved and confirmed in its correct home, remove it from the temp folder — nothing lingers there "just in case."
4. If it's unclear where a given file belongs, flag it rather than guessing or leaving it in temp indefinitely.

This keeps the staging folder clean between drops and prevents the same carry-over/blending problem this protocol already exists to solve — files sitting unmoved in a dump folder are just another form of stale, unreconciled content.

## Guardrail
This shares infrastructure with the documentation staleness-check system already queued (alongside the OCR/semantic-reasoning beta accuracy tracker). Build them together as one system, not as two overlapping ones.
