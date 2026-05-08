/**
 * Navigation Consistency E2E Test
 * 
 * Verifies that all 5 base navigation links (Home, Library, Office, Tools, Help)
 * are present and working on every page throughout Semptify.
 * 
 * Run with: npx playwright test navigation_consistency.spec.js
 */

const { test, expect } = require('@playwright/test');

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
  
  // Verify each of the 5 base links exists
  for (const expected of BASE_NAV_LINKS) {
    const found = nav.main_nav.find(item => item.name === expected.name);
    expect(found, `Missing navigation item: ${expected.name}`).toBeDefined();
    expect(found.path).toBe(expected.path);
    expect(found.icon).toBe(expected.icon);
  }
});

/**
 * Test: Verify navigation consistency on every page
 */
for (const pagePath of PAGES_TO_TEST) {
  test(`Page ${pagePath} has all 5 base navigation links in header`, async ({ page }) => {
    await page.goto(`${BASE_URL}${pagePath}`);
    
    // Wait for header navigation to be visible
    const headerNav = page.locator('nav.core-nav');
    await expect(headerNav).toBeVisible();
    
    // Verify all 5 links are present in header
    for (const link of BASE_NAV_LINKS) {
      const navLink = headerNav.locator(`a[href="${link.path}"]`);
      await expect(navLink, `Missing ${link.name} link on ${pagePath}`).toBeVisible();
      await expect(navLink).toContainText(link.name);
    }
  });

  test(`Page ${pagePath} has all 5 base navigation links in mobile drawer`, async ({ page }) => {
    await page.goto(`${BASE_URL}${pagePath}`);
    
    // Mobile drawer is initially hidden, check it exists in DOM
    const drawer = page.locator('nav.nav-drawer');
    await expect(drawer).toHaveCount(1);
    
    // Verify all 5 links are present in drawer
    for (const link of BASE_NAV_LINKS) {
      const drawerLink = drawer.locator(`a[href="${link.path}"]`);
      await expect(drawerLink, `Missing ${link.name} in mobile drawer on ${pagePath}`).toHaveCount(1);
    }
  });
}

/**
 * Test: Verify all navigation links are clickable and work
 */
for (const fromPage of PAGES_TO_TEST) {
  for (const toLink of BASE_NAV_LINKS) {
    // Skip clicking link to same page
    if (fromPage === toLink.path) continue;
    
    test(`Navigation from ${fromPage} to ${toLink.name} works`, async ({ page }) => {
      // Start at source page
      await page.goto(`${BASE_URL}${fromPage}`);
      
      // Click the navigation link
      const navLink = page.locator(`nav.core-nav a[href="${toLink.path}"]`);
      await navLink.click();
      
      // Verify we navigated to the correct page
      await expect(page).toHaveURL(`${BASE_URL}${toLink.path}`);
      
      // Verify the target page loaded (has header)
      await expect(page.locator('nav.core-nav')).toBeVisible();
    });
  }
}

/**
 * Test: Verify mobile drawer navigation works
 */
test('Mobile drawer opens and navigation works', async ({ page }) => {
  // Set mobile viewport
  await page.setViewportSize({ width: 375, height: 667 });
  
  await page.goto(`${BASE_URL}/home.html`);
  
  // Open hamburger menu
  const hamburger = page.locator('button.hamburger');
  await expect(hamburger).toBeVisible();
  await hamburger.click();
  
  // Drawer should be visible
  const drawer = page.locator('nav.nav-drawer');
  await expect(drawer).toHaveClass(/open/);
  
  // Click Library link in drawer
  const libraryLink = drawer.locator('a[href="/library.html"]');
  await libraryLink.click();
  
  // Should navigate to Library
  await expect(page).toHaveURL(`${BASE_URL}/library.html`);
});

/**
 * Test: Verify active state on current page
 */
for (const pagePath of PAGES_TO_TEST) {
  test(`Active state is correct on ${pagePath}`, async ({ page }) => {
    await page.goto(`${BASE_URL}${pagePath}`);
    
    const headerNav = page.locator('nav.core-nav');
    
    // Find which link should be active
    const expectedActive = BASE_NAV_LINKS.find(l => l.path === pagePath);
    
    if (expectedActive) {
      // This page's link should have 'active' class
      const activeLink = headerNav.locator(`a.active`);
      await expect(activeLink).toHaveAttribute('href', pagePath);
    }
  });
}

/**
 * Test: Verify no SSOT violations (no hardcoded navigation paths)
 */
test('No SSOT violations in page source', async ({ page }) => {
  await page.goto(`${BASE_URL}/home.html`);
  
  // Get page HTML
  const html = await page.content();
  
  // Check for hardcoded navigation patterns that violate SSOT
  const violations = [];
  
  // Look for hardcoded hrefs that don't match our 5 base paths
  const hardcodedPatterns = [
    /href="\/home"/g,      // Should be /home.html
    /href="\/cases"/g,     // Old SSOT path
    /href="\/documents"/g, // Old SSOT path
    /href="\/timeline"/g,  // Old SSOT path
    /href="\/settings"/g,  // Old SSOT path
  ];
  
  for (const pattern of hardcodedPatterns) {
    if (pattern.test(html)) {
      violations.push(`Found hardcoded path matching: ${pattern}`);
    }
  }
  
  expect(violations, `SSOT violations found: ${violations.join(', ')}`).toHaveLength(0);
});

/**
 * Test: Verify navigation survives page reload
 */
test('Navigation persists after page reload', async ({ page }) => {
  await page.goto(`${BASE_URL}/home.html`);
  
  // Click to Library
  await page.locator('nav.core-nav a[href="/library.html"]').click();
  await expect(page).toHaveURL(`${BASE_URL}/library.html`);
  
  // Reload page
  await page.reload();
  
  // Navigation should still be present
  const headerNav = page.locator('nav.core-nav');
  await expect(headerNav).toBeVisible();
  
  // All 5 links should still be there
  for (const link of BASE_NAV_LINKS) {
    await expect(headerNav.locator(`a[href="${link.path}"]`)).toBeVisible();
  }
});
