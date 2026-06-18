/**
 * Live Test: Case Builder Persistence (Task 3)
 *
 * Verifies:
 * - Case creation succeeds
 * - Case persists after Render restart
 * - Documents in case survive restart
 *
 * Prerequisites:
 * - User completes OAuth flow manually when prompted
 * - User has storage connected
 * - Ability to restart Render service (manual step in test)
 *
 * Run: npx playwright test live_case_persistence.spec.js --headed
 * Env vars: SEMPTIFY_URL
 *
 * NOTE: This test requires manual Render restart between phases.
 * The test will pause and prompt you to restart Render.
 * Semptify uses OAuth-based auth (no username/password).
 */

const { test, expect } = require('@playwright/test');

const BASE = process.env.SEMPTIFY_URL || 'https://semptify.org';

test('case persists after render restart', async ({ page, request }) => {
  // Navigate to storage providers (OAuth entry point)
  await page.goto(BASE + '/storage/providers');

  // Wait for user to complete OAuth and be redirected to tenant home
  console.log('\n=== MANUAL STEP REQUIRED ===');
  console.log('Please complete OAuth sign-in in the browser window.');
  console.log('NOTE: Google may block Playwright browser. Try Dropbox or OneDrive first.');
  console.log('The test will continue once you reach any tenant page\n');

  // Wait for any URL that indicates successful auth
  try {
    await page.waitForURL(url => url.pathname.includes('/tenant'), { timeout: 120000 });
  } catch (e) {
    console.log('\n=== OAUTH TIMEOUT OR BLOCKED ===');
    console.log('Google OAuth may have blocked the Playwright browser.');
    console.log('Please test manually:');
    console.log('1. Open https://semptify.org/storage/providers in your regular browser');
    console.log('2. Complete OAuth with Dropbox or OneDrive');
    console.log('3. Create a case, restart Render, verify case persists\n');
    throw new Error('OAuth blocked or timeout - manual verification required');
  }

  const cookies = await page.context().cookies();
  const sessionCookie = cookies.find(c => c.name === 'semptify_session');
  expect(sessionCookie).toBeTruthy();

  // Create a case
  const createCaseRes = await request.post(BASE + '/api/cases', {
    headers: {
      'Cookie': `semptify_session=${sessionCookie.value}`,
      'Content-Type': 'application/json',
    },
    data: {
      title: 'Persistence Test Case',
      description: 'Test case for Render restart verification',
      case_type: 'eviction',
    },
  });

  expect(createCaseRes.ok()).toBeTruthy();
  const caseData = await createCaseRes.json();
  expect(caseData.case_id).toBeDefined();

  const caseId = caseData.case_id;

  // Upload a document to attach to case
  const fileBuffer = Buffer.from('Test document for case persistence');
  const uploadRes = await request.post(BASE + '/api/vault/upload', {
    multipart: {
      file: {
        name: 'case-test.txt',
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
  const vaultId = uploadData.vault_id;

  // Attach document to case
  const attachRes = await request.post(BASE + `/api/cases/${caseId}/documents`, {
    headers: {
      'Cookie': `semptify_session=${sessionCookie.value}`,
      'Content-Type': 'application/json',
    },
    data: {
      vault_id: vaultId,
      document_type: 'evidence',
    },
  });

  expect(attachRes.ok()).toBeTruthy();

  // Verify case exists before restart
  const beforeRes = await request.get(BASE + `/api/cases/${caseId}`, {
    headers: {
      'Cookie': `semptify_session=${sessionCookie.value}`,
    },
  });

  expect(beforeRes.ok()).toBeTruthy();
  const beforeData = await beforeRes.json();
  expect(beforeData.case_id).toBe(caseId);
  expect(beforeData.documents).toBeInstanceOf(Array);
  expect(beforeData.documents.length).toBeGreaterThan(0);

  console.log('\n=== MANUAL STEP REQUIRED ===');
  console.log('Case created:', caseId);
  console.log('Please restart the Render service now.');
  console.log('Press Enter in this terminal when Render is back online...');
  console.log('=============================\n');

  // Pause for manual Render restart
  // In CI/CD, this would be a separate job with actual restart
  await new Promise(resolve => {
    process.stdin.once('data', resolve);
  });

  // Wait for Render to be back online
  await page.waitForTimeout(10000);

  // Verify case still exists after restart
  const afterRes = await request.get(BASE + `/api/cases/${caseId}`, {
    headers: {
      'Cookie': `semptify_session=${sessionCookie.value}`,
    },
  });

  expect(afterRes.ok()).toBeTruthy();
  const afterData = await afterRes.json();

  expect(afterData.case_id).toBe(caseId);
  expect(afterData.title).toBe('Persistence Test Case');
  expect(afterData.documents).toBeInstanceOf(Array);
  expect(afterData.documents.length).toBeGreaterThan(0);

  // Verify document still attached
  const attachedDoc = afterData.documents.find(d => d.vault_id === vaultId);
  expect(attachedDoc).toBeDefined();
});
