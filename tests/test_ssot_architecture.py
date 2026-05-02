"""
SSOT Architecture Tests — CI/CD enforcement of Single Source of Truth.

Run these in CI to block SSOT violations:
    pytest tests/test_ssot_architecture.py -v

These tests are the "immune system" against architectural drift.
"""
import re
import ast
from pathlib import Path
from typing import List, Tuple, Set

import pytest


PROJECT_ROOT = Path(__file__).parent.parent
APP_DIR = PROJECT_ROOT / "app"
STATIC_DIR = PROJECT_ROOT / "static"


class SSOTViolation(Exception):
    """Test failure for SSOT violations."""
    pass


# =============================================================================
# Forbidden Patterns — These indicate SSOT bypass attempts
# =============================================================================

FORBIDDEN_PATTERNS: List[Tuple[str, str]] = [
    # Python: Hardcoded redirect URLs
    (
        r'RedirectResponse\s*\(\s*url\s*=\s*["\']/(?!api|docs|openapi)[a-zA-Z0-9/_-]+\.html?["\']',
        "Hardcoded URL in RedirectResponse - use navigation registry"
    ),
    
    # Python: Direct path strings in routes
    (
        r'["\']/(?!api|docs|openapi|health|static)[a-zA-Z0-9/_-]+\.html["\']',
        "Hardcoded path string - use navigation.get_stage()"
    ),
    
    # JS/HTML: Inline hardcoded navigation
    (
        r'window\.location\.href\s*=\s*["\'][^"\']+["\']',
        "Hardcoded window.location - use SSOT API fetch"
    ),
    
    # JS/HTML: Direct href to onboarding pages
    (
        r'href\s*=\s*["\']/onboarding-assets/[^"\']+["\']',
        "Hardcoded onboarding-assets path - use SSOT navigation"
    ),
    
    # Python: Import bypass (files that should use navigation but don't)
    (
        r'^(?!.*navigation).*(?:redirect|url|path).*(?:onboarding|storage)',
        "Navigation-related code missing navigation import - likely SSOT bypass"
    ),
]


# Files exempt from certain checks (documented exceptions)
EXEMPT_FILES: Set[str] = {
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
        from app.core.navigation import navigation, NavigationRegistry
        
        # Must have onboarding flow defined
        assert hasattr(navigation, 'ONBOARDING_FLOW')
        assert len(navigation.ONBOARDING_FLOW) > 0
        
        # Must have main navigation
        assert hasattr(navigation, 'MAIN_NAV')
        
        # Must provide canonical entry points
        assert navigation.get_onboarding_start() == "/onboarding/start"
        assert navigation.get_reconnect_flow() == "/storage/reconnect"
        
        # Must export to dict for API consumption
        nav_dict = navigation.to_dict()
        assert 'onboarding_flow' in nav_dict
        assert 'main_nav' in nav_dict
        assert 'entry_points' in nav_dict
        
    except ImportError as e:
        raise SSOTViolation(f"Navigation registry not importable: {e}")


def test_no_hardcoded_urls_in_routers():
    """Scan all router files for hardcoded URL strings."""
    violations = []
    
    router_files = list((APP_DIR / "routers").rglob("*.py"))
    
    for file_path in router_files:
        relative_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        
        if relative_path in EXEMPT_FILES:
            continue
            
        content = file_path.read_text(encoding='utf-8')
        
        # Check for RedirectResponse with hardcoded URLs (excluding navigation import)
        if 'RedirectResponse' in content and 'url=' in content:
            # Find all RedirectResponse calls
            matches = re.finditer(
                r'RedirectResponse\s*\(\s*url\s*=\s*["\']([^"\']+)["\']',
                content
            )
            for match in matches:
                url = match.group(1)
                # Allow SSOT registry usage patterns
                if not any(pattern in url for pattern in [
                    'navigation.get',
                    'get_stage',
                    'get_onboarding',
                    'get_reconnect'
                ]):
                    # Check if it's a hardcoded path
                    if url.startswith('/') and not url.startswith('/api/'):
                        line_num = content[:match.start()].count('\n') + 1
                        violations.append(
                            f"{relative_path}:{line_num} - Hardcoded redirect URL: '{url}'"
                        )
    
    if violations:
        raise SSOTViolation(
            f"SSOT violations found in routers:\n" + "\n".join(violations)
        )


def test_no_hardcoded_navigation_in_static_files():
    """Scan static HTML/JS files for hardcoded navigation URLs."""
    violations = []
    
    html_files = list(STATIC_DIR.rglob("*.html"))
    js_files = list(STATIC_DIR.rglob("*.js"))
    
    for file_path in html_files + js_files:
        relative_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        
        if relative_path in EXEMPT_FILES:
            continue
            
        content = file_path.read_text(encoding='utf-8')
        
        # Check for window.location with hardcoded paths (not using SSOT)
        matches = re.finditer(
            r'window\.location\.href\s*=\s*["\'](/onboarding-assets/[^"\']+)["\']',
            content
        )
        for match in matches:
            url = match.group(1)
            # Allow if it's using the SSOT fetch pattern
            if 'ssot_navigation' not in content and 'loadNavigation' not in content:
                line_num = content[:match.start()].count('\n') + 1
                violations.append(
                    f"{relative_path}:{line_num} - Hardcoded navigation: '{url}' (not using SSOT API)"
                )
    
    if violations:
        raise SSOTViolation(
            f"SSOT violations in static files:\n" + "\n".join(violations)
        )


def test_middleware_uses_ssot_navigation():
    """Verify middleware imports and uses navigation registry."""
    middleware_dir = APP_DIR / "core"
    violations = []
    
    for file_path in middleware_dir.rglob("*_middleware.py"):
        relative_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        
        if relative_path in EXEMPT_FILES:
            continue
            
        content = file_path.read_text(encoding='utf-8')
        
        # Check if it has redirect logic
        if 'RedirectResponse' in content:
            # Must import navigation
            if 'from app.core.navigation' not in content and 'import navigation' not in content:
                violations.append(
                    f"{relative_path} - Middleware with redirects missing navigation import"
                )
            
            # Must use navigation methods (not hardcoded paths to onboarding)
            if '/onboarding/' in content or '/storage/' in content:
                if 'navigation.get' not in content:
                    violations.append(
                        f"{relative_path} - Hardcoded onboarding/storage path in middleware"
                    )
    
    if violations:
        raise SSOTViolation(
            f"SSOT violations in middleware:\n" + "\n".join(violations)
        )


def test_ssot_api_endpoint_exists():
    """Verify the SSOT navigation API endpoint is registered."""
    try:
        from app.routers.onboarding import router
        
        # Check routes for ssot-navigation endpoint
        routes = [route.path for route in router.routes]
        
        assert "/ssot-navigation" in routes, \
            "SSOT navigation API endpoint /ssot-navigation not found in onboarding router"
            
    except ImportError as e:
        raise SSOTViolation(f"Cannot verify SSOT endpoint: {e}")


# =============================================================================
# CI/CD Integration Helpers
# =============================================================================

def run_ssot_audit() -> List[str]:
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
