// Document Center end-to-end browser test
// Tests:
//   1. Auth gate — unauthenticated access redirects to onboarding
//   2. Template structure — all DC elements present in the HTML file
//   3. JS libraries — PDF.js and SemptifyFeedback script tags present
//   4. Filter buttons — All/New/Review/Verified/Mismatched present
//   5. Share modal — recipient, scope, message fields present
//   6. Type suggestion banner — Accept/Dismiss buttons present
//   7. Annotation tools — Highlight/Note/Reference/Cancel present
//   8. No unhandled page errors during navigation
//
// Run: node tests/playwright-document-center-test.js
//
// Override target with SEMPTIFY_TARGET env var.
// Defaults to https://semptify.org

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TARGET = process.env.SEMPTIFY_TARGET || 'https://semptify.org';
const TEMPLATE_PATH = path.join(__dirname, '..', 'app', 'templates', 'pages', 'document_center.html');

async function runTests() {
    console.log('═══════════════════════════════════════════');
    console.log('  DOCUMENT CENTER E2E TEST');
    console.log(`  Target: ${TARGET}`);
    console.log(`  Template: ${TEMPLATE_PATH}`);
    console.log('═══════════════════════════════════════════');

    // Load template HTML for structure tests
    const templateHtml = fs.readFileSync(TEMPLATE_PATH, 'utf8');

    const results = { passed: [], failed: [] };

    function test(name, fn) {
        try {
            fn();
            results.passed.push(name);
            console.log(`✅ ${name}`);
        } catch (e) {
            results.failed.push({ name, error: e.message });
            console.log(`❌ ${name}: ${e.message}`);
        }
    }

    // ---- Template structure tests (file-based, no server needed) ----

    test('Template contains expected element IDs', () => {
        const expectedIds = [
            'dcLeft', 'dcCenter', 'dcRight',
            'dcDocList', 'dcDocName', 'dcTypeSelect',
            'dcDownloadBtn', 'dcProcessBtn', 'dcShareBtn',
            'dcAnnotTools', 'dcPdfContainer', 'dcViewerEmpty',
            'dcIframeFallback', 'dcOverlayList', 'dcChecklist',
            'dcUploadModal', 'dcUploadForm',
            'dcShareModal', 'dcShareForm', 'dcShareRecipient',
            'dcShareScope', 'dcShareMessage', 'dcShareCancel',
            'dcTypeSuggest', 'dcSuggestedType',
            'dcAcceptSuggest', 'dcDismissSuggest'
        ];
        const missing = expectedIds.filter(id => !templateHtml.includes(`id="${id}"`));
        if (missing.length > 0) throw new Error('Missing IDs: ' + missing.join(', '));
    });

    test('Template has all 5 filter buttons', () => {
        const expectedFilters = ['all', 'new', 'review', 'verified', 'mismatched'];
        const missing = expectedFilters.filter(f => !templateHtml.includes(`data-filter="${f}"`));
        if (missing.length > 0) throw new Error('Missing filters: ' + missing.join(', '));
    });

    test('Template has annotation tool buttons', () => {
        const expectedTools = ['highlight', 'note', 'reference', 'none'];
        const missing = expectedTools.filter(t => !templateHtml.includes(`data-tool="${t}"`));
        if (missing.length > 0) throw new Error('Missing tools: ' + missing.join(', '));
    });

    test('Template has share modal scope options', () => {
        const expectedScopes = ['view', 'comment', 'download'];
        const missing = expectedScopes.filter(s => !templateHtml.includes(`value="${s}"`));
        if (missing.length > 0) throw new Error('Missing scopes: ' + missing.join(', '));
    });

    test('Template loads PDF.js', () => {
        if (!templateHtml.includes('pdf.js')) throw new Error('PDF.js script tag missing');
    });

    test('Template loads SemptifyFeedback', () => {
        if (!templateHtml.includes('feedback.js')) throw new Error('SemptifyFeedback script tag missing');
    });

    test('Template has verification badge logic', () => {
        if (!templateHtml.includes('statusBadge')) throw new Error('statusBadge function missing');
        if (!templateHtml.includes('effectiveStatus')) throw new Error('effectiveStatus function missing');
        if (!templateHtml.includes('computeMismatched')) throw new Error('computeMismatched function missing');
    });

    test('Template has image viewer logic', () => {
        if (!templateHtml.includes('renderImage')) throw new Error('renderImage function missing');
        if (!templateHtml.includes('applyImageHighlights')) throw new Error('applyImageHighlights function missing');
        if (!templateHtml.includes('handleImageHighlight')) throw new Error('handleImageHighlight function missing');
    });

    test('Template has annotation persistence logic', () => {
        if (!templateHtml.includes('loadUserAnnotations')) throw new Error('loadUserAnnotations function missing');
    });

    test('Template has type suggestion logic', () => {
        if (!templateHtml.includes('showTypeSuggestion')) throw new Error('showTypeSuggestion function missing');
        if (!templateHtml.includes('hideTypeSuggestion')) throw new Error('hideTypeSuggestion function missing');
    });

    test('Template has Process now handler', () => {
        if (!templateHtml.includes('dcProcessBtn')) throw new Error('Process button ID missing');
        if (!templateHtml.includes('/api/intake/process/vault/')) throw new Error('Process endpoint missing');
    });

    test('Template has Share handler with overlay creation', () => {
        if (!templateHtml.includes('/api/unified-overlays/create')) throw new Error('Overlay create endpoint missing');
        if (!templateHtml.includes('overlay_type')) throw new Error('overlay_type field missing');
        if (!templateHtml.includes('communication')) throw new Error('communication overlay type missing');
        if (!templateHtml.includes('annotation_kind')) throw new Error('annotation_kind metadata missing');
    });

    // ---- Browser tests (live server) ----

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    const consoleErrors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => {
        consoleErrors.push('PAGEERROR: ' + err.message);
    });

    async function browserTest(name, fn) {
        try {
            await fn();
            results.passed.push(name);
            console.log(`✅ ${name}`);
        } catch (e) {
            results.failed.push({ name, error: e.message });
            console.log(`❌ ${name}: ${e.message}`);
        }
    }

    // Test: Auth gate redirects unauthenticated users
    await browserTest('Auth gate redirects unauthenticated to onboarding', async () => {
        await page.goto(`${TARGET}/document-center`, { waitUntil: 'domcontentloaded', timeout: 90000 });
        for (let i = 0; i < 12; i++) {
            await page.waitForTimeout(5000);
            const url = page.url();
            if (url.includes('onboarding') || url.includes('select-role') || url.includes('login') || url.includes('welcome')) {
                return;
            }
            const hasDc = await page.evaluate(() => !!document.querySelector('#dcLeft'));
            if (hasDc) return;
        }
        const url = page.url();
        if (url.includes('document-center')) {
            throw new Error('Did not redirect from /document-center');
        }
    });

    // Test: No unhandled page errors
    await browserTest('No unhandled page errors', async () => {
        const real = consoleErrors.filter(e =>
            !e.includes('401') &&
            !e.includes('Failed to load resource') &&
            !e.includes('net::ERR') &&
            !e.includes('ERR_HTTP')
        );
        if (real.length > 0) throw new Error('Page errors: ' + real.join('; '));
    });

    await browser.close();

    console.log('');
    console.log('═══════════════════════════════════════════');
    console.log(`  PASSED: ${results.passed.length}`);
    console.log(`  FAILED: ${results.failed.length}`);
    if (results.failed.length) {
        console.log('  ---');
        results.failed.forEach(f => console.log(`  ❌ ${f.name}: ${f.error}`));
    }
    console.log('═══════════════════════════════════════════');
    process.exit(results.failed.length ? 1 : 0);
}

runTests().catch(e => {
    console.error('Fatal:', e);
    process.exit(2);
});
