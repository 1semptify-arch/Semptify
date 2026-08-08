/**
 * Live Test: Upload → Timeline Row (Task 2)
 *
 * Verifies:
 * - Document upload succeeds
 * - Timeline row with event_type "document_uploaded" appears
 * - Timeline row contains correct vault_id
 *
 * Prerequisites:
 * - User completes OAuth flow manually when prompted
 * - User has storage connected (Google Drive/Dropbox/OneDrive)
 *
 * Run: npx playwright test live_upload_timeline.spec.js --headed
 * Env vars: SEMPTIFY_URL
 *
 * NOTE: Semptify uses OAuth-based auth (no username/password).
 * The test will open a browser and wait for you to complete OAuth sign-in.
 */

const { test, expect } = require('@playwright/test');

const BASE = process.env.SEMPTIFY_URL || 'https://semptify.org';

// Skip all tests in this file unless running interactively
// This test requires manual OAuth sign-in in a browser window
test.describe('live upload timeline (requires manual OAuth)', () => {
  test.skip(!process.env.SEMPTIFY_LIVE_TESTS, 'Set SEMPTIFY_LIVE_TESTS=1 to run interactive OAuth tests');

test('upload document creates timeline row', async ({ page, request }) => {
  // Navigate to storage providers (OAuth entry point)
  await page.goto(BASE + '/storage/providers');

  // Wait for user to complete OAuth and be redirected to tenant home
  // This gives the user time to click a provider and sign in
  console.log('\n=== MANUAL STEP REQUIRED ===');
  console.log('Please complete OAuth sign-in in the browser window.');
  console.log('NOTE: Google may block Playwright browser. Try Dropbox or OneDrive first.');
  console.log('The test will continue once you reach any tenant page\n');

  // Wait for any URL that indicates successful auth (tenant home, dashboard, etc.)
  // If OAuth fails, user can manually test via browser
  try {
    await page.waitForURL(url => url.pathname.includes('/tenant'), { timeout: 120000 });
  } catch (e) {
    console.log('\n=== OAUTH TIMEOUT OR BLOCKED ===');
    console.log('Google OAuth may have blocked the Playwright browser.');
    console.log('Please test manually:');
    console.log('1. Open https://semptify.org/storage/providers in your regular browser');
    console.log('2. Complete OAuth with Dropbox or OneDrive');
    console.log('3. Upload a document and check /api/timeline/unified for document_uploaded event\n');
    throw new Error('OAuth blocked or timeout - manual verification required');
  }

  // Get session cookie for API calls
  const cookies = await page.context().cookies();
  const sessionCookie = cookies.find(c => c.name === 'semptify_session');
  expect(sessionCookie).toBeTruthy();

  // Upload a test document
  const fileBuffer = Buffer.from('Test document content for timeline verification');
  const uploadRes = await request.post(BASE + '/api/vault/upload', {
    multipart: {
      file: {
        name: 'timeline-test.txt',
        mimeType: 'text/plain',
        buffer: fileBuffer,
      },
    },
    headers: {
      'Cookie': `semptify_session=${sessionCookie.value}`,
    },
  });

  expect(uploadRes.ok()).toBeTruthy();
  const uploadData = await uploadRes.json();
  expect(uploadData.vault_id).toBeDefined();

  // Wait for event processing (timeline is async)
  await page.waitForTimeout(2000);

  // Check timeline API for document_uploaded event
  const timelineRes = await request.get(BASE + '/api/timeline/unified', {
    headers: {
      'Cookie': `semptify_session=${sessionCookie.value}`,
    },
  });

  expect(timelineRes.ok()).toBeTruthy();
  const timelineData = await timelineRes.json();
  expect(timelineData.events).toBeInstanceOf(Array);

  // Find document_uploaded event
  const uploadEvent = timelineData.events.find(
    e => e.event_type === 'document_uploaded' && e.vault_id === uploadData.vault_id
  );

  expect(uploadEvent).toBeDefined();
  expect(uploadEvent.timestamp).toBeDefined();
});
});
