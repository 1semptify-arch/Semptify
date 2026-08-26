#!/usr/bin/env python3
"""
Semptify — AI Context Compiler
Bundles the real canonical project docs into one paste-ready handoff file,
so switching between Gemini / MSN Copilot / a fresh Windsurf session doesn't
require manually re-gathering context each time.

Save at: scripts/compile_ai_context.py
Run before any handoff:  python scripts/compile_ai_context.py
Output: AI_HANDOFF_PACKET.md (in the project root)
"""

import os
import shutil
import subprocess

from app.core.utc import utc_now

OUTPUT_FILE = "AI_HANDOFF_PACKET.md"

# These are the REAL canonical files for this project — update paths here
# if any of these move or get renamed. Keep this list in sync with what
# actually exists; an outdated list here silently produces a stale packet.
TARGET_DOCS = [
    "Semptify_AI_Orchestration_Blueprint.md",
    "docs/admin/Semptify_Site_GUI_Framework.md",
    ".devin/skills/preflight/SKILL.md",
    "ACTIVE_CONTEXT.md",
    "BUILD_STATE.md",
]

# The inventory workbook is Excel, not text — can't inline it directly.
# Just remind whoever reads the packet that it exists and where.
WORKBOOK_NOTE = (
    "Note: Semptify_Master_Inventory_LIVE.xlsx also exists at the project "
    "root — it's the live module/task tracking workbook. Not inlined here "
    "since it's a spreadsheet, not text. Reference it by name if the "
    "session needs current module status or the Task Queue."
)


def get_git_commit():
    """Get the current commit hash, or a clear placeholder if not in a repo."""
    git_path = shutil.which("git")
    if git_path is None:
        return "NO_GIT_REPOSITORY_DETECTED"
    try:
        return (
            subprocess.check_output([git_path, "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        )
    except Exception:
        return "NO_GIT_REPOSITORY_DETECTED"


def compile_handoff_packet():
    commit_hash = get_git_commit()
    timestamp = utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("# SEMPTIFY — AI HANDOFF PACKET\n")
        out.write(f"**Generated:** {timestamp} | **Git commit at generation:** `{commit_hash}`\n\n")
        out.write(
            "**Instructions for the AI reading this:** this packet bundles the "
            "current, real state of the Semptify project. Read it fully before "
            "proposing or making any change. Do not assume file names or "
            "structures beyond what's shown here.\n\n---\n\n"
        )
        out.write(f"## Reference note\n{WORKBOOK_NOTE}\n\n---\n\n")

        for doc_path in TARGET_DOCS:
            out.write(f"## SOURCE FILE: {doc_path}\n\n")
            if os.path.exists(doc_path):
                with open(doc_path, encoding="utf-8") as f:
                    out.write(f.read())
                print(f"  merged: {doc_path}")
            else:
                out.write("*(File not found at this path — skipped. Check the path is current.)*\n")
                print(f"  SKIPPED (not found): {doc_path}")
            out.write("\n\n---\n\n")

    print(f"\nDone. Packet written to: {OUTPUT_FILE}")
    print("Copy its full contents into Gemini, MSN Copilot, or a fresh session to sync context.")


if __name__ == "__main__":
    compile_handoff_packet()
