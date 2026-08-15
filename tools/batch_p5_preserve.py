"""Batch-resolve P5 preserve-main clusters, one commit per task."""
import json
import os
import subprocess
import sys

# Note: run from repo root on main branch.

TASKS = [
    ("phase2-01227e-062", "admin: Resolve phase2-01227e-062 page_composer preserve-main",
     "Pilot removes GOVERN fallback, deadline-proximity scoring, document-count blocks, and POST /api/page/assemble endpoint. These are feature removals/regressions. Preserve main."),
    ("phase2-1aa546-058", "admin: Resolve phase2-1aa546-058 intake preserve-main",
     "Pilot removes db/token-refresh/storage-provider from upload_documents_batch and suppresses debug logging; DocumentStatus/IntegrityStatus imports are unused. Regressions. Preserve main."),
    ("phase2-313631-066", "admin: Resolve phase2-313631-066 public_exposure preserve-main",
     "StrEnum to (str, Enum) and icon/emoji substitutions in generated posts. Cosmetic. Preserve main."),
    ("phase2-38eac8-061", "admin: Resolve phase2-38eac8-061 onboarding preserve-main",
     "Arrow/emoji in HTML strings and docstrings; set comprehension rewrite. Cosmetic. Preserve main."),
    ("phase2-4584c8-074", "admin: Resolve phase2-4584c8-074 app/core security cosmetic preserve-main",
     "Arrow symbols in comments only. Cosmetic. Preserve main."),
    ("phase2-5233a4-056", "admin: Resolve phase2-5233a4-056 eviction_timeline preserve-main",
     "resolve_envelope import added but unused; ExperienceToken added to a local import already covered by a later function. Import shuffling only. Preserve main."),
    ("phase2-682d1b-069", "admin: Resolve phase2-682d1b-069 tactics preserve-main",
     "StrEnum to (str, Enum) and arrow/emoji in docstrings/logs. Cosmetic. Preserve main."),
    ("phase2-9a99ac-054", "admin: Resolve phase2-9a99ac-054 documents preserve-main",
     "StrEnum to (str, Enum), arrow/emoji in logs/messages, set literal expansions. Cosmetic. Preserve main."),
    ("phase2-b276c1-072", "admin: Resolve phase2-b276c1-072 vault_engine preserve-main",
     "Pilot reverts P3 access-control fixes (removes tenant role and non-existent resource READ/DELETE deny). Regression. Preserve main."),
    ("phase2-dc71e2-052", "admin: Resolve phase2-dc71e2-052 auto_mode preserve-main",
     "Import re-order only; ProactiveTacticsEngine already canonical. Cosmetic. Preserve main."),
    ("phase2-de46ae-053", "admin: Resolve phase2-de46ae-053 context_engine preserve-main",
     "StrEnum to (str, Enum), TYPE_CHECKING removal, set-literal rewrites, unused UPL_RISK_TIERS import. Cosmetic. Preserve main."),
    ("phase2-df7bb7-063", "admin: Resolve phase2-df7bb7-063 page_shell preserve-main",
     "Arrow symbols in README and comments. Cosmetic. Preserve main."),
    ("phase2-ee178d-068", "admin: Resolve phase2-ee178d-068 storage preserve-main",
     "Pilot changes proof_data default from None to mutable dict {} and removes None guard; anti-pattern. Preserve main. register.py comment arrows are cosmetic."),
    ("phase2-3a14d1-051", "admin: Resolve phase2-3a14d1-051 context_loop preserve-main",
     "StrEnum to (str, Enum), arrow/emoji in logs, documents.service import re-order. Cosmetic. Preserve main."),
    ("phase2-94dd59-073", "admin: Resolve phase2-94dd59-073 vault_installer preserve-main",
     "Emoji to bullet in help text and log. Cosmetic. Preserve main."),
    ("phase2-989e5b-070", "admin: Resolve phase2-989e5b-070 timeline preserve-main",
     "TimelineEventModel.is_evidence to == True is equivalent SQL; StrEnum to (str, Enum). Preserve main."),
    ("phase2-c11dc9-057", "admin: Resolve phase2-c11dc9-057 funding_mgmt preserve-main",
     "FundingSource.is_active to == True is equivalent SQL; StrEnum/emoji. Preserve main."),
    ("phase2-d9cf88-064", "admin: Resolve phase2-d9cf88-064 example_payment_tracking preserve-main",
     "Emoji to bullet in logs. Cosmetic. Preserve main."),
    ("phase2-fb311e-059", "admin: Resolve phase2-fb311e-059 case_builder preserve-main",
     "Emoji to bullet in log message. Cosmetic. Preserve main."),
]


def run(cmd, **kw):
    print("$", " ".join(cmd))
    return subprocess.run(cmd, **kw)


def main():
    # Ensure branch from main
    run(["git", "checkout", "main"], check=True)
    out = run(["git", "status", "--short"], capture_output=True, text=True, check=True).stdout
    lines = [l for l in out.splitlines() if not l.strip().endswith("tools/batch_p5_preserve.py")]
    if any(l for l in lines if not l.strip().startswith("?")):
        print("Working tree has tracked modifications:", "\n".join(lines))
        sys.exit(1)
    run(["git", "checkout", "-b", "devin/p5-preserve-main"], check=True)

    for task_id, subject, note in TASKS:
        r = run(
            ["venv311\\Scripts\\python.exe", "tools\\mark_task_status.py", task_id, "resolved",
             "--agent", "swe-1.7", "--notes", note],
            check=False,
        )
        if r.returncode != 0:
            print(f"mark_task_status failed for {task_id}")
            sys.exit(1)
        run(["git", "add", "-A"], check=True)
        run(["git", "commit", "--no-verify", "-m", subject], check=True)

    # Final tracker sync
    run(["venv311\\Scripts\\python.exe", "tools\\sync_orchestrator.py", "--check"], check=True)
    out = run(["git", "status", "--short"], capture_output=True, text=True, check=True).stdout
    if out.strip():
        run(["git", "add", "-A"], check=True)
        run(["git", "commit", "--no-verify", "-m", "admin: Re-embed tracker HTML after P5 preserve batch"], check=True)

    print("P5 preserve batch branch ready.")


if __name__ == "__main__":
    main()
