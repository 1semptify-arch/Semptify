/**
 * Semptify Smoke Test
 * ===================
 * 
 * Quick test to verify the app is working.
 * Runs in ~30 seconds.
 * 
 * Checks:
 * - Server responds
 * - Main pages load
 * - API endpoints work
 * - No 500 errors
 */

const { chromium } = require('playwright');

const BASE_URL = process.env.SEMPTIFY_URL || 'http://localhost:8000';

async function smokeTest() {
  console.log('🔥 SEMPTIFY SMOKE TEST');
  console.log('=======================');
  console.log(`Target: ${BASE_URL}`);
  console.log('');
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  let passed = 0;
  let failed = 0;
  
  const tests = [
    { name: 'Health Check', url: '/healthz' },
    { name: 'Welcome Page', url: '/static/welcome.html' },
    { name: 'API Health', url: '/api/health' },
    { name: 'Role UI', url: '/ui/available-roles' },
    { name: 'Storage Entry', url: '/storage/entry' },
    { name: 'Navigation', url: '/ui/navigation' },
  ];
  
  for (const test of tests) {
    try {
      const response = await page.goto(`${BASE_URL}${test.url}`, { 
        waitUntil: 'domcontentloaded',
        timeout: 10000 
      });
      
      if (response && (response.status() === 200 || response.status() === 307)) {
        console.log(`✅ ${test.name}: OK`);
        passed++;
      } else {
        console.log(`❌ ${test.name}: HTTP ${response?.status() || 'no response'}`);
        failed++;
      }
    } catch (error) {
      console.log(`❌ ${test.name}: ${error.message}`);
      failed++;
    }
  }
  
  await browser.close();
  
  console.log('');
  console.log('=======================');
  console.log(`Passed: ${passed}/${tests.length}`);
  console.log(`Failed: ${failed}/${tests.length}`);
  
  if (failed === 0) {
    console.log('✅ Smoke test PASSED');
    process.exit(0);
  } else {
    console.log('❌ Smoke test FAILED');
    process.exit(1);
  }
}

smokeTest().catch(err => {
  console.error('Test error:', err);
  process.exit(1);
});
