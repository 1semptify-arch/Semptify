"""
fees_policy_check.py — guardrail for the fees-terminology policy.

Ensures that no module classified as fees_policy=exempt_advanced is reachable
by the tenant role. The exemption exists because advanced/admin/research
modules use "fee" as a domain term describing landlord conduct found in tenant
evidence (e.g. detect_repeated_fees). If an exempt module ever becomes tenant-
reachable, this guardrail fails the build until a human reclassifies it.
"""

import sys
from pathlib import Path
from typing import Any

# Guardrail plugins live in tools/checks/; app/ is two directories up.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from guardrail_engine import CheckResult  # noqa: E402


class _FakeEntry:
    """Lightweight stand-in for ModuleEntry used by unit tests."""

    def __init__(self, module_path: str, fees_policy_value: str, requires_role: tuple[str, ...] = ()):
        self.module_path = module_path
        self.fees_policy_value = fees_policy_value
        self.requires_role = requires_role

    @property
    def fees_policy(self) -> Any:
        return self

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.fees_policy_value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.fees_policy_value)

    def __repr__(self) -> str:
        return f"_FakeEntry({self.module_path!r}, {self.fees_policy_value!r}, requires_role={self.requires_role!r})"


def _is_exempt(entry: Any, fees_policy_enum: Any) -> bool:
    """Return True if entry's fees_policy is the exempt_advanced member."""
    policy = entry.fees_policy
    return policy == fees_policy_enum.EXEMPT_ADVANCED


def _is_tenant_reachable(entry: Any, tenant_modules: set[str]) -> bool:
    """Determine whether the tenant role can reach this module.

    Uses the canonical tenant capability defaults. A non-empty requires_role
    containing "tenant" is also treated as tenant-reachable.
    """
    return entry.module_path in tenant_modules or "tenant" in getattr(entry, "requires_role", ())


def check_manifest(manifest_entries: list[Any], capability_defaults: dict[str, list[str]]) -> CheckResult:
    """Validate that no exempt_advanced module is tenant-reachable.

    Accepts a list of ModuleEntry-like objects and a capability-defaults dict
    so the same logic can be unit-tested with fake entries.
    """
    import importlib

    product_manifest = importlib.import_module("app.core.product_manifest")
    FeesPolicy = product_manifest.FeesPolicy

    tenant_modules = set(capability_defaults.get("tenant", []))
    failures: list[str] = []

    for entry in manifest_entries:
        if not _is_exempt(entry, FeesPolicy):
            continue
        if _is_tenant_reachable(entry, tenant_modules):
            failures.append(
                f"{entry.module_path}: fees_policy=exempt_advanced but tenant role can reach it "
                f"(requires_role={getattr(entry, 'requires_role', ())})"
            )

    if failures:
        return CheckResult(
            name="fees_policy_check",
            passed=False,
            summary=f"{len(failures)} exempt_advanced module(s) are reachable by the tenant role.",
            details="\n".join(failures),
        )

    return CheckResult(
        name="fees_policy_check",
        passed=True,
        summary="No exempt_advanced module is reachable by the tenant role.",
    )


def run(repo_root: Path) -> CheckResult:
    """Entry point for guardrail_engine. Imports the real manifest and checks it."""
    repo_root = Path(repo_root).resolve()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from app.core.product_manifest import CAPABILITY_DEFAULTS, MANIFEST

    return check_manifest(MANIFEST.all(), CAPABILITY_DEFAULTS)
