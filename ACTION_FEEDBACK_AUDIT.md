# Action Feedback Audit — 2026-06-21

> Every user-facing action must inform the user what's happening (in-progress) and the result (success/failure with details). No silent actions.

---

## 1. Headline Counts

| Metric | Count |
| --- | --- |
| `fetch()` calls across HTML pages | **124** across 32 files |
| `catch` blocks (any error handling at all) | **48** across 21 files |
| **Fetch calls with NO error handling (silent failures)** | **~76 (62%)** |
| `alert()` calls (browser-native, bad UX) | **82** across 17 files |
| Existing toast/notification helper components | **0** |
| Existing loading-overlay component | **1** (`static/components/loading-overlay.html`) |
| Pages with loading/spinner states | 27 files, inconsistent |
| Pages with `onclick`/`handleSubmit` handlers | 54 files, **499 handlers total** |

---

## 2. Current State — What's Broken

### A. Silent Failures (the big problem)

**~76 fetch calls have no `.catch()` block.** If the network fails, the server 500s, or the JSON is malformed, the user sees nothing. The button stays clickable, no spinner, no error, no confirmation. They click again, same thing. They assume Semptify is broken.

#### Worst offenders (fetch calls with no catch):

- `static/admin/dashboard.html` — 34 fetches, only 7 have catch (27 silent)
- `static/admin/review-checklist.html` — 20 fetches, only 3 have catch (17 silent)
- `static/admin/dev_lab.html` — 7 fetches, only 4 have catch (3 silent)
- `static/overlays/viewer.html` — 6 fetches, only 1 has catch (5 silent)
- `static/office/inbox.html` — 5 fetches, 4 catch (1 silent)
- `static/office/delivery.html` — 4 fetches, 4 catch (0 silent — good)
- `static/admin/module_flags.html` — 4 fetches, 2 catch (2 silent)
- `static/admin/contract-browser.html` — 3 fetches, 1 catch (2 silent)
- `static/admin/page-editor.html` — 3 fetches, 0 catch (3 silent)
- `static/library.html` — 3 fetches, 3 catch (0 silent — good)
- `static/onboarding/activate-vault.html` — 3 fetches, 1 catch (2 silent)
- `static/tenant/dashboard.html` — 3 fetches, 1 catch (2 silent)
- `static/tenant/documents.html` — 3 fetches, 1 catch (2 silent)
- 19 more files with 1-2 fetches each, mostly no catch

### B. `alert()` as Primary Feedback (bad UX)

**82 `alert()` calls across 17 files.** Browser-native alert() is:

- Blocking (locks the page)
- Ugly (browser chrome, not Semptify styling)
- Inaccessible (screen readers handle it inconsistently)
- Not dismissible without clicking OK
- Can't be styled, can't show rich content, can't auto-dismiss

#### Worst offenders:

- `static/admin/dashboard.html` — 22 alerts
- `static/office/inbox.html` — 14 alerts
- `static/admin/dev_lab.html` — 11 alerts
- `static/office/delivery.html` — 5 alerts
- `static/tools/generators.html` — 5 alerts
- `static/tools/calculators.html` — 4 alerts
- `static/office/signer.html` — 3 alerts
- `static/tenant/journal.html` — 3 alerts (including "Delete not yet implemented" — a stub alert)
- `static/tools/checklists.html` — 3 alerts

### C. No Unified Feedback System

- **Zero toast/notification components exist.** No `showToast()`, no `notify()`, no `Toast` class.
- Every page reinvents feedback: some use `alert()`, some use `innerHTML = 'Error: ...'`, some use `console.error()` (invisible to user), some do nothing.
- The existing `loading-overlay.html` component is good but only handles the in-progress state, not success/failure.
- No standard for: "what does a success message look like?", "what does an error message look like?", "how long does it stay?", "where does it appear?"

### D. Inconsistent Loading States

- `loading-overlay.html` exists with spinner + `btn--loading` class — good foundation
- 190 loading/spinner references across 27 files — but usage is inconsistent
- Some pages show a full-screen overlay, some show an inline spinner, some just disable the button, some do nothing
- No standard for: "when does loading start?", "when does it end?", "what if it takes 30 seconds?"

---

## 3. What's Already Good

- **`static/components/loading-overlay.html`** — solid foundation. Full-screen overlay + inline spinner + button loading state. Just needs to be used consistently.
- **`static/office/delivery.html`** — 4 fetches, 4 catch blocks. Model page.
- **`static/library.html`** — 3 fetches, 3 catch blocks. Model page.
- **`static/admin/dashboard.html`** — has a `setStatus()` pattern (34 matches) that could be promoted to the global helper.
- **`static/tenant/dashboard.html:337-342`** — inline error message pattern:

  ```js
  } catch (err) {
    console.error('Dashboard load error:', err);
    document.getElementById('hero-summary').innerHTML = 'Sign in to see your case dashboard.';
  }
  ```

  This is the right idea, just needs to be a reusable helper.

---

## 4. The Fix — Unified Action Feedback Helper

### Design: `static/components/feedback.html`

One component, included on every page, provides three functions:

```js
// 1. In-progress state (button becomes spinner, text changes)
SemptifyFeedback.start(buttonEl, 'Uploading...');

// 2. Success (toast appears, auto-dismisses, button restores)
SemptifyFeedback.success('Evidence uploaded to your vault. Timestamped and saved.');

// 3. Error (toast appears, stays until dismissed, button restores)
SemptifyFeedback.error('Upload failed. Check your connection and try again.', { detail: err.message });

// 4. Info (non-blocking, auto-dismisses)
SemptifyFeedback.info('Tip: Date and time are automatically saved with every upload.');

// 5. Story moment (after task completion — ties into Context Engine)
SemptifyFeedback.story({
  circumstance: 'My landlord stopped responding to repair requests...',
  task_completed: 'Uploaded photos and a written request to my vault.',
  outcome: 'When I sent the landlord the timestamped evidence, they sent a plumber within 48 hours.'
});
```text

### Toast Component Spec

- Fixed position, bottom-right (or top-center on mobile)
- Four variants: success (green), error (red), info (blue), story (warm yellow)
- Auto-dismiss after 5s for success/info, stay for error/story
- Dismissible by click
- Stackable (max 3 visible, queue the rest)
- Accessible: `role="status"` for success/info, `role="alert"` for error
- Calm tone, no animations that feel alarming

### Button Loading State

- Reuse existing `.btn--loading` class from `loading-overlay.html`
- `SemptifyFeedback.start(buttonEl, text)` sets the class + disables the button + updates `data-loading-text`
- `SemptifyFeedback.done(buttonEl)` restores the button

### Integration Pattern

Every fetch becomes:

```js
async function uploadEvidence(file) {
  SemptifyFeedback.start(uploadBtn, 'Uploading...');
  try {
    const res = await fetch('/api/vault/upload', { method: 'POST', body: formData });
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    const data = await res.json();
    SemptifyFeedback.success('Evidence uploaded. Timestamped and saved to your vault.');
    // Context Engine hook — surface a relevant story
    SemptifyFeedback.story(await fetchStoryForSubject('evidence'));
  } catch (err) {
    SemptifyFeedback.error('Upload failed. Check your connection and try again.', { detail: err.message });
  } finally {
    SemptifyFeedback.done(uploadBtn);
  }
}
```

---

## 5. Retrofit Plan (Priority Order)

### Tier 1 — Critical (silent failures on user-facing pages)

- [ ] Build `static/components/feedback.html` component
- [ ] Include on every page via base template
- [ ] Retrofit `static/tenant/journal.html` (3 alerts, 2 silent fetches)
- [ ] Retrofit `static/tenant/documents.html` (3 fetches, 2 silent)
- [ ] Retrofit `static/tenant/dashboard.html` (3 fetches, 2 silent)
- [ ] Retrofit `static/tenant/tools/letters.html` (2 alerts, 1 silent fetch)
- [ ] Retrofit `static/tenant/tools/deadlines.html` (1 alert, 0 catch)
- [ ] Retrofit `static/onboarding/activate-vault.html` (3 fetches, 2 silent)
- [ ] Retrofit `static/onboarding/index.html` (3 fetches, 0 catch)

### Tier 2 — Admin pages (high fetch count, bad UX)

- [ ] Retrofit `static/admin/dashboard.html` (22 alerts, 27 silent fetches — biggest offender)
- [ ] Retrofit `static/admin/review-checklist.html` (20 fetches, 17 silent)
- [ ] Retrofit `static/admin/dev_lab.html` (11 alerts, 3 silent fetches)
- [ ] Retrofit `static/admin/module_flags.html` (4 alerts, 2 silent fetches)
- [ ] Retrofit `static/admin/contract-browser.html` (1 alert, 2 silent fetches)
- [ ] Retrofit `static/admin/page-editor.html` (3 silent fetches)
- [ ] Retrofit `static/admin/api_workbook.html` (2 alerts, 1 silent fetch)
- [ ] Retrofit `static/admin/login.html` (2 alerts)

### Tier 3 — Office/advocate pages

- [ ] Retrofit `static/office/inbox.html` (14 alerts, 1 silent fetch)
- [ ] Retrofit `static/office/delivery.html` (5 alerts, 0 silent — already good)
- [ ] Retrofit `static/office/signer.html` (3 alerts)
- [ ] Retrofit `static/office/vault.html` (1 alert)
- [ ] Retrofit `static/overlays/viewer.html` (5 silent fetches)

### Tier 4 — Tools

- [ ] Retrofit `static/tools/generators.html` (5 alerts, 1 silent fetch)
- [ ] Retrofit `static/tools/calculators.html` (4 alerts, 1 silent fetch)
- [ ] Retrofit `static/tools/checklists.html` (3 alerts, 1 silent fetch)

### Tier 5 — Remaining pages with fetches

- [ ] Retrofit `static/components/preview-modal.html` (1 alert, 1 silent fetch)
- [ ] Retrofit `static/components/vault-portal.html` (1 alert, 1 silent fetch)
- [ ] Retrofit `static/filedored.html` (1 silent fetch)
- [ ] Retrofit `static/mndes/compliance-guide.html` (1 silent fetch)
- [ ] Retrofit `static/mndes/guide.html` (1 silent fetch)
- [ ] Retrofit `static/public/feedback.html` (1 silent fetch)
- [ ] Retrofit `static/public/welcome.html` (1 silent fetch)
- [ ] Retrofit `static/search.html` (1 silent fetch)
- [ ] Retrofit `static/onboarding/validation/validate-advocate.html` (2 alerts, 1 silent fetch)
- [ ] Retrofit `static/onboarding/validation/validate-legal.html` (2 alerts, 1 silent fetch)
- [ ] Retrofit `static/templates/journal-refactored.html` (1 alert, 1 silent fetch)
- [ ] Retrofit `static/reconnect/index.html` (1 silent fetch)
- [ ] Retrofit `static/tenant/tools/deadlines.html` (1 alert)

---

## 6. Backend Side (Python)

Every API endpoint should return a structured result that the frontend can display. Currently, endpoints return:

- `{"status": "ok"}` (vague)
- `{"detail": "..."}` (FastAPI error format)
- Raw data (no metadata)
- HTTP 500 with no body (silent crash)

### Proposed: Standardized Result Envelope

```python
{
  "ok": true,
  "message": "Evidence uploaded to vault.",  # user-displayable
  "detail": "File lease.pdf saved to /vault/documents/",  # optional, more info
  "data": { ... },  # the actual payload
  "next_steps": ["Review the uploaded document", "Add it to your timeline"]  # optional
}
```

This is a bigger change — defer to Phase 4. For now, focus on the frontend retrofit.

---

## 7. Ties Into Context Engine

The `SemptifyFeedback.story()` call is the bridge between Action Feedback and Context Engine. When a user completes a task:

1. Action Feedback shows success toast
2. Context Engine returns a relevant story
3. Story toast surfaces below the success toast
4. User can save the story to their journal

This is the "one visit and the outcome when they complete a task" flow the user described.

---

## 8. Next Steps

1. **Build `static/components/feedback.html`** — the toast + button-loading helper
2. **Include it in the base template** so every page gets it automatically
3. **Retrofit Tier 1 pages first** (tenant-facing, most impactful)
4. **Then Tier 2 admin pages** (highest silent-fetch count)
5. **Then Tier 3-5** as time permits
6. **Backend envelope** deferred to Phase 4

---

*Generated 2026-06-21 by action feedback audit. Snapshot, not a live document.*
