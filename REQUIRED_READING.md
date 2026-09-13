# REQUIRED_READING.md — Semptify Reading Manifest

> **This is the single source of truth for "what must I read before touching Semptify."**
> Every agent/human entry point (`AGENTS.md`, `.cursor/rules/`, `.devin/skills/`,
> `.github/prompts/`) points here. If the required-reading set changes, change
> **this file** — do not scatter new lists into skills, rules, or docs.
>
> Order matters: read top to bottom within each tier. If any Tier-4 document
> conflicts with Tier 1, **Tier 1 wins** (per `PROJECT_BIBLE.md` hierarchy).

---

## TIER 1 — Read at the start of EVERY session, before any work

| # | File | What it gives you |
| --- | --- | --- |
| 1 | `AGENTS.md` | Python 3.11.9 mandate, **Known Failure Registry (all items)**, module contract rules, NO-TOUCH modules, task-claiming rule |
| 2 | `ACTIVE_CONTEXT.md` | What is being worked on right now — do not start something else |
| 3 | `BUILD_STATE.md` | Last 2 entries: what shipped, what is broken, what is pending |
| 4 | `PROJECT_BIBLE.md` | Canonical doc hierarchy and governance — the tie-breaker when docs disagree |
| 5 | `CORE_CONTEXT.md` | Mission: public utility not a product; Time to Real Help; banned language; the five questions |

## TIER 2 — Read before writing or approving any code or copy

| # | File | What it gives you |
| --- | --- | --- |
| 6 | `docs/admin/MOTIVATIONS.md` | Foundational motivations, language rules, Information Integrity Standards |
| 7 | `docs/AI_TEAM_OPERATING_PROTOCOL.md` | Three-way collaboration protocol, decision authority matrix, batching rules |
| 8 | `docs/adr/` — all ADRs (currently 0001–0009) | Permanent dated decisions (storage, navigation, attraction, banned motivations, language, open access, OCR privacy, information orchestrator, fact-check freshness) — never edited |
| 9 | `SEMPTIFY_SYSTEM_MANIFEST.md` | Module registry: active/disabled modules, tier map, golden rules — **required before touching any module or router** |

## TIER 3 — Read when touching that domain

| File | Required when |
| --- | --- |
| `SECURITY_AND_PRIVACY_ARCHITECTURE.md` | Auth, storage, PII, tenant data, cookies, OAuth |
| `DEPLOYMENT_READINESS.md` | Deploys, production verification, Render/Neon work |
| `docs/admin/SSOT_EXPORT.md` | Data flows, canonical paths, storage/tracing — the SSOT reference |
| `README.md` | Build/run/env setup, dependency changes |
| `.devin/rules/*.md` | Standing rules matching your task (four pillars, redirects, roles/identity, journal-calendar-timeline, onboarding gates, progressive disclosure, vault SDK, forge) |
| `.devin/skills/<name>/SKILL.md` | The workflow you are executing (`preflight`, `ship`, `forge`, `review`, `ssot-analysis`, `orchestrator_preflight`, `cloudflare-dev-mode`, `help-page-review`) — and its `.github/prompts/` mirror stays in sync |
| `.cursor/rules/01-gui-chronological-spatial.mdc` | Any GUI work — chronological/spatial ordering + eye-path self-audit |
| `GAPS.md` | Auto-generated gap report (regenerate via `tools/gap_report.py`) |

## TIER 4 — Historical / stale: read ONLY with cross-check against Tier 1

| File | Status |
| --- | --- |
| `BUILD_GUIDE_SSOT.md` | **SUPERSEDED** — May 2026 stub. Live build truth is `BUILD_STATE.md` + `ACTIVE_CONTEXT.md` |
| `BLUEPRINT.md` | **STALE** — pre-shell architecture inventory; duplicates SYSTEM_MANIFEST |
| `SEMPtIFY_CURRENT_MAP.md` | **STALE** — May 2026 snapshot |
| `ROADMAP_TO_PUBLIC_RELEASE.md` | **STALE** — roadmap superseded by ACTIVE_CONTEXT |
| `STUB_AUDIT.md` | Point-in-time (2026-06-19); several items since fixed |
| `STATUS_AUDIT.md`, `ACTION_FEEDBACK_AUDIT.md` | Point-in-time snapshots — historical inputs, not current status |
| `DOC_INDEX.md` | Inventory of canonical-claiming docs + staleness flags (2026-07-03) |

## For humans / tooling only

- `docs/doc-map.yaml` — doc↔code map that drives the commit-prefix hook and the scheduled staleness check. Append an entry when adding a doc under `docs/`.

---

## Rules of this manifest

1. **One list.** This file is the only place the required-reading set is defined. Entry points link to it; they do not maintain their own lists.
2. **Conflicts:** canonical hierarchy in `PROJECT_BIBLE.md` §1 decides; Tier 4 never overrides Tiers 1–3.
3. **Adding a required read:** append it to the correct tier here, then (if it lives under `docs/`) add a `doc-map.yaml` entry so the staleness check sees it.
4. **Session start = Tier 1.** Task start = Tier 1 + Tier 2. Domain work = + matching Tier 3 rows.
