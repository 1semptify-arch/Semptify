#!/usr/bin/env python
"""
Semptify 5.0 - Contract Validation Script (CI Gate)

Run this script in CI or pre-commit to validate all registered page contracts.
Exit code 0 = all contracts valid.
Exit code 1 = one or more violations found.

Usage:
    python scripts/validate_contracts.py
    python scripts/validate_contracts.py --verbose
    python scripts/validate_contracts.py --page welcome
"""

import sys
import argparse

# Adjust path so imports work from project root
sys.path.insert(0, ".")

from app.core.page_contracts import PAGE_CONTRACTS, validate_all_contracts
from app.core.process_registry import PROCESS_GROUPS, ALL_GROUP_NAMES


def check_registry_integrity() -> list[str]:
    """Validate the process registry itself is internally consistent."""
    errors: list[str] = []

    seen_ids: set[int] = set()
    seen_names: set[str] = set()

    for group in PROCESS_GROUPS:
        if group.group_id in seen_ids:
            errors.append(f"Duplicate group_id: {group.group_id}")
        seen_ids.add(group.group_id)

        if group.name in seen_names:
            errors.append(f"Duplicate group name: '{group.name}'")
        seen_names.add(group.name)

        if not group.purpose:
            errors.append(f"Group '{group.name}' has no purpose defined")

        if not group.success_metrics:
            errors.append(f"Group '{group.name}' has no success_metrics defined")

    expected_ids = set(range(1, len(PROCESS_GROUPS) + 1))
    if seen_ids != expected_ids:
        errors.append(
            f"Group IDs are not sequential. Expected {sorted(expected_ids)}, got {sorted(seen_ids)}"
        )

    return errors


def check_coverage_completeness() -> list[str]:
    """
    Check that the union of all active+linked coverages touches every group.
    Warns if a group has no active coverage anywhere in the registry.
    """
    warnings: list[str] = []
    active_groups: set[str] = set()
    linked_groups: set[str] = set()

    for contract in PAGE_CONTRACTS.values():
        for group_name, coverage in contract.group_coverage.items():
            if coverage == "active":
                active_groups.add(group_name)
            elif coverage == "linked":
                linked_groups.add(group_name)

    for group_name in ALL_GROUP_NAMES:
        if group_name not in active_groups:
            warnings.append(
                f"No page has group '{group_name}' as 'active'. "
                "This group has no primary coverage in the registry."
            )

    return warnings


def run_validation(verbose: bool = False, page_filter: str = "") -> int:
    """
    Run all validations. Returns exit code (0=pass, 1=fail).
    """
    print("=" * 60)
    print("  Semptify Contract Validation")
    print(f"  Registered groups:   {len(PROCESS_GROUPS)}")
    print(f"  Registered contracts:{len(PAGE_CONTRACTS)}")
    print("=" * 60)

    total_errors = 0
    total_warnings = 0

    # 1. Registry integrity
    print("\n[1/3] Registry integrity...")
    registry_errors = check_registry_integrity()
    if registry_errors:
        total_errors += len(registry_errors)
        for e in registry_errors:
            print(f"  ERROR: {e}")
    else:
        print("  OK")

    # 2. Per-contract validation
    print("\n[2/3] Page contract validation...")
    contracts_to_check = PAGE_CONTRACTS
    if page_filter:
        if page_filter not in PAGE_CONTRACTS:
            print(f"  ERROR: Page '{page_filter}' not in registry.")
            return 1
        contracts_to_check = {page_filter: PAGE_CONTRACTS[page_filter]}

    violations = validate_all_contracts() if not page_filter else {
        page_filter: PAGE_CONTRACTS[page_filter].validate()
    }

    if violations:
        for page_id, errors in violations.items():
            print(f"\n  Contract '{page_id}':")
            for e in errors:
                print(f"    ERROR: {e}")
                total_errors += 1
    else:
        print(f"  All {len(contracts_to_check)} contract(s) passed")

    if verbose:
        print("\n  Registered contracts:")
        for page_id, contract in contracts_to_check.items():
            coverage_summary = ", ".join(
                f"{g}={v}"
                for g, v in contract.group_coverage.items()
                if v != "n-a"
            )
            print(f"    {page_id:30s} roles={len(contract.roles_supported)} | {coverage_summary}")

    # 3. Coverage completeness warnings
    print("\n[3/3] Coverage completeness...")
    coverage_warnings = check_coverage_completeness()
    if coverage_warnings:
        total_warnings += len(coverage_warnings)
        for w in coverage_warnings:
            print(f"  WARN: {w}")
    else:
        print("  All groups have active coverage")

    # Summary
    print("\n" + "=" * 60)
    if total_errors == 0:
        status = "PASS"
        print(f"  Result: {status} ({total_warnings} warning(s))")
    else:
        status = "FAIL"
        print(f"  Result: {status} ({total_errors} error(s), {total_warnings} warning(s))")
    print("=" * 60)

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Semptify page contracts")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show coverage detail per contract")
    parser.add_argument("--page", "-p", default="", help="Validate a single page by page_id")
    args = parser.parse_args()

    exit_code = run_validation(verbose=args.verbose, page_filter=args.page)
    sys.exit(exit_code)
