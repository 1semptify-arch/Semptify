/**
 * Comprehensive SSOT Audit - Checks all pages for violations
 *
 * This audit verifies:
 * 1. All 5 base navigation links present on every page
 * 2. No hardcoded URLs that bypass SSOT registry
 * 3. Text/content adheres to Semptify standards
 * 4. Template compliance across all pages
 *
 * Run: node tests/e2e/comprehensive_ssot_audit.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.SEMPTIFY_URL || 'http://localhost:8000';

// The 5 base navigation links that MUST be on EVERY page (SSOT)
const BASE_NAV_LINKS = [
  { name: 'Home', path: '/home.html', icon: '🏠', required: true },
  { name: 'Library', path: '/library.html', icon: '📚', required: true },
  { name: 'Office', path: '/office.html', icon: '🏢', required: true },
  { name: 'Tools', path: '/tools.html', icon: '🔧', required: true },
  { name: 'Help', path: '/help.html', icon: '🆘', required: true },
];

// Pages to audit (add more as needed)
const PAGES_TO_AUDIT = [
  '/home.html',
  '/library.html',
  '/office.html',
  '/tools.html',
  '/help.html',
  '/',
  '/welcome',
  '/onboarding/start',
];

// SSOT Violation patterns to detect
const VIOLATION_PATTERNS = {
  // Hardcoded old paths that should not exist
  oldPaths: [
    { pattern: /href="\/home"/g, message: 'Old path /home should be /home.html' },
    { pattern: /href="\/cases"/g, message: 'Old path /cases found - use SSOT registry' },
    { pattern: /href="\/documents"/g, message: 'Old path /documents found - use SSOT registry' },
    { pattern: /href="\/settings"/g, message: 'Old path /settings found - use SSOT registry' },
    { pattern: /href="\/tenant\/home"/g, message: 'Old tenant/home path found' },
    { pattern: /href="\/advocate"/g, message: 'Old advocate path found' },
  ],
  // Navigation structure violations
  structure: [
    { pattern: /nav\.core-nav.*missing|no.*navigation/i, message: 'Missing navigation structure' },
  ],
  // Content standards
  content: [
    { pattern: /coming soon|under construction|placeholder/i, message: 'Placeholder text found - violates standards' },
    { pattern: /lorem ipsum/i, message: 'Lorem ipsum placeholder found - violates standards' },
    { pattern: /todo|fixme|hack/i, message: 'Developer TODO/FIXME found in user-facing text' },
  ],
  // SSOT registry bypass
  ssot: [
    { pattern: /window\.location\.href\s*=\s*["']\//g, message: 'Hardcoded JavaScript navigation - use SSOT API' },
    { pattern: /<meta[^>]*refresh[^>]*url=/gi, message: 'Meta refresh redirect - use SSOT navigation' },
  ],
};

const auditResults = {
  pagesAudited: 0,
  violationsFound: 0,
  navigationOk: 0,
  navigationFail: 0,
  violations: [],
  passed: [],
};

function logViolation(page, type, message, severity = 'error') {
  const icon = severity === 'error' ? '❌' : severity === 'warning' ? '⚠️' : 'ℹ️';
  console.log(`${icon} [${page}] ${type}: ${message}`);
  auditResults.violations.push({ page, type, message, severity });
  auditResults.violationsFound++;
}

function logPass(page, message) {
  console.log(`✅ [${page}] ${message}`);
  auditResults.passed.push({ page, message });
}

/**
 * Check navigation consistency on a page
 */
async function auditNavigation(page, pagePath) {
  const fullUrl = pagePath.startsWith('http') ? pagePath : `${BASE_URL}${pagePath}`;

  try {
    await page.goto(fullUrl, { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(500);

    // Check header navigation
    const headerNav = await page.locator('nav.core-nav').count();
    if (headerNav === 0) {
      logViolation(pagePath, 'NAVIGATION', 'Missing nav.core-nav element', 'error');
      return false;
    }

    // Check all 5 links in header
    let allLinksPresent = true;
    for (const link of BASE_NAV_LINKS) {
      const linkLocator = page.locator(`nav.core-nav a[href="${link.path}"]`);
      const count = await linkLocator.count();
      const visible = count > 0 ? await linkLocator.isVisible().catch(() => false) : false;

      if (count === 0) {
        logViolation(pagePath, 'NAVIGATION', `Missing ${link.name} link in header`, 'error');
        allLinksPresent = false;
      } else if (!visible) {
        logViolation(pagePath, 'NAVIGATION', `${link.name} link not visible in header`, 'warning');
      }
    }

    // Check mobile drawer
    const drawer = await page.locator('nav.nav-drawer').count();
    if (drawer === 0) {
      logViolation(pagePath, 'NAVIGATION', 'Missing mobile drawer (nav.nav-drawer)', 'warning');
    } else {
      // Check all 5 links in drawer
      for (const link of BASE_NAV_LINKS) {
        const drawerLink = page.locator(`nav.nav-drawer a[href="${link.path}"]`);
        const count = await drawerLink.count();
        if (count === 0) {
          logViolation(pagePath, 'MOBILE_NAV', `Missing ${link.name} link in mobile drawer`, 'error');
          allLinksPresent = false;
        }
      }
    }

    if (allLinksPresent) {
      logPass(pagePath, 'All 5 navigation links present in header and drawer');
      auditResults.navigationOk++;
      return true;
    } else {
      auditResults.navigationFail++;
      return false;
    }

  } catch (error) {
    logViolation(pagePath, 'LOAD_ERROR', `Failed to load page: ${error.message}`, 'error');
    auditResults.navigationFail++;
    return false;
  }
}

/**
 * Check for hardcoded URL violations in page HTML
 */
async function auditSSOTViolations(page, pagePath) {
  const html = await page.content();

  // Check for old hardcoded paths
  for (const check of VIOLATION_PATTERNS.oldPaths) {
    const matches = html.match(check.pattern);
    if (matches && matches.length > 0) {
      logViolation(pagePath, 'SSOT_OLD_PATH', `${check.message} (${matches.length} occurrences)`, 'error');
    }
  }

  // Check for JavaScript hardcoded navigation
  for (const check of VIOLATION_PATTERNS.ssot) {
    const matches = html.match(check.pattern);
    if (matches && matches.length > 0) {
      logViolation(pagePath, 'SSOT_BYPASS', `${check.message} (${matches.length} occurrences)`, 'error');
    }
  }

  // Check for placeholder content
  for (const check of VIOLATION_PATTERNS.content) {
    const matches = html.match(check.pattern);
    if (matches && matches.length > 0) {
      logViolation(pagePath, 'CONTENT', `${check.message} (${matches.length} occurrences)`, 'warning');
    }
  }
}

/**
 * Check active state is correct
 */
async function auditActiveState(page, pagePath) {
  const currentPath = pagePath.replace(/\/$/, '/home.html'); // Normalize root
  const expectedLink = BASE_NAV_LINKS.find(l => l.path === currentPath || pagePath.includes(l.path));

  if (expectedLink) {
    const activeLink = page.locator('nav.core-nav a.active');
    const count = await activeLink.count();

    if (count === 0) {
      logViolation(pagePath, 'ACTIVE_STATE', `No active link for current page (${expectedLink.name})`, 'warning');
    } else {
      const activeHref = await activeLink.getAttribute('href').catch(() => '');
      if (activeHref !== expectedLink.path) {
        logViolation(pagePath, 'ACTIVE_STATE', `Wrong active link: ${activeHref} should be ${expectedLink.path}`, 'error');
      } else {
        logPass(pagePath, `Active state correct (${expectedLink.name})`);
      }
    }
  }
}

/**
 * Audit navigation links actually work
 */
async function auditNavigationWorks(page, fromPage, toLink) {
  try {
    await page.goto(`${BASE_URL}${fromPage}`, { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(500);

    const navLink = page.locator(`nav.core-nav a[href="${toLink.path}"]`);
    const visible = await navLink.isVisible().catch(() => false);

    if (!visible) {
      logViolation(fromPage, 'NAV_FUNCTION', `Cannot click ${toLink.name} - not visible`, 'error');
      return false;
    }

    await navLink.click();
    await page.waitForTimeout(1000);

    const url = page.url();
    const expectedUrl = `${BASE_URL}${toLink.path}`;

    if (url === expectedUrl) {
      logPass(fromPage, `Navigation to ${toLink.name} works correctly`);
      return true;
    } else {
      logViolation(fromPage, 'NAV_FUNCTION', `Navigation failed: expected ${expectedUrl}, got ${url}`, 'error');
      return false;
    }
  } catch (error) {
    logViolation(fromPage, 'NAV_FUNCTION', `Navigation error: ${error.message}`, 'error');
    return false;
  }
}

/**
 * Run the complete audit
 */
async function runComprehensiveAudit() {
  console.log('\n' + '='.repeat(70));
  console.log('🔍 COMPREHENSIVE SSOT & NAVIGATION AUDIT');
  console.log('=' .repeat(70));
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Pages to audit: ${PAGES_TO_AUDIT.length}`);
  console.log(`Base nav links required: ${BASE_NAV_LINKS.length}`);
  console.log('');

  const browser = await chromium.launch({ headless: true });

  try {
    // Phase 1: Audit each page for navigation presence
    console.log('━'.repeat(70));
    console.log('PHASE 1: Navigation Presence Audit');
    console.log('━'.repeat(70));

    for (const pagePath of PAGES_TO_AUDIT) {
      const context = await browser.newContext();
      const page = await context.newPage();

      auditResults.pagesAudited++;
      await auditNavigation(page, pagePath);
      await auditSSOTViolations(page, pagePath);
      await auditActiveState(page, pagePath);

      await context.close();
    }

    // Phase 2: Test navigation functionality (sample)
    console.log('\n' + '━'.repeat(70));
    console.log('PHASE 2: Navigation Functionality Audit (Sample)');
    console.log('━'.repeat(70));

    const sampleTests = [
      { from: '/home.html', to: BASE_NAV_LINKS[1] }, // Home -> Library
      { from: '/library.html', to: BASE_NAV_LINKS[2] }, // Library -> Office
      { from: '/office.html', to: BASE_NAV_LINKS[3] }, // Office -> Tools
    ];

    for (const test of sampleTests) {
      const context = await browser.newContext();
      const page = await context.newPage();

      await auditNavigationWorks(page, test.from, test.to);

      await context.close();
    }

  } finally {
    await browser.close();
  }

  // Print summary
  console.log('\n' + '='.repeat(70));
  console.log('📊 AUDIT SUMMARY');
  console.log('=' .repeat(70));
  console.log(`Pages Audited: ${auditResults.pagesAudited}`);
  console.log(`Navigation OK: ${auditResults.navigationOk} ✅`);
  console.log(`Navigation Failed: ${auditResults.navigationFail} ❌`);
  console.log(`Total Violations: ${auditResults.violationsFound}`);

  if (auditResults.violationsFound > 0) {
    console.log('\n❌ VIOLATIONS BY CATEGORY:');
    const byCategory = {};
    for (const v of auditResults.violations) {
      byCategory[v.type] = (byCategory[v.type] || 0) + 1;
    }
    for (const [cat, count] of Object.entries(byCategory)) {
      console.log(`  ${cat}: ${count}`);
    }

    console.log('\n❌ ALL VIOLATIONS:');
    for (const v of auditResults.violations) {
      const icon = v.severity === 'error' ? '❌' : '⚠️';
      console.log(`  ${icon} [${v.page}] ${v.type}: ${v.message}`);
    }
  } else {
    console.log('\n✅ NO VIOLATIONS FOUND - All pages comply with SSOT standards!');
  }

  // Save report
  const reportPath = path.join(__dirname, 'audit-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(auditResults, null, 2));
  console.log(`\n📄 Full report saved to: ${reportPath}`);

  console.log('');
  process.exit(auditResults.violationsFound > 0 ? 1 : 0);
}

runComprehensiveAudit().catch(error => {
  console.error('Audit failed:', error);
  process.exit(1);
});
