/**
 * Live Test: Capability Seeding (Task 4)
 *
 * Verifies:
 * - Fresh login triggers capability seeding
 * - user_capabilities table has rows for the user
 * - Capabilities include base tier capabilities
 *
 * Prerequisites:
 * - User completes OAuth flow manually when prompted
 * - Direct PostgreSQL access (or API endpoint to check capabilities)
 *
 * Run: npx playwright test live_capability_seeding.spec.js --headed
 * Env vars: SEMPTIFY_URL, DATABASE_URL
 *
 * NOTE: Requires DATABASE_URL for direct PostgreSQL access.
 * Semptify uses OAuth-based auth (no username/password).
 */

const { test, expect } = require('@playwright/test');
const { Pool } = require('pg');

const BASE = process.env.SEMPTIFY_URL || 'https://semptify.org';
const DATABASE_URL = process.env.DATABASE_URL;

test('fresh login seeds capabilities', async ({ page, request }) => {
  // Clear existing session (logout)
  await page.goto(BASE + '/logout');
  await page.context().clearCookies();

  // Navigate to storage providers (OAuth entry point)
  await page.goto(BASE + '/storage/providers');

  // Wait for user to complete OAuth and be redirected to tenant home
  console.log('\n=== MANUAL STEP REQUIRED ===');
  console.log('Please complete OAuth sign-in in the browser window.');
  console.log('Select Google Drive, Dropbox, or OneDrive and authorize Semptify.');
  console.log('The test will continue once you reach /tenant/home\n');

  await page.waitForURL(BASE + '/tenant/home', { timeout: 120000 });

  const cookies = await page.context().cookies();
  const sessionCookie = cookies.find(c => c.name === 'semptify_session');
  expect(sessionCookie).toBeTruthy();

  // Extract user_id from session cookie
  const userId = sessionCookie.value.split('.')[0];

  // Check capabilities via API (no DB access needed)
  const capsRes = await request.get(BASE + '/api/capabilities', {
    headers: {
      'Cookie': `semptify_session=${sessionCookie.value}`,
    },
  });

  expect(capsRes.ok()).toBeTruthy();
  const capsData = await capsRes.json();

  expect(capsData.capabilities).toBeInstanceOf(Array);
  expect(capsData.capabilities.length).toBeGreaterThan(0);

  // Verify base capabilities are present
  const baseCaps = ['vault_upload', 'timeline_view', 'documents_view'];
  const presentCaps = capsData.capabilities.map(c => c.capability_id);

  for (const cap of baseCaps) {
    expect(presentCaps).toContain(cap);
  }

  // If DATABASE_URL is provided, verify DB directly
  if (DATABASE_URL) {
    const pool = new Pool({ connectionString: DATABASE_URL });

    try {
      const result = await pool.query(
        'SELECT * FROM user_capabilities WHERE user_id = $1',
        [userId]
      );

      expect(result.rows.length).toBeGreaterThan(0);

      // Verify at least one capability has a granted_at timestamp
      const seededCap = result.rows.find(r => r.granted_at !== null);
      expect(seededCap).toBeDefined();
    } finally {
      await pool.end();
    }
  }
});
