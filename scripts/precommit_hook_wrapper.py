#!/usr/bin/env python
"""Universal wrapper for pre-commit-hooks executables that strips the -w flag
injected by pre-commit 3.8.0 on Windows.

Usage: python scripts/precommit_hook_wrapper.py <hook_name> [args...]
Example: python scripts/precommit_hook_wrapper.py trailing-whitespace-fixer file1.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "venv311" / "Scripts"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: precommit_hook_wrapper.py <hook_name> [args...]", file=sys.stderr)
        return 2

    hook_name = sys.argv[1]
    # Strip -w / --write flags injected by pre-commit framework
    args = [a for a in sys.argv[2:] if a not in ("-w", "--write")]

    exe = SCRIPTS / f"{hook_name}.exe"
    if not exe.exists():
        print(f"Hook not found: {exe}", file=sys.stderr)
        return 2

    result = subprocess.run([str(exe)] + args, capture_output=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
