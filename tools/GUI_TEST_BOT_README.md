# Semptify GUI Test Bot

An **artificial user testing system** that simulates real users navigating the entire Semptify application using Playwright browser automation.

## Overview

Unlike static crawlers or API tests, this bot:
- Opens a **real Chromium browser**
- Clicks buttons, waits for elements, interacts with forms
- Tests each role (tenant, advocate, manager, legal, admin)
- Takes **screenshots on failure**
- Generates **HTML + JSON reports**
- Tests **responsive layouts** at multiple viewports

## Quick Start

### 1. Install Playwright (first time only)

```bash
# Windows
pip install playwright
playwright install chromium

# Or use the convenience script
tools\run_gui_tests.bat --install
```

### 2. Start Your Semptify Server

```bash
# Make sure the server is running
python run_server.py
# or
uvicorn app.main:app --reload
```

### 3. Run Tests

```bash
# Run all tests headless (fastest)
python tools/gui_test_bot.py

# Watch tests run in a visible browser
python tools/gui_test_bot.py --headed --slow 500

# Test only tenant flows
python tools/gui_test_bot.py --role tenant

# Test only advocate flows
python tools/gui_test_bot.py --role advocate

# Test against a different URL
python tools/gui_test_bot.py --url http://localhost:3000
```

### Windows Batch Script

```bash
# Run all tests
tools\run_gui_tests.bat

# Watch in headed mode
tools\run_gui_tests.bat --headed --slow

# Test specific role
tools\run_gui_tests.bat --role manager
```

## What Gets Tested

### Tenant Role
- ✅ Home page loads
- ✅ Documents page accessible
- ✅ Document intake flow
- ✅ Timeline view renders
- ✅ Vault access
- ✅ Navigation elements present
- ✅ Form interactions work
- ✅ Responsive layout (mobile/tablet/desktop)
- ✅ API health from UI context
- ✅ Dashboard widgets present

### Advocate Role
- ✅ Advocate dashboard
- ✅ Client management page
- ✅ Document review page
- ✅ Navigation elements
- ✅ API health

### Manager Role
- ✅ Manager dashboard
- ✅ Team view
- ✅ Reports page
- ✅ Navigation elements
- ✅ API health

### Legal Role
- ✅ Legal dashboard
- ✅ Case review page
- ✅ Documents page
- ✅ Navigation elements
- ✅ API health

### Admin Role
- ✅ Admin dashboard
- ✅ User management
- ✅ System health page
- ✅ Navigation elements
- ✅ API health

## Output

### Screenshots
Failed tests automatically capture full-page screenshots:
```
test_artifacts/screenshots/FAILED_test_name_20240424_123045.png
```

### Reports
Generated after each run:
```
test_artifacts/reports/gui_test_report_20240424_123045.html
test_artifacts/reports/gui_test_report_20240424_123045.json
```

The HTML report includes:
- Summary cards (Total, Passed, Failed, Pass Rate)
- Detailed test results table
- Screenshots links
- Error messages with stack traces

## Command Line Options

| Option | Description |
|--------|-------------|
| `--headed` | Show browser window (for debugging) |
| `--slow MS` | Slow motion delay in milliseconds |
| `--role ROLE` | Test specific role: tenant/advocate/manager/legal/admin/all |
| `--url URL` | Target URL (default: http://localhost:8000) |

## Debugging Failed Tests

1. **Run in headed mode** to watch the failure:
   ```bash
   python tools/gui_test_bot.py --headed --slow 500 --role tenant
   ```

2. **Check screenshots** in `test_artifacts/screenshots/`

3. **Open the HTML report** in a browser:
   ```bash
   start test_artifacts/reports/gui_test_report_*.html
   ```

4. **Check the JSON report** for raw error details:
   ```bash
   cat test_artifacts/reports/gui_test_report_*.json
   ```

## Extending the Bot

Add new tests by editing `tools/gui_test_bot.py`:

```python
async def test_my_new_feature(self, page: Page, role: str):
    await page.goto(f"{BASE_URL}/my-feature")
    
    # Wait for specific element
    await page.wait_for_selector("[data-my-feature]", state="visible")
    
    # Interact with form
    await page.fill("input[name='test']", "test value")
    await page.click("button[type='submit']")
    
    # Verify result
    success = await page.locator(".success-message").is_visible()
    if not success:
        raise AssertionError("Success message not found")
```

Then add it to a role's test list:

```python
async def run_tenant_tests(self, page: Page):
    tests = [
        # ... existing tests ...
        ("Tenant - My New Feature", self.test_my_new_feature),
    ]
```

## CI/CD Integration

Run in GitHub Actions or similar:

```yaml
- name: GUI Tests
  run: |
    pip install playwright
    playwright install chromium
    python tools/gui_test_bot.py
  continue-on-error: false
```

## Requirements

- Python 3.11+
- Playwright (`pip install playwright`)
- Chromium browser (auto-installed by `playwright install chromium`)
- Semptify server running on localhost:8000 (or specify `--url`)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `playwright not found` | Run `pip install playwright && playwright install chromium` |
| `Connection refused` | Start the Semptify server first |
| Tests timeout | Increase timeout in `new_page()` method |
| Screenshots blank | Check if page is fully loaded before screenshot |
