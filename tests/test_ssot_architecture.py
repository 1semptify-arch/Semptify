"""
SSOT Architecture Tests — CI/CD enforcement of Single Source of Truth.

Run these in CI to block SSOT violations:
    pytest tests/test_ssot_architecture.py -v

These tests are the "immune system" against architectural drift.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.core_gate

PROJECT_ROOT = Path(__file__).parent.parent
APP_DIR = PROJECT_ROOT / "app"
STATIC_DIR = PROJECT_ROOT / "static"


class SSOTViolation(Exception):
    """Test failure for SSOT violations."""

    pass


# =============================================================================
# Forbidden Patterns — These indicate SSOT bypass attempts
# =============================================================================

FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    # Python: Hardcoded redirect URLs
    (
        r'RedirectResponse\s*\(\s*url\s*=\s*["\']/(?!api|docs|openapi)[a-zA-Z0-9/_-]+\.html?["\']',
        "Hardcoded URL in RedirectResponse - use navigation registry",
    ),
    # Python: Direct path strings in routes
    (
        r'["\']/(?!api|docs|openapi|health|static)[a-zA-Z0-9/_-]+\.html["\']',
        "Hardcoded path string - use navigation.get_stage()",
    ),
    # JS/HTML: Inline hardcoded navigation
    (r'window\.location\.href\s*=\s*["\'][^"\']+["\']', "Hardcoded window.location - use SSOT API fetch"),
    # JS/HTML: Direct href to onboarding pages
    (r'href\s*=\s*["\']/onboarding-assets/[^"\']+["\']', "Hardcoded onboarding-assets path - use SSOT navigation"),
    # Python: Import bypass (files that should use navigation but don't)
    (
        r"^(?!.*navigation).*(?:redirect|url|path).*(?:onboarding|storage)",
        "Navigation-related code missing navigation import - likely SSOT bypass",
    ),
]


# Files exempt from certain checks (documented exceptions)
EXEMPT_FILES: set[str] = {
    # Core SSOT infrastructure is exempt from self-referential checks
    "app/core/navigation.py",
    "app/core/ssot_guard.py",
    "tests/test_ssot_architecture.py",
}


# =============================================================================
# Test Cases
# =============================================================================


def test_navigation_registry_exists():
    """Verify SSOT registry is importable and functional."""
    try:
        from app.core.navigation import navigation

        # Must have onboarding flow defined
        assert hasattr(navigation, "ONBOARDING_FLOW")
        assert len(navigation.ONBOARDING_FLOW) > 0

        # Must have main navigation
        assert hasattr(navigation, "MAIN_NAV")

        # Must provide canonical entry points
        assert navigation.get_onboarding_start() == "/preamble"
        assert navigation.get_reconnect_flow() == "/storage/reconnect"

        # Must export to dict for API consumption
        nav_dict = navigation.to_dict()
        assert "onboarding_flow" in nav_dict
        assert "main_nav" in nav_dict
        assert "entry_points" in nav_dict

    except ImportError as e:
        raise SSOTViolation(f"Navigation registry not importable: {e}")


def test_no_hardcoded_urls_in_routers():
    """Scan all router files for hardcoded URL strings.

    Covers app/main.py, app/routers/, and app/modules/*/router.py — the
    actual locations where Semptify routes are registered. The deprecated
    app/routers/ dir is kept for historical coverage; new code lives in
    app/modules/.
    """
    violations = []

    # Scan targets: deprecated app/routers/, app/main.py, and all module routers.
    scan_files: list[Path] = []
    scan_files.extend((APP_DIR / "routers").rglob("*.py"))
    main_py = APP_DIR / "main.py"
    if main_py.exists():
        scan_files.append(main_py)
    scan_files.extend((APP_DIR / "modules").rglob("*.py"))

    for file_path in scan_files:
        relative_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

        if relative_path in EXEMPT_FILES:
            continue

        content = file_path.read_text(encoding="utf-8")

        # Check for RedirectResponse with hardcoded URLs (excluding navigation import)
        if "RedirectResponse" in content and "url=" in content:
            # Find all RedirectResponse calls
            matches = re.finditer(r'RedirectResponse\s*\(\s*url\s*=\s*["\']([^"\']+)["\']', content)
            for match in matches:
                url = match.group(1)
                # Allow SSOT registry usage patterns
                if (
                    not any(
                        pattern in url for pattern in ["navigation.get", "get_stage", "get_onboarding", "get_reconnect"]
                    )
                    and url.startswith("/")
                    and not url.startswith("/api/")
                ):
                    line_num = content[: match.start()].count("\n") + 1
                    violations.append(f"{relative_path}:{line_num} - Hardcoded redirect URL: '{url}'")

        # Catch raw RedirectResponse calls that are not external OAuth (auth_url/callback_url)
        # or the SSOT helper in app/core/ssot_guard.py (which is not scanned above).
        if "RedirectResponse(" in content:
            for match in re.finditer(r"RedirectResponse\s*\(", content):
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.start())
                if line_end == -1:
                    line_end = len(content)
                line = content[line_start:line_end]
                # External OAuth redirects are legitimate raw RedirectResponses.
                if "auth_url" in line or "callback_url" in line:
                    continue
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{relative_path}:{line_num} - Raw RedirectResponse call (use ssot_redirect)")

    if violations:
        raise SSOTViolation("SSOT violations found in routers:\n" + "\n".join(violations))


def test_no_hardcoded_navigation_in_static_files():
    """Scan static HTML/JS files for hardcoded navigation URLs."""
    violations = []

    html_files = list(STATIC_DIR.rglob("*.html"))
    js_files = list(STATIC_DIR.rglob("*.js"))

    for file_path in html_files + js_files:
        relative_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

        if relative_path in EXEMPT_FILES:
            continue

        content = file_path.read_text(encoding="utf-8")

        # Check for window.location with hardcoded paths (not using SSOT)
        matches = re.finditer(r'window\.location\.href\s*=\s*["\'](/onboarding-assets/[^"\']+)["\']', content)
        for match in matches:
            url = match.group(1)
            # Allow if it's using the SSOT fetch pattern
            if "ssot_navigation" not in content and "loadNavigation" not in content:
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{relative_path}:{line_num} - Hardcoded navigation: '{url}' (not using SSOT API)")

    if violations:
        raise SSOTViolation("SSOT violations in static files:\n" + "\n".join(violations))


def test_middleware_uses_ssot_navigation():
    """Verify middleware imports and uses navigation registry."""
    middleware_dir = APP_DIR / "core"
    violations = []

    for file_path in middleware_dir.rglob("*_middleware.py"):
        relative_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

        if relative_path in EXEMPT_FILES:
            continue

        content = file_path.read_text(encoding="utf-8")

        # Check if it has redirect logic
        if "RedirectResponse" in content:
            # Must import navigation
            if "from app.core.navigation" not in content and "import navigation" not in content:
                violations.append(f"{relative_path} - Middleware with redirects missing navigation import")

            # Must use navigation methods (not hardcoded paths to onboarding)
            if ("/onboarding/" in content or "/storage/" in content) and "navigation.get" not in content:
                violations.append(f"{relative_path} - Hardcoded onboarding/storage path in middleware")

    if violations:
        raise SSOTViolation("SSOT violations in middleware:\n" + "\n".join(violations))


def test_ssot_api_endpoint_exists():
    """Verify the SSOT navigation API endpoint is registered."""
    try:
        from app.modules.onboarding.config import OnboardingConfig
        from app.modules.onboarding.router import create_router

        config = OnboardingConfig(
            product_name="Semptify",
            allowed_roles=["tenant"],
            allowed_providers=["google_drive"],
            on_complete_redirect="/onboarding/complete",
        )
        router = create_router(config)

        # Check routes for ssot-navigation endpoint
        routes = [route.path for route in router.routes]

        assert any("ssot-navigation" in r for r in routes), f"SSOT navigation API endpoint not found. Routes: {routes}"

    except ImportError as e:
        raise SSOTViolation(f"Cannot verify SSOT endpoint: {e}")


# =============================================================================
# Tenant PII Boundary Tests
# Enforce: no PII fields written to Semptify DB for tenant users.
# Source of truth: SECURITY_AND_PRIVACY_ARCHITECTURE.md § Role-Scoped Data Privacy Policy
# =============================================================================

# Fields that must NEVER appear as DB column assignments in tenant-role code paths.
# These are the canonical forbidden PII fields on the User model and related tables.
TENANT_PII_FORBIDDEN_FIELDS = [
    "email",
    "display_name",
    "full_name",
    "first_name",
    "last_name",
    "phone",
    "phone_number",
    "address",
    "property_address",
    "home_address",
    "street_address",
]

# DB model classes that must never receive tenant PII fields.
# Expanding this list is the right way to add new models to the check.
PROTECTED_DB_MODELS = [
    "User",
    "LinkedProvider",
]

# Files that are explicitly exempt (e.g. migrations, seed scripts, test fixtures).
TENANT_PII_EXEMPT_FILES: set[str] = {
    "tests/test_ssot_architecture.py",
    "app/core/user_context.py",  # Comments only — no DB writes
    "app/models/models.py",  # Model definition — checked separately
    "SECURITY_AND_PRIVACY_ARCHITECTURE.md",
}


def test_user_model_has_no_pii_fields():
    """
    Verify the User DB model does not declare PII columns.

    The User table is the canonical tenant identity record.
    PII fields must never be added to it.
    """
    models_file = APP_DIR / "models" / "models.py"
    if not models_file.exists():
        pytest.skip("models.py not found")

    content = models_file.read_text(encoding="utf-8")

    # Find the User class block (up to the next class or end of file)
    user_class_match = re.search(r"class User\b.*?(?=\nclass |\Z)", content, re.DOTALL)
    if not user_class_match:
        pytest.skip("User class not found in models.py")

    user_class_body = user_class_match.group(0)
    violations = []

    for field in TENANT_PII_FORBIDDEN_FIELDS:
        # Match column declarations like:  email: Mapped[...] = mapped_column(...)
        pattern = rf"^\s+{re.escape(field)}\s*[:=]"
        if re.search(pattern, user_class_body, re.MULTILINE | re.IGNORECASE):
            violations.append(f"User model contains forbidden PII field: '{field}'")

    if violations:
        raise SSOTViolation(
            "TENANT PII VIOLATION — User model has PII fields:\n"
            + "\n".join(violations)
            + "\nSee SECURITY_AND_PRIVACY_ARCHITECTURE.md § Role-Scoped Data Privacy Policy"
        )


def test_no_pii_written_to_user_model_in_routers():
    """
    Scan all router and module Python files for attempts to assign PII fields
    to User model instances (e.g. user.email = ..., User(email=...)).

    This catches runtime violations — code that would write PII to the DB.
    """
    violations = []

    search_dirs = [
        APP_DIR / "routers",
        APP_DIR / "modules",
        APP_DIR / "core",
        APP_DIR / "services",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for file_path in search_dir.rglob("*.py"):
            relative_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if relative_path in TENANT_PII_EXEMPT_FILES:
                continue

            content = file_path.read_text(encoding="utf-8")

            for field in TENANT_PII_FORBIDDEN_FIELDS:
                # Pattern 1: user.email = "..." or user.email=value
                attr_assign = rf"\buser\.{re.escape(field)}\s*="
                for match in re.finditer(attr_assign, content, re.IGNORECASE):
                    line_num = content[: match.start()].count("\n") + 1
                    violations.append(
                        f"{relative_path}:{line_num} — user.{field} assigned (tenant PII must not be written to DB)"
                    )

                # Pattern 2: User(email=...) constructor kwarg
                for model in PROTECTED_DB_MODELS:
                    ctor_kwarg = rf"\b{re.escape(model)}\s*\([^)]*\b{re.escape(field)}\s*="
                    for match in re.finditer(ctor_kwarg, content, re.DOTALL | re.IGNORECASE):
                        line_num = content[: match.start()].count("\n") + 1
                        violations.append(
                            f"{relative_path}:{line_num} — {model}({field}=...) "
                            f"constructor with PII field (tenant PII must not be written to DB)"
                        )

    if violations:
        raise SSOTViolation(
            "TENANT PII VIOLATIONS — PII field assignments found:\n"
            + "\n".join(violations)
            + "\nSee SECURITY_AND_PRIVACY_ARCHITECTURE.md § Role-Scoped Data Privacy Policy"
        )


def test_create_or_update_user_no_pii():
    """
    Specifically verify the create_or_update_user function (the canonical
    user-upsert path) does not pass PII fields.
    """
    storage_router = APP_DIR / "modules" / "storage" / "router.py"
    if not storage_router.exists():
        pytest.skip("storage/router.py not found")

    content = storage_router.read_text(encoding="utf-8")

    # Find the create_or_update_user function body
    fn_match = re.search(
        r"async def create_or_update_user\b.*?(?=\nasync def |\ndef |\Z)",
        content,
        re.DOTALL,
    )
    if not fn_match:
        pytest.skip("create_or_update_user not found")

    fn_body = fn_match.group(0)
    violations = []

    # Strip triple-quoted docstrings and comment lines before checking.
    # Avoids false positives where a docstring documents what the function does NOT store
    # (e.g. 'No email, display_name, or PII is written').
    code_only = re.sub(r'""".*?"""', "", fn_body, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
    code_only = "\n".join(line for line in code_only.splitlines() if not re.match(r"^\s*#", line))

    for field in TENANT_PII_FORBIDDEN_FIELDS:
        if re.search(rf"\b{re.escape(field)}\b", code_only, re.IGNORECASE):
            violations.append(f"create_or_update_user references PII field: '{field}'")

    if violations:
        raise SSOTViolation(
            "TENANT PII VIOLATION in create_or_update_user:\n"
            + "\n".join(violations)
            + "\nThis function is the canonical user-upsert path. It must never write PII."
        )


# =============================================================================
# CI/CD Integration Helpers
# =============================================================================


def run_ssot_audit() -> list[str]:
    """
    Run full SSOT audit and return list of violations.

    Usage in CI:
        violations = run_ssot_audit()
        if violations:
            print("SSOT VIOLATIONS FOUND:")
            for v in violations:
                print(f"  - {v}")
            exit(1)
    """
    violations = []

    try:
        test_navigation_registry_exists()
    except AssertionError as e:
        violations.append(f"Registry check: {e}")

    try:
        test_no_hardcoded_urls_in_routers()
    except SSOTViolation as e:
        violations.append(str(e))

    try:
        test_no_hardcoded_navigation_in_static_files()
    except SSOTViolation as e:
        violations.append(str(e))

    try:
        test_middleware_uses_ssot_navigation()
    except SSOTViolation as e:
        violations.append(str(e))

    try:
        test_ssot_api_endpoint_exists()
    except (SSOTViolation, AssertionError) as e:
        violations.append(f"SSOT endpoint check: {e}")

    try:
        test_user_model_has_no_pii_fields()
    except SSOTViolation as e:
        violations.append(str(e))

    try:
        test_no_pii_written_to_user_model_in_routers()
    except SSOTViolation as e:
        violations.append(str(e))

    try:
        test_create_or_update_user_no_pii()
    except SSOTViolation as e:
        violations.append(str(e))

    return violations


if __name__ == "__main__":
    # Run audit directly
    print("Running SSOT Architecture Audit...")
    violations = run_ssot_audit()

    if violations:
        print("\n❌ SSOT VIOLATIONS FOUND:")
        for v in violations:
            print(f"  - {v}")
        exit(1)
    else:
        print("\n✅ All SSOT architecture tests passed!")
        exit(0)
