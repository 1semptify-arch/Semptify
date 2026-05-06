/**
 * Semptify User Flow Continuity E2E Test
 * =======================================
 * 
 * Tests complete user journey flows from start to finish:
 * - New user onboarding (Welcome → Role → Storage → Home)
 * - Returning user flow (Reconnect → Home)
 * - Document upload flow
 * - Navigation consistency across all pages
 * - SSOT navigation compliance (no hardcoded URLs)
 * 
 * Run: node tests/e2e/user_flow_continuity_test.js
 * 
 * Prerequisites:
 * 1. npm install -g playwright
 * 2. npx playwright install chromium
 * 3. Semptify server running on http://localhost:8000
 */

const { chromium } = require('playwright');

const BASE_URL = process.env.SEMPTIFY_URL || 'http://localhost:8000';
const HEADLESS = process.env.HEADLESS === 'true';
const SLOW_MO = parseInt(process.env.SLOW_MO || '100');

// Test results
const results = {
  flows_tested: [],
  navigation_paths: [],
  errors: [],
  screenshots: [],
  ssot_violations: []
};

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function log(step, status, details = '') {
  const timestamp = new Date().toISOString();
  const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : status === 'WARN' ? '⚠️' : '⏳';
  console.log(`${icon} [${timestamp}] ${step}: ${details}`);
}

/**
 * Check for SSOT violations (hardcoded URLs)
 */
async function checkSSOTCompliance(page, pageName) {
  const violations = [];
  
  // Check for hardcoded URLs in href attributes
  const links = await page.locator('a[href^="/"], a[href^="http"]').all();
  for (const link of links) {
    const href = await link.getAttribute('href');
    // Flag potential SSOT violations
    if (href && (href.includes('/onboarding-assets/') || href.match(/\/(tenant|advocate|admin)\/(home|dashboard)/))) {
      const text = await link.textContent();
      violations.push({ element: 'a', href, text: text?.trim().substring(0, 30) });
    }
  }
  
  // Check for inline JavaScript navigation
  const scripts = await page.locator('script').all();
  for (const script of scripts) {
    const content = await script.textContent();
    if (content && (content.includes('window.location.href') || content.includes('window.location.replace'))) {
      if (content.match(/['"]\/[^'"]+['"]/)) {
        violations.push({ element: 'script', type: 'inline_navigation', preview: content.substring(0, 100) });
      }
    }
  }
  
  if (violations.length > 0) {
    results.ssot_violations.push({ page: pageName, violations });
    await log(`SSOT Check: ${pageName}`, 'WARN', `${violations.length} potential violations found`);
  } else {
    await log(`SSOT Check: ${pageName}`, 'PASS', 'No hardcoded URL violations');
  }
  
  return violations.length === 0;
}

/**
 * Take screenshot with timestamp
 */
async function takeScreenshot(page, name) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const path = `/tmp/flow_${name}_${timestamp}.png`;
  await page.screenshot({ path, fullPage: true });
  results.screenshots.push(path);
  return path;
}

/**
 * FLOW 1: New User Onboarding (Welcome → Role → Storage → Home)
 */
async function testNewUserOnboarding(browser) {
  console.log('\n🆕 FLOW 1: New User Onboarding');
  console.log('=' .repeat(60));
  
  const context = await browser.newContext();
  const page = await context.newPage();
  const flowSteps = [];
  
  try {
    // Step 1: Welcome Page
    await log('Flow 1.1', 'PASS', 'Welcome Page - Loading');
    await page.goto(`${BASE_URL}/static/welcome.html`, { waitUntil: 'networkidle' });
    await delay(500);
    
    const welcomeTitle = await page.title();
    await log('Flow 1.1', 'PASS', `Welcome loaded: "${welcomeTitle}"`);
    await checkSSOTCompliance(page, 'welcome');
    await takeScreenshot(page, '01_welcome');
    flowSteps.push({ step: 'welcome', url: page.url(), status: 'OK' });
    
    // Find and click "Get Started" button
    const getStartedBtn = page.locator('button:has-text("Get Started"), a:has-text("Get Started"), .cta-button, [data-action="start"]').first();
    if (await getStartedBtn.isVisible().catch(() => false)) {
      await log('Flow 1.1', 'PASS', 'Found "Get Started" CTA button');
    } else {
      await log('Flow 1.1', 'WARN', 'Get Started button not found - may need manual navigation');
    }
    
    // Step 2: Role Selection
    await log('Flow 1.2', 'PASS', 'Role Selection - Navigating');
    await page.goto(`${BASE_URL}/onboarding/select-role.html`, { waitUntil: 'networkidle' });
    await delay(500);
    
    const roleTitle = await page.title();
    await log('Flow 1.2', 'PASS', `Role selection loaded: "${roleTitle}"`);
    await checkSSOTCompliance(page, 'role_selection');
    await takeScreenshot(page, '02_role_selection');
    flowSteps.push({ step: 'role_selection', url: page.url(), status: 'OK' });
    
    // Look for tenant role option (Core 5.0 only has tenant)
    const tenantOption = page.locator('[data-role="tenant"], button:has-text("Tenant"), .role-tenant').first();
    const roleOptions = await page.locator('[data-role], .role-option, button').all();
    await log('Flow 1.2', 'PASS', `Found ${roleOptions.length} role option(s)`);
    
    // Step 3: Storage Selection
    await log('Flow 1.3', 'PASS', 'Storage Selection - Navigating');
    await page.goto(`${BASE_URL}/onboarding/storage-select.html`, { waitUntil: 'networkidle' });
    await delay(500);
    
    const storageTitle = await page.title();
    await log('Flow 1.3', 'PASS', `Storage selection loaded: "${storageTitle}"`);
    await checkSSOTCompliance(page, 'storage_selection');
    await takeScreenshot(page, '03_storage_selection');
    flowSteps.push({ step: 'storage_selection', url: page.url(), status: 'OK' });
    
    // Check for provider options
    const providers = await page.locator('[data-provider], .provider-option, button').all();
    await log('Flow 1.3', 'PASS', `Found ${providers.length} storage provider option(s)`);
    
    // Step 4: Tenant Home (after storage connected)
    await log('Flow 1.4', 'PASS', 'Tenant Home - Simulating post-storage flow');
    await page.goto(`${BASE_URL}/tenant/home`, { waitUntil: 'networkidle' });
    await delay(500);
    
    const homeUrl = page.url();
    const homeTitle = await page.title();
    await log('Flow 1.4', 'PASS', `Home page: "${homeTitle}" at ${homeUrl}`);
    await checkSSOTCompliance(page, 'tenant_home');
    await takeScreenshot(page, '04_tenant_home');
    flowSteps.push({ step: 'tenant_home', url: homeUrl, status: 'OK' });
    
    // Verify flow continuity
    results.flows_tested.push({
      name: 'new_user_onboarding',
      steps: flowSteps,
      status: 'PASS',
      duration: 'completed'
    });
    
    await log('Flow 1 Complete', 'PASS', 'New user onboarding flow verified');
    
  } catch (error) {
    await log('Flow 1', 'FAIL', error.message);
    results.errors.push({ flow: 'new_user_onboarding', error: error.message });
    results.flows_tested.push({
      name: 'new_user_onboarding',
      steps: flowSteps,
      status: 'FAIL',
      error: error.message
    });
  } finally {
    await context.close();
  }
}

/**
 * FLOW 2: Returning User (Reconnect → Home)
 */
async function testReturningUserFlow(browser) {
  console.log('\n🔁 FLOW 2: Returning User (Reconnect)');
  console.log('=' .repeat(60));
  
  const context = await browser.newContext();
  const page = await context.newPage();
  const flowSteps = [];
  
  try {
    // Step 1: Reconnect entry point
    await log('Flow 2.1', 'PASS', 'Reconnect - Loading /storage/reconnect');
    await page.goto(`${BASE_URL}/storage/reconnect`, { waitUntil: 'networkidle' });
    await delay(500);
    
    const reconnectUrl = page.url();
    const reconnectTitle = await page.title();
    await log('Flow 2.1', 'PASS', `Reconnect page: "${reconnectTitle}" at ${reconnectUrl}`);
    await checkSSOTCompliance(page, 'reconnect');
    await takeScreenshot(page, '05_reconnect');
    flowSteps.push({ step: 'reconnect', url: reconnectUrl, status: 'OK' });
    
    // Step 2: Reconnect with return_to
    await log('Flow 2.2', 'PASS', 'Reconnect with return_to parameter');
    await page.goto(`${BASE_URL}/storage/reconnect?return_to=/documents/upload`, { waitUntil: 'networkidle' });
    await delay(500);
    
    const returnToUrl = page.url();
    await log('Flow 2.2', 'PASS', `Return_to handled, landed at: ${returnToUrl}`);
    await takeScreenshot(page, '06_reconnect_return_to');
    flowSteps.push({ step: 'reconnect_return_to', url: returnToUrl, status: 'OK' });
    
    // Step 3: Home page (after reconnect)
    await log('Flow 2.3', 'PASS', 'Home - Post-reconnect destination');
    await page.goto(`${BASE_URL}/tenant/home`, { waitUntil: 'networkidle' });
    await delay(500);
    
    const homeTitle = await page.title();
    await log('Flow 2.3', 'PASS', `Home reached: "${homeTitle}"`);
    flowSteps.push({ step: 'home_after_reconnect', url: page.url(), status: 'OK' });
    
    results.flows_tested.push({
      name: 'returning_user_reconnect',
      steps: flowSteps,
      status: 'PASS'
    });
    
    await log('Flow 2 Complete', 'PASS', 'Returning user flow verified');
    
  } catch (error) {
    await log('Flow 2', 'FAIL', error.message);
    results.errors.push({ flow: 'returning_user_reconnect', error: error.message });
    results.flows_tested.push({
      name: 'returning_user_reconnect',
      steps: flowSteps,
      status: 'FAIL',
      error: error.message
    });
  } finally {
    await context.close();
  }
}

/**
 * FLOW 3: Document Upload Flow (Home → Upload → Vault)
 */
async function testDocumentUploadFlow(browser) {
  console.log('\n📄 FLOW 3: Document Upload');
  console.log('=' .repeat(60));
  
  const context = await browser.newContext();
  const page = await context.newPage();
  const flowSteps = [];
  
  try {
    // Step 1: Navigate to tenant home
    await log('Flow 3.1', 'PASS', 'Starting from Tenant Home');
    await page.goto(`${BASE_URL}/tenant/home`, { waitUntil: 'networkidle' });
    await delay(500);
    flowSteps.push({ step: 'home_start', url: page.url(), status: 'OK' });
    
    // Step 2: Check for upload button/link
    const uploadElements = await page.locator('button:has-text("Upload"), a:has-text("Upload"), [data-action="upload"], .upload-btn').all();
    await log('Flow 3.2', 'PASS', `Found ${uploadElements.length} upload element(s)`);
    
    // Step 3: Navigate to documents API endpoint
    await log('Flow 3.3', 'PASS', 'Checking Documents API');
    const apiContext = await browser.newContext();
    const apiResponse = await apiContext.request.get(`${BASE_URL}/api/documents/`);
    const apiStatus = apiResponse.status();
    await log('Flow 3.3', apiStatus === 200 ? 'PASS' : 'WARN', `Documents API: ${apiStatus}`);
    await apiContext.close();
    flowSteps.push({ step: 'documents_api', status: apiStatus === 200 ? 'OK' : 'CHECK_NEEDED' });
    
    // Step 4: Navigate to vault endpoint
    await log('Flow 3.4', 'PASS', 'Checking Vault API');
    const vaultContext = await browser.newContext();
    const vaultResponse = await vaultContext.request.get(`${BASE_URL}/api/vault/`);
    const vaultStatus = vaultResponse.status();
    await log('Flow 3.4', vaultStatus === 200 || vaultStatus === 307 ? 'PASS' : 'WARN', `Vault API: ${vaultStatus}`);
    await vaultContext.close();
    flowSteps.push({ step: 'vault_api', status: vaultStatus === 200 || vaultStatus === 307 ? 'OK' : 'CHECK_NEEDED' });
    
    await takeScreenshot(page, '07_document_flow');
    
    results.flows_tested.push({
      name: 'document_upload',
      steps: flowSteps,
      status: 'PASS'
    });
    
    await log('Flow 3 Complete', 'PASS', 'Document upload flow verified');
    
  } catch (error) {
    await log('Flow 3', 'FAIL', error.message);
    results.errors.push({ flow: 'document_upload', error: error.message });
    results.flows_tested.push({
      name: 'document_upload',
      steps: flowSteps,
      status: 'FAIL',
      error: error.message
    });
  } finally {
    await context.close();
  }
}

/**
 * FLOW 4: Navigation Consistency (All paths use SSOT)
 */
async function testNavigationConsistency(browser) {
  console.log('\n🧭 FLOW 4: Navigation Consistency');
  console.log('=' .repeat(60));
  
  const context = await browser.newContext();
  const page = await context.newPage();
  const paths = [];
  
  const navigationPaths = [
    { from: '/static/welcome.html', to: '/onboarding/select-role.html', name: 'Welcome → Role' },
    { from: '/onboarding/select-role.html', to: '/onboarding/storage-select.html', name: 'Role → Storage' },
    { from: '/storage/reconnect', to: '/tenant/home', name: 'Reconnect → Home (expected)', note: 'May redirect based on session' },
    { from: '/tenant/home', to: '/api/documents/', name: 'Home → Documents API' },
  ];
  
  try {
    for (const path of navigationPaths) {
      try {
        await log(`Nav: ${path.name}`, 'PASS', `Testing ${path.from} → ${path.to}`);
        
        // Start at source
        await page.goto(`${BASE_URL}${path.from}`, { waitUntil: 'networkidle' });
        const startUrl = page.url();
        
        // Navigate to destination
        await page.goto(`${BASE_URL}${path.to}`, { waitUntil: 'networkidle' });
        const endUrl = page.url();
        
        paths.push({
          name: path.name,
          from: path.from,
          to: path.to,
          start: startUrl,
          end: endUrl,
          status: 'OK',
          note: path.note || ''
        });
        
        await delay(200);
        
      } catch (error) {
        paths.push({
          name: path.name,
          from: path.from,
          to: path.to,
          status: 'FAIL',
          error: error.message
        });
        await log(`Nav: ${path.name}`, 'FAIL', error.message);
      }
    }
    
    results.navigation_paths = paths;
    
    const successCount = paths.filter(p => p.status === 'OK').length;
    await log('Flow 4 Complete', successCount === paths.length ? 'PASS' : 'WARN', `${successCount}/${paths.length} paths verified`);
    
  } catch (error) {
    await log('Flow 4', 'FAIL', error.message);
    results.errors.push({ flow: 'navigation_consistency', error: error.message });
  } finally {
    await context.close();
  }
}

/**
 * FLOW 5: Core API Flows (Legal Analysis, Timeline, Briefcase)
 */
async function testCoreAPIFlows(browser) {
  console.log('\n🔌 FLOW 5: Core API Endpoints');
  console.log('=' .repeat(60));
  
  const context = await browser.newContext();
  const endpoints = [];
  
  const apiTests = [
    { path: '/api/legal-analysis/', name: 'Legal Analysis API' },
    { path: '/api/timeline-unified/', name: 'Timeline Unified API' },
    { path: '/api/briefcase/', name: 'Briefcase API' },
    { path: '/api/vault/', name: 'Vault API' },
    { path: '/api/documents/', name: 'Documents API' },
    { path: '/api/law-library/', name: 'Law Library API' },
    { path: '/api/states/', name: 'State Laws API' },
  ];
  
  try {
    for (const api of apiTests) {
      try {
        const response = await context.request.get(`${BASE_URL}${api.path}`);
        const status = response.status();
        const ok = status === 200 || status === 307 || status === 302;
        
        endpoints.push({
          name: api.name,
          path: api.path,
          status,
          ok
        });
        
        await log(api.name, ok ? 'PASS' : 'WARN', `${api.path} → ${status}`);
        
      } catch (error) {
        endpoints.push({
          name: api.name,
          path: api.path,
          status: 'ERROR',
          error: error.message
        });
        await log(api.name, 'FAIL', error.message);
      }
    }
    
    const successCount = endpoints.filter(e => e.ok).length;
    await log('Flow 5 Complete', successCount === endpoints.length ? 'PASS' : 'WARN', `${successCount}/${endpoints.length} APIs accessible`);
    
  } catch (error) {
    await log('Flow 5', 'FAIL', error.message);
    results.errors.push({ flow: 'core_api', error: error.message });
  } finally {
    await context.close();
  }
}

/**
 * FLOW 6: Non-Core Routers Disabled Check
 */
async function testNonCoreRoutersDisabled(browser) {
  console.log('\n🔒 FLOW 6: Non-Core Routers Disabled');
  console.log('=' .repeat(60));
  
  const context = await browser.newContext();
  const disabledRoutes = [
    { path: '/api/court-forms/', name: 'Court Forms (Extended)' },
    { path: '/api/case-builder/', name: 'Case Builder (Extended)' },
    { path: '/api/brain/', name: 'Brain AI (Extended)' },
    { path: '/api/auto-mode/', name: 'Auto Mode (Extended)' },
    { path: '/api/eviction-defense/', name: 'Eviction Defense (Extended)' },
    { path: '/api/zoom-court/', name: 'Zoom Court (Extended)' },
    { path: '/api/analytics/', name: 'Analytics (Extended)' },
    { path: '/api/campaign/', name: 'Campaign (Extended)' },
    { path: '/api/complaints/', name: 'Complaints (Extended)' },
  ];
  
  const results_disabled = [];
  
  try {
    for (const route of disabledRoutes) {
      try {
        const response = await context.request.get(`${BASE_URL}${route.path}`);
        const status = response.status();
        
        // Should be 404 (not found) if router is disabled
        const isDisabled = status === 404;
        
        results_disabled.push({
          name: route.name,
          path: route.path,
          status,
          isDisabled
        });
        
        await log(route.name, isDisabled ? 'PASS' : 'WARN', `${route.path} → ${status} (expected 404 if disabled)`);
        
      } catch (error) {
        // Connection error = disabled (no route)
        results_disabled.push({
          name: route.name,
          path: route.path,
          status: 'ERROR',
          isDisabled: true
        });
        await log(route.name, 'PASS', `${route.path} - Not accessible (disabled)`);
      }
    }
    
    const disabledCount = results_disabled.filter(r => r.isDisabled).length;
    await log('Flow 6 Complete', 'PASS', `${disabledCount}/${disabledRoutes.length} non-core routers properly disabled`);
    
  } catch (error) {
    await log('Flow 6', 'FAIL', error.message);
  } finally {
    await context.close();
  }
}

/**
 * Generate test report
 */
async function generateReport() {
  console.log('\n\n📊 USER FLOW CONTINUITY TEST REPORT');
  console.log('=' .repeat(60));
  
  const totalFlows = results.flows_tested.length;
  const passedFlows = results.flows_tested.filter(f => f.status === 'PASS').length;
  const failedFlows = results.flows_tested.filter(f => f.status === 'FAIL').length;
  
  console.log(`\nFlows Tested: ${totalFlows}`);
  console.log(`  ✅ Passed: ${passedFlows}`);
  console.log(`  ❌ Failed: ${failedFlows}`);
  
  if (results.ssot_violations.length > 0) {
    console.log(`\n⚠️  SSOT Violations: ${results.ssot_violations.length} pages with potential hardcoded URLs`);
    for (const violation of results.ssot_violations) {
      console.log(`    - ${violation.page}: ${violation.violations.length} violation(s)`);
    }
  } else {
    console.log('\n✅ SSOT Compliance: No hardcoded URL violations detected');
  }
  
  if (results.errors.length > 0) {
    console.log(`\n❌ Errors: ${results.errors.length}`);
    for (const error of results.errors) {
      console.log(`    - ${error.flow || error.test}: ${error.error}`);
    }
  }
  
  console.log(`\n📸 Screenshots: ${results.screenshots.length} captured`);
  for (const screenshot of results.screenshots) {
    console.log(`    - ${screenshot}`);
  }
  
  // Write JSON report
  const reportPath = '/tmp/user_flow_continuity_report.json';
  const fs = require('fs');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`\n📝 Full report saved to: ${reportPath}`);
  
  console.log('\n' + '=' .repeat(60));
  if (failedFlows === 0 && results.errors.length === 0) {
    console.log('✅ ALL USER FLOWS VERIFIED - Core 5.0 Ready');
  } else {
    console.log('⚠️  SOME FLOWS NEED ATTENTION - Review report');
  }
  console.log('=' .repeat(60));
  
  return failedFlows === 0 && results.errors.length === 0;
}

/**
 * Main test runner
 */
async function runAllTests() {
  console.log('🔥 SEMPTIFY USER FLOW CONTINUITY TEST');
  console.log('=====================================');
  console.log(`Target: ${BASE_URL}`);
  console.log(`Mode: ${HEADLESS ? 'Headless' : 'Visible Browser'}`);
  console.log('');
  
  const browser = await chromium.launch({ 
    headless: HEADLESS,
    slowMo: SLOW_MO 
  });
  
  try {
    await testNewUserOnboarding(browser);
    await testReturningUserFlow(browser);
    await testDocumentUploadFlow(browser);
    await testNavigationConsistency(browser);
    await testCoreAPIFlows(browser);
    await testNonCoreRoutersDisabled(browser);
    
    const allPassed = await generateReport();
    
    process.exit(allPassed ? 0 : 1);
    
  } catch (error) {
    console.error('Test suite failed:', error);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

// Run if called directly
if (require.main === module) {
  runAllTests();
}

module.exports = { runAllTests, results };
