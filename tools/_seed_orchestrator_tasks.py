"""Seed tools/agent_orchestrator_tasks.json with a fresh consolidated todo list.

Compiles incomplete items from:
  - BUILD_STATE.md Known Broken/Pending + Next Session Should Start With
  - ACTIVE_CONTEXT.md NEXT TO BUILD
  - FNG_TODO.md unchecked items
  - STUB_AUDIT.md Tier 1-4

Run once to refresh the orchestrator queue. Idempotent: overwrites the file.
"""

from __future__ import annotations

import json
from pathlib import Path

TS = "2026-07-19T00:00:00Z"

TASKS = [
    # BUILD_STATE.md — Known Broken / Pending + Next Session Should Start With
    {
        "id": "todo-001",
        "title": "SSOT pre-commit hook: fix hardcoded URL violations",
        "description": (
            "Pre-existing hardcoded URL strings across the codebase make the SSOT "
            "Architecture Verification pre-commit hook fail. Fix all "
            'RedirectResponse(url="/...") calls to use navigation.get_stage() + '
            "ssot_redirect(). Currently commits require --no-verify."
        ),
        "category": "refactor",
        "target_model": "swe-1.7",
        "priority": "high",
        "file_path": "app/routers/",
        "status": "pending",
        "notes": (
            "BUILD_STATE.md Known Broken/Pending. auth.py, storage.py, onboarding.py, "
            "document_delivery.py, role_ui.py already fixed 2026-05-02. Remaining "
            "violations elsewhere."
        ),
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-002",
        "title": "Sync-orchestrator pre-commit hook: use venv311 python",
        "description": (
            "Hook uses Python 3.13 (App Store) instead of venv311. Conflicts with "
            "stashed unstaged changes during pre-commit. Fix hook config to: "
            "entry: venv311/Scripts/python.exe tools/sync_orchestrator.py --git-add"
        ),
        "category": "refactor",
        "target_model": "swe-1.6",
        "priority": "medium",
        "file_path": ".pre-commit-config.yaml",
        "status": "pending",
        "notes": "BUILD_STATE.md Known Broken/Pending",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-003",
        "title": "Review and commit uncommitted working-tree drift",
        "description": (
            "8 files modified but uncommitted: .env.example, .env.production.example, "
            "AI_HANDOFF_PACKET.md, app/core/config.py, app/core/product_manifest.py "
            "(page_shell registration), app/modules/free_api_pack.py, "
            "tools/.sync_orchestrator_hash, app/main.py. Review each diff and commit "
            "in logical groups."
        ),
        "category": "other",
        "target_model": "swe-1.6",
        "priority": "medium",
        "file_path": ".env.example",
        "status": "pending",
        "notes": (
            "BUILD_STATE.md Known Broken/Pending. git status shows M on all listed files. "
            "Multi-file task: see description for full list."
        ),
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-004",
        "title": "Review and commit Page Shell mobile renderer (spec 12)",
        "description": (
            "Uncommitted: app/modules/page_shell/, static/page_shell/, "
            "static/admin/page_shell_demo.html. CSS-only mobile renderer with 1024px "
            "breakpoint, GOVERN sticky pin, skeleton-specific zone ordering. Needs "
            "review then commit."
        ),
        "category": "other",
        "target_model": "swe-1.6",
        "priority": "medium",
        "file_path": "static/page_shell/page_shell.css",
        "status": "pending",
        "notes": "BUILD_STATE.md Known Broken/Pending. Prior session work.",
        "created_at": TS,
        "updated_at": TS,
    },
    # ACTIVE_CONTEXT.md — NEXT TO BUILD
    {
        "id": "todo-005",
        "title": "GUI Phase 1 - Four-pillar interface (Home/Record/Know/Act)",
        "description": (
            "Continue tenant-facing GUI. /gui/* four-pillar nav in place. know.html "
            "and act.html are real hubs. Next: integrate Calendar/Timeline, home-page "
            "dashboard cards. See Semptify_Site_GUI_Framework.md for canonical pillar "
            "definitions."
        ),
        "category": "other",
        "target_model": "glm-5.2",
        "priority": "high",
        "file_path": "app/templates/gui/",
        "status": "in_progress",
        "notes": "ACTIVE_CONTEXT.md priority #2. UPL guardrail (#1) complete.",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-006",
        "title": "Document Center planning",
        "description": (
            "Implement per docs/planning/DOCUMENT_CENTER_PLAN.md, "
            "DC_DESIGN_SONNET.md, DC_HANDOFF_SONNET.md. Pending - no code yet."
        ),
        "category": "other",
        "target_model": "glm-5.2",
        "priority": "medium",
        "file_path": "docs/planning/DOCUMENT_CENTER_PLAN.md",
        "status": "pending",
        "notes": "ACTIVE_CONTEXT.md NEXT TO BUILD #3",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-007",
        "title": "Attorney Intake Packet - feature/attorney-intake-packet branch",
        "description": (
            "Scaffold exists on feature branch, uncommitted. Needs user review of " "scaffold before continuing."
        ),
        "category": "other",
        "target_model": "swe-1.6",
        "priority": "medium",
        "file_path": "app/modules/attorney_intake_packet/",
        "status": "in_progress",
        "notes": "ACTIVE_CONTEXT.md NEXT TO BUILD #4. Blocked on user review. Branch: feature/attorney-intake-packet",
        "created_at": TS,
        "updated_at": TS,
    },
    # FNG_TODO.md
    {
        "id": "todo-008",
        "title": "Audit .card--interactive:hover for leftover box-shadow leaks",
        "description": (
            "base.html and ssot-design-system.css both have .card:hover { box-shadow: "
            "var(--shadow-md); } - spec says zero shadows. Reconcile."
        ),
        "category": "refactor",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "app/templates/base.html",
        "status": "pending",
        "notes": "FNG_TODO.md design system task",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-009",
        "title": "Replace emoji nav icons in base.html with line icons",
        "description": (
            "base.html:490-494 uses emoji nav icons. Design handoff says single-color "
            "line icons only, never emoji. Cosmetic, low priority."
        ),
        "category": "refactor",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "app/templates/base.html",
        "line_start": 490,
        "line_end": 494,
        "status": "pending",
        "notes": "FNG_TODO.md design system task",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-010",
        "title": "Visually verify 5 template color sets render in production",
        "description": (
            "template-1 through template-5 color sets verified by reading CSS source "
            "only - never visually confirmed in production after deploy. Use Playwright "
            "mcp3_browser_navigate + screenshot for each."
        ),
        "category": "test_add",
        "target_model": "kimi-2.7",
        "priority": "low",
        "file_path": "static/css/ssot-design-system.css",
        "status": "pending",
        "notes": "FNG_TODO.md design system task",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-011",
        "title": "Dark mode toggle or prefers-color-scheme fallback",
        "description": (
            "ssot-design-system.css:192-201 has dark-mode overrides but nothing in "
            "app/templates or static/ ever sets data-theme=dark. Dark mode is defined "
            "but unreachable. Add either a toggle UI or prefers-color-scheme: dark "
            "media query fallback."
        ),
        "category": "refactor",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "static/css/ssot-design-system.css",
        "line_start": 192,
        "line_end": 201,
        "status": "pending",
        "notes": "FNG_TODO.md design system task",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-012",
        "title": "Fix broken emoji encoding in tenant_home.html",
        "description": "Emoji characters show ? instead of emoji. Fix encoding.",
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "medium",
        "file_path": "app/templates/pages/tenant_home.html",
        "status": "pending",
        "notes": "FNG_TODO.md tenant home rebuild",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-013",
        "title": "Fix /tenant/journal link -> should point to /tenant/timeline",
        "description": (
            "tenant_home.html has a link to /tenant/journal that should route to " "/tenant/timeline per current SSOT."
        ),
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "medium",
        "file_path": "app/templates/pages/tenant_home.html",
        "status": "pending",
        "notes": "FNG_TODO.md tenant home rebuild",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-014",
        "title": "Fix /documents link -> non-existent route",
        "description": (
            "tenant_home.html links to /documents which is not a registered route. "
            "Replace with correct target (likely /vault or /gui/record)."
        ),
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "medium",
        "file_path": "app/templates/pages/tenant_home.html",
        "status": "pending",
        "notes": "FNG_TODO.md tenant home rebuild",
        "created_at": TS,
        "updated_at": TS,
    },
    # STUB_AUDIT.md Tier 1 - Core User Flow
    {
        "id": "todo-015",
        "title": "stateless_oauth.py:239 - Token refresh not implemented",
        "description": (
            "Token refresh returns None. Users get logged out when token expires and "
            "cannot reconnect. HIGH priority - blocks primary tenant journey."
        ),
        "category": "stub_fix",
        "target_model": "swe-1.7",
        "priority": "high",
        "file_path": "app/core/stateless_oauth.py",
        "line_start": 239,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 1.1",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-016",
        "title": "storage_middleware.py:284 - DB-based token pre-check is TEMPORARY",
        "description": (
            "Every request hits DB for token check. Needs ice-cube in-memory model. "
            "HIGH priority - performance impact."
        ),
        "category": "refactor",
        "target_model": "swe-1.7",
        "priority": "high",
        "file_path": "app/core/storage_middleware.py",
        "line_start": 284,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 1.2",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-017",
        "title": "static/js/core/app.js - uploadToVault() is a stub",
        "description": (
            "Lines 40, 61: uploadToVault() uses alert() instead of fetch to "
            "/api/vault/upload. Vault portal UI button does nothing. HIGH priority."
        ),
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "high",
        "file_path": "static/js/core/app.js",
        "line_start": 40,
        "line_end": 61,
        "status": "pending",
        "notes": ("STUB_AUDIT.md Tier 1.3. May overlap with vault-portal.js reactive pattern."),
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-018",
        "title": "timeline.html:232 - TODO Submit to API",
        "description": ("Timeline event add just alerts + reloads. Users cannot add timeline " "events from UI."),
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "medium",
        "file_path": "app/templates/pages/timeline.html",
        "line_start": 232,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 1.4",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-019",
        "title": "workspace-stage-model.js - 25-line stub",
        "description": ("Tests expect workflow API integration. Workspace panels do not load " "stage data."),
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "medium",
        "file_path": "static/js/workspace-stage-model.js",
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 1.5",
        "created_at": TS,
        "updated_at": TS,
    },
    # STUB_AUDIT.md Tier 2 - Module Completeness
    {
        "id": "todo-020",
        "title": "litigation_intelligence/router.py - 3 endpoints return 501",
        "description": (
            "Lines 218, 250, 275: entity graph, visualization, shortest-path all "
            "return 501 Graph engine not implemented."
        ),
        "category": "stub_fix",
        "target_model": "swe-1.7",
        "priority": "medium",
        "file_path": "app/modules/litigation_intelligence/router.py",
        "line_start": 218,
        "line_end": 275,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 2.1",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-021",
        "title": "mndes_api_client.py - 3 NotImplementedError (MNDES submit/status/exhibits)",
        "description": ("Lines 193, 202, 208. External API dependency, blocked on EAST team."),
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "app/services/mndes_api_client.py",
        "line_start": 193,
        "line_end": 208,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 2.2 - BLOCKED on external team",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-022",
        "title": "housing_accountability/router.py:83 - detect_repeated_fees() placeholder",
        "description": "Returns empty patterns. Fraud detection does not work.",
        "category": "stub_fix",
        "target_model": "swe-1.7",
        "priority": "medium",
        "file_path": "app/modules/housing_accountability/router.py",
        "line_start": 83,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 2.3",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-023",
        "title": "components/router.py:781 - TODO role-specific config",
        "description": "Returns static config dict instead of role-specific configuration from user context.",
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "app/modules/components/router.py",
        "line_start": 781,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 2.4",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-024",
        "title": "filedored_service.py:91 - TODO integrate with SWE 1.6 or local model",
        "description": "Document classification uses fallback. Needs integration with SWE 1.6 or local model.",
        "category": "stub_fix",
        "target_model": "swe-1.7",
        "priority": "low",
        "file_path": "app/services/filedored_service.py",
        "line_start": 91,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 2.5",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-025",
        "title": "research_module.py:376 - placeholder for actual cloud upload",
        "description": "Logs would upload instead of performing cloud upload. Research module cloud sync does not work.",
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "app/modules/research_module.py",
        "line_start": 376,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 2.6",
        "created_at": TS,
        "updated_at": TS,
    },
    # STUB_AUDIT.md Tier 3 - Disabled Infrastructure (DEFER)
    {
        "id": "todo-026",
        "title": "main.py:370 - Positronic Brain DISABLED (memory hog)",
        "description": "Event tracking offline. Re-enable after optimization. Intentionally disabled.",
        "category": "stub_fix",
        "target_model": "swe-1.7",
        "priority": "low",
        "file_path": "app/main.py",
        "line_start": 370,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 3.1 - DEFER",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-027",
        "title": "main.py:470,489 - Distributed mesh network DISABLED",
        "description": "Cross-instance comms offline. Intentionally disabled.",
        "category": "stub_fix",
        "target_model": "swe-1.7",
        "priority": "low",
        "file_path": "app/main.py",
        "line_start": 470,
        "line_end": 489,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 3.2 - DEFER",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-028",
        "title": "main.py:1341,1376 - Performance monitoring DISABLED (85% memory)",
        "description": "No perf telemetry. Intentionally disabled.",
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "app/main.py",
        "line_start": 1341,
        "line_end": 1376,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 3.3 - DEFER",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-029",
        "title": "storage/router.py:1591 - OAuth state cleanup DISABLED",
        "description": "Expired states accumulate. Needs DB role fix (Neon DELETE permission).",
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "app/modules/storage/router.py",
        "line_start": 1591,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 3.4 - DEFER, needs DB role fix",
        "created_at": TS,
        "updated_at": TS,
    },
    # STUB_AUDIT.md Tier 4 - Data Stubs (DEFER, safe to ship)
    {
        "id": "todo-030",
        "title": "state_laws/router.py:80 - Most states return stub",
        "description": "Only MN is complete. Other states show limited data banner with link to lawhelp.org. BY DESIGN.",
        "category": "stub_fix",
        "target_model": "kimi-2.7",
        "priority": "low",
        "file_path": "app/modules/state_laws/router.py",
        "line_start": 80,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 4.1 - DEFER, safe to ship",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-031",
        "title": "eviction/seed_court_data.py - Seed data TODOs",
        "description": "4 matches of TODO in seed data. Court data incomplete.",
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "app/services/eviction/seed_court_data.py",
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 4.2 - DEFER",
        "created_at": TS,
        "updated_at": TS,
    },
    {
        "id": "todo-032",
        "title": "legal_filing_module.py:6 - Placeholder for mesh/network integration",
        "description": "Module works, mesh hook is no-op. Low impact.",
        "category": "stub_fix",
        "target_model": "swe-1.6",
        "priority": "low",
        "file_path": "app/modules/legal_filing_module.py",
        "line_start": 6,
        "status": "pending",
        "notes": "STUB_AUDIT.md Tier 4.3 - DEFER",
        "created_at": TS,
        "updated_at": TS,
    },
]


def main() -> int:
    out = "tools/docs_todos.json"
    with Path(out).open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(TASKS, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {len(TASKS)} doc-sourced tasks to {out}")
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for t in TASKS:
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
        by_priority[t["priority"]] = by_priority.get(t["priority"], 0) + 1
    print("by status:", by_status)
    print("by priority:", by_priority)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
