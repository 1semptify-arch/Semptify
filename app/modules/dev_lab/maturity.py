"""
Module Maturity Checklist — Phase 3.3

Defines the requirements for each lifecycle stage transition.
Used by dev_lab to determine if a module is ready for promotion.
"""
from typing import Dict, List


# Maturity checklist — what's required at each stage
MATURITY_CHECKLIST: Dict[str, List[str]] = {
    "dev_only": [
        "Module registered in product_manifest.py",
        "Router module exists and imports cleanly",
        "lifecycle='dev_only' set in manifest",
        "Basic health check endpoint responds",
    ],
    "experimental": [
        "Unit tests exist (tests/ directory with at least 1 test file)",
        "All unit tests pass",
        "Basic README.md with module description",
        "Works in isolation (no dependency on other dev modules)",
        "Pydantic models for all request/response bodies",
        "No bare except: blocks (specific exception types)",
        "Uses utc_now() not datetime.now()",
    ],
    "beta": [
        "Integration tests exist and pass",
        "User-facing documentation written",
        "Works with other modules (no circular dependencies)",
        "FunctionGroupContract registered in module_contracts.py",
        "Feature flag gating configured (if applicable)",
        "Error handling with logging (no silent failures)",
        "Admin can enable/disable via Module Flag Overlay UI",
    ],
    "stable": [
        "E2E tests exist and pass",
        "Admin documentation written",
        "Used by real users (dogfooded or beta-tested)",
        "Monitored for errors (telemetry hooks active)",
        "All applicable roles have access per requires_role",
        "No dev_notes or TODO markers for core functionality",
        "Performance validated under expected load",
    ],
}

# Lifecycle progression order
LIFECYCLE_ORDER: List[str] = ["dev_only", "experimental", "beta", "stable"]


def get_checklist(lifecycle: str) -> List[str]:
    """Get the maturity checklist for a lifecycle stage."""
    return MATURITY_CHECKLIST.get(lifecycle, [])


def get_next_lifecycle(current: str) -> str:
    """Get the next lifecycle stage, or empty string if already stable."""
    try:
        idx = LIFECYCLE_ORDER.index(current)
        if idx < len(LIFECYCLE_ORDER) - 1:
            return LIFECYCLE_ORDER[idx + 1]
    except ValueError:
        pass
    return ""


def can_promote(current: str, target: str) -> bool:
    """Check if promotion from current to target is valid (must be adjacent)."""
    try:
        current_idx = LIFECYCLE_ORDER.index(current)
        target_idx = LIFECYCLE_ORDER.index(target)
        return target_idx == current_idx + 1
    except ValueError:
        return False
