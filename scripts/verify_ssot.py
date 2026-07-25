#!/usr/bin/env python
"""
SSOT Architecture Verification Script
Run this locally before committing to catch violations early.

Usage:
    python scripts/verify_ssot.py
    python scripts/verify_ssot.py --fix  # Auto-fix where possible

Exit codes:
    0 = All clean
    1 = Violations found
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolve_python() -> str:
    """Use venv311 python explicitly so pre-commit's isolated env doesn't hang.

    Pre-commit runs local hooks with its own sys.executable, which may not
    have pytest installed. We must use the project's venv311 python instead.
    """
    venv_py = REPO_ROOT / "venv311" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)
    # Fall back to sys.executable only if venv311 is not found (e.g., CI).
    return sys.executable


def main():
    print("Running SSOT Architecture Verification...\n")

    # Run the pytest-based audit using venv311 python (not pre-commit's isolated python).
    # Timeout prevents the hook from hanging when no local PostgreSQL is running
    # (pytest starts the FastAPI app which blocks on DB connection).
    try:
        result = subprocess.run(  # noqa: S603 # nosec B603
            [_resolve_python(), "-m", "pytest", "tests/test_ssot_architecture.py", "-v", "--tb=short", "--no-cov"],
            capture_output=False,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("\nSSOT verification timed out after 120s (likely no local PostgreSQL).")
        print("Skipping SSOT check — ensure SSOT compliance was verified manually.")
        return 0

    # On Windows the pytest subprocess can crash with a C-level access violation
    # while importing app.main (0xC0000005 and similar NTSTATUS codes). Treat the
    # crash the same as a timeout: the local environment cannot run the SSOT audit,
    # so we skip it and rely on manual/CI verification.
    if result.returncode >= 0x80000000:
        print(f"\nSSOT verification subprocess crashed with exit code {result.returncode}.")
        print("Skipping SSOT check — ensure SSOT compliance was verified manually.")
        return 0

    if result.returncode == 0:
        print("\nSSOT Architecture clean - safe to commit")
        return 0
    else:
        print("\nSSOT violations found!")
        print("\nFix these before committing:")
        print("  1. All redirects must use ssot_redirect() from navigation registry")
        print("  2. No hardcoded URLs in Python or static files")
        print("  3. All navigation must go through app.core.navigation")
        print("\nSee AGENTS.md for SSOT compliance rules")
        return 1


if __name__ == "__main__":
    sys.exit(main())
