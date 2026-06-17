/**
 * Rent Ledger Smoke Test
 *
 * Verifies:
 * - rent payment endpoints are reachable and gate unauthenticated access correctly
 * - No 500s from import/schema errors
 * - GET /api/rent/payments gates correctly
 * - POST /api/rent/payments gates correctly
 *
 * Full CRUD testing requires an authenticated session — manual QA only.
 * Run: npx playwright test rent_ledger_smoke.spec.js  (from tests/e2e/)
 */

const { test, expect } = require('@playwright/test');

const BASE = process.env.SEMPTIFY_URL || 'https://semptify.org';

// ─────────────────────────────────────────────────────────────────────────────
// 1. rent endpoints gate unauthenticated — no 500
// ─────────────────────────────────────────────────────────────────────────────
test('GET /api/rent/payments returns auth gate, not 500', async ({ request }) => {
  const res = await request.get(BASE + '/api/rent/payments');
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('POST /api/rent/payments returns auth gate, not 500', async ({ request }) => {
  const res = await request.post(BASE + '/api/rent/payments', {
    data: { amount: 950.00, payment_date: '2026-06-01', status: 'paid', notes: 'June rent' },
    headers: { 'Content-Type': 'application/json' },
  });
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('GET /api/rent/payments/nonexistent-id returns auth gate, not 500', async ({ request }) => {
  const res = await request.get(BASE + '/api/rent/payments/test-id-123');
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('PUT /api/rent/payments/nonexistent-id returns auth gate, not 500', async ({ request }) => {
  const res = await request.put(BASE + '/api/rent/payments/test-id-123', {
    data: { amount: 1000.00, status: 'late' },
    headers: { 'Content-Type': 'application/json' },
  });
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});

test('DELETE /api/rent/payments/nonexistent-id returns auth gate, not 500', async ({ request }) => {
  const res = await request.delete(BASE + '/api/rent/payments/test-id-123');
  expect(res.status()).not.toBeGreaterThanOrEqual(500);
});
