"""
guardrail_engine.py
--------------------
Single entry point for ALL pre-commit guardrail checks.

Instead of running stub_detector.py, sync_orchestrator.py, manifest checks,
etc. as separate scattered scripts, this engine discovers every check in
tools/checks/, runs them all, and produces ONE pass/fail report.

Each check is a plugin: a .py file in tools/checks/ that defines a
run() function returning a CheckResult.

Add a new guardrail = drop a new file in tools/checks/. Nothing else
needs to change.

Wire into .pre-commit-config.yaml as the ONLY local hook (replace
individual script hooks with a call to this file).

Exit code 0 = all checks passed. Exit code 1 = at least one check failed
(blocks the commit, same as your existing hooks do today).
"""

import importlib.util
import logging
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = Path(__file__).resolve().parent / "checks"
BUILD_STATE_PATH = REPO_ROOT / "BUILD_STATE.md"


@dataclass
class CheckResult:
    name: str
    passed: bool
    summary: str
    details: str = ""


@dataclass
class EngineReport:
    results: list = field(default_factory=list)
    started_at: str = ""
    duration_seconds: float = 0.0

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


def discover_checks():
    """Find every check plugin in tools/checks/. A plugin is any .py file
    that is not __init__.py or _template.py, and defines a run() function."""
    if not CHECKS_DIR.exists():
        return []

    check_modules = []
    for path in sorted(CHECKS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"guardrail_check_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            # A broken check plugin should be reported as a failed check,
            # not crash the whole engine.
            check_modules.append((path.stem, None, traceback.format_exc()))
            continue
        if hasattr(module, "run"):
            check_modules.append((path.stem, module, None))
    return check_modules


def run_all_checks() -> EngineReport:
    report = EngineReport(started_at=datetime.now(UTC).isoformat(timespec="seconds"))
    start = time.time()

    checks = discover_checks()
    if not checks:
        report.results.append(
            CheckResult(
                name="engine",
                passed=False,
                summary="No check plugins found in tools/checks/. Nothing was verified.",
            )
        )
        report.duration_seconds = time.time() - start
        return report

    for name, module, load_error in checks:
        if load_error is not None:
            report.results.append(
                CheckResult(
                    name=name,
                    passed=False,
                    summary="Check plugin failed to load (bug in the check itself).",
                    details=load_error,
                )
            )
            continue

        try:
            result = module.run(repo_root=REPO_ROOT)
            # Duck-type instead of isinstance: each check plugin imports its
            # own copy of CheckResult (separate module load), so isinstance
            # would incorrectly fail even for a valid CheckResult.
            if hasattr(result, "passed") and hasattr(result, "summary"):
                result = CheckResult(
                    name=getattr(result, "name", None) or name,
                    passed=result.passed,
                    summary=result.summary,
                    details=getattr(result, "details", ""),
                )
            else:
                # Be forgiving: allow a plugin to return (bool, str) instead.
                passed, summary = result
                result = CheckResult(name=name, passed=passed, summary=summary)
            report.results.append(result)
        except Exception:
            report.results.append(
                CheckResult(
                    name=name,
                    passed=False,
                    summary="Check crashed while running.",
                    details=traceback.format_exc(),
                )
            )

    report.duration_seconds = time.time() - start
    return report


def format_console_report(report: EngineReport) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("GUARDRAIL ENGINE REPORT")
    lines.append("=" * 60)
    for r in report.results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"[{status}] {r.name}: {r.summary}")
        if not r.passed and r.details:
            lines.append("  --- details ---")
            for line in r.details.strip().splitlines():
                lines.append(f"  {line}")
    lines.append("-" * 60)
    overall = "ALL CHECKS PASSED" if report.all_passed else "ONE OR MORE CHECKS FAILED"
    lines.append(f"{overall}  ({report.duration_seconds:.2f}s)")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_build_state_entry(report: EngineReport) -> str:
    """Formats a short entry matching the existing BUILD_STATE.md session-log
    style, so this can be appended automatically instead of hand-written."""
    lines = []
    lines.append(f"\n### Guardrail Engine Run — {report.started_at}\n")
    for r in report.results:
        mark = "PASS" if r.passed else "FAIL"
        lines.append(f"- **{r.name}**: {mark} — {r.summary}")
    overall = "All checks passed." if report.all_passed else "One or more checks failed — see console output."
    lines.append(f"\n{overall}\n")
    return "\n".join(lines)


def _entry_signature(entry: str) -> str:
    """Strip the timestamp line so two entries with the same pass/fail
    results but different timestamps compare equal. The timestamp is
    the only non-substantive part of the entry."""
    lines = entry.splitlines()
    return "\n".join(line for line in lines if not line.strip().startswith("### Guardrail Engine Run —")).strip()


def append_to_build_state(report: EngineReport):
    """Best-effort append. Never blocks the commit if BUILD_STATE.md is
    missing or unwritable — logging is a nice-to-have, not a gate.

    Idempotency: pre-commit auto-stages hook modifications and retries the
    commit, which re-runs this hook. If we always insert a fresh timestamped
    entry, the file changes every run → pre-commit never converges → infinite
    loop. Skip the write when the top entry's substantive content (everything
    except the timestamp line) already matches what we'd write. This makes
    retry a no-op so the commit can succeed.
    """
    try:
        entry = format_build_state_entry(report)
        if BUILD_STATE_PATH.exists():
            existing = BUILD_STATE_PATH.read_text(encoding="utf-8")
            # Insert right after the first line (the file header/instruction line)
            # so newest entries stay at the top, matching existing convention.
            first_newline = existing.find("\n")
            if first_newline == -1:
                new_content = existing + entry
            else:
                new_content = existing[: first_newline + 1] + entry + existing[first_newline + 1 :]

            # Idempotency guard: if the top entry's substantive content already
            # matches what we'd write, skip the write so pre-commit's retry sees
            # no diff and can converge. Only the timestamp line varies between
            # runs; everything else (check names, pass/fail, summaries) is stable
            # for the same commit being retried.
            body_after_header = existing[first_newline + 1 :] if first_newline != -1 else ""
            if body_after_header.lstrip().startswith("### Guardrail Engine Run —"):
                rest = body_after_header.lstrip()
                # Find the end of the top entry (next "### " heading or "---" separator).
                next_heading_pos = rest.find("\n### ", 1)
                separator_pos = rest.find("\n---", 1)
                end_positions = [p for p in (next_heading_pos, separator_pos) if p != -1]
                top_entry_end = min(end_positions) + 1 if end_positions else len(rest)
                top_entry = rest[:top_entry_end]
                if _entry_signature(top_entry) == _entry_signature(entry):
                    return  # Already logged; no diff → pre-commit can converge.

            BUILD_STATE_PATH.write_text(new_content, encoding="utf-8")
        # If BUILD_STATE.md doesn't exist, silently skip — don't create
        # surprise files during a commit hook.
    except Exception:
        # Never let logging failures block a commit, but surface them for debugging.
        logger.debug("append_to_build_state failed", exc_info=True)


def main():
    report = run_all_checks()
    print(format_console_report(report))
    append_to_build_state(report)
    sys.exit(0 if report.all_passed else 1)


if __name__ == "__main__":
    main()
