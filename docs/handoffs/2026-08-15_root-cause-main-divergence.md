# HANDOFF: Root-Cause Fix — Prevent Local `main` Divergence From Recurring

**Why this exists:** Everything in the Tier 2 / ADR-0008 reconciliation effort (PRs #69–#84) was cleanup of a *symptom*. The actual root cause — why local `main` had 33 commits with different SHAs than `origin/main` in the first place — was never diagnosed or fixed. This handoff closes that gap.

---

## 1. Background (for context, don't re-litigate)

At the start of this effort, local `main` had 33 direct commits that were logically identical to work already on `origin/main`, but merged there via PR (different SHAs). Local `main` also had 18 fewer commits than origin overall. The fix at the time was `git reset --hard origin/main` (with a backup branch first) — a correct, safe way to resolve the *immediate* divergence. But it did not answer: how did local `main` get 33 direct commits that never went through the PR flow origin's copies went through?

If that workflow gap is still open, local `main` can silently diverge again, and we'd be back to another multi-day reconciliation effort like this one.

---

## 2. Investigation — do this first, before any fix

1. **Determine whether direct commits to local `main` are currently possible.** Check:
   ```
   git branch --show-current
   git log main --oneline -20
   ```
   Look at whether recent commits on `main` were made directly (`git commit` while on `main`) vs. arrived only via `git merge`/`gh pr merge` from a feature branch. Every PR in this session's history (#69–#84) went through branch → PR → merge — confirm that's actually enforced, not just a habit that happened to hold during this session.

2. **Check for branch protection on the GitHub side** (`github-direct` remote, `1semptify-arch/Semptify`):
   ```
   gh api repos/1semptify-arch/Semptify/branches/main/protection
   ```
   If this 404s or returns no protection rules, that confirms there's currently nothing stopping a direct push to `main` on GitHub itself.

3. **Check for local safeguards** — is there anything in `.git/hooks/`, `tools/hooks/`, or `.pre-commit-config.yaml` that would block a commit made while checked out directly on `main`? (Likely no, based on what's been built so far — the pre-commit work in PR #82 was about tracker convergence, not branch discipline.)

4. **Ask: how did the original 33 commits get there?** This may not be fully answerable forensically (reflog may not go back far enough), but check:
   ```
   git reflog show main | tail -50
   ```
   If there's a clear pattern (e.g., an agent or session committing directly to `main` instead of a feature branch), name it. If it's unrecoverable/inconclusive, say so — don't guess.

**Report findings from steps 1–4 before proposing or implementing any fix.**

---

## 3. Likely fix direction (pending investigation results — don't implement blind)

If direct commits to local `main` are currently possible, the fix is almost certainly some combination of:

- **GitHub branch protection on `main`** — require PRs, require status checks to pass (Lint + fast marker-subset Test, per the PR #83 split), disallow direct pushes. This is the authoritative fix since it's enforced server-side regardless of which agent/session is working.
- **Local git hook** (`tools/hooks/pre-commit` or a new `pre-push` hook) that refuses a commit/push if the current branch is `main` — belt-and-suspenders for local safety, especially useful for agents working directly in the canonical clone.
- **Update `AI_TEAM_OPERATING_PROTOCOL.md`** to state explicitly: no agent (SWE-1.7-Max, Devin, or any other) commits directly to local or remote `main` under any circumstance — everything is branch → PR → merge, no exceptions, matching the pattern already proven out across PRs #69–#84.

Do not implement all three blind — report step 2's findings (does GitHub branch protection already exist in some partial form?) before deciding scope.

---

## 4. Verification, once fixed

- Attempt a direct commit to local `main` in a throwaway test and confirm it's blocked (locally and/or rejected on push).
- Confirm `gh api repos/1semptify-arch/Semptify/branches/main/protection` now returns actual protection rules, not a 404.
- Update `AI_TEAM_OPERATING_PROTOCOL.md` if the protocol doc doesn't already state the no-direct-commit rule explicitly.

---

## 5. Standing rules — unchanged

- No `git reset --hard` without explicit human confirmation.
- `sync_orchestrator.py --check` after any tracker-affecting change.
- Commit messages: `admin:` / `user:` / `help:` / `adr:` prefix.
- This is investigation-first, fix-second. Report step 2 findings before implementing branch protection changes — those are a Tier A / repo-configuration decision, not something to apply unilaterally.
