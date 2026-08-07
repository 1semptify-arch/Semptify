# Semptify Documentation System

This directory holds all Semptify documentation. The system is designed to make
documentation drift **visible fast** rather than to make editing docs automatic.
A human or agent still reviews every real update, per Semptify's existing sign-off
rules.

## Structure

```
docs/
  admin/         — internal admin operations, module registry, contracts, deploy
  user-guides/   — tenant-facing how-to content
  help/          — support / FAQ-style content
  adr/           — Architecture Decision Records (permanent, dated, never edited)
  doc-map.yaml   — maps each doc to the code paths it describes (load-bearing)
  README.md      — this file
```

## How it works

Four mechanisms, each independent:

### 1. `doc-map.yaml` (load-bearing)

Each entry maps a doc to the code paths whose behavior it describes:

```yaml
- doc: user-guides/uploading-documents.md
  covers:
    - app/modules/vault
    - app/modules/onboarding
  category: user
```

Without this mapping there is no way to know which docs a given code change
should have touched. **Adding a new doc means appending an entry here** — the
staleness check only sees docs that appear in this file.

### 2. Commit-tagged categorized changelog

Every commit touching something in a doc's `covers` list gets a category prefix
in its message: `admin:`, `user:`, `help:`, or `adr:`. A git hook / CI step
parses commit messages on push and appends a line to
`docs/CHANGELOG-{category}.md` — timestamp, commit hash, short description,
files touched.

This produces a running, categorized log automatically. No one has to remember
to write it by hand.

> **Status:** hook not yet implemented. Tracked follow-up.

### 3. Scheduled staleness check

A script (cron or CI, weekly) does the following for each entry in
`doc-map.yaml`:

1. Find the most recent commit date touching any file in `covers`.
2. Compare against the most recent commit date touching the doc file itself.
3. If the code changed more recently than the doc **and** the gap exceeds
   **21 days**, flag it.

Output: `docs/STALENESS-REPORT.md`, regenerated each run — not auto-committed
changes to the docs. A designated agent triages the report, drafts update
tasks, and pings Brad only for Tier-A-adjacent content per existing sign-off
rules. A flagged item still goes through normal review before anything changes.

> **Status:** staleness script not yet implemented. Tracked follow-up.
> Threshold: 21 days (decided 2026-08-06).

### 4. ADRs for foundational decisions

Some content doesn't belong in a "living doc" that has to stay perfectly current
forever — it belongs in a permanent, dated record. Examples: the storage
architecture split (ADR 0001), the Navigation Principle, the banned-motivations
standard.

Format: `docs/adr/NNNN-<slug>.md`, numbered sequentially. See
`docs/adr/TEMPLATE.md`.

**Old ADRs are never edited.** If a decision changes, write a new ADR
referencing and superseding the old one. This is what stops drift on this
category of content — there's nothing to keep "up to date," just a clear,
permanent trail.

### Agent attribution

No new sign-in system. The existing file-based locking in
`tools/workorder_runner.py` already tracks which agent touched what and when
(`claimed_by.agent` + `claimed_at` on each task, guarded by `FileLock`). The
commit-tagged changelog (mechanism 2) pulls attribution from there rather than
building a parallel identity system.

## What this system does NOT do

- It does not auto-rewrite documentation. Ever.
- It does not decide what's "correct" — it only flags where doc and code have
  diverged.
- It does not replace the one-task-per-commit / no-self-approval rules already
  standing for Semptify.

## Current state (2026-08-06)

- [x] Directory structure scaffolded.
- [x] `doc-map.yaml` created with existing docs backfilled (mapped at their
      current flat paths in `docs/`).
- [x] ADR template + ADR 0001 (storage architecture split) created.
- [ ] Commit-tagged changelog hook — follow-up.
- [ ] Staleness check script — follow-up.
- [ ] Relocate existing flat docs into subdirs — follow-up (do NOT do this in
      the same pass as the staleness mechanism; see Known Failure #17).

## Follow-up: relocating existing flat docs

Existing docs (`ADMIN_MANUAL.md`, `USER_GUIDE.md`, etc.) currently live flat in
`docs/`. They are mapped in `doc-map.yaml` at those flat paths. The intended
final layout is to move them into `admin/`, `user-guides/`, etc., but this must
be a dedicated pass that updates every reference (template links, AGENTS.md
pointers, etc.) and verifies the running app still resolves them — not a
side effect of the staleness mechanism. A half-finished relocation committed
overnight is worse than no relocation (Known Failure #17).
