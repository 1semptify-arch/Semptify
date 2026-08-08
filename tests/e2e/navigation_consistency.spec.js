/**
 * Navigation Consistency E2E Test
 *
 * Verifies that the SSOT navigation system is consistent across the app.
 * Tests the 5 base navigation links (Home, Library, Office, Tools, Help)
 * defined in navigation.MAIN_NAV.
 *
 * Pages that extend base.html use nav.header__nav with /home, /library, etc.
 * Pages that extend gui/base.html use nav.gui-nav with different links
 * (tenant-specific routes) — these are tested separately.
 *
 * Run with: npx playwright test navigation_consistency.spec.js
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.SEMPTIFY_URL || 'http://localhost:8000';

// The 5 base navigation links from navigation.MAIN_NAV (SSOT)
// Paths are RENDERED routes — never .html static files.
const BASE_NAV_LINKS = [
  { name: 'Home', path: '/home', icon: '○', order: 0 },
  { name: 'Library', path: '/library', icon: '○', order: 1 },
  { name: 'Office', path: '/office', icon: '○', order: 2 },
  { name: 'Tools', path: '/tools', icon: '▸', order: 3 },
  { name: 'Help', path: '/help', icon: '🆘', order: 4 },
];

// Pages that extend base.html and should have nav.header__nav with all 5 links
const PAGES_WITH_HEADER_NAV = [
  '/home',
  '/library',
  '/office',
  '/tools',
];

// Pages that extend gui/base.html and use nav.gui-nav (different link set)
const PAGES_WITH_GUI_NAV = [
  '/help',
];

/**
 * Test: Verify SSOT Navigation Registry API
 */
test('SSOT Navigation API returns correct 5 base links', async ({ request }) => {
  const response = await request.get(`${BASE_URL}/onboarding/ssot-navigation`);
  expect(response.ok()).toBeTruthy();

  const nav = await response.json();

  // Verify main_nav exists and has 5 items
  expect(nav.main_nav).toBeDefined();
  expect(nav.main_nav.length).toBe(5);

  // Verify each of the 5 base links exists with correct name and path
  for (const expected of BASE_NAV_LINKS) {
    const found = nav.main_nav.find(item => item.name === expected.name);
    expect(found, `Missing navigation item: ${expected.name}`).toBeDefined();
    expect(found.path).toBe(expected.path);
  }
});

/**
 * Test: Verify navigation consistency on base.html pages
 * These pages should have nav.header__nav with all 5 SSOT links.
 */
for (const pagePath of PAGES_WITH_HEADER_NAV) {
  test(`Page ${pagePath} has nav.header__nav with all 5 SSOT links`, async ({ page }) => {
    await page.goto(`${BASE_URL}${pagePath}`);

    const headerNav = page.locator('nav.header__nav');
    await expect(headerNav).toBeVisible();

    // Verify all 5 links are present
    for (const link of BASE_NAV_LINKS) {
      const navLink = headerNav.locator(`a[href="${link.path}"]`);
      await expect(navLink, `Missing ${link.name} link on ${pagePath}`).toBeVisible();
      await expect(navLink).toContainText(link.name);
    }
  });
}

/**
 * Test: Verify gui/base.html pages have nav.gui-nav
 * These pages use a different nav structure (tenant-specific routes).
 */
for (const pagePath of PAGES_WITH_GUI_NAV) {
  test(`Page ${pagePath} has nav.gui-nav`, async ({ page }) => {
    await page.goto(`${BASE_URL}${pagePath}`);

    const guiNav = page.locator('nav.gui-nav');
    await expect(guiNav).toBeVisible();
    // gui-nav has at least 2 links (brand + nav items)
    const navLinks = guiNav.locator('a');
    const count = await navLinks.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });
}

/**
 * Test: Verify all navigation links are clickable and work
 * Only test base.html pages (gui-nav pages use different routes).
 */
for (const fromPage of PAGES_WITH_HEADER_NAV) {
  for (const toLink of BASE_NAV_LINKS) {
    // Skip clicking link to same page
    if (fromPage === toLink.path) continue;
    // Skip /help — it uses gui/base.html, no header__nav to click from
    if (toLink.path === '/help') continue;

    test(`Navigation from ${fromPage} to ${toLink.name} works`, async ({ page }) => {
      await page.goto(`${BASE_URL}${fromPage}`);

      const navLink = page.locator(`nav.header__nav a[href="${toLink.path}"]`);
      await navLink.click();

      await expect(page).toHaveURL(`${BASE_URL}${toLink.path}`);
    });
  }
}

/**
 * Test: Verify active state on current page
 */
for (const pagePath of PAGES_WITH_HEADER_NAV) {
  test(`Active state is correct on ${pagePath}`, async ({ page }) => {
    await page.goto(`${BASE_URL}${pagePath}`);

    const headerNav = page.locator('nav.header__nav');

    // Find which link should be active
    const expectedActive = BASE_NAV_LINKS.find(l => l.path === pagePath);

    if (expectedActive) {
      // The active link should have class "active"
      const activeLink = headerNav.locator('a.active');
      await expect(activeLink).toHaveAttribute('href', pagePath);
    }
  });
}

/**
 * Test: Verify no SSOT violations (no deprecated navigation paths)
 */
test('No SSOT violations in page source', async ({ page }) => {
  await page.goto(`${BASE_URL}/home`);

  const html = await page.content();

  // Check for hardcoded navigation patterns that violate SSOT
  const violations = [];

  // Look for .html extensions on nav links (should be route paths, not static files)
  const htmlExtPattern = /href="\/(home|library|office|tools)\.html"/g;
  if (htmlExtPattern.test(html)) {
    violations.push('Found .html extension in nav link (should be route path)');
  }

  // Look for old SSOT paths that were deprecated
  const deprecatedPatterns = [
    /href="\/cases"/g,
    /href="\/documents"/g,
    /href="\/timeline"/g,
    /href="\/settings"/g,
  ];

  for (const pattern of deprecatedPatterns) {
    if (pattern.test(html)) {
      violations.push(`Found deprecated path matching: ${pattern}`);
    }
  }

  expect(violations, `SSOT violations found: ${violations.join(', ')}`).toHaveLength(0);
});

/**
 * Test: Verify navigation survives page reload
 */
test('Navigation persists after page reload', async ({ page }) => {
  await page.goto(`${BASE_URL}/home`);

  // Click to Library
  await page.locator('nav.header__nav a[href="/library"]').click();
  await expect(page).toHaveURL(`${BASE_URL}/library`);

  // Reload page
  await page.reload();

  // Navigation should still be present
  const headerNav = page.locator('nav.header__nav');
  await expect(headerNav).toBeVisible();

  // All 5 links should still be there
  for (const link of BASE_NAV_LINKS) {
    await expect(headerNav.locator(`a[href="${link.path}"]`)).toBeVisible();
  }
});
