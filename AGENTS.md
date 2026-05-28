# Semptify Agent Guide

This repository contains a housing-rights and tenant-support product. Any AI agent working here should follow these standards.

> Canonical project governance and doc hierarchy are defined in `PROJECT_BIBLE.md`.

---

## ⚠️ MANDATORY PRE-FLIGHT — Every AI Agent MUST Do This First

**Before writing a single line of code, you MUST:**

1. **Read `BUILD_STATE.md`** — What was last shipped, what is known broken, what is pending.
2. **Read `ACTIVE_CONTEXT.md`** — What is being worked on RIGHT NOW. Do not start something else.
3. **Read the Known Failure Registry below** — Do not repeat a past mistake.
4. **State your plan before acting** — Tell the user what you intend to change and why before touching any file.
5. **Do not ship without a verification step** — Every change needs a compile check or test run.

**If you skip pre-flight, you will repeat a past mistake. The history proves this.**

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

---

## 📋 Agent Session Checklist

Before ending any session, you MUST:

- [ ] Verify all changed Python files compile: `python -m py_compile <file>`
- [ ] Run SSOT tests if any navigation changed: `python tests/test_ssot_architecture.py`
- [ ] Update `BUILD_STATE.md` with: what was shipped, what is known working, what is pending
- [ ] Update `ACTIVE_CONTEXT.md` if the current priority changed
- [ ] Do NOT mark something "working" unless it was actually tested — write "pending live test" if untested

---

## Core Mission

Semptify is built to better protect the rights of humans facing housing problems.
It is for people who may not be able to afford a legal team, may be overwhelmed, and may need help organizing documents, evidence, timelines, and next steps.

## Non-Negotiables

- Free forever.
- No advertising ever.
- Privacy-respecting by design.
- User-controlled documents and storage wherever possible.
- Evidence preservation over feature novelty.
- Calm, clear, trustworthy UX.

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

## SSOT Architecture Enforcement (CRITICAL)

All navigation, routing, and URL construction MUST follow Single Source of Truth (SSOT) principles:

### NEVER DO (will be rejected):
- Hardcoded URL strings: `"/onboarding-assets/select-role.html"`, `"/storage/providers"`
- Direct `RedirectResponse(url="/some/path")` without navigation registry
- Inline JS navigation: `window.location.href = "/path/to/page"`
- HTML href attributes with hardcoded paths: `<a href="/onboarding/...">`
- Middleware or routers defining their own redirect targets

### ALWAYS DO:
- Import: `from app.core.navigation import navigation`
- Use: `navigation.get_stage("role_select").path`
- Use: `navigation.get_onboarding_start()` for entry points
- Use: `navigation.get_next_path(current_stage)` for transitions
- Static files: Fetch `/onboarding/ssot-navigation` API, then navigate
- Python redirects: Use paths from navigation registry only

### Verification (MANDATORY):
Before committing any navigation change, run:
```bash
python tests/test_ssot_architecture.py
```
All tests must pass. Violations block deployment.

### Why This Matters:
SSOT violations are the #1 cause of redirect loops, broken flows, and "many chiefs" architecture. Navigation is a **process**, not a property of individual pages. Centralize or perish.

### Files that must use SSOT:
- All files in `app/routers/*.py` that return redirects
- All files in `app/core/*_middleware.py`
- All files in `static/onboarding/*.html`
- Any new navigation/routing logic

### SSOT Evolution (When to Break Rules):

**Rules exist to enable flow, not prevent it.** The SSOT registry is alive and grows with the product.

**Legitimate exceptions:**
- **Experimental features**: Use `navigation.add_escape_hatch(path, reason="Beta feature", ttl_days=7)`
- **New flows**: Use `navigation.register_stage(FlowStage(...))` to expand SSOT
- **Deprecating old paths**: Use `navigation.deprecate_path("/old", "/new")` for graceful evolution

**Philosophy:** 
- A rule that cannot evolve is a prison
- A rule that is never enforced is a suggestion
- Good rules have escape hatches with TTLs (time-to-live)
- Break rules intentionally, document the exception, let it expire or integrate

**When breaking SSOT:**
1. Document WHY in code
2. Use escape_hatch with expiration
3. After the experiment, either: 
   - Kill it (remove the code)
   - Formalize it (register as proper FlowStage)
   - Deprecate it (old path → new canonical)