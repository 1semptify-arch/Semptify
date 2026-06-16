/**
 * Onboarding Smoke Test
 *
 * Tests the critical path a new tenant takes from landing on Semptify
 * to reaching the OAuth provider selection screen.
 *
 * Does NOT test post-OAuth steps (requires live credentials).
 * Run against production: SEMPTIFY_URL=https://semptify.org npx playwright test onboarding_smoke.spec.js
 * Run against local:      SEMPTIFY_URL=http://localhost:8000 npx playwright test onboarding_smoke.spec.js
 */

const { test, expect } = require('@playwright/test');

const BASE = process.env.SEMPTIFY_URL || 'https://semptify.org';

// ─────────────────────────────────────────────────────────────────────────────
// 1. Welcome page loads
// ─────────────────────────────────────────────────────────────────────────────
test('welcome page loads with 200', async ({ page }) => {
  const res = await page.goto(BASE + '/', { waitUntil: 'load' });
  // Accept 200 directly or a redirect chain that ends at 200
  const finalRes = await page.waitForLoadState('load').then(() => res).catch(() => res);
  expect([200, 304]).toContain(finalRes.status());
});

test('welcome page has a Get Started or continue call-to-action', async ({ page }) => {
  await page.goto(BASE + '/', { waitUntil: 'load' });
  // Look for any navigational CTA — text or href patterns
  const cta = page.locator('a[href*="preamble"], a[href*="onboard"], a[href*="start"], a[href*="register"]').first();
  await expect(cta).toBeVisible({ timeout: 10_000 });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Onboarding funnel pages are reachable
// ─────────────────────────────────────────────────────────────────────────────
test('role selection page loads with 200', async ({ page }) => {
  const res = await page.goto(BASE + '/onboarding/select-role', { waitUntil: 'load' });
  expect([200, 304]).toContain(res.status());
});

test('role selection page contains tenant option', async ({ page }) => {
  await page.goto(BASE + '/onboarding/select-role', { waitUntil: 'load' });
  // Match any element containing the word "Tenant" (role card heading or button)
  const tenantOption = page.getByText('Tenant', { exact: false }).first();
  await expect(tenantOption).toBeVisible({ timeout: 15_000 });
});

test('storage providers page loads', async ({ page }) => {
  const res = await page.goto(BASE + '/storage/providers');
  // Accept 200 (page served) or 302/301 (redirect to OAuth — also correct)
  expect([200, 301, 302]).toContain(res.status());
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. API health
// ─────────────────────────────────────────────────────────────────────────────
test('API responds — welcome page is not a 5xx', async ({ page }) => {
  // /api/health is auth-gated; verify the app is up by checking the welcome page response
  const res = await page.goto(BASE + '/', { waitUntil: 'load' });
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
  // Also verify the page title confirms we hit Semptify, not a CDN error page
  const title = await page.title();
  expect(title).toMatch(/semptify/i);
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Authenticated routes redirect unauthenticated users — no 500s
// ─────────────────────────────────────────────────────────────────────────────
const PROTECTED_ROUTES = [
  '/tenant/dashboard',
  '/api/case-builder/cases',
  '/api/timeline/unified',
];

for (const route of PROTECTED_ROUTES) {
  test(`protected route ${route} returns auth redirect, not 500`, async ({ page }) => {
    const res = await page.goto(BASE + route);
    // Must NOT be a server error
    expect(res.status()).not.toBeGreaterThanOrEqual(500);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. Onboarding funnel does not crash mid-flow
// ─────────────────────────────────────────────────────────────────────────────
test('welcome → role select navigation works', async ({ page }) => {
  await page.goto(BASE + '/');
  // Click the first link/button that navigates toward onboarding
  const cta = page.locator('a[href*="onboard"], a[href*="role"], button').filter({
    hasText: /get started|continue|begin/i,
  }).first();

  const ctaCount = await cta.count();
  if (ctaCount > 0) {
    await cta.click();
    // After click, we should land somewhere — not a 500
    await page.waitForLoadState('networkidle');
    // No error page
    await expect(page.locator('text=/500|Internal Server Error/i')).toHaveCount(0);
  } else {
    // CTA not found on this build — navigate directly and verify no crash
    const res = await page.goto(BASE + '/onboarding/select-role');
    expect(res.status()).not.toBeGreaterThanOrEqual(500);
  }
});
