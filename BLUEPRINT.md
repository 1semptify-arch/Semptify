# SEMPTIFY COURT DEFENSE SYSTEM - MASTER BLUEPRINT (SUPERSEDED — HISTORICAL)

> **Status: SUPERSEDED — retained for historical reference only. Do not build from this document.**
>
> This blueprint describes the original single-case "Court Defense System" design from
> before the Semptify 5.0 module/tier/contract architecture. Its router/service status
> tables, "Form Data Hub" central-bus design, and phased TODO list are all stale —
> `DOC_INDEX.md` already flags it as a stale duplicate of the module inventory.
>
> **Current sources of truth:**
> - Module registry: `app/core/product_manifest.py` (live) + `SEMPTIFY_SYSTEM_MANIFEST.md` (snapshot)
> - Module blueprints: `docs/blueprints/` (approval-gated)
> - Master 5.0 blueprint: `bp 9 2.md` (`C:\master-repo\brads temp\`) — pending move into docs when approved
> - Governance: `PROJECT_BIBLE.md` · Work state: `ACTIVE_CONTEXT.md` / `BUILD_STATE.md`
>
> **PII note (2026-09-05):** the original version of this file referenced a specific
> real court case — case number and party names. That content has been removed per
> the workspace rule that no case data or PII belongs in the repo.
>
> What remains below is the original bi-directional data-flow diagram and the
> asset inventory shape, kept because they document the design lineage that led to
> the current Context Loop / contract-driven architecture.

---

## 🔄 BI-DIRECTIONAL DATA FLOW ARCHITECTURE (original concept)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SEMPTIFY DATA MESH                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐            │
│  │   WELCOME    │────▶│   FORM DATA HUB  │◀────│   COPILOT    │            │
│  │   WIZARD     │     │   (Central Bus)   │     │   (AI)       │            │
│  └──────────────┘     └────────┬─────────┘     └──────────────┘            │
│                                │                                             │
│         ┌──────────────────────┼──────────────────────┐                     │
│         │                      │                      │                     │
│         ▼                      ▼                      ▼                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   DOCUMENT   │◀───▶│   TIMELINE   │◀───▶│   CALENDAR   │                │
│  │   VAULT      │     │   ENGINE     │     │   SYSTEM     │                │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              │                                              │
│                              ▼                                              │
│                    ┌──────────────────┐                                     │
│                    │   DEFENSE        │                                     │
│                    │   GENERATOR      │                                     │
│                    └────────┬─────────┘                                     │
│                             │                                               │
│         ┌───────────────────┼───────────────────┐                          │
│         │                   │                   │                          │
│         ▼                   ▼                   ▼                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │   ANSWER     │  │   MOTIONS    │  │ COUNTERCLAIM │                     │
│  │   FORM       │  │   FORMS      │  │   FORMS      │                     │
│  └──────────────┘  └──────────────┘  └──────────────┘                     │
│                                                                            │
│                              │                                              │
│                              ▼                                              │
│                    ┌──────────────────┐                                     │
│                    │   PDF GENERATOR  │                                     │
│                    │   (Court Ready)  │                                     │
│                    └──────────────────┘                                     │
│                                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Lineage note

The "central bus + auto-population" idea in this diagram survives today in different
form: the **Context Loop / Context Engine** (facts, explanations, tapering), the
**FunctionGroupContract** system (declared module I/O), and the **PII boundary**
(documents in the user's own cloud vault, pointers in Postgres) — none of which
existed when this was written. The specific "Form Data Hub" service (`form_data`)
is now a RESEARCH-tier module, not the central bus.

*Original document archived in place 2026-09-05. For current plans see `ACTIVE_CONTEXT.md`.*
