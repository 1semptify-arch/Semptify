#!/usr/bin/env python
"""Wrapper for detect-secrets-hook that strips -w/--write args injected by pre-commit."""

import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "venv311" / "Scripts" / "detect-secrets-hook.exe"


def main() -> int:
    # Strip -w / --write flags that older pre-commit hook definitions may inject
    args = [a for a in sys.argv[1:] if a not in ("-w", "--write")]
    result = subprocess.run([str(HOOK)] + args, capture_output=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
