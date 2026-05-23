const { chromium } = require('playwright');

const TARGET = 'https://semptify.org';

async function runOnboardingTests() {
  console.log('═══════════════════════════════════════════');
  console.log('  SEMPITFY ONBOARDING FLOW TESTS');
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

  // Test 1: Role selection page loads
  await test('Onboarding: Role selection page loads', async () => {
    await page.goto(`${TARGET}/onboarding/select-role`);
    await page.waitForTimeout(2000);
    const hasRoleCards = await page.locator('a.role-card, .role-card, [class*="role"]').count() > 0;
    if (!hasRoleCards) throw new Error('No role selection elements found');
  });

  // Test 2: Tenant role card exists
  await test('Onboarding: Tenant role card exists', async () => {
    await page.goto(`${TARGET}/onboarding/select-role`);
    await page.waitForTimeout(2000);
    const content = await page.content();
    if (!content.toLowerCase().includes('tenant')) {
      throw new Error('Tenant role not found on page');
    }
  });

  // Test 3: Vault setup step 1 page loads
  await test('Onboarding: Vault setup step 1 loads', async () => {
    await page.goto(`${TARGET}/vault-setup`);
    await page.waitForTimeout(2000);
    const url = page.url();
    if (!url.includes('vault-setup') && !url.includes('select-role')) {
      throw new Error(`Unexpected redirect: ${url}`);
    }
  });

  // Test 4: Vault setup step 2 page loads
  await test('Onboarding: Vault setup step 2 loads', async () => {
    await page.goto(`${TARGET}/vault-setup/security`);
    await page.waitForTimeout(2000);
    const url = page.url();
    if (!url.includes('security') && !url.includes('vault-setup') && !url.includes('select-role')) {
      throw new Error(`Unexpected redirect: ${url}`);
    }
  });

  // Test 5: Vault setup step 3 page loads
  await test('Onboarding: Vault setup step 3 loads', async () => {
    await page.goto(`${TARGET}/vault-setup/inspect`);
    await page.waitForTimeout(2000);
    const url = page.url();
    if (!url.includes('inspect') && !url.includes('vault-setup') && !url.includes('select-role')) {
      throw new Error(`Unexpected redirect: ${url}`);
    }
  });

  // Test 6: API: Vault init endpoint exists
  await test('API: Vault init endpoint responds', async () => {
    const resp = await page.evaluate(async (target) => {
      try {
        const r = await fetch(`${target}/onboarding/api/vault/init`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        return { status: r.status };
      } catch (e) {
        return { error: e.message };
      }
    }, TARGET);
    // 401 (no auth) or 400 (no data) is expected, 404 or 500 is not
    if (resp.status === 404 || resp.status === 500) {
      throw new Error(`Vault init endpoint error: ${resp.status}`);
    }
  });

  // Test 7: API: Vault security endpoint exists
  await test('API: Vault security endpoint responds', async () => {
    const resp = await page.evaluate(async (target) => {
      try {
        const r = await fetch(`${target}/onboarding/api/vault/security`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        return { status: r.status };
      } catch (e) {
        return { error: e.message };
      }
    }, TARGET);
    if (resp.status === 404 || resp.status === 500) {
      throw new Error(`Vault security endpoint error: ${resp.status}`);
    }
  });

  // Test 8: API: Vault verify endpoint exists
  await test('API: Vault verify endpoint responds', async () => {
    const resp = await page.evaluate(async (target) => {
      try {
        const r = await fetch(`${target}/onboarding/api/vault/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        return { status: r.status };
      } catch (e) {
        return { error: e.message };
      }
    }, TARGET);
    if (resp.status === 404 || resp.status === 500) {
      throw new Error(`Vault verify endpoint error: ${resp.status}`);
    }
  });

  // Test 9: Onboarding complete page loads
  await test('Onboarding: Complete page loads', async () => {
    await page.goto(`${TARGET}/onboarding/complete`);
    await page.waitForTimeout(2000);
    const url = page.url();
    if (!url.includes('complete') && !url.includes('select-role')) {
      throw new Error(`Unexpected redirect: ${url}`);
    }
  });

  // Test 10: Onboarding status endpoint exists
  await test('API: Onboarding status endpoint responds', async () => {
    const resp = await page.evaluate(async (target) => {
      try {
        const r = await fetch(`${target}/onboarding/status`);
        return { status: r.status };
      } catch (e) {
        return { error: e.message };
      }
    }, TARGET);
    if (resp.status === 404 || resp.status === 500) {
      throw new Error(`Onboarding status endpoint error: ${resp.status}`);
    }
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

runOnboardingTests().catch(e => {
  console.error('Test runner crashed:', e);
  process.exit(1);
});
