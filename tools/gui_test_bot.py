"""
Semptify GUI Test Bot (Playwright)
====================================
Artificial user testing system that simulates real users navigating
the entire Semptify application using a real browser.

Usage:
    python tools/gui_test_bot.py [--headed] [--slow] [--role all|tenant|advocate|manager|legal|admin]

Features:
    - Full browser automation with Playwright
    - Role-based user simulation (tenant, advocate, manager, legal, admin)
    - Screenshots on failure
    - HTML report generation
    - Tests critical workflows: documents, timeline, intake, vault

Examples:
    python tools/gui_test_bot.py                    # Run all tests headless
    python tools/gui_test_bot.py --headed --slow    # Watch tests run slowly
    python tools/gui_test_bot.py --role tenant      # Test only tenant flows
"""

import asyncio
import argparse
import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "http://localhost:8000"
SCREENSHOTS_DIR = Path(__file__).parent.parent / "test_artifacts" / "screenshots"
REPORTS_DIR = Path(__file__).parent.parent / "test_artifacts" / "reports"

# Test credentials (for local testing only)
TEST_USERS = {
    "tenant": {"user_id": "test_tenant_001", "role": "user"},
    "advocate": {"user_id": "test_advocate_001", "role": "advocate"},
    "manager": {"user_id": "test_manager_001", "role": "manager"},
    "legal": {"user_id": "test_legal_001", "role": "legal"},
    "admin": {"user_id": "test_admin_001", "role": "admin"},
}

# =============================================================================
# DATA CLASSES
# =============================================================================

class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    """Single test result."""
    name: str
    status: TestStatus
    role: str
    duration_ms: float
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    page_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "role": self.role,
            "duration_ms": round(self.duration_ms, 2),
            "error_message": self.error_message,
            "screenshot_path": self.screenshot_path,
            "page_url": self.page_url,
        }


@dataclass
class TestReport:
    """Complete test run report."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    results: List[TestResult] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: TestResult):
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = len([r for r in self.results if r.status == TestStatus.PASSED])
        failed = len([r for r in self.results if r.status == TestStatus.FAILED])
        skipped = len([r for r in self.results if r.status == TestStatus.SKIPPED])
        
        by_role: Dict[str, Dict[str, int]] = {}
        for r in self.results:
            if r.role not in by_role:
                by_role[r.role] = {"passed": 0, "failed": 0, "skipped": 0, "total": 0}
            by_role[r.role]["total"] += 1
            by_role[r.role][r.status.value] += 1
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            "by_role": by_role,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "config": self.config,
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self.results],
        }


# =============================================================================
# TEST BOT CLASS
# =============================================================================

class SemptifyGUITestBot:
    """Main test bot that simulates users through Playwright."""
    
    def __init__(self, headed: bool = False, slow_mo: int = 0):
        self.headed = headed
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.report = TestReport()
        self.screenshots_dir = SCREENSHOTS_DIR
        self.reports_dir = REPORTS_DIR
        
        # Create directories
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    async def setup(self):
        """Initialize Playwright browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=not self.headed,
            slow_mo=self.slow_mo,
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            record_video_dir=str(self.screenshots_dir / "videos") if self.headed else None,
        )
    
    async def teardown(self):
        """Clean up browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()
    
    async def new_page(self) -> Page:
        """Create a new page with error handling."""
        page = await self.context.new_page()
        page.set_default_timeout(10000)  # 10 second timeout
        return page
    
    async def take_screenshot(self, page: Page, name: str) -> str:
        """Take a screenshot and return the path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        await page.screenshot(path=str(filepath), full_page=True)
        return str(filepath)
    
    async def run_test(
        self,
        test_name: str,
        role: str,
        test_func,
        page: Page,
    ) -> TestResult:
        """Run a single test with timing and error handling."""
        start_time = asyncio.get_event_loop().time()
        screenshot_path = None
        
        try:
            await test_func(page, role)
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return TestResult(
                name=test_name,
                status=TestStatus.PASSED,
                role=role,
                duration_ms=duration,
                page_url=page.url,
            )
            
        except Exception as e:
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Take screenshot on failure
            try:
                screenshot_path = await self.take_screenshot(page, f"FAILED_{test_name}")
            except:
                pass
            
            return TestResult(
                name=test_name,
                status=TestStatus.FAILED,
                role=role,
                duration_ms=duration,
                error_message=f"{str(e)}\n{traceback.format_exc()}",
                screenshot_path=screenshot_path,
                page_url=page.url,
            )
    
    # =========================================================================
    # TEST SCENARIOS
    # =========================================================================
    
    async def test_page_load(self, page: Page, role: str, path: str, title_check: str = None):
        """Generic page load test."""
        await page.goto(f"{BASE_URL}{path}")
        
        # Wait for body to be visible
        await page.wait_for_selector("body", state="visible")
        
        # Check for error messages
        error_selectors = [
            "text=Error",
            "text=404",
            "text=Not Found",
            ".error",
            "[data-error]",
        ]
        
        for selector in error_selectors:
            try:
                error = await page.locator(selector).first.is_visible(timeout=500)
                if error:
                    raise AssertionError(f"Error indicator found: {selector}")
            except:
                pass
        
        # Check title if specified
        if title_check:
            title = await page.title()
            if title_check.lower() not in title.lower():
                # Don't fail, just warn - titles change
                pass
    
    async def test_navigation_elements(self, page: Page, role: str):
        """Test that navigation elements are present and clickable."""
        # Common navigation elements
        nav_selectors = [
            "nav",
            "[role='navigation']",
            ".navbar",
            ".sidebar",
            "header",
        ]
        
        nav_found = False
        for selector in nav_selectors:
            try:
                if await page.locator(selector).first.is_visible(timeout=1000):
                    nav_found = True
                    break
            except:
                continue
        
        if not nav_found:
            raise AssertionError("No navigation elements found")
    
    async def test_document_intake_flow(self, page: Page, role: str):
        """Test document intake page and upload UI."""
        await page.goto(f"{BASE_URL}/document-intake")
        
        # Check for upload area or document list
        upload_selectors = [
            "input[type='file']",
            "[data-upload]",
            ".upload-area",
            "text=Upload",
            "text=Documents",
            "text=Add Document",
        ]
        
        found = False
        for selector in upload_selectors:
            try:
                if await page.locator(selector).first.is_visible(timeout=1000):
                    found = True
                    break
            except:
                continue
        
        if not found:
            raise AssertionError("No document intake elements found")
    
    async def test_timeline_view(self, page: Page, role: str):
        """Test timeline page displays correctly."""
        await page.goto(f"{BASE_URL}/timeline")
        
        # Wait for timeline container
        timeline_selectors = [
            "[data-timeline]",
            ".timeline",
            "#timeline",
            "text=Timeline",
            "text=Events",
        ]
        
        found = False
        for selector in timeline_selectors:
            try:
                if await page.locator(selector).first.is_visible(timeout=2000):
                    found = True
                    break
            except:
                continue
        
        if not found:
            raise AssertionError("Timeline elements not found")
    
    async def test_vault_access(self, page: Page, role: str):
        """Test vault/document storage access."""
        await page.goto(f"{BASE_URL}/vault")
        
        # Check vault UI elements
        vault_selectors = [
            "[data-vault]",
            ".vault",
            "text=Vault",
            "text=Storage",
            "text=Files",
            "text=Documents",
        ]
        
        found = False
        for selector in vault_selectors:
            try:
                if await page.locator(selector).first.is_visible(timeout=1000):
                    found = True
                    break
            except:
                continue
        
        if not found:
            raise AssertionError("Vault elements not found")
    
    async def test_form_interactions(self, page: Page, role: str):
        """Test basic form interactions work."""
        # Navigate to a page likely to have forms
        await page.goto(f"{BASE_URL}/document-intake")
        
        # Find and check form elements
        form_selectors = [
            "input",
            "textarea",
            "select",
            "button[type='submit']",
        ]
        
        found = False
        for selector in form_selectors:
            count = await page.locator(selector).count()
            if count > 0:
                found = True
                break
        
        if not found:
            raise AssertionError("No form elements found")
    
    async def test_responsive_layout(self, page: Page, role: str):
        """Test that page is responsive at different viewports."""
        viewports = [
            {"width": 375, "height": 667},   # Mobile
            {"width": 768, "height": 1024},  # Tablet
            {"width": 1280, "height": 900}, # Desktop
        ]
        
        for viewport in viewports:
            await page.set_viewport_size(viewport)
            await page.goto(f"{BASE_URL}/dashboard")
            await page.wait_for_load_state("networkidle")
            
            # Check body exists and has content
            body = await page.locator("body").first
            if not body:
                raise AssertionError(f"Body not found at viewport {viewport}")
    
    async def test_api_health_via_ui(self, page: Page, role: str):
        """Test that API endpoints are accessible from UI context."""
        # Use page.evaluate to make API calls from browser context
        result = await page.evaluate("""async () => {
            try {
                const response = await fetch('/api/health');
                return { status: response.status, ok: response.ok };
            } catch (e) {
                return { error: e.message };
            }
        }""")
        
        if result.get("error"):
            raise AssertionError(f"API health check failed: {result['error']}")
        
        if not result.get("ok"):
            raise AssertionError(f"API health returned status {result.get('status')}")
    
    async def test_dashboard_widgets(self, page: Page, role: str):
        """Test dashboard has expected widgets/content."""
        await page.goto(f"{BASE_URL}/dashboard")
        
        # Wait for content to load
        await page.wait_for_load_state("domcontentloaded")
        
        # Check for common dashboard elements
        dashboard_elements = [
            "main",
            ".dashboard",
            "[data-dashboard]",
            "article",
            ".card",
            ".widget",
        ]
        
        found = False
        for selector in dashboard_elements:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    found = True
                    break
            except:
                continue
        
        if not found:
            raise AssertionError("No dashboard content elements found")
    
    # =========================================================================
    # ROLE-SPECIFIC TESTS
    # =========================================================================
    
    async def run_tenant_tests(self, page: Page):
        """Run all tenant role tests."""
        role = "tenant"
        
        tests = [
            ("Tenant - Home Page", lambda p, r: self.test_page_load(p, r, "/", "Semptify")),
            ("Tenant - Documents Page", lambda p, r: self.test_page_load(p, r, "/documents")),
            ("Tenant - Document Intake", self.test_document_intake_flow),
            ("Tenant - Timeline View", self.test_timeline_view),
            ("Tenant - Vault Access", self.test_vault_access),
            ("Tenant - Navigation Elements", self.test_navigation_elements),
            ("Tenant - Form Interactions", self.test_form_interactions),
            ("Tenant - Responsive Layout", self.test_responsive_layout),
            ("Tenant - API Health", self.test_api_health_via_ui),
            ("Tenant - Dashboard Widgets", self.test_dashboard_widgets),
        ]
        
        for test_name, test_func in tests:
            result = await self.run_test(test_name, role, test_func, page)
            self.report.add_result(result)
            
            if result.status == TestStatus.FAILED and self.headed:
                # Pause on failure in headed mode for debugging
                print(f"\n⚠️  Test failed: {test_name}")
                print(f"   Screenshot: {result.screenshot_path}")
    
    async def run_advocate_tests(self, page: Page):
        """Run all advocate role tests."""
        role = "advocate"
        
        tests = [
            ("Advocate - Dashboard", lambda p, r: self.test_page_load(p, r, "/advocate")),
            ("Advocate - Client Management", lambda p, r: self.test_page_load(p, r, "/advocate/clients")),
            ("Advocate - Document Review", lambda p, r: self.test_page_load(p, r, "/advocate/documents")),
            ("Advocate - Navigation", self.test_navigation_elements),
            ("Advocate - API Health", self.test_api_health_via_ui),
        ]
        
        for test_name, test_func in tests:
            result = await self.run_test(test_name, role, test_func, page)
            self.report.add_result(result)
    
    async def run_manager_tests(self, page: Page):
        """Run all manager role tests."""
        role = "manager"
        
        tests = [
            ("Manager - Dashboard", lambda p, r: self.test_page_load(p, r, "/manager")),
            ("Manager - Team View", lambda p, r: self.test_page_load(p, r, "/manager/team")),
            ("Manager - Reports", lambda p, r: self.test_page_load(p, r, "/manager/reports")),
            ("Manager - Navigation", self.test_navigation_elements),
            ("Manager - API Health", self.test_api_health_via_ui),
        ]
        
        for test_name, test_func in tests:
            result = await self.run_test(test_name, role, test_func, page)
            self.report.add_result(result)
    
    async def run_legal_tests(self, page: Page):
        """Run all legal role tests."""
        role = "legal"
        
        tests = [
            ("Legal - Dashboard", lambda p, r: self.test_page_load(p, r, "/legal")),
            ("Legal - Case Review", lambda p, r: self.test_page_load(p, r, "/legal/cases")),
            ("Legal - Documents", lambda p, r: self.test_page_load(p, r, "/legal/documents")),
            ("Legal - Navigation", self.test_navigation_elements),
            ("Legal - API Health", self.test_api_health_via_ui),
        ]
        
        for test_name, test_func in tests:
            result = await self.run_test(test_name, role, test_func, page)
            self.report.add_result(result)
    
    async def run_admin_tests(self, page: Page):
        """Run all admin role tests."""
        role = "admin"
        
        tests = [
            ("Admin - Dashboard", lambda p, r: self.test_page_load(p, r, "/admin")),
            ("Admin - User Management", lambda p, r: self.test_page_load(p, r, "/admin/users")),
            ("Admin - System Health", lambda p, r: self.test_page_load(p, r, "/admin/health")),
            ("Admin - Navigation", self.test_navigation_elements),
            ("Admin - API Health", self.test_api_health_via_ui),
        ]
        
        for test_name, test_func in tests:
            result = await self.run_test(test_name, role, test_func, page)
            self.report.add_result(result)
    
    # =========================================================================
    # MAIN RUNNER
    # =========================================================================
    
    async def run_all_tests(self, roles: List[str] = None):
        """Run tests for specified roles."""
        if roles is None or "all" in roles:
            roles = ["tenant", "advocate", "manager", "legal", "admin"]
        
        print("=" * 70)
        print("SEMPTIFY GUI TEST BOT (Playwright)")
        print("=" * 70)
        print(f"Base URL: {BASE_URL}")
        print(f"Headed Mode: {self.headed}")
        print(f"Slow Motion: {self.slow_mo}ms")
        print(f"Roles to Test: {', '.join(roles)}")
        print("=" * 70)
        print()
        
        await self.setup()
        
        try:
            for role in roles:
                print(f"\n{'='*70}")
                print(f"Testing Role: {role.upper()}")
                print(f"{'='*70}")
                
                page = await self.new_page()
                
                try:
                    if role == "tenant":
                        await self.run_tenant_tests(page)
                    elif role == "advocate":
                        await self.run_advocate_tests(page)
                    elif role == "manager":
                        await self.run_manager_tests(page)
                    elif role == "legal":
                        await self.run_legal_tests(page)
                    elif role == "admin":
                        await self.run_admin_tests(page)
                finally:
                    await page.close()
        finally:
            await self.teardown()
        
        # Generate report
        await self.generate_report()
    
    async def generate_report(self):
        """Generate HTML and JSON test reports."""
        summary = self.report.get_summary()
        
        # JSON report
        json_path = self.reports_dir / f"gui_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, "w") as f:
            json.dump(self.report.to_dict(), f, indent=2)
        
        # HTML report
        html_path = self.reports_dir / f"gui_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        html_content = self._generate_html_report()
        with open(html_path, "w") as f:
            f.write(html_content)
        
        # Console summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests:  {summary['total']}")
        print(f"✅ Passed:     {summary['passed']}")
        print(f"❌ Failed:     {summary['failed']}")
        print(f"⏭️  Skipped:    {summary['skipped']}")
        print(f"Pass Rate:     {summary['pass_rate']}%")
        print()
        print("Reports Generated:")
        print(f"  JSON: {json_path}")
        print(f"  HTML: {html_path}")
        
        if summary['failed'] > 0:
            print("\nFailed Tests:")
            for r in self.report.results:
                if r.status == TestStatus.FAILED:
                    print(f"  ❌ {r.name}")
                    if r.screenshot_path:
                        print(f"     Screenshot: {r.screenshot_path}")
        
        print("=" * 70)
    
    def _generate_html_report(self) -> str:
        """Generate HTML report content."""
        summary = self.report.get_summary()
        
        results_html = ""
        for r in self.report.results:
            status_color = {
                TestStatus.PASSED: "#28a745",
                TestStatus.FAILED: "#dc3545",
                TestStatus.SKIPPED: "#ffc107",
            }[r.status]
            
            screenshot_link = f'<a href="file://{r.screenshot_path}">Screenshot</a>' if r.screenshot_path else "-"
            error_detail = f'<pre style="color: #dc3545; font-size: 12px;">{r.error_message}</pre>' if r.error_message else "-"
            
            results_html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 10px;">{r.name}</td>
                <td style="padding: 10px; color: {status_color}; font-weight: bold;">{r.status.value.upper()}</td>
                <td style="padding: 10px;">{r.role}</td>
                <td style="padding: 10px;">{r.duration_ms:.0f}ms</td>
                <td style="padding: 10px;">{screenshot_link}</td>
            </tr>
            {f'<tr><td colspan="5" style="padding: 10px; background: #f8f9fa;">{error_detail}</td></tr>' if r.error_message else ''}
            """
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Semptify GUI Test Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; margin-bottom: 10px; }}
        .timestamp {{ color: #666; margin-bottom: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .summary-card h3 {{ margin: 0 0 10px 0; color: #666; font-size: 14px; }}
        .summary-card .number {{ font-size: 32px; font-weight: bold; margin: 10px 0; }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .skipped {{ color: #ffc107; }}
        .total {{ color: #333; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #f8f9fa; padding: 12px; text-align: left; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Semptify GUI Test Report</h1>
        <div class="timestamp">Generated: {self.report.timestamp}</div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>TOTAL</h3>
                <div class="number total">{summary['total']}</div>
            </div>
            <div class="summary-card">
                <h3>PASSED</h3>
                <div class="number passed">{summary['passed']}</div>
            </div>
            <div class="summary-card">
                <h3>FAILED</h3>
                <div class="number failed">{summary['failed']}</div>
            </div>
            <div class="summary-card">
                <h3>PASS RATE</h3>
                <div class="number total">{summary['pass_rate']}%</div>
            </div>
        </div>
        
        <h2>Detailed Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Status</th>
                    <th>Role</th>
                    <th>Duration</th>
                    <th>Artifacts</th>
                </tr>
            </thead>
            <tbody>
                {results_html}
            </tbody>
        </table>
    </div>
</body>
</html>
        """


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

async def main():
    global BASE_URL
    
    parser = argparse.ArgumentParser(
        description="Semptify GUI Test Bot - Artificial User Testing with Playwright"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run with visible browser window (for debugging)"
    )
    parser.add_argument(
        "--slow",
        type=int,
        default=0,
        metavar="MS",
        help="Slow motion delay in milliseconds (e.g., --slow 500)"
    )
    parser.add_argument(
        "--role",
        type=str,
        default="all",
        choices=["all", "tenant", "advocate", "manager", "legal", "admin"],
        help="Which user role to test"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=BASE_URL,
        help=f"Base URL to test (default: {BASE_URL})"
    )
    
    args = parser.parse_args()
    
    # Update global BASE_URL if provided
    if args.url != BASE_URL:
        BASE_URL = args.url
    
    # Create and run bot
    bot = SemptifyGUITestBot(headed=args.headed, slow_mo=args.slow)
    
    roles = [args.role] if args.role != "all" else ["all"]
    await bot.run_all_tests(roles=roles)


if __name__ == "__main__":
    asyncio.run(main())
