/**
 * Navigation Consistency E2E Test
 * 
 * Verifies that all 5 base navigation links (Home, Library, Office, Tools, Help)
 * are present and working on every page throughout Semptify.
 * 
 * Run: node tests/e2e/navigation_consistency_test.js
 * 
 * Prerequisites:
 * 1. npm install -g playwright
 * 2. npx playwright install chromium
 * 3. Semptify server running on http://localhost:8000
 */

const { chromium } = require('playwright');

const BASE_URL = process.env.SEMPTIFY_URL || 'http://localhost:8000';

// The 5 base navigation links that must be on EVERY page
const BASE_NAV_LINKS = [
  { name: 'Home', path: '/home.html', icon: '🏠' },
  { name: 'Library', path: '/library.html', icon: '📚' },
  { name: 'Office', path: '/office.html', icon: '🏢' },
  { name: 'Tools', path: '/tools.html', icon: '🔧' },
  { name: 'Help', path: '/help.html', icon: '🆘' },
];

// All pages that must have the 5 base navigation links
const PAGES_TO_TEST = [
  '/home.html',
  '/library.html',
  '/office.html',
  '/tools.html',
  '/help.html',
];

// Test results
const results = {
  passed: 0,
  failed: 0,
  tests: []
};

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function log(testName, status, details = '') {
  const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : '⏳';
  console.log(`${icon} ${testName}: ${details}`);
  results.tests.push({ name: testName, status, details });
  if (status === 'PASS') results.passed++;
  if (status === 'FAIL') results.failed++;
}

/**
 * Test 1: Verify SSOT Navigation Registry API
 */
async function testSSOTNavigationAPI(browser) {
  console.log('\n📡 TEST 1: SSOT Navigation API');
  console.log('=' .repeat(50));
  
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    // Fetch the SSOT navigation API
    const response = await page.goto(`${BASE_URL}/onboarding/ssot-navigation`);
    
    if (!response.ok()) {
      log('API Response', 'FAIL', `Status: ${response.status()}`);
      return;
    }
    
    const nav = await response.json();
    
    // Verify main_nav exists and has 5 items
    if (!nav.main_nav || nav.main_nav.length !== 5) {
      log('API Main Nav Count', 'FAIL', `Expected 5 items, got ${nav.main_nav?.length || 0}`);
    } else {
      log('API Main Nav Count', 'PASS', '5 navigation items');
    }
    
    // Verify each of the 5 base links exists
    let allFound = true;
    for (const expected of BASE_NAV_LINKS) {
      const found = nav.main_nav?.find(item => item.name === expected.name);
      if (!found) {
        log(`API Link: ${expected.name}`, 'FAIL', 'Not found in registry');
        allFound = false;
      } else if (found.path !== expected.path) {
        log(`API Link: ${expected.name}`, 'FAIL', `Path mismatch: ${found.path} != ${expected.path}`);
        allFound = false;
      }
    }
    
    if (allFound) {
      log('API All 5 Links', 'PASS', 'All present with correct paths');
    }
    
  } catch (error) {
    log('SSOT API Test', 'FAIL', error.message);
  } finally {
    await context.close();
  }
}

/**
 * Test 2: Verify navigation consistency on every page
 */
async function testNavigationOnPage(browser, pagePath) {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    await page.goto(`${BASE_URL}${pagePath}`);
    await delay(500);
    
    // Test header navigation
    const headerNav = page.locator('nav.core-nav');
    const headerVisible = await headerNav.isVisible().catch(() => false);
    
    if (!headerVisible) {
      log(`${pagePath} Header Nav`, 'FAIL', 'Header navigation not found');
      return;
    }
    
    let allLinksPresent = true;
    for (const link of BASE_NAV_LINKS) {
      const navLink = headerNav.locator(`a[href="${link.path}"]`);
      const visible = await navLink.isVisible().catch(() => false);
      const text = await navLink.textContent().catch(() => '');
      
      if (!visible) {
        log(`${pagePath} - ${link.name}`, 'FAIL', 'Link not visible in header');
        allLinksPresent = false;
      } else if (!text.includes(link.name)) {
        log(`${pagePath} - ${link.name}`, 'FAIL', `Wrong text: ${text}`);
        allLinksPresent = false;
      }
    }
    
    if (allLinksPresent) {
      log(`${pagePath} Header Links`, 'PASS', 'All 5 links present');
    }
    
    // Test mobile drawer (check it exists in DOM)
    const drawer = page.locator('nav.nav-drawer');
    const drawerExists = await drawer.count() > 0;
    
    if (!drawerExists) {
      log(`${pagePath} Mobile Drawer`, 'FAIL', 'Mobile drawer not found');
      return;
    }
    
    let allDrawerLinksPresent = true;
    for (const link of BASE_NAV_LINKS) {
      const drawerLink = drawer.locator(`a[href="${link.path}"]`);
      const count = await drawerLink.count();
      
      if (count === 0) {
        log(`${pagePath} Drawer - ${link.name}`, 'FAIL', 'Link not found');
        allDrawerLinksPresent = false;
      }
    }
    
    if (allDrawerLinksPresent) {
      log(`${pagePath} Drawer Links`, 'PASS', 'All 5 links present');
    }
    
    // Test active state
    const currentPageLink = BASE_NAV_LINKS.find(l => l.path === pagePath);
    if (currentPageLink) {
      const activeLink = headerNav.locator('a.active');
      const activeHref = await activeLink.getAttribute('href').catch(() => '');
      
      if (activeHref === pagePath) {
        log(`${pagePath} Active State`, 'PASS', `${currentPageLink.name} is active`);
      } else {
        log(`${pagePath} Active State`, 'FAIL', `Expected ${pagePath}, got ${activeHref}`);
      }
    }
    
  } catch (error) {
    log(`${pagePath} Navigation`, 'FAIL', error.message);
  } finally {
    await context.close();
  }
}

/**
 * Test 3: Verify all navigation links work
 */
async function testNavigationLinksWork(browser, fromPage, toLink) {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    // Start at source page
    await page.goto(`${BASE_URL}${fromPage}`);
    await delay(500);
    
    // Click the navigation link
    const navLink = page.locator(`nav.core-nav a[href="${toLink.path}"]`);
    const visible = await navLink.isVisible().catch(() => false);
    
    if (!visible) {
      log(`Nav ${fromPage} → ${toLink.name}`, 'FAIL', 'Link not visible');
      return;
    }
    
    await navLink.click();
    await delay(1000);
    
    // Check URL
    const url = page.url();
    const expectedUrl = `${BASE_URL}${toLink.path}`;
    
    if (url === expectedUrl) {
      log(`Nav ${fromPage} → ${toLink.name}`, 'PASS', 'Navigation successful');
    } else {
      log(`Nav ${fromPage} → ${toLink.name}`, 'FAIL', `Wrong URL: ${url}`);
    }
    
  } catch (error) {
    log(`Nav ${fromPage} → ${toLink.name}`, 'FAIL', error.message);
  } finally {
    await context.close();
  }
}

/**
 * Test 4: Mobile drawer navigation
 */
async function testMobileDrawer(browser) {
  console.log('\n📱 TEST 4: Mobile Drawer');
  console.log('=' .repeat(50));
  
  const context = await browser.newContext({
    viewport: { width: 375, height: 667 }
  });
  const page = await context.newPage();
  
  try {
    await page.goto(`${BASE_URL}/home.html`);
    await delay(500);
    
    // Open hamburger menu
    const hamburger = page.locator('button.hamburger');
    const hamburgerVisible = await hamburger.isVisible().catch(() => false);
    
    if (!hamburgerVisible) {
      log('Mobile Hamburger', 'FAIL', 'Not visible on mobile viewport');
      return;
    }
    
    await hamburger.click();
    await delay(300);
    
    // Drawer should have open class
    const drawer = page.locator('nav.nav-drawer');
    const hasOpenClass = await drawer.evaluate(el => el.classList.contains('open'));
    
    if (hasOpenClass) {
      log('Mobile Drawer Open', 'PASS', 'Drawer opens on hamburger click');
    } else {
      log('Mobile Drawer Open', 'FAIL', 'Drawer did not open');
    }
    
    // Click Library link in drawer
    const libraryLink = drawer.locator('a[href="/library.html"]');
    await libraryLink.click();
    await delay(500);
    
    const url = page.url();
    if (url === `${BASE_URL}/library.html`) {
      log('Mobile Nav to Library', 'PASS', 'Navigation works from drawer');
    } else {
      log('Mobile Nav to Library', 'FAIL', `Wrong URL: ${url}`);
    }
    
  } catch (error) {
    log('Mobile Drawer Test', 'FAIL', error.message);
  } finally {
    await context.close();
  }
}

/**
 * Main test runner
 */
async function runTests() {
  console.log('\n' + '='.repeat(60));
  console.log('🔍 NAVIGATION CONSISTENCY E2E TEST');
  console.log('=' .repeat(60));
  console.log(`Testing against: ${BASE_URL}`);
  console.log('Pages: ' + PAGES_TO_TEST.join(', '));
  console.log('');
  
  const browser = await chromium.launch({ headless: true });
  
  try {
    // Test 1: SSOT API
    await testSSOTNavigationAPI(browser);
    
    // Test 2: Navigation on each page
    console.log('\n📄 TEST 2: Navigation on Each Page');
    console.log('=' .repeat(50));
    
    for (const pagePath of PAGES_TO_TEST) {
      await testNavigationOnPage(browser, pagePath);
    }
    
    // Test 3: Navigation links work
    console.log('\n🔗 TEST 3: Navigation Links Work');
    console.log('=' .repeat(50));
    
    for (const fromPage of PAGES_TO_TEST.slice(0, 2)) { // Test from first 2 pages
      for (const toLink of BASE_NAV_LINKS.slice(0, 3)) { // Test to first 3 links
        if (fromPage !== toLink.path) {
          await testNavigationLinksWork(browser, fromPage, toLink);
        }
      }
    }
    
    // Test 4: Mobile drawer
    await testMobileDrawer(browser);
    
  } finally {
    await browser.close();
  }
  
  // Print summary
  console.log('\n' + '='.repeat(60));
  console.log('📊 TEST SUMMARY');
  console.log('=' .repeat(60));
  console.log(`Total Tests: ${results.tests.length}`);
  console.log(`Passed: ${results.passed} ✅`);
  console.log(`Failed: ${results.failed} ❌`);
  
  if (results.failed > 0) {
    console.log('\n❌ FAILED TESTS:');
    for (const test of results.tests.filter(t => t.status === 'FAIL')) {
      console.log(`  - ${test.name}: ${test.details}`);
    }
  }
  
  console.log('');
  process.exit(results.failed > 0 ? 1 : 0);
}

runTests().catch(error => {
  console.error('Test runner failed:', error);
  process.exit(1);
});
