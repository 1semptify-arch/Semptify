# Plan: Quick Document Button + Monthly Reminders

## Philosophy
**"Document Everything First"** - Semptify believes in being proactive in tenancy by helping you before you're in trouble. The first word is always: **Document Everything!**

---

## Features to Implement

### 1. Quick Document Button (Always Visible)
One-tap upload from any page - make documenting frictionless.

**Location:** Floating action button (FAB) in bottom-right corner of all pages

**Behavior:**
- Camera icon 📸 + "Document" label
- Click navigates to `document_intake.html?quick=true`
- Uses existing `/api/vault/upload` endpoint with ID tokens
- All existing security (Bearer tokens, CORS, validation) unchanged

**Styling:**
- Position: `fixed`, bottom-right, `z-index: 1000`
- Color: Semptify blue (#3B5998), round FAB with shadow
- Mobile: Larger touch target (56px minimum)

**Implementation:** Add to `static/js/header.js` so it appears on all pages

---

### 2. Monthly Documentation Reminders
Proactive prompts to keep users documenting consistently.

**Reminder Types:**
- **1st of month:** "Time to save this month's rent receipt"
- **15th of month:** "Any maintenance issues to document?"
- **Other days:** "Keep your case file growing - document something today"

**Logic (localStorage-based):**
```javascript
// Track last documentation
localStorage.getItem('lastDocumentDate')

// Track if reminder dismissed this month
localStorage.getItem('reminderDismissed')

// Show reminder if:
// - >30 days since last document AND
// - Not dismissed this month
```

**Display:**
- Toast notification using existing `notification-toast.js`
- Dismissable with "Remind me later" or "I'll document now"
- "Document now" navigates to `document_intake.html`

**Implementation:** Create new `static/js/reminders.js`, include via `header.js`

---

### 3. Security (Unchanged)
All existing security measures remain in place:
- Bearer token authentication
- ID tokens for user identification
- Existing `/api/vault/upload` endpoint
- CORS configuration
- File validation and sanitization
- Same authentication flow throughout

---

## Technical Implementation

### File: `static/js/header.js` (Modify)
Add Quick Document FAB after existing header injection:

```javascript
// Quick Document FAB
const fab = document.createElement('a');
fab.href = '/static/document_intake.html?quick=true';
fab.className = 'quick-document-fab';
fab.innerHTML = '📸 Document';
fab.title = 'Quick Document - Upload photo, receipt, or screenshot';
document.body.appendChild(fab);

// FAB Styles
const fabStyle = document.createElement('style');
fabStyle.textContent = `
  .quick-document-fab {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #3B5998;
    color: white;
    padding: 16px 20px;
    border-radius: 50px;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.95rem;
    box-shadow: 0 4px 12px rgba(59, 89, 152, 0.4);
    z-index: 1000;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .quick-document-fab:hover {
    background: #2d4a7c;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(59, 89, 152, 0.5);
  }
  @media (max-width: 600px) {
    .quick-document-fab {
      bottom: 16px;
      right: 16px;
      padding: 14px 18px;
    }
  }
`;
document.head.appendChild(fabStyle);
```

### File: `static/js/reminders.js` (Create New)

```javascript
// Documentation Reminders System
(function() {
  const REMINDER_KEY = 'semptify_reminder_dismissed';
  const LAST_DOC_KEY = 'semptify_last_document';
  
  function shouldShowReminder() {
    const lastDoc = localStorage.getItem(LAST_DOC_KEY);
    const dismissed = localStorage.getItem(REMINDER_KEY);
    const now = new Date();
    const thisMonth = `${now.getFullYear()}-${now.getMonth()}`;
    
    // Don't show if dismissed this month
    if (dismissed === thisMonth) return false;
    
    // Show if never documented or >30 days ago
    if (!lastDoc) return true;
    const daysSince = (now - new Date(lastDoc)) / (1000 * 60 * 60 * 24);
    return daysSince > 30;
  }
  
  function getReminderMessage() {
    const day = new Date().getDate();
    if (day <= 5) return "🧾 Time to save this month's rent receipt!";
    if (day >= 13 && day <= 17) return "🔧 Any maintenance issues to document?";
    return "📄 Keep your case file growing - document something today!";
  }
  
  function showReminder() {
    if (!shouldShowReminder()) return;
    
    // Use existing toast system if available
    if (window.showToast) {
      window.showToast(getReminderMessage(), 'info', 10000, {
        action: { text: 'Document Now', href: '/static/document_intake.html' },
        onDismiss: () => {
          const now = new Date();
          localStorage.setItem(REMINDER_KEY, `${now.getFullYear()}-${now.getMonth()}`);
        }
      });
    }
  }
  
  // Mark document uploaded (call from document_intake.html on success)
  window.markDocumentUploaded = function() {
    localStorage.setItem(LAST_DOC_KEY, new Date().toISOString());
  };
  
  // Show reminder after page loads
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(showReminder, 2000));
  } else {
    setTimeout(showReminder, 2000);
  }
})();
```

### File: `static/document_intake.html` (Modify)
Add call to `markDocumentUploaded()` on successful upload:

```javascript
// After successful upload
markDocumentUploaded && markDocumentUploaded();
showConfetti && showConfetti();
```

---

## User Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROACTIVE DOCUMENTATION FLOW                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   User visits ANY page                                              │
│           │                                                         │
│           ├── Sees Quick Document FAB (bottom-right) 📸             │
│           │                                                         │
│           ├── If >30 days since last doc:                          │
│           │   └── Toast reminder appears                           │
│           │       "Time to save this month's rent receipt!"        │
│           │       [Document Now] [Dismiss]                         │
│           │                                                         │
│           └── User taps FAB or "Document Now"                      │
│                       │                                             │
│                       ▼                                             │
│               document_intake.html?quick=true                       │
│                       │                                             │
│                       ├── Upload file (secure, with tokens)        │
│                       ├── Select document type                     │
│                       ├── Submit → /api/vault/upload               │
│                       │                                             │
│                       ▼                                             │
│               Success! 🎉                                           │
│               └── markDocumentUploaded() called                    │
│               └── Confetti celebration                             │
│               └── Reminder timer resets                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `static/js/header.js` | MODIFY | Add Quick Document FAB |
| `static/js/reminders.js` | CREATE | Monthly reminder system |
| `static/document_intake.html` | MODIFY | Add `markDocumentUploaded()` call |

---

## Success Criteria

- [ ] Quick Document FAB visible on all pages with header
- [ ] FAB navigates to document_intake.html
- [ ] Monthly reminders appear after 30 days of no uploads
- [ ] Reminders dismissable and don't repeat same month
- [ ] Successful uploads reset the reminder timer
- [ ] All security (tokens, auth) unchanged and working
- [ ] Mobile-friendly FAB sizing
- [ ] Celebration on successful upload

---

## Future Enhancements (Not in this phase)

1. **Documentation Streak** - Gamify with "X days in a row" tracking
2. **Smart Reminders** - Based on lease dates (renewal coming up, etc.)
3. **Quick Camera** - Inline photo capture without leaving page
4. **Voice Memos** - Audio documentation for accessibility
5. **Reminder Settings** - User can adjust frequency (weekly/monthly/off)
