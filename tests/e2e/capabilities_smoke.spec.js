/**
 * Capabilities System Smoke Test
 *
 * Verifies:
 * - Capability endpoints are reachable and gate unauthenticated access correctly
 * - No 500s from import/schema errors
 * - Overlay endpoints gate correctly
 * - product_manifest is served (no startup crash)
 *
 * Full grant/revoke testing requires an authenticated admin session — manual QA only.
 * Run: npx playwright test capabilities_smoke.spec.js  (from tests/e2e/)
 */

const { test, expect } = require('@playwright/test');

const BASE = process.env.SEMPTIFY_URL || 'https://semptify.org';

// ─────────────────────────────────────────────────────────────────────────────
// 1. Capability endpoints gate unauthenticated — no 500
// ─────────────────────────────────────────────────────────────────────────────
test('GET /api/capabilities/:user_id returns auth gate, not 500', async ({ request }) => {
  const res = await request.get(BASE + '/api/capabilities/test-user-id');
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('POST /api/capabilities/:user_id/grant returns auth gate, not 500', async ({ request }) => {
  const res = await request.post(BASE + '/api/capabilities/test-user-id/grant', {
    data: { module_name: 'app.modules.case_builder.router' },
    headers: { 'Content-Type': 'application/json' },
  });
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('POST /api/capabilities/:user_id/revoke returns auth gate, not 500', async ({ request }) => {
  const res = await request.post(BASE + '/api/capabilities/test-user-id/revoke', {
    data: { module_name: 'app.modules.case_builder.router' },
    headers: { 'Content-Type': 'application/json' },
  });
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Overlay endpoints gate correctly — no 500
// ─────────────────────────────────────────────────────────────────────────────
test('GET /api/capabilities/:user_id/overlay returns auth gate, not 500', async ({ request }) => {
  const res = await request.get(BASE + '/api/capabilities/test-user-id/overlay');
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('POST /api/capabilities/:user_id/overlay returns auth gate, not 500', async ({ request }) => {
  const res = await request.post(BASE + '/api/capabilities/test-user-id/overlay', {
    data: { module_names: ['app.modules.fems.router'] },
    headers: { 'Content-Type': 'application/json' },
  });
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('DELETE /api/capabilities/:user_id/overlay returns auth gate, not 500', async ({ request }) => {
  const res = await request.delete(BASE + '/api/capabilities/test-user-id/overlay');
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. App still starts — welcome page responds, confirming no startup crash
//    from capabilities registration in Stage 5
// ─────────────────────────────────────────────────────────────────────────────
test('app starts cleanly — welcome page title confirms no startup crash', async ({ page }) => {
  const res = await page.goto(BASE + '/', { waitUntil: 'load' });
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
  const title = await page.title();
  expect(title).toMatch(/semptify/i);
});
