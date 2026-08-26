# Handoff — Phase B: `adr-0008-pilot` / `main` reconciliation

**Status:** Phase A complete. PR #34 merged. Phase B ready to start in a fresh session. Stop-and-report per group.

**Repository:** `C:\master-repo\sources\app-semptify-fastapi` (origin `https://github.com/1semptify-arch/Semptify.git`)

---

## 1. Context

Phase A merged ADR docs 0001–0007, `docs/doc-map.yaml`, `docs/MOTIVATIONS.md`, etc., from `adr-0008-pilot` into `main` via PR #34. `origin/main` is now at `d0ef69bd` (merge of PR #34).

`adr-0008-pilot` remains at `4136a96e`. The backup `origin/backup/adr-0008-pilot-full-history` still matches it exactly.

---

## 2. Current inventory (re-counted after Phase A merge)

The original Phase A handoff estimated 551 identical, 446 conflicting, ~1,590 pilot-only, and 42 main-only files. A direct `git diff --name-status origin/main origin/adr-0008-pilot` after the Phase A merge gives different absolute counts because of renames and the way the initial estimate was produced. The current canonical numbers are:

| Bucket | Count | Meaning |
|--------|-------|---------|
| `A` — only on `adr-0008-pilot` | 101 | New files not on `main` (Phase B candidates, minus ADR-0008 pilot new files) |
| `M` — different on both | 965 | True conflict / modified zone (Phase C) |
| `D` — only on `main` | 172 | Files absent from pilot; do **not** delete when reconciling |
| `R` — renamed/moved on pilot | 28 | Source path on `main`, target path on pilot (decision-needed pass) |

Full per-status lists are in `C:\master-repo\phase_b_inventory.md` (generated alongside this handoff). Reproduce with:

```powershell
cd C:\master-repo\sources\app-semptify-fastapi
git fetch origin
git diff --name-status origin/main origin/adr-0008-pilot > E:\tmp\phase_b_diff.txt
```

---

## 3. Phase B scope — low-risk, additive

Phase B moves **only the purely additive `A` files** from `adr-0008-pilot` to `main`, in small groups, one group per PR/branch, one commit per file or tiny logical group.

**Excluded from Phase B (handle later):**

- The ADR-0008 pilot new files — defer to **Phase D**. These are:
  - `app/core/context_envelope.py`
  - `app/core/experience_token.py`
  - `app/core/page_envelope.py`
  - `app/modules/eviction_timeline/envelopes.py`
  - `app/modules/vault/envelopes.py`
  - `tests/test_information_orchestrator_pilot.py`
  - `docs/adr/0008-information-orchestrator.md`

- The 28 `R` rename/moves — handle in a dedicated rename pass (do not blindly delete the main-side source paths).
- All `M` files — Phase C.

**That leaves 94 additive files for Phase B**, grouped as follows:

### 3.1 GUI templates (63)

`app/templates/pages/*.html` (full list in `phase_b_inventory.md` under `A → app/templates`)

These are the 75-page Jinja2 conversion batch from `adr-0008-pilot`. They are new templates and should merge cleanly. Verify each extends `base.html` / `gui/base.html` and has the `ssot-design-system.css` classes; no runtime logic changes.

### 3.2 Page router / context engine (4)

- `app/modules/page_router/__init__.py`
- `app/modules/page_router/router.py`
- `app/modules/context_engine/explanation_entries.py`
- `app/modules/context_engine/retrieval.py`

### 3.3 New tests (21)

- `tests/module_health/test_all_modules.py`
- `tests/services/__init__.py`
- `tests/services/eviction/__init__.py`
- `tests/services/eviction/pytest.ini`
- `tests/services/eviction/test_case_builder.py`
- `tests/services/eviction/test_court_learning.py`
- `tests/services/eviction/test_court_procedures.py`
- `tests/test_advanced_security.py`
- `tests/test_ai_tool_crib.py`
- `tests/test_async_token_calls.py`
- `tests/test_contracts_framework.py`
- `tests/test_document_types.py`
- `tests/test_eviction_case_builder.py`
- `tests/test_gemini_ai.py`
- `tests/test_groq_ai.py`
- `tests/test_unified_timeline.py`

### 3.4 Tooling / workflows / scripts (10)

- `.devin/workflows/gui.md`
- `.devin/workflows/open-workbook.md`
- `scripts/precommit_hook_wrapper.py`
- `tools/docs_changelog.py`
- `tools/docs_staleness_check.py`
- `tools/hooks/check_commit_msg.py`
- `tools/hooks/commit-msg`
- `tools/new_audit_tasks.json`
- `tools/recurring_scheduler.py`

### 3.5 Static assets (2)

- `static/assets/semptify-favicon.svg`
- `static/css/semptify.css`

---

## 4. Recommended approach

Do **not** do one giant merge. Open one focused PR per group above (or smaller if a group is still large):

1. **Branch from latest `origin/main`:**
   ```powershell
   git checkout -b phase-b/gui-templates origin/main
   ```
2. **Check out the relevant files from `adr-0008-pilot` into the new branch.** For the GUI templates group:
   ```powershell
   git checkout origin/adr-0008-pilot -- app/templates/pages/brain.html ...
   ```
   (or use `git restore --source=origin/adr-0008-pilot -- ...` if you prefer `restore` syntax)
3. **Commit one file or a tiny logical group per commit.** Example:
   ```
   gui: add brain.html page template
   ```
4. **Push and open a small, focused PR** just for that group.
5. **Run CI and verify checks pass before merge.**
6. **Stop and report after each PR is merged** before starting the next group.

---

## 5. Hard constraints (carry forward from Phase A)

- **No force-push** on any reconciliation branch.
- **No bulk "take theirs"/"take mine"** across many files.
- **Do not delete any of the 172 main-only files** (full list in `phase_b_inventory.md` under `D`), especially the 42 notable ones referenced in section 7, even if a merge strategy would naturally delete them.
- **Do not touch `origin/backup/adr-0008-pilot-full-history`**. It remains the recovery point.
- **Do not start Phase C or D** until Phase B additive files are all landed and the branch is verified.
- **Standing rules apply:** one task per commit, no self-approval, full-file preflight reads before edits, stop-and-report rather than scope-expand.

---

## 6. Main-only files to protect

All `D` files from `git diff --name-status origin/main origin/adr-0008-pilot` are main-only and must not be deleted. The full list is in `phase_b_inventory.md` under `D`.

The 42 notable main-side files from the original handoff include the service files and docs below. Note that many of the docs are the *source* of `R` renames to `docs/admin/*.md` on the pilot — do **not** let a rename merge delete the `docs/*.md` paths from main before a final decision is made on the directory restructure.

### 6.1 Notable main-only services (7)

- `app/services/vault_engine.py`
- `app/services/court_form_generator.py`
- `app/services/document_notarization.py`
- `app/services/event_extractor.py`
- `app/services/hud_funding_guide.py`
- `app/services/proactive_tactics.py`
- `app/services/progress_tracker.py`

### 6.2 Notable main-only docs (many are `R` sources)

- `docs/ADMIN_MANUAL.md`
- `docs/AGENT_ORCHESTRATOR_MANUAL.md`
- `docs/CONTRACTS.md`
- `docs/CREDENTIALS_SETUP_WORKBOOK.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/MODULE_DEVELOPMENT.md`
- `docs/OAUTH_SETUP.md`
- `docs/OVERLAY_SYSTEM_DESIGN.md`
- `docs/PYTEST_HANG_ROOT_CAUSE_2026-07-27.md`
- `docs/SECURITY_AUDIT_EVAL_EXEC_2026-07-27.md`

See `phase_b_inventory.md` for the complete list, including other main-only files like `.devin/skills/*`, `.markdownlint-cli2.jsonc`, and temporary audit artifacts.

---

## 7. Conflict zone preview (Phase C)

`M` count: 965. The full list is in `phase_b_inventory.md`.

Foundation files to handle first in Phase C, per the original handoff:

- `app/core/navigation.py`
- `app/core/oauth_token_manager.py`
- `app/core/module_sdk.py`
- `app/core/page_manifest.py`
- `app/core/gdpr_compliance.py`
- `app/core/gui_contract.py`

and approximately 959 more. Phase C will be split by logical groups: `app/core/` foundational files first, then module routers, then tests last.

---

## 8. Phase D preview (the ADR-0008 pilot itself)

Once `main` and a reconciled branch agree on the `M` conflict zone, the ADR-0008 pilot commits should apply cleanly on top. Exact pilot commits from the original handoff:

| Deliverable | Commit | Files |
|---|---|---|
| Object Context Envelope | `d1e353ff` | `app/core/context_envelope.py` |
| Page Envelope | `db5fea0d` | `app/core/page_envelope.py` |
| Experience Token | `f6d85f84`, `e0496c08`, `f6bb48c6` | `app/core/experience_token.py` |
| Eviction Timeline instrumentation | `a54d4ced` | `app/modules/eviction_timeline/envelopes.py`, `router.py` |
| Vault upload instrumentation | `aebf178e` | `app/modules/vault/envelopes.py`, `router.py` |
| Live Event-Driven Narration | `26c51f61` | `app/services/vault_upload_service.py`, `app/services/document_flow_orchestrator.py`, `app/core/event_bus.py` |
| End-to-end pilot test | `ab1e5fdf` | `tests/test_information_orchestrator_pilot.py` |

---

## 9. First session prompt for Phase B

```
Starting Phase B of the adr-0008-pilot / main reconciliation
(see HANDOFF_branch_reconciliation_phase_b.md and phase_b_inventory.md).

Begin with the GUI templates group only:
1. Create a new branch from current origin/main:
   git checkout -b phase-b/gui-templates origin/main
2. Add the 63 new app/templates/pages/*.html files from origin/adr-0008-pilot.
3. Commit one file (or a tiny logical group) per commit.
4. Push the branch and open a small, focused PR.
5. Wait for CI to pass, then merge.
6. Stop and report. Do not proceed to the next Phase B group without review.
```

---

## 10. Artifacts generated with this handoff

- `C:\master-repo\HANDOFF_branch_reconciliation_phase_b.md` (this file)
- `C:\master-repo\phase_b_inventory.md` (full A/M/D/R file lists)
- `C:\master-repo\generate_phase_b_inventory.py` (script that generated the inventory)

---

*This handoff is self-contained. A fresh agent picking it up cold should be able to start Phase B with just this file, `phase_b_inventory.md`, and access to the repo.*
