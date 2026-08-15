# Handoff — Phase D: Land the ADR-0008 Pilot on Reconciled `main`

**Part of:** `adr-0008-pilot` / `main` reconciliation. Read `HANDOFF_branch_reconciliation.md` first.
**Precondition:** Phase C is fully complete — every file in the conflict zone resolved and merged to `main`. Do not start this early; the pilot commits were built assuming a codebase state that only exists once Phase C is done.

---

## 1. What this phase does

Applies the actual ADR-0008 Information Orchestrator pilot on top of a `main` that now has everything: the audit, the GUI work, the ADR docs, and all 446 reconciled core files. This should be the cleanest phase — the pilot's files are new (no `main`-side equivalent existed at investigation time), so conflicts here would be a signal something in Phase C wasn't actually finished, not an expected outcome.

## 2. The pilot commits (reference — same as in the master handoff)

| Deliverable | Commit | Files |
|---|---|---|
| Object Context Envelope | `d1e353ff` | `app/core/context_envelope.py` |
| Page Envelope | `db5fea0d` | `app/core/page_envelope.py` |
| Experience Token | `f6d85f84`, `e0496c08`, `f6bb48c6` | `app/core/experience_token.py` |
| Eviction Timeline instrumentation | `a54d4ced` | `app/modules/eviction_timeline/envelopes.py`, `router.py` |
| Vault upload instrumentation | `aebf178e` | `app/modules/vault/envelopes.py`, `router.py` |
| Live Event-Driven Narration | `26c51f61` | `app/services/vault_upload_service.py`, `app/services/document_flow_orchestrator.py`, `app/core/event_bus.py` |
| End-to-end pilot test | `ab1e5fdf` | `tests/test_information_orchestrator_pilot.py` |

Full spec: `ADR-0008-information-orchestrator.md`.

## 3. Step 1 — Fresh branch, cherry-pick pilot commits only

```
git fetch origin main
git checkout -b reconciliation/phase-d origin/main
git cherry-pick d1e353ff db5fea0d f6d85f84 e0496c08 f6bb48c6 a54d4ced aebf178e 26c51f61 ab1e5fdf
```

Cherry-pick in this order — later commits (envelope instrumentation, narration) depend on the earlier foundational ones (Context Envelope, Page Envelope, Experience Token) existing first.

## 4. Step 2 — If conflicts appear here, stop and investigate before resolving

Unlike Phase C, conflicts in this phase are **unexpected**, not assumed. If `git cherry-pick` reports a conflict on any of these commits:

1. Do not resolve it the way Phase C conflicts were resolved (read-both-and-merge).
2. First check: did the file this pilot commit touches (e.g. `app/core/oauth_token_manager.py`, if the narration work touched it) get changed differently during Phase C's reconciliation than what the pilot commit expects? That would mean Phase C's resolution and the pilot's assumptions disagree — worth understanding *why* before picking a side.
3. Report the specific conflict and its cause before resolving, rather than resolving first and reporting after.

## 5. Step 3 — Full verification, not spot-checks

Once cherry-picks are applied cleanly:

```
python -m compileall app/
pytest tests/test_information_orchestrator_pilot.py -q --no-cov
```

Also re-run the Playwright smoke suite and the full test suite if time allows — the pilot was originally verified against a much older `main`, so a full re-verification against the reconciled codebase is the actual point of this step, not a formality.

## 6. Step 4 — Ship

- Push `reconciliation/phase-d`, open a PR into `main`.
- PR description should reference this handoff and confirm: which reconciliation phases preceded it, and that verification (Step 3) passed.
- This is the PR that finally represents "the pilot is actually on main" — treat the review with the weight that deserves, even though the commits themselves are small.

## 7. After this merges

The reconciliation project is complete. `agent_orchestrator_tasks.json` should reflect: `todo-063`–`075` (the pilot batch) as resolved-and-shipped, not just resolved-on-branch. Update `BUILD_STATE.md` / `ACTIVE_CONTEXT.md` to reflect that `main` now contains the full history that was previously split across `adr-0008-pilot`. The `backup/adr-0008-pilot-full-history` branch can stay as a permanent archival reference — no need to delete it, but nothing further should depend on it.
