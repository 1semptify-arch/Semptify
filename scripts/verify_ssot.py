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
import sys
import subprocess
from pathlib import Path

def main():
    print("Running SSOT Architecture Verification...\n")
    
    # Run the pytest-based audit
    result = subprocess.run(  # noqa: S603 # nosec B603
        [sys.executable, "-m", "pytest", "tests/test_ssot_architecture.py", "-v", "--tb=short"],
        capture_output=False,
        text=True,
    )
    
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
