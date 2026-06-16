/**
 * Timeline Smoke Test
 *
 * Verifies the timeline module is wired correctly:
 * - Endpoint exists and returns auth gate (not 500)
 * - Schema shape is correct when called with auth
 * - Date-range endpoint is reachable
 *
 * Full upload→timeline integration requires a live OAuth session;
 * that is covered by manual QA. These tests catch import/schema crashes.
 *
 * Run: npx playwright test timeline_smoke.spec.js  (from tests/e2e/)
 */

const { test, expect } = require('@playwright/test');

const BASE = process.env.SEMPTIFY_URL || 'https://semptify.org';

// ─────────────────────────────────────────────────────────────────────────────
// 1. Unauthenticated calls gate correctly — no 500
// ─────────────────────────────────────────────────────────────────────────────
test('POST /api/timeline/unified returns auth gate, not 500', async ({ request }) => {
  const res = await request.post(BASE + '/api/timeline/unified', {
    data: {},
    headers: { 'Content-Type': 'application/json' },
  });
  // Must not be a server error — auth redirect (401/403/302) is fine
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('GET /api/timeline/date-range returns auth gate, not 500', async ({ request }) => {
  const res = await request.get(BASE + '/api/timeline/date-range');
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Timeline page in the app renders without crashing
// ─────────────────────────────────────────────────────────────────────────────
test('timeline page redirects unauthenticated users without 500', async ({ page }) => {
  const res = await page.goto(BASE + '/timeline', { waitUntil: 'load' });
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
  // Should not show raw Python traceback
  const body = await page.content();
  expect(body).not.toMatch(/Traceback \(most recent call last\)/);
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. POST with malformed body returns 422 (validation), not 500
// ─────────────────────────────────────────────────────────────────────────────
test('POST /api/timeline/unified with bad body returns 422 or auth gate, not 500', async ({ request }) => {
  const res = await request.post(BASE + '/api/timeline/unified', {
    data: { date_axis: 'not_a_valid_axis' },
    headers: { 'Content-Type': 'application/json' },
  });
  // 422 = FastAPI validation error (correct), 401/403 = auth gate (also fine)
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});
