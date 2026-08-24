#!/usr/bin/env python3
"""
gap_report.py — One consolidated, repeatable gap report for Semptify.

Does NOT reinvent gap detection. This repo already has real tooling:
  - tools/stub_detector.py    (AST-verified genuine code stubs)
  - tools/guardrail_engine.py (contract/route/fee/manifest checks)
  - tools/module_registry.yaml (per-module health + flag_reason)
  - app/core/contract_loader.py (which modules are missing a FunctionGroupContract)

This script runs/reads all of them and writes ONE prioritized Markdown report
so gaps don't have to be rediscovered by hand each session. It also records
architectural gaps that no automated check can find (documented below in
KNOWN_ARCHITECTURAL_GAPS) so they stay visible instead of getting lost.

Usage:
    python tools/gap_report.py [--out GAPS.md]

Exit code is always 0 — this is a reporting tool, not a gate. Use
guardrail_engine.py (which does exit non-zero) for CI/pre-commit gating.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# Contract gaps that are real (register.py has a genuine FunctionGroupContract
# that isn't loaded) but already intentionally excluded and documented inline
# in contract_loader.py. Keep this in sync with that file's comments so the
# report doesn't re-flag an already-decided item as if it were new.
KNOWN_INTENTIONAL_CONTRACT_EXCLUSIONS: dict[str, str] = {
    "app.modules.litigation_intelligence": (
        "Excluded on purpose (see contract_loader.py comment): module is INACTIVE "
        "in the manifest and has a pre-existing SyntaxError in router.py "
        "(non-default arg after default arg)."
    ),
}

# Architectural / product-judgment gaps that no automated check catches.
# Add to this list when you find one during manual audit work — it's the
# durable record so the next session doesn't have to rediscover it.
KNOWN_ARCHITECTURAL_GAPS: list[dict[str, str]] = [
    {
        "severity": "HIGH",
        "title": "Two independent, live context-tracking systems",
        "detail": (
            "app.services.context_loop.context_loop (fed by app/services/document_pipeline.py "
            "on every document upload/analysis) and app.modules.context_loop.service "
            "(subscribed to the event bus at app startup, app/main.py) are separate "
            "UserContext implementations with incompatible shapes (dict-based deadlines "
            "vs object-attribute deadlines). Both are real and live, not dead code. "
            "Page Composer's assembly formula reads only the former "
            "(app.services.context_loop) — confirmed correct for that one dependency, "
            "but any other consumer needs to know which one has the data it wants. "
            "Needs a product decision: consolidate to one, or clearly document which "
            "consumer should use which and why."
        ),
        "files": "app/services/context_loop.py, app/modules/context_loop/service.py",
        "owner_decision_needed": "yes",
    },
]


def run_stub_detector() -> dict:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "stub_detector.py"), "app", "--out", "/tmp/_gap_report_stubs.json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    stubs_path = Path("/tmp/_gap_report_stubs.json")
    stubs = json.loads(stubs_path.read_text()) if stubs_path.exists() else []
    return {"ok": proc.returncode == 0, "stdout": proc.stdout.strip(), "stubs": stubs}


def run_guardrail_engine() -> dict:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "guardrail_engine.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return {"ok": proc.returncode == 0, "output": proc.stdout.strip() or proc.stderr.strip()}


def read_module_registry_flags() -> list[dict]:
    registry_path = REPO_ROOT / "tools" / "module_registry.yaml"
    if not registry_path.exists():
        return []
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or []
    entries = data if isinstance(data, list) else data.get("modules", [])
    flagged = []
    for entry in entries:
        if entry.get("flag_reason") or entry.get("status") not in ("ok", None):
            flagged.append(
                {
                    "id": entry.get("id"),
                    "display_name": entry.get("display_name"),
                    "status": entry.get("status"),
                    "flag_reason": entry.get("flag_reason"),
                }
            )
    return flagged


def _register_py_has_function_group_contract(package: str) -> bool:
    """True if <package>/register.py exists and actually calls register_function_group().

    Some modules have a register.py that does something else entirely (a
    ModuleEntry declaration, a plain `register_x(app)` router-mount helper,
    etc.) — those aren't contract gaps, just a naming coincidence. Only a
    register.py that genuinely registers a FunctionGroupContract counts.
    """
    parts = package.split(".")
    register_path = REPO_ROOT.joinpath(*parts, "register.py")
    if not register_path.exists():
        return False
    try:
        text = register_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "register_function_group(" in text


def find_missing_contracts() -> list[str]:
    """Modules with a real FunctionGroupContract-bearing register.py that
    contract_loader.py never imports (so it never reaches the live registry).
    """
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from app.core.contract_loader import _MODULES_WITH_CONTRACTS
        from app.core.product_manifest import MANIFEST
    except Exception as e:  # pragma: no cover - diagnostic path only
        return [f"<could not import manifest: {e}>"]

    contract_packages = {".".join(m.split(".")[:3]) for m in _MODULES_WITH_CONTRACTS}
    missing = []
    seen_packages: set[str] = set()
    for entry in MANIFEST.all():
        package = ".".join(entry.module_path.split(".")[:3])
        if package in contract_packages or package in seen_packages:
            continue
        seen_packages.add(package)
        if _register_py_has_function_group_contract(package):
            missing.append(package)
    return sorted(missing)


def render_report(stub_result: dict, guardrail_result: dict, flagged_modules: list[dict], missing_contracts: list[str]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Semptify Gap Report",
        "",
        f"Generated {now} by `tools/gap_report.py`. Regenerate anytime — this file is a "
        "snapshot, not a source of truth. The source of truth is the tools it runs.",
        "",
        "## 1. Architectural gaps (require product/owner judgment)",
        "",
    ]
    for gap in KNOWN_ARCHITECTURAL_GAPS:
        lines += [
            f"### [{gap['severity']}] {gap['title']}",
            "",
            gap["detail"],
            "",
            f"- Files: `{gap['files']}`",
            f"- Owner decision needed: {gap['owner_decision_needed']}",
            "",
        ]

    lines += ["## 2. Automated stub scan (`tools/stub_detector.py`)", ""]
    if stub_result["stubs"]:
        lines.append(f"**{len(stub_result['stubs'])} genuine stub(s) found:**")
        lines.append("")
        for s in stub_result["stubs"]:
            lines.append(f"- `{s['file']}:{s['line']}` — `{s['function']}` — {s['reason']}")
    else:
        lines.append("None found. (AST-verified — this is real, not a grep guess.)")
    lines.append("")

    lines += ["## 3. Guardrail Engine (`tools/guardrail_engine.py`)", ""]
    lines.append("```")
    lines.append(guardrail_result["output"])
    lines.append("```")
    lines.append("")

    lines += ["## 4. Flagged modules (`tools/module_registry.yaml`)", ""]
    if flagged_modules:
        lines.append("| Module | Status | Reason |")
        lines.append("| --- | --- | --- |")
        for m in flagged_modules:
            lines.append(f"| {m['display_name']} (`{m['id']}`) | {m['status']} | {m['flag_reason'] or '—'} |")
    else:
        lines.append("None flagged.")
    lines.append("")

    lines += ["## 5. Real FunctionGroupContract gaps (register.py exists, never loaded)", ""]
    new_gaps = [m for m in missing_contracts if m not in KNOWN_INTENTIONAL_CONTRACT_EXCLUSIONS]
    known_gaps = [m for m in missing_contracts if m in KNOWN_INTENTIONAL_CONTRACT_EXCLUSIONS]
    lines.append(
        "These packages have a `register.py` that genuinely calls "
        "`register_function_group()`, but it is not in `app/core/contract_loader.py`'s "
        "`_MODULES_WITH_CONTRACTS` tuple — so the contract exists in code but never "
        "reaches the live registry at runtime. This is a real gap, not a false positive "
        "(a `register.py` that does something else, like a `ModuleEntry` declaration or "
        "a plain router-mount helper, is not counted here)."
    )
    lines.append("")
    if new_gaps:
        lines.append("**New / unaddressed:**")
        for m in new_gaps:
            lines.append(f"- `{m}`")
    else:
        lines.append("None new.")
    if known_gaps:
        lines.append("")
        lines.append("**Already decided / intentionally excluded (not new work):**")
        for m in known_gaps:
            lines.append(f"- `{m}` — {KNOWN_INTENTIONAL_CONTRACT_EXCLUSIONS[m]}")
    lines.append("")

    lines += [
        "## How to act on this report",
        "",
        "1. Claim a gap in the task tracker before touching it: "
        "`python tools/mark_task_status.py <task_id> in_progress --agent <agent-id>`.",
        "2. Fix the root cause, not a downstream symptom (see AGENTS.md Known Failure Registry).",
        "3. Re-run `python tools/guardrail_engine.py` and the relevant `pytest tests/module_health` "
        "subset before marking anything resolved.",
        "4. Regenerate this report (`python tools/gap_report.py`) so the next session sees current state.",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="GAPS.md")
    args = parser.parse_args()

    print("Running stub_detector.py ...")
    stub_result = run_stub_detector()
    print("Running guardrail_engine.py ...")
    guardrail_result = run_guardrail_engine()
    print("Reading module_registry.yaml flags ...")
    flagged_modules = read_module_registry_flags()
    print("Checking FunctionGroupContract coverage ...")
    missing_contracts = find_missing_contracts()

    report = render_report(stub_result, guardrail_result, flagged_modules, missing_contracts)
    out_path = REPO_ROOT / args.out
    out_path.write_text(report, encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
