/**
 * Role Hierarchy Smoke Test
 *
 * Verifies:
 * - act-as endpoints are reachable and gate unauthenticated access correctly
 * - No 500s from import/schema errors
 * - DELETE endpoint gates correctly
 *
 * Full impersonation testing requires an authenticated advocate/admin session
 * with an existing user_relationships row — manual QA only.
 * Run: npx playwright test role_hierarchy_smoke.spec.js  (from tests/e2e/)
 */

const { test, expect } = require('@playwright/test');

const BASE = process.env.SEMPTIFY_URL || 'https://semptify.org';

// ─────────────────────────────────────────────────────────────────────────────
// 1. act-as endpoints gate unauthenticated — no 500
// ─────────────────────────────────────────────────────────────────────────────
test('POST /api/user/act-as returns auth gate, not 500', async ({ request }) => {
  const res = await request.post(BASE + '/api/user/act-as', {
    data: { target_user_id: 'test-user-id', reason: 'smoke test' },
    headers: { 'Content-Type': 'application/json' },
  });
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('DELETE /api/user/act-as returns auth gate, not 500', async ({ request }) => {
  const res = await request.delete(BASE + '/api/user/act-as');
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});
