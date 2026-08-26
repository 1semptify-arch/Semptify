# Semptify Agent Guide

This repository contains a housing-rights and tenant-support product. Any AI agent working here should follow these standards.

> Canonical project governance and doc hierarchy are defined in `PROJECT_BIBLE.md`.

**This file is read by every AI assistant in this repo** — Cascade/Devin, GitHub Copilot
(via `.github/copilot-instructions.md`), Cursor (via `.cursor/rules/00-semptify-agents.mdc`),
and Claude — not only one tool. Repeatable slash-command procedures (pre-flight, ship,
forge, review, etc.) are defined once in `.devin/skills/*/SKILL.md` and mirrored as VS Code
prompt files in `.github/prompts/*.prompt.md` so they run as `/preflight`, `/ship`, `/forge`,
`/review`, `/cloudflare-dev-mode`, `/help-page-review`, `/ssot-analysis` in Copilot Chat too.
If you edit a skill, update both copies.

---

## 🐍 PYTHON VERSION MANDATE — NON-NEGOTIABLE

### Semptify requires Python 3.11.9. This is a hard mandate, not a suggestion

- **ALL code, modules, add-ons, plugins, and extensions MUST target Python 3.11.9.**
- **Do NOT introduce any dependency that requires Python 3.12, 3.13, 3.14, or any other version.**
- **Do NOT suggest upgrading Python. Until further notice, 3.11.9 is the locked version.**
- **Local dev:** Use `venv311` (`.\\venv311\\Scripts\\Activate.ps1` on Windows)
- **Production:** `Dockerfile` uses `python:3.11-slim`, `runtime.txt` pins `3.11.9`
- **Before adding ANY new package:** Confirm it supports Python 3.11.9

If a proposed library only works on 3.12+, **reject it and find an alternative.**

---

## ⚠️ MANDATORY PRE-FLIGHT — Every AI Agent MUST Do This First

### Before writing a single line of code, you MUST:

1. **Read `BUILD_STATE.md`** — What was last shipped, what is known broken, what is pending.
2. **Read `ACTIVE_CONTEXT.md`** — What is being worked on RIGHT NOW. Do not start something else.
3. **Read `PROJECT_BIBLE.md`** — Canonical hierarchy, gate chain, and governance.
4. **Read `docs/admin/MOTIVATIONS.md`** — Foundational motivations, language rules, and design principles. Permanent decisions are also in `docs/adr/0001`–`0006`.
5. **Read `docs/AI_TEAM_OPERATING_PROTOCOL.md`** — Three-way collaboration protocol, decision authority matrix, and batching rules.
6. **Read the Known Failure Registry below** — Do not repeat a past mistake.
7. **State your plan before acting** — Tell the user what you intend to change and why before touching any file.
8. **Do not ship without a verification step** — Every change needs a compile check or test run.
9. **Verify Python 3.11.9** — Confirm the active interpreter is `venv311` before running anything.
10. **Fix the root cause, not the symptom** — Trace every bug to its source. NEVER add downstream compensating checks to mask upstream failures. Band-aids compound. Fix the source.

#### Task claiming rule — must be followed before any file edit

- Before writing a single line of code, set your task to `in_progress` and record your agent id as `assigned_agent` using the task tracker:
  ```
  python tools/mark_task_status.py <task_id> in_progress --agent <agent-id>
  ```
- Before claiming `in_progress`, check the tracker for any existing `in_progress` entry on the same `file_path`. If one exists, resolve or reassign the existing task first.
- Do NOT start coding while the task is still `pending` or unassigned.

### If you skip pre-flight, you will repeat a past mistake. The history proves this

---

## 🚫 Known Failure Registry — NEVER Repeat These

These failures have each cost multiple sessions to fix. Read them. Do not cause them again.

### 1. Vault Folder Creation Silent Failures

- **What happened:** `create_vault_folders()` ignored boolean return values from `create_folder()`. Failures were silent.
- **Fix:** Every `create_folder()` call must check its return value. Raise `RuntimeError` with the specific path on failure.
- **File:** `app/modules/onboarding/vault.py`

### 2. Dropbox 409 Error Masking

- **What happened:** All HTTP 409 responses from Dropbox were treated as success. `path_not_found` errors were swallowed.
- **Fix:** Inspect the 409 response body. Only `folder_name_exists` is success. All other 409s must raise.
- **File:** `app/services/storage/dropbox.py`

### 3. Missing Parent Vault Folder (.Semptify5.0)

- **What happened:** Dropbox requires explicit parent folder creation before nested folders. The root `.Semptify5.0` folder was missing from `CANONICAL_VAULT_FOLDERS`.
- **Fix:** `.Semptify5.0` must be the first entry in `CANONICAL_VAULT_FOLDERS`.
- **File:** `app/modules/onboarding/config.py`

### 4. Vault Verification Treating Empty Folders as Missing

- **What happened:** `verify_vault_folders()` treated `[]` (empty list) as folder not found. New vaults always failed verification.
- **Fix:** Only fail if `list_files()` raises an exception. An empty list is a valid, accessible folder.
- **File:** `app/modules/onboarding/vault.py`

### 5. Cloudflare 504 Timeout on Vault Setup

- **What happened:** Step 1 of vault setup did too much work (folders + files), exceeding Cloudflare's 30s gateway limit.
- **Fix:** Step 1 creates folders only. Step 2 creates files. Never put more than ~20s of work in a single API call behind Cloudflare.
- **File:** `app/modules/onboarding/router.py`

### 6. Import Injection Breaking Syntax

- **What happened:** An automated logging migration injected `import logging` lines inside import blocks, not at the top of files. Caused 37 syntax errors.
- **Fix:** Imports always go at the top of the file. Never inject imports mid-file.

### 7. Bare `except:` Blocks

- **What happened:** Bare `except:` swallowed real errors silently. Replaced 45 of them.
- **Fix:** Always use specific exception types: `except ValueError`, `except RuntimeError`, etc. Never `except:` alone.

### 8. Naive `datetime.now()` Without UTC

- **What happened:** 446 occurrences of `datetime.now()` without timezone caused token expiry bugs.
- **Fix:** Always use `utc_now()` from `app.core.utc`. Never call `datetime.now()` directly.

### 9. SSOT Navigation Violations

- **What happened:** Hardcoded URL strings in redirects caused redirect loops and broken flows.
- **Fix:** Always use `navigation.get_stage(...)` for redirects. See SSOT section below.

### 10. `VaultResult` Missing from SDK Exports

- **What happened:** `VaultResult` was not exported from `app/sdk/vault/__init__.py`, causing import errors across modules.
- **Fix:** Any new model or class used outside its own module must be added to the relevant `__init__.py`.

### 11. Duplicate Exception Handler Registration

- **What happened:** `setup_exception_handlers()` was called twice in `main.py`, overwriting detailed handlers with generic ones. Real errors showed as "An unexpected error occurred".
- **Fix:** Register exception handlers exactly once. Search for duplicates before adding new ones.

### 12. Cloudflare Tunnel Not Running as Service

- **What happened:** `cloudflared` was run manually. Every machine restart killed the tunnel, breaking `semptify.org`.
- **Fix:** Run `sc config cloudflared start= auto` and `sc start cloudflared` as Administrator once. The service then survives reboots.

### 13. File Rewrite Creating New Filename (Cascading Reference Break)

- **What happened:** When a file needed rewriting, the AI kept the broken original and created a new file with a different name (e.g. `vault_upload_service_v2.py`). Every import across the codebase still pointed at the old broken file. The AI then had to update all references, missed some, ran out of context, and left the system broken.
- **Fix:** Use the swap protocol:
  1. **Ask the user** to rename the original to `<filename>_old.py` (one filesystem rename — takes 2 seconds)
  2. AI rewrites the clean version into the **original filename** (`<filename>.py`)
  3. Every import everywhere still works — nothing else changes
  4. The `_old` file is the rollback. Delete it once the rewrite is verified.
- **Rule:** NEVER create `_v2`, `_new`, `_fixed`, `_impl` as the "replacement" file. NEVER update references in other files because of a rewrite. If you need to rewrite a file, **ask the user to rename the original first**, then write into the original name.
- **If in doubt:** Ask. One question prevents hours of cascading breakage.

### 14. Wrong Python Version

- **What happened:** Code ran on Python 3.13/3.14 (Windows default `python` command) instead of 3.11.9. Silent incompatibilities and startup failures.
- **Fix:** Always activate `venv311` before running. `main.py` will hard-exit if the wrong Python is detected.
- **Mandate:** Python 3.11.9 is the ONLY permitted version for this repo. Any new module, add-on, or dependency MUST support 3.11.9. Do NOT upgrade Python without explicit written approval from the project owner.
- **Local command:** `.\\venv311\\Scripts\\Activate.ps1` then `python -m uvicorn app.main:app ...`

### 15. Workaround Instead of Root Cause Fix

- **What happened:** A bug in `google_drive.py`'s `_get_folder_id()` caused `create_folder()` to return `False` when a folder already existed. Instead of fixing the source, an additional `file_exists()` check was added in `VaultClient` as a band-aid. This masked the root cause, added an unnecessary API call per folder, and left the downstream code fragile.
- **Fix:** Always trace the error to the source and fix it there. If a storage provider returns an incorrect value, fix the provider. If a function returns wrong results, fix that function. Do NOT add compensating checks downstream.
- **Rule: NEVER add workarounds downstream when the root cause is upstream. Fix the root. Band-aids compound over time.**
- **File:** `app/services/storage/google_drive.py` — fixed `_get_folder_id()` to search before create with retry logic.

### 16. Hallucinated Overlay API Signatures

- **What happened:** Three services (`filedored_service.py`, `duplicate_detection_service.py`, `court_forms/router.py`) invented their own `CreateOverlayRequest` fields (`vault_id`, `user_id`, `overlay_path`, `overlay_data`) that do not exist on the Pydantic model. They also called non-existent methods `get_overlays_by_type()` and `get_overlays_by_path()` on `UnifiedOverlayManager`. And they imported from `app.core.storage_factory` — a module that never existed. All of this crashed at runtime.
- **Fix:** Aligned all callers to the real signature (`overlay_type`, `document_id`, `vault_path`, `payload`, `metadata`, `ephemeral`) and real methods (`get_overlays()`, `create_overlay()`, `update_overlay()`, `delete_overlay()`). Replaced `storage_factory` with the real pattern: `oauth_token_manager.get_valid_token_for_user()` + `services.storage.get_provider()` + `user_id.get_provider_from_user_id()`.
- **Rule: BEFORE writing any code that touches the overlay system, READ THE CONTRACTS in `app/services/unified_overlay_manager.py` (bottom of file).** The `FunctionGroupContract` registrations are the SSOT for method names, field names, and signatures. If a field or method is not in the contract, it does not exist. Do not invent it.
- **Contracts registered:** `overlays::overlay_create`, `overlays::overlay_query`, `overlays::overlay_update`, `overlays::overlay_delete`, `overlays::overlay_compose_view`.
- **Files:** `app/services/filedored_service.py`, `app/services/duplicate_detection_service.py`, `app/modules/filedored/router.py`, `app/modules/court_forms/router.py`.

### 17. Half-Finished Static Asset Migration Left Uncommitted

- **What happened:** An earlier session deleted `static/css/` live files and created copies in `static/data/css/` as part of a CSS migration, but never updated template `<link>` tags, never added a static mount for the new path, and never committed any of it. The app's CSS was silently broken on disk (7 files missing) while git still showed them as present. A later session found the orphan copy directory, assumed it was an intentional migration target, and nearly deleted the originals permanently before catching the problem.
- **Fix:** Restored all files from the orphan copy back to `static/css/` (the correctly mounted location). Deleted the orphan `static/data/css/` directory.
- **Rule: NEVER delete a static asset file (CSS, JS, image) that is referenced by a template until the replacement is verified live in the running app. If a migration is started and cannot be completed in the same session, revert the deletions before committing. A half-finished migration committed or left on disk overnight is worse than no migration at all.**

### 18. Corrupt Git Commit-Graph Causing `git status` Misreport

- **What happened:** `.git/objects/info/commit-graphs/` became corrupt, referencing 8 commits that no longer existed in the object database (`failed to parse commit ... from object database for commit-graph`). This caused `git status` to report committed files as modified/added and to show a dirty tree that was actually clean. The corruption likely came from automatic `git gc`/prune or worktree/cascade snapshot maintenance, not from the Devin safety rules.
- **Fix:** Remove/rename the old split graph, regenerate with `git commit-graph write --reachable`, then verify with `git commit-graph verify` and `git fsck --full`.
- **Rule:** If `git status` reports large numbers of staged/unstaged changes that don't match what you expect — especially after worktree operations, cascade snapshots, or `git gc`/`git prune` — run `git fsck --full` and `git commit-graph verify` before assuming the working tree is dirty. Do NOT run `git reset --hard` or `git clean -fd` blindly to "fix" the apparent dirtiness.

### 19. OAuth Token Refresh Blocking the Async Event Loop

- **What happened:** `app.core.auto_refresh.ensure_valid_token()` was calling `token_manager.refresh_token_if_needed()`, which is a synchronous method that uses `httpx.Client` (blocking) to call Google/Dropbox/OneDrive token refresh endpoints. Under `uvicorn`/async workers this blocks the event loop, causes timeouts / 504s, and produces the same reconnect-loop symptom the user sees when signing in with OAuth.
- **Fix:** Rewrite `app/core/auto_refresh.py::_refresh_from_db()` to use the existing async `app.modules.storage.router.refresh_access_token()` (which uses `httpx.AsyncClient`) instead of the synchronous `token_manager` refresh path. Normalize naive `expires_at` datetimes to UTC before calling `token.is_expired()` to prevent aware/naive datetime comparison crashes.
- **Rule:** Never call a synchronous HTTP client (`httpx.Client`, `requests`, etc.) from inside an `async def` code path in this repo. Token refresh, provider validation, and storage I/O must all be async. If you see `token_manager.refresh_token_if_needed()` or `get_valid_token_for_user()` being called from an async route/service, replace it with `auto_refresh.ensure_valid_token()` or make the caller `await` an async equivalent.
- **Files:** `app/core/auto_refresh.py`, `app/core/oauth_token_manager.py`, `app/core/security.py` (`get_current_user`), `app/core/storage_middleware.py`.

---

## � Gap Report — run this before hunting for bugs by hand

`python tools/gap_report.py` wires together the gap-detection tooling that already exists in
this repo (`tools/stub_detector.py` AST-verified stub scan, `tools/guardrail_engine.py`,
`tools/module_registry.yaml` flags, and `FunctionGroupContract` coverage from
`app/core/contract_loader.py`) into one prioritized `GAPS.md` snapshot, plus a short list of
architectural gaps no automated check can find (documented directly in the script). Regenerate
it at the start of a gap-hunting session instead of re-discovering the same issues by hand.
`GAPS.md` is gitignored — it's a snapshot, not authored documentation; the script is the
source of truth.

---

## �📋 Module Contract Mandate

### Every service that exposes a reusable API MUST register a `FunctionGroupContract` in `app/core/module_contracts.py`

This is non-negotiable. The contract is the SSOT for:

- Method names (no hallucinated methods)
- Input/output field names (no wrong signatures)
- Dependencies (no phantom imports like `app.core.storage_factory`)

### Pattern:

```python
from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
    module="<module_name>",
    group_name="<function_name>",
    title="<Human Title> (SSOT)",
    description="CANONICAL ... What it does. What it does NOT do.",
    inputs=("<required>", "<optional>?"),
    outputs=("<output>",),
    dependencies=("app.services.<module>",),
    deterministic=True,
))
```text

**Before writing code that calls another service's API, check the contract registry first.** If no contract exists, ask the user — do not invent the API.

---

## 🎨 GUI Design — Chronological & Spatial Task Ordering

Applies to all tenant-facing and admin GUI work, in addition to the existing design-system rules (no card borders, zone-based background separation, `ssot-design-system.css` only).

- Layout must follow the strict chronological order of the user's task: first required action top/left, each subsequent step below or to the right, final/completion step at the bottom or end of the path.
- Never place an early step below a later one. Never place a final action near the top.
- High-priority, immediate-use controls: top of viewport.
- Secondary/configuration controls: middle, grouped logically.
- Low-frequency or destructive actions (Reset, Delete, etc.): bottom, visually separated.
- Group related controls with zone-based background separation, not card borders.
- Before marking any GUI task done, trace the eye path top-left → down/right. If an earlier step's control sits below a later step's control, rearrange.
- For full wording see `.cursor/rules/01-gui-chronological-spatial.mdc`.

## 📋 Agent Session Checklist

Before ending any session, you MUST:

- [ ] Verify all changed Python files compile: `python -m py_compile <file>`
- [ ] Run SSOT tests if any navigation changed: `python tests/test_ssot_architecture.py`
- [ ] Update `BUILD_STATE.md` with: what was shipped, what is known working, what is pending
- [ ] Update `ACTIVE_CONTEXT.md` if the current priority changed
- [ ] Do NOT mark something "working" unless it was actually tested — write "pending live test" if untested

### Orchestrator Task Status Rule

Semptify's module-level queue is still `tools/agent_orchestrator_tasks.json`, managed by `tools/mark_task_status.py`. For Semptify tasks, continue using:

- Pick up: `python tools/mark_task_status.py <task_id> in_progress --agent <your-model-name>`
- Finish: `python tools/mark_task_status.py <task_id> resolved --notes "<one-line summary>" --agent <your-model-name>`
- Blocked: `python tools/mark_task_status.py <task_id> review --notes "<why>" --agent <your-model-name>`

The **master orchestrator queue** is `C:\master-repo\tools\orchestrator_state.json`. Use it for any task with a `model_tier` or a handoff. Read it to find the next task, and use:

- Pick up: `python C:\master-repo\tools\orchestrator_mark_task.py <task_id> in_progress --agent <your-model-name>`
- Executor finish (swe-executor): `python C:\master-repo\tools\orchestrator_mark_task.py <task_id> review --usage '{"wall_clock_min": X, "tool_calls": Y}' --agent swe-executor`
- Orchestrator finish (Claude): `python C:\master-repo\tools\orchestrator_mark_task.py <task_id> resolved --pr <url> --agent claude-code`
- Blocked: `python C:\master-repo\tools\orchestrator_mark_task.py <task_id> blocked_on_decision --blocked-reason "<why>" --agent <your-model-name>`

Unlimited agents (swe-executor, SWE-1.7, etc.) may NOT mark a task `resolved` or `rejected`; they stop at `review` or `blocked_on_decision`. Do this every time, without being asked — it is how the queue stays accurate without a human tracking it by hand.

---

## Core Mission

Semptify is built to better protect the rights of humans facing housing problems.
It is for people who may not be able to afford a legal team, may be overwhelmed, and may need help organizing documents, evidence, timelines, and next steps.

## Non-Negotiables

- **Semptify is NOT a business model.** It is a public-service housing-rights tool.
- **NEVER use the word "free"** on any page, button, label, or description — *when describing Semptify itself*. Saying "free" insinuates we charge for other things. We don't. We never have. We never will. **Exception:** factual descriptions of external resources (e.g., "Free legal help for low-income tenants" describing Legal Aid) are permitted — these are facts about *their* services, not Semptify self-promotion.
- **NEVER expose AI/LLM output in the tenant/advocate/attorney-facing system.** AI may be used for development tooling and future backend/admin-only modules (system health, staleness checks), but it is never surfaced to tenants, attorneys, or advocates. Form-fill and signatures are browser-native only — never stored server-side or treated as Semptify-managed profile data.
- **NEVER use business-model terminology** — no "accounts", "log in", "sign up", "subscription", "upgrade", "premium", "paid plan", "trial", "pricing", or similar. These words imply a commercial product. Semptify is not one.
- No advertising — ever. No banner ads, no sponsored content, no affiliate links, no tracking pixels for ad networks.
- **Listing vs advertising — there is a difference.** A *listing* is a neutral directory entry of a resource (e.g., "HOME Line MN — 612-728-5767"). An *advertisement* is promotional content paid for or placed to generate revenue/clicks. Listings are permitted only when:
  - The resource is directly relevant to tenant housing rights
  - The user (project owner) has reviewed and approved the specific listing
  - The listing is neutral, factual, and non-promotional
  - **When in doubt, do NOT add the listing. Ask the user first.**
- Privacy-respecting by design.
- User-controlled documents and storage wherever possible.
- Evidence preservation over feature novelty.
- Calm, clear, trustworthy UX.

## Fees Terminology Policy

Semptify's public commitment is **no fees, ever, to tenants** — that is a
policy about what Semptify charges users, not a ban on the word "fee" in
housing-rights analysis.

- In **tenant-facing modules** (`fees_policy = "tenant_no_fees"`), do not use
  language that implies Semptify charges fees, subscriptions, or paid plans.
  The word "fee" may appear when it clearly refers to a landlord charge
  recorded by the tenant (e.g. a rent-ledger line item), but never in a way
  that suggests Semptify is the one charging.

- In **advanced/admin/research modules** (`fees_policy = "exempt_advanced"`),
  "fee" is a domain term describing landlord conduct found in tenant evidence
  (for example, `detect_repeated_fees()` in `housing_accountability`). These
  modules are exempt from the "no fees" wording rule because they are analyzing
  what a landlord charged, not what Semptify charges.

- The exemption is **conditional on the module remaining unreachable by the
  tenant role**. The manifest declares `fees_policy` on every module entry;
  `tools/guardrail_engine.py` fails the build if an `exempt_advanced` module
  becomes tenant-reachable.

- **Do not "fix," remove, or reword fee-detection language in exempt modules**
  on the assumption that it conflicts with the no-fees policy. If a module's
  tenant-reachability status is changing, flag it for `fees_policy` review
  rather than editing fee logic directly.

## Truth Standard

- **Semptify is on the side of tenants — always.**
- We stand for what is lawful and factual. The law is the law. Facts are facts.
- When the law protects a tenant, say so clearly. Do not soften it.
- When a landlord violates the law, name it plainly. Do not excuse it.
- Build for facts, records, chronology, and evidence — never emotion or assumption.
- The "responsibilities" framing exists to help tenants protect themselves legally,
  not to create false moral equivalence between tenants and landlords.
- A tenant who follows their lease removes every landlord excuse — that is empowerment, not capitulation.
- Do not support deceptive, retaliatory, or manipulative flows.
- Do not produce content that victim-blames, hedges legal facts into uselessness, or treats housing as a "both sides" issue when the law is clear.

## AI Behavior Standards

- Give plain-language guidance.
- Optimize for stressed users with limited time, money, and attention.
- Avoid dark patterns, growth-hack framing, ad logic, or engagement bait.
- Avoid introducing features that depend on surveillance, analytics, or user profiling.
- Keep legal boundaries clear: organization and education are acceptable; unsupported legal-advice claims are not.

## Architecture Preference

- Prefer objects, qualifiers, functions, sequences, processes, and output objects as the structural model.
- Treat pages as UI surfaces generated from process needs, not as the deepest source of truth.
- Keep policy and transition logic centralized rather than duplicated across routers or templates.
- Favor strict serial gating for high-stakes workflows where later steps must not run before earlier steps complete.

## Product Decision Filter

When choosing between options, prefer the one that best improves:

1. Rights protection
2. Evidence integrity
3. User control
4. Clarity under stress
5. Privacy
6. Honest representation of system capabilities

Reject or challenge changes that primarily optimize for:

1. Monetization
2. Advertising
3. Vanity UX over usability
4. Hidden state that weakens auditability
5. Complexity without workflow benefit

## Repo Guidance

- Keep implementation consistent with public promises made in welcome, about, and privacy materials.
- If a proposed change creates a mismatch between product claims and actual behavior, flag it.
- Prefer deterministic, testable, auditable code paths.
- Preserve user trust as a first-order engineering concern.

## Blueprint-First Mandate — NON-NEGOTIABLE

**No module, plugin, or add-on may be built without a written blueprint approved by the project owner first.**

Code written before a blueprint is approved will be removed.

### If asked to build a module without a blueprint, you MUST say

> "This module needs a blueprint before I can build it. I can write the blueprint for your review right now — shall I?"

Then write the blueprint. Present it. Wait for explicit approval ("yes build it" counts). Only then open any source files.

### Blueprint must cover (minimum)

- Module name + dotted `module_path`
- Type: Pipeline Module or Feature Module?
- Problem it solves (which tenant right or workflow gap)
- Scope — what it does AND what it explicitly does NOT do
- Which roles get it by default
- Every new DB table (or "none")
- Every API endpoint: method + path + one-line purpose
- Which existing modules/services it calls
- Capability tier: CORE / EXTENDED / ADVOCATE / ADMIN / RESEARCH / DEV
- Risk: what could break

### Where blueprints live

```text
docs/blueprints/your_module_name_blueprint.md
```

### Full spec: `MODULE_BLUEPRINT.md` — Part 0A

---

## Capability System — MANDATORY for Every New Module

### As of 2026-06-16, Semptify has a live Capability System. Every new Feature Module MUST comply

### The Two Module Types (never confuse them)

| Type | What it is | Always on? | In user_capabilities? | Gated? |
| --- | --- | --- | --- | --- |
| **Pipeline Module** | Internal processor, no UI, passes output to other modules | YES | NO | NO |
| **Feature Module** | User-facing capability with UI + routes | NO | YES | YES |

#### Examples:

- `context_loop`, `positronic_brain`, `vault_upload_service` → Pipeline. Never gate these.
- `case_builder`, `eviction_defense`, `timeline`, `vault` UI → Feature. Gate these.

### When Building a NEW Feature Module

#### Step 1 — Add it to `CAPABILITY_DEFAULTS` in `app/core/product_manifest.py`

Decide which roles get it by default and add the `module_path` to the appropriate list:

```python
CAPABILITY_DEFAULTS = {
    "tenant":   [..., "app.modules.your_module.router"],
    "advocate": [..., "app.modules.your_module.router"],
    ...
}
```python

If it's admin-only, skip all role lists — admins get `__all__` automatically.

#### Step 2 — Add the gate to your router

One line at the top of your `router.py`:

```python
from app.core.capabilities import require_capability

router = APIRouter(
    prefix="/api/your-module",
    tags=["Your Module"],
    dependencies=[Depends(require_capability("app.modules.your_module.router"))],
)
```

That's it. The gate handles admin bypass, overlay grants, unseeded users, and 403 responses automatically.

#### Step 3 — Register in `product_manifest.py`

Add a `_register(...)` call in the correct tier block. The module_path MUST match exactly what you used in `CAPABILITY_DEFAULTS` and `require_capability()`.

### When Building a NEW Pipeline Module

- Do NOT add it to `CAPABILITY_DEFAULTS`
- Do NOT add `require_capability()` to it
- Pipeline modules are always registered and always running
- They call DOWN to services, never UP to feature modules

### The One Rule That Protects Everything

```text
Feature modules  →  call DOWN to  →  Pipeline modules
Pipeline modules →  NEVER call UP  →  Feature modules
Feature modules  →  NEVER call     →  Other feature modules directly
```text

### Admin Overlay (Dev Node / Hot-Swap)

Admins can temporarily grant any module to any user without touching the database:

```text
POST /api/capabilities/{user_id}/overlay
{ "module_names": ["app.modules.your_module.router"] }
```

Expires in 1 hour. Cannot be used to REMOVE real capabilities — add-only.

### Key Files

- `app/core/capabilities.py` — `require_capability()`, `seed_capability_defaults()`, `can_load_module()`, overlay functions
- `app/core/product_manifest.py` — `CAPABILITY_DEFAULTS` dict, `_register()` calls
- `app/modules/capabilities/router.py` — Admin REST API for granting/revoking/overlaying
- `app/models/models.py` — `UserCapability` SQLAlchemy model

---

## SSOT Architecture Enforcement (CRITICAL)

All navigation, routing, and URL construction MUST follow Single Source of Truth (SSOT) principles:

### NEVER DO (will be rejected)

- Hardcoded URL strings: `"/onboarding-assets/select-role.html"`, `"/storage/providers"`
- Direct `RedirectResponse(url="/some/path")` without navigation registry
- Inline JS navigation: `window.location.href = "/path/to/page"`
- HTML href attributes with hardcoded paths: `<a href="/onboarding/...">`
- Middleware or routers defining their own redirect targets

### ALWAYS DO

- Import: `from app.core.navigation import navigation`
- Use: `navigation.get_stage("role_select").path`
- Use: `navigation.get_onboarding_start()` for entry points
- Use: `navigation.get_next_path(current_stage)` for transitions
- Static files: Fetch `/onboarding/ssot-navigation` API, then navigate
- Python redirects: Use paths from navigation registry only

### Verification (MANDATORY)

Before committing any navigation change, run:

```bash
python tests/test_ssot_architecture.py
```

All tests must pass. Violations block deployment.

### Why This Matters

SSOT violations are the #1 cause of redirect loops, broken flows, and "many chiefs" architecture. Navigation is a **process**, not a property of individual pages. Centralize or perish.

### Files that must use SSOT

- All files in `app/routers/*.py` that return redirects
- All files in `app/core/*_middleware.py`
- All files in `static/onboarding/*.html`
- Any new navigation/routing logic

### SSOT Evolution (When to Break Rules)

**Rules exist to enable flow, not prevent it.** The SSOT registry is alive and grows with the product.

#### Legitimate exceptions:

- **Experimental features**: Use `navigation.add_escape_hatch(path, reason="Beta feature", ttl_days=7)`
- **New flows**: Use `navigation.register_stage(FlowStage(...))` to expand SSOT
- **Deprecating old paths**: Use `navigation.deprecate_path("/old", "/new")` for graceful evolution

#### Philosophy:

- A rule that cannot evolve is a prison
- A rule that is never enforced is a suggestion
- Good rules have escape hatches with TTLs (time-to-live)
- Break rules intentionally, document the exception, let it expire or integrate

#### When breaking SSOT:

1. Document WHY in code
2. Use escape_hatch with expiration
3. After the experiment, either:
   - Kill it (remove the code)
   - Formalize it (register as proper FlowStage)
   - Deprecate it (old path → new canonical)

---

## Data Sensitivity Tiers

- **T0 — System / operational.** No PII. Version, uptime, module counts,
  config flags, cost counters. Safe to log and display to admin.
- **T1 — Account / capability metadata.** No direct PII. Hashed user IDs,
  role, jurisdiction, module usage, invite codes. Admin-only, audit logged.
- **T2 — Tenant PII / sensitive personal data.** Names, addresses, contact
  info, documents, communications, concerns. Admin-only, audit logged,
  minimal retention.
- **T3 — Legal / court evidence.** Filings, exhibits, case materials.
  Same handling as T2 plus evidence-preservation / chain-of-custody rules.

### Tile-to-tier mapping (B1)

| Tile | Tier | Notes |
| --- | --- | --- |
| `system_health` | T0 | No PII. |
| `run_modules` | T1 | Hashed IDs, role, jurisdiction only. |
| `correspondence` | T2 | Tenant/landlord correspondence, metadata + content. |
| `user_concerns` | T2 | Tenant-submitted content, PII-bearing. |
| `advanced` | T1 (tools) / T0 (`detect_repeated_fees` cost-guard) | Cost-guard is counting only, no identity data. |

### 20. Alembic `sa.ARRAY` migrations fail on SQLite (module_registry and feature_flags)

- **What happened:** SQLite has no native `ARRAY` type. Two Alembic migrations used `sa.ARRAY(sa.String())` and silently failed to run on local SQLite:
  - First occurrence: `alembic/versions/20260615_add_module_registry.py` (`module_registry.depends_on` column) — caused 24 test failures until `app/models/models.py` changed `depends_on` from `ARRAY(String)` to `JSON`.
  - Second occurrence: `alembic/versions/20260609_add_feature_flags_table.py` (`feature_flags.allowed_roles` and `allowed_states`) — the table silently did not exist in local dev, masking real feature-flag behavior.
- **Fix pattern:** Keep the PostgreSQL/Render Alembic migrations unchanged (they are correct for Postgres), but add a dialect-aware `ensure_schema()` startup path for SQLite:
  - `app/core/module_overrides.py::ensure_schema()` already uses this pattern for the `module_overrides` table.
  - `app/core/features.py::ensure_schema()` now mirrors it for `feature_flags`, creating the table with `TEXT` columns instead of `TEXT[]`, `INTEGER PRIMARY KEY AUTOINCREMENT` instead of `SERIAL`, and `CURRENT_TIMESTAMP` instead of `NOW()`.
  - `app/main.py` calls both `ensure_schema()` functions during the lifespan "Module Overrides Init" stage.
  - Readers (e.g. `FeatureFlagManager._refresh_from_db()`) must tolerate `allowed_roles` as a JSON string on SQLite.
- **Rule: ANY new Alembic migration that uses `sa.ARRAY` needs a SQLite-compatible fallback path from the start.** Either avoid `sa.ARRAY` in the model, or add a matching dialect-aware `ensure_schema()` and make the reader code tolerate the SQLite representation.
- **Files:** `alembic/versions/20260615_add_module_registry.py`, `alembic/versions/20260609_add_feature_flags_table.py`, `app/models/models.py`, `app/core/module_overrides.py`, `app/core/features.py`, `app/main.py`.
- **Other `sa.ARRAY` migrations found during this search:** Only the two above (`module_registry` and `feature_flags`). No other Alembic migration in `alembic/versions/` currently uses `sa.ARRAY`.
