# Semptify Project Bible

This document is the canonical source-of-truth for the Semptify FastAPI repository.
It defines the authoritative build reference, governance rules, onboarding flow, and the disciplined doc hierarchy that all developers, reviewers, and AI agents must follow.

## 1. Canonical Source-of-Truth Hierarchy

Use the following files as the primary authoritative references.
If any other file conflicts with these, the canonical file wins unless the team explicitly agrees to a new canonical replacement.

1. `PROJECT_BIBLE.md` — Project governance, doc hierarchy, and source-of-truth rules.
2. `README.md` — Canonical developer build, run, and local onboarding instructions.
3. `AGENTS.md` — Canonical AI behavior and product standard guide.
4. `SECURITY_AND_PRIVACY_ARCHITECTURE.md` — Canonical integrity, security, and privacy guide.
5. `DEPLOYMENT_READINESS.md` — Canonical production readiness and deployment verification checklist.

## 2. Single Build Reference

All build and startup instructions must be maintained in `README.md`.
This is the authoritative developer build guide.

Use `README.md` for:
- local environment setup
- dependency installation
- running the development server
- supported runtime modes
- basic project structure
- health and API endpoint references

Do not treat `QUICKSTART.md`, `ENTERPRISE_README.md`, or other ad hoc docs as the primary build guide. Those are supplementary and should link back to `README.md`.

## 3. Integrity and Governance Compass

The project must be aligned with these core values:
- protect tenant rights and evidence integrity
- preserve user control and privacy
- avoid ads, manipulation, and hidden data collection
- keep workflows calm, transparent, and stress-safe
- prefer deterministic, auditable behavior over cleverness

For any question about ethics, AI behavior, or product policy, consult `AGENTS.md`.
For any question about security, privacy, or production safety, consult `SECURITY_AND_PRIVACY_ARCHITECTURE.md`.

## 4. Approved Onboarding Flow (Core 5.0)

The canonical first-run onboarding flow is:

1. Welcome screen (`/static/welcome.html`)
2. Role selection (`/onboarding/select-role.html`) — Tenant only in Core
3. **Storage connection (MANDATORY)** (`/onboarding/storage-select.html`)
4. Vault activation (automatic post-OAuth)
5. Tenant home (`/tenant/home`)

**Note:** Storage connection is mandatory for Core 5.0. There is no "skip" option.
Documents are stored in user's cloud provider (Google Drive, Dropbox, or OneDrive).
The aspirational 9-step Extended journey has been archived to `concepts/EXTENDED_USER_JOURNEY_CONCEPT.md`.

The following files are the canonical onboarding assets:
- `static/onboarding/welcome.html`
- `static/onboarding/select-role.html`
- `static/onboarding/validate-advocate.html`
- `static/onboarding/validate-legal.html`

This flow must land the user in an active vault session and a role-specific home page, not a dead-end or ambiguous state.

## 5. Doc Rules for Developers and Agents

- When making a code change, update the relevant canonical doc first.
- If a new feature needs documentation, add it to `README.md` and only then add supplementary docs.
- If an AI agent is asked to make a recommendation, it must cite this hierarchy and prefer the canonical files.
- Do not create new top-level files without first checking whether `README.md`, `AGENTS.md`, or `SECURITY_AND_PRIVACY_ARCHITECTURE.md` already cover it.

## 6. Practical Enforcement

- `README.md` is the build bible.
- `PROJECT_BIBLE.md` is the governance bible.
- `AGENTS.md` is the AI and product ethics bible.
- `SECURITY_AND_PRIVACY_ARCHITECTURE.md` is the system integrity bible.
- `DEPLOYMENT_READINESS.md` is the production acceptance bible.

If there is any ambiguity, update `PROJECT_BIBLE.md` and the referenced canonical doc.

## 7. Recommended Workstream

1. Keep `README.md` updated with the current local build and startup steps.
2. Keep `AGENTS.md` updated when product or AI behavior policies change.
3. Keep `SECURITY_AND_PRIVACY_ARCHITECTURE.md` updated for any security or privacy changes.
4. Keep `DEPLOYMENT_READINESS.md` updated for deployment and release checks.
5. Use this file as the first-level reference before consulting other docs.
