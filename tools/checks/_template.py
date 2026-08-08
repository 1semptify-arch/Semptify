"""
_template.py — copy this file to create a new guardrail check.

RULES FOR A CHECK PLUGIN:
1. File must live in tools/checks/ and NOT start with "_" (files starting
   with "_" are ignored by the engine — that's how this template is skipped).
2. Must define a function: run(repo_root: Path) -> CheckResult
3. Must not raise on a normal failure — return CheckResult(passed=False, ...)
   instead. Only let it raise for a genuine bug in the check itself (the
   engine will catch it and report the check as broken, not crash).
4. Keep each check doing ONE thing. If you need two things checked,
   write two files.

To rename this into a real check:
- rename the file to something like doc_drift_check.py
- rename the function stays `run`
- fill in real logic below
"""

# Import the shared CheckResult so plugins don't need to redefine it.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from guardrail_engine import CheckResult  # noqa: E402


def run(repo_root: Path) -> CheckResult:
    # Replace this with real logic. Example shape:
    #
    # problems = []
    # for f in repo_root.glob("some/pattern/*.py"):
    #     if some_condition(f):
    #         problems.append(str(f))
    #
    # if problems:
    #     return CheckResult(
    #         name="template",
    #         passed=False,
    #         summary=f"{len(problems)} issue(s) found.",
    #         details="\n".join(problems),
    #     )
    return CheckResult(name="template", passed=True, summary="Not yet implemented — template only.")
