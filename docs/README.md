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
in its message: `admin:`, `user:`, `help:`, or `adr:`. The `commit-msg` hook
enforces the prefix, and `tools/docs_changelog.py` parses the history and
regenerates `docs/CHANGELOG-{category}.md` (timestamp, commit hash, short
description, files touched).

This produces a running, categorized log automatically. No one has to remember
to write it by hand.

> **Status:** implemented in `tools/hooks/commit-msg` (enforcement) and
> `tools/docs_changelog.py` (regeneration). Run the regenerator directly or via
> `tools/recurring_scheduler.py --run docs-changelog`.
>
> Enable the `commit-msg` hook with `git config core.hooksPath tools/hooks`.
> (`tools/hooks` also contains an existing `pre-commit` hook; if you only want
> the category check, copy `tools/hooks/commit-msg` to your active git hooks
> directory instead.)

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

> **Status:** implemented in `tools/docs_staleness_check.py` (21-day threshold).
> Run it directly or via `tools/recurring_scheduler.py --run docs-staleness`.

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
- [x] `doc-map.yaml` created with existing docs mapped to code paths.
- [x] ADR template + ADR 0001 (storage architecture split) created.
- [x] Commit-tagged changelog hook — `tools/docs_changelog.py`.
- [x] Staleness check script — `tools/docs_staleness_check.py` (21-day threshold).
- [x] Recurring scheduler — `tools/recurring_scheduler.py` (runs staleness, changelog, and future OCR beta review on a weekly cadence).
- [x] Existing flat docs relocated into `admin/`, `user-guides/`, etc., with cross-references updated.
