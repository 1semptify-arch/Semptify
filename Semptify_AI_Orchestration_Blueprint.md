# Semptify 5.0 — AI Build Orchestration Blueprint

**System Level:** Layer 0 — sits above the GUI Framework and Master Inventory.
**Objective:** Rule-based resource routing to get maximum use out of one $20/month subscription plus free tools, while protecting the security of a zero-knowledge, storage-as-identity system. Built and maintained by one person (you), using AI tools as labor and judgment aids — not a team with separate hired roles.

This is the single canonical version of this document. Earlier drafts (from this conversation, from Gemini/MSN Copilot, from GitHub Copilot) are all merged in here. Don't create a `_v2` — update this file in place going forward, same rule as everything else in this project.

---

## 1. Core Principle

**No task gets assigned mid-conversation, ad hoc, to whichever tool happens to be open.** Every task gets a routing tag before it goes anywhere. That tag answers, in one glance, what kind of task it is and where it should go.

---

## 2. Fast-Tag Routing System

Four tags. Every task gets exactly one, appended to its description when logged.

| Tag | Meaning | Routes to |
| --- | --- | --- |
| **[RI]** — Research / Isolated | Gathering external facts, comparing approaches, legal rules, design patterns. No repo access needed. | Gemini or MSN Copilot (free) |
| **[EI]** — Execution / Isolated | Code for a single file or endpoint, no cross-module dependencies. | Windsurf house models or GLM-5.2 |
| **[EF]** — Execution / Full-Repo | Logic spanning multiple routers, models, or services. | Windsurf premium credits |
| **[JF]** — Judgment / Fragile | Touches security, auth tokens, OAuth, database migrations, tenant data, or any architecture decision. | Claude first (design/decision), then handed down as an already-decided task to an execution resource |

```text
[ incoming task ]
        │
   ┌────┴─────┐
   ▼          ▼
[Isolated]  [Full-Repo / Sensitive]
   │            │
┌──┴──┐     ┌───┴────┐
▼     ▼     ▼        ▼
[RI] [EI]  [EF]     [JF]
 │    │     │         │
 ▼    ▼     ▼         ▼
Gemini/  Windsurf  Windsurf   Claude (judgment)
MSN      House/    Premium      │
Copilot  GLM-5.2   Credits      ▼
                            Windsurf execution
                            (task now pre-decided)
```

**Why a tag instead of re-asking the 3 questions every time:** the questions still matter, but once you've answered them for a task, the tag *is* the answer — no need to re-derive it every time you look at the queue.

---

## 3. Resource Roster (real cost structure)

Windsurf ($20/month) is the only paid subscription. Inside it: unlimited "house" model usage plus a limited pool of premium credits. Everything else is a separate, free, standalone tool — none of them talk to each other directly. You are the bridge, carrying context between them (Section 7 below reduces how manual that has to be).

| Resource | Real Cost | Best For | Weak For | Context |
| --- | --- | --- | --- | --- |
| **Windsurf — house models** | Unlimited (in $20/mo) | Default for [EI] routine execution — no rationing needed | Judgment calls, full-repo architecture decisions | Full repo |
| **Windsurf — premium credits** | Limited pool (in $20/mo) | [EF] full-repo work, security sweeps, anything judgment-adjacent | Routine/simple execution — don't spend here | Full repo |
| **GLM-5.2** | Free | [EI] overflow when premium credits should be conserved | Novel architecture decisions | Large, verify per session |
| **VS Code Copilot** | Separate account | Inline completions while hand-editing | Multi-file orchestration | File/selection level |
| **Gemini** | Free tier | [RI] research, large-document synthesis, second opinions | Direct repo execution | Very large |
| **MSN Copilot** | Free | [RI] external research only — cannot save or run code | Repo access, persistence | Session-only |
| **Local AI (smollm3/AI Toolkit)** | Free, runs on laptop | **Do not use** — 8GB RAM makes this unreliable | Everything | Small |
| **Claude (this conversation)** | Whatever your plan is | [JF] judgment calls, reconciling conflicting reports, maintaining these canonical docs | Direct repo file editing | Large |

**Practical rule:** default to Windsurf house models for anything [EI]. Reserve premium credits specifically for [EF] and [JF]-adjacent execution. GLM-5.2 is your overflow valve.

---

## 4. Task Queue Schema

Columns for the Task Queue tab in `Semptify_Master_Inventory_LIVE.xlsx`:

`Task ID | Tag | Description | Pillar | Target File/Path | Assigned Resource | Cost Tier | Status | Depends On | Context Baseline (Git Commit) | Verification Step | Date Logged | Date Resolved`

### Column notes:

- **Tag** — one of [RI]/[EI]/[EF]/[JF] from Section 2
- **Target File/Path** — the specific file/folder being touched (e.g. `app/modules/storage/router.py`) — this is what prevents two sessions from silently colliding on the same file
- **Context Baseline (Git Commit)** — the commit hash the task was assigned under, so an execution tool never works against stale assumptions
- **Verification Step** — the explicit, checkable proof the task is actually done (e.g. "run `pytest tests/test_vault.py`, paste output" or "confirm `/gui/record` returns 200 with a real uploaded file visible")
- **Status** — Open → In Progress → Blocked → Review → Done

**Status update is mandatory** before any commit — this is the single rule most likely to get skipped under time pressure, and the one that matters most for not losing track of what's real.

---

## 5. Module Contract Template

Every module gets one of these — living in the Module Inventory tab, one line minimum, full version for anything security-sensitive.

### One-line version (minimum):

`module.path — Inputs: X; Outputs: Y; Dependencies: Z; Status: Working/Partial/Deprecated`

### Full version (for anything [JF]-tagged or security-sensitive):

- Module path:
- Pillar: RECORD/KNOW/ACT/GOVERN
- Status: Planned / Partial / Working / Deprecated
- Public endpoints: (list routes)
- Inputs: (auth context, request body, files)
- Outputs: (DB records, events, files, state changes)
- Dependencies: (other modules, services, env flags)
- Security classification: public / internal / tenant-sensitive / legal-sensitive
- Acceptance test: (what proves it works)
- Rollback plan: (how to undo safely if it breaks)

### Filled example — vault.router (already the resolved canonical vault):

- Module path: `app.modules.vault.router`
- Pillar: RECORD
- Status: Working (keystone — do not modify without judgment-call review)
- Public endpoints: `/api/vault/all`, `/api/vault/{id}/download`, `/api/vault/document/{vault_id}/content`, `/api/vault/export` (new — ZIP endpoint)
- Inputs: authenticated user context (via `yellow_access`), file upload, metadata
- Outputs: stored document record, vault index entry
- Dependencies: storage backend, `auth.middleware`, `unified_overlays` (for viewing)
- Security classification: tenant-sensitive
- Acceptance test: upload → appears in list → view/download works → unauthorized user denied
- Rollback plan: revert to prior commit; disable `/export` endpoint individually if it's the point of failure

---

## 6. Preflight + Judgment Gate

Before any code change, whichever resource is executing confirms:

- [ ] Task Queue row exists and is current
- [ ] Tag confirmed ([RI]/[EI]/[EF]/[JF])
- [ ] Assigned resource matches the tag's routing rule
- [ ] Security/legal-sensitive ([JF])? → routed through Claude/human judgment *before* execution, not after
- [ ] Target file(s) listed and scoped
- [ ] Verification step defined
- [ ] Rollback plan noted for anything [EF] or [JF]
- [ ] Status updated in Task Queue before commit

This is in addition to — not a replacement for — the existing `preflight.md` session-start checklist (reading `ACTIVE_CONTEXT.md`, `BUILD_STATE.md`, the Known Failure Registry, and now the Master Inventory + Task Queue).

---

## 7. Reducing the Manual Handoff Bottleneck

You are the bridge between tools that don't talk to each other. That's real and won't change — but it can be made less tedious.

**Optional automation — a context-compiler script** (adapted below to your actual files, not the placeholder names an earlier draft assumed). Running this before switching to Gemini/Copilot/MSN Copilot bundles your real canonical docs into one paste-ready file, instead of you manually gathering them each time.

Save as `scripts/compile_ai_context.py` (script provided separately — see below). Run before any handoff:

```python
python scripts/compile_ai_context.py
```

This produces `AI_HANDOFF_PACKET.md` — copy its full contents into Gemini, MSN Copilot, or a fresh Windsurf session to sync it instantly with where things actually stand.

**Multi-session coordination (only relevant if you ever run more than one AI session at once):** never let two execution sessions work in the same file/folder simultaneously. If you do run parallel sessions, split by directory (e.g., one session on `app/modules/calendar/`, another on `app/modules/timeline/`) and rely on the Task Queue's Target File/Path column to catch overlaps before they happen.

---

## 8. Immediate Priorities (the real, current queue — not hypothetical)

These are logged as the actual seed of your Task Queue, reflecting tonight's real state:

| Task | Tag | Resource | Status |
| --- | --- | --- | --- |
| Make `user_id` authoritative from session, not form field | [JF]→[EI] | Claude decided → Windsurf house | Fix applied, confirm end-to-end |
| Quarantine `vault_engine`/`vault_all_in_one` | [JF]→[EI] | Claude decided → Windsurf | Done |
| Build `/api/vault/export` ZIP endpoint | [EI] | Windsurf house | In progress |
| Finish OH/NC/GA state data | [EI] | GLM-5.2 or Windsurf | In progress |
| Apply remaining capability gates (5 ADMIN + 4 CORE modules) | [EI] | Windsurf house | Pending confirmation |
| Brain/mesh router-level deregistration | [JF]→[EI] | Claude decided → Windsurf | Done |
| Timeline/incidents migration | [JF]→[EF] | Claude decided → Windsurf premium | Pending |
| Audit-log implementation (feature branch) | [EF] | Windsurf premium | In progress, not merged |
| Wire `upl_risk_tier` into `product_manifest.py` | [EI] | Windsurf house or GLM-5.2 | Pending |
| GUI Screens 1–4 (nav shell, home, record, export) | [EF] | Windsurf (full-repo, touches routing) | Screens 1–3 done, export ZIP pending |

---

## 9. Realistic Build Sequence (not a team sprint plan — a solo-builder order of operations)

**Right now:** get the ZIP export working end-to-end — this is what unlocks the actual demo you need.
**Next:** confirm the 4 GUI screens work together as a real click-through flow.
**Then:** close out the remaining security sweep items (capability gates, brain/mesh confirmation, audit-log merge decision).
**Then:** wire the UPL risk tiers into the actual module registrations.
**Ongoing, no fixed deadline:** state-law data expansion, Library content, ACT tool buildout — these matter but don't block the current demo goal.

No named roles beyond "you" exist yet. If the housing worker's office becomes real beta testers, they're testers, not builders — that's a separate relationship from the AI resources doing the actual coding.

---

## 10. Risks to Keep Watching

- **Premium credit exhaustion** — mitigated by the tag system routing routine work to house models.
- **Manual bottleneck** — mitigated by the context-compiler script, not eliminated (you're still the bridge, just a faster one).
- **Two sessions colliding on the same file** — mitigated by Target File/Path in the Task Queue; only matters once you're running parallel sessions.
- **Local AI unreliability** — already resolved: don't use it for anything real.
