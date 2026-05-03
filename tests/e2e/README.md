# Semptify E2E Testing System

Real browser automation testing using Playwright. Actually clicks buttons, follows links, and validates the entire GUI.

## Quick Start

```bash
# 1. Install Playwright
npm install -g playwright
npx playwright install chromium

# 2. Start Semptify
python -m app.main

# 3. Run tests (in another terminal)
cd tests/e2e
./run_e2e_tests.sh
```

## Test Types

| Test | Command | Time | What It Does |
|------|---------|------|--------------|
| **Smoke** | `./run_e2e_tests.sh --quick` | 30s | Basic health checks, 6 endpoints |
| **Full** | `./run_e2e_tests.sh` | 3-5min | Every page, every link, every flow |
| **CI** | `./run_e2e_tests.sh --ci` | 3-5min | Full test, headless, no browser window |

## What Gets Tested

### 1. Static Pages (13 pages)
- `/` - Root
- `/static/welcome.html` - Welcome
- `/static/help.html` - Help
- `/static/library.html` - Library
- `/static/home.html` - Home
- `/static/admin/dashboard.html` - Admin
- `/static/advocate/dashboard.html` - Advocate
- `/static/tenant/index.html` - Tenant
- And more...

### 2. Link Validation
- Crawls welcome page
- Tests up to 50 internal links
- Verifies they return HTTP 200

### 3. API Endpoints (6 endpoints)
- `/healthz` - Health check
- `/api/health` - API health
- `/ui/available-roles` - Role list
- `/ui/navigation` - Navigation menu
- `/storage/session/status` - Session status
- `/api/docs` - Swagger docs

### 4. Flow Tests
- **Onboarding Flow**: Welcome → Start → Role Select → Providers
- **Reconnect Flow**: Entry point with return_to parameter
- **UI Router**: All role-based UI endpoints

### 5. Responsive Design
- Mobile (375x667)
- Tablet (768x1024)
- Desktop (1920x1080)

## Output

### Console Output
```
🔥 SEMPTIFY SMOKE TEST
=======================
✅ Health Check: OK
✅ Welcome Page: OK
✅ API Health: OK
✅ Role UI: OK
✅ Storage Entry: OK
✅ Navigation: OK

=======================
Passed: 6/6
Failed: 0/6
✅ Smoke test PASSED
```

### Screenshots
Saved to `/tmp/`:
- `semptify_welcome_page.png`
- `semptify_help_page.png`
- `semptify_responsive_mobile.png`
- `semptify_responsive_desktop.png`
- etc.

### JSON Report
```bash
cat /tmp/semptify_e2e_report.json
```

Contains:
- All pages tested with status
- All links checked with status
- All forms tested
- All errors found
- All screenshots taken

## CI/CD Integration

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start Server
        run: python -m app.main &
        
      - name: Install Playwright
        run: |
          npm install -g playwright
          npx playwright install chromium
          
      - name: Run E2E Tests
        run: cd tests/e2e && ./run_e2e_tests.sh --ci
        
      - name: Upload Screenshots
        uses: actions/upload-artifact@v3
        with:
          name: screenshots
          path: /tmp/semptify_*.png
```

## Custom Test Scripts

### Test a specific page
```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  await page.goto('http://localhost:8000/static/welcome.html');
  
  // Click the "Get Started" button
  await page.click('button:has-text("Get Started")');
  
  // Wait for navigation
  await page.waitForURL('**/onboarding/**');
  
  console.log('Navigation successful!');
  await browser.close();
})();
```

### Test form submission
```javascript
// Fill and submit a form
await page.fill('input[name="email"]', 'test@example.com');
await page.fill('input[name="password"]', 'password123');
await page.click('button[type="submit"]');

// Wait for success message
await page.waitForSelector('.success-message');
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEMPTIFY_URL` | `http://localhost:8000` | Target server URL |
| `HEADLESS` | `false` | Run without browser window |
| `SLOW_MO` | `50` | Slow down operations by N ms |

## Troubleshooting

### "Server not responding"
```bash
# Start the server first
python -m app.main

# In another terminal, run tests
cd tests/e2e && ./run_e2e_tests.sh
```

### "Playwright not installed"
```bash
npm install -g playwright
npx playwright install chromium
```

### "Test times out"
- Server might be slow
- Increase timeout in script
- Check server logs for errors

### "Browser doesn't open"
- Use `--ci` mode for headless
- Check display/X11 settings on Linux
- Try running with `headless: true`

## Adding New Tests

1. Edit `playwright_full_system_test.js`
2. Add test function following the pattern:
```javascript
async function testMyFeature(browser) {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    await page.goto(`${BASE_URL}/my-route`);
    // ... test logic
    await log('My Feature', 'PASS', 'Details');
  } catch (error) {
    await log('My Feature', 'FAIL', error.message);
  } finally {
    await context.close();
  }
}
```
3. Call it in `runAllTests()`

## Architecture

```
┌─────────────────┐
│  Playwright     │  ← Browser automation library
│  (Chromium)     │
└────────┬────────┘
         │
         ▼ HTTP requests
┌─────────────────┐
│  Semptify App   │  ← Your FastAPI server
│  (localhost:8000)│
└─────────────────┘
         │
         ▼ Validated
┌─────────────────┐
│  Test Results   │  ← JSON report + screenshots
│  (/tmp/)        │
└─────────────────┘
```

## Why Playwright?

- **Real browser**: Tests actual Chromium, not mocks
- **Visual**: Can see what happens (screenshots)
- **Complete**: Tests everything - HTML, CSS, JS, API
- **Reliable**: Waits for elements, handles async
- **Fast**: Parallel tests, headless mode

## Next Steps

1. Run the smoke test: `./run_e2e_tests.sh --quick`
2. Run full test: `./run_e2e_tests.sh`
3. Check screenshots in `/tmp/`
4. Review JSON report
5. Add to CI/CD pipeline
