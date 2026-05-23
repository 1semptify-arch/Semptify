const { chromium } = require('playwright');

const TARGET = 'https://semptify.org';

async function runTests() {
  console.log('═══════════════════════════════════════════');
  console.log('  SEMPITFY FULL SYSTEM TEST');
  console.log('═══════════════════════════════════════════');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const results = { passed: [], failed: [] };

  async function test(name, fn) {
    try {
      await fn();
      results.passed.push(name);
      console.log(`✅ ${name}`);
    } catch (e) {
      results.failed.push({ name, error: e.message });
      console.log(`❌ ${name}: ${e.message}`);
    }
  }

  // Test 1: Welcome page
  await test('Welcome page loads', async () => {
    await page.goto(`${TARGET}/`);
    await page.waitForTimeout(2000);
    const title = await page.title();
    if (!title.includes('Semptify')) throw new Error(`Unexpected title: ${title}`);
  });

  // Test 2: Register page
  await test('Register page loads', async () => {
    await page.goto(`${TARGET}/register`);
    await page.waitForTimeout(2000);
    const url = page.url();
    const content = await page.content();
    // Register may redirect to onboarding or login - check for valid Semptify content
    if (!content.includes('Semptify') && !url.includes('register') && !url.includes('onboarding')) {
      throw new Error(`Register page not found, redirect to: ${url}`);
    }
  });

  // Test 3: Role selection
  await test('Role selection loads', async () => {
    await page.goto(`${TARGET}/onboarding/select-role`);
    await page.waitForTimeout(2000);
    const hasLinks = await page.locator('a.role-card, .role-card').count() > 0;
    if (!hasLinks) throw new Error('No role cards found');
  });

  // Test 4: Storage providers
  await test('Storage providers page', async () => {
    await page.goto(`${TARGET}/storage/providers`);
    await page.waitForTimeout(2000);
    const content = await page.content();
    if (!content.includes('Google') && !content.includes('storage')) {
      throw new Error('Storage providers content not found');
    }
  });

  // Test 5: Vault page
  await test('Vault page loads', async () => {
    await page.goto(`${TARGET}/vault`);
    await page.waitForTimeout(3000);
    const url = page.url();
    if (!url.includes('/vault') && !url.includes('/login') && !url.includes('/select-role')) {
      throw new Error(`Unexpected vault redirect: ${url}`);
    }
  });

  // Test 6: API health
  await test('API: Health endpoint', async () => {
    const resp = await page.evaluate(async (target) => {
      const r = await fetch(`${target}/health`);
      return { status: r.status, json: await r.json() };
    }, TARGET);
    if (resp.status !== 200) throw new Error(`Health check failed: ${resp.status}`);
  });

  // Test 7: Upload endpoint (401 expected without auth)
  await test('Vault: Upload endpoint responds', async () => {
    const resp = await page.evaluate(async (target) => {
      try {
        const formData = new FormData();
        const r = await fetch(`${target}/api/vault/sidebar/upload`, {
          method: 'POST',
          body: formData
        });
        return { status: r.status };
      } catch (e) {
        return { error: e.message };
      }
    }, TARGET);
    // 400 (no files) or 401 (no auth) is expected, 500 is not
    if (resp.status === 500) throw new Error('Upload endpoint returns 500');
  });

  // Test 8: Documents page
  await test('Documents: Page loads', async () => {
    await page.goto(`${TARGET}/documents`);
    await page.waitForTimeout(3000);
  });

  // Test 9: Timeline page
  await test('Timeline: Page loads', async () => {
    await page.goto(`${TARGET}/timeline`);
    await page.waitForTimeout(3000);
  });

  // Test 10: Storage reconnect
  await test('Storage: Reconnect page', async () => {
    await page.goto(`${TARGET}/storage/reconnect`);
    await page.waitForTimeout(2000);
  });

  await browser.close();

  // Print summary
  console.log('\n═══════════════════════════════════════════');
  console.log(`✅ PASSED: ${results.passed.length}`);
  console.log(`❌ FAILED: ${results.failed.length}`);
  if (results.failed.length > 0) {
    console.log('\nFailed tests:');
    results.failed.forEach(f => console.log(`  - ${f.name}: ${f.error}`));
  }
  console.log('═══════════════════════════════════════════');

  process.exit(results.failed.length > 0 ? 1 : 0);
}

runTests().catch(e => {
  console.error('Test runner crashed:', e);
  process.exit(1);
});
