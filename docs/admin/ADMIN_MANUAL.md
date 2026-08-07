# Semptify Admin Manual

**Version:** 1.0  
**Last Updated:** 2026-06-16  
**For:** System Administrators

---

## Table of Contents

1. [Admin Portal Overview](#admin-portal-overview)
2. [Admin Dashboard](#admin-dashboard)
3. [Function Browser](#function-browser)
4. [Contract Browser](#contract-browser)
5. [Page Editor](#page-editor)
6. [Review Checklist](#review-checklist)
7. [Fix-It Bot](#fix-it-bot)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Issue Reporting](#issue-reporting)

---

## Admin Portal Overview

The Semptify Admin Portal provides system-wide oversight, configuration, and maintenance tools. Access requires admin credentials and 2FA authentication.

### Access Requirements

- **Authentication:** Username + Password + 6-digit TOTP code
- **Environment Variables Required:**
  - `ADMIN_USERNAME` - Admin username (default: "admin")
  - `ADMIN_PASSWORD` - Admin password
  - `ADMIN_TOTP_SECRET` - TOTP secret for 2FA

### Admin Pages

| Page | URL | Purpose |
|------|-----|---------|
| Admin Home | `/admin/home` | Entry point with sign-in |
| Admin Dashboard | `/admin/dashboard.html` | System overview and metrics |
| Function Browser | `/admin/function-browser.html` | Interactive function documentation |
| Contract Browser | `/admin/contract-browser.html` | Page/module contracts and health |
| Page Editor | `/admin/page-editor.html` | Edit static/template files |
| Review Checklist | `/admin/review-checklist.html` | System verification tests |

---

## Admin Dashboard

### Location
`/admin/dashboard.html`

### Purpose
Central hub for system monitoring, user management, and quick access to admin tools.

### Features

#### 1. System Overview Hero
**What it does:** Displays high-level platform metrics at a glance.

**Metrics shown:**
- Total users (with weekly growth percentage)
- Active cases (with weekly growth)
- Documents in vaults (with daily additions)
- Pending signatures (with weekly change)
- Uptime percentage (30-day)
- Security incidents (30-day)
- Rate limit violations (today)
- Blockchain timestamps (verified count)

**How to use:** Monitor these metrics daily to detect anomalies. Sudden drops in uptime or spikes in rate limit violations may indicate attacks or system issues.

**Testing:** No switches to test. Metrics are read-only from database.

**Troubleshooting:**
- **Metrics not loading:** Check database connection. Verify `get_db_session()` is working.
- **Stale data:** Metrics may cache for up to 5 minutes. Refresh page.
- **Zero values:** Check if database tables are populated.

---

#### 2. User Breakdown Card
**What it does:** Shows user distribution by role (Tenant, Advocate, Legal Professional, Property Manager).

**How to use:** Understand user composition. High property manager count may indicate need for landlord-facing features.

**Testing:** No switches to test.

**Troubleshooting:**
- **Incorrect counts:** Verify role assignment logic in user registration flow.
- **Missing roles:** Check if new roles are added to `USER_ROLES` enum.

---

#### 3. Recent Activity Feed
**What it does:** Real-time log of system events (new users, document signatures, uploads, advocate onboarding, maintenance).

**How to use:** Monitor for unusual activity patterns. Spikes in document uploads may indicate bulk imports or abuse.

**Testing:** No switches to test.

**Troubleshooting:**
- **Feed not updating:** Check activity logging middleware. Verify events are being written to audit log.
- **Old events:** Feed shows last 5 events. Check timestamp logic.

---

#### 4. Security Card
**What it does:** Displays security metrics (uptime, incidents, rate limits, blockchain verification).

**How to use:** Track security posture. All metrics should show green/healthy status.

**Testing:** No switches to test.

**Troubleshooting:**
- **Security incidents > 0:** Review security logs immediately. Check for unauthorized access attempts.
- **Rate limit violations:** If high, investigate potential DDoS or API abuse.
- **Blockchain failures:** Check timestamping service integration.

---

#### 5. MNDES System Compliance Card
**What it does:** Shows compliance status with Minnesota District E-Filing System (MNDES) Order ADM09-8010.

**What it does:** Enforces Acceptable File Types List automatically.

**How to use:** Click "MNDES Compliance Guide" to view detailed requirements. Update `mndes_compliance.py` when State Court Administrator revises the official list.

**Testing:** No switches to test.

**Troubleshooting:**
- **Compliance warning:** Check if file type list in `mndes_compliance.py` matches current MNDES requirements.
- **Link broken:** Verify `/mndes/compliance-guide` route exists and returns content.

---

#### 6. Quick Actions Panel
**What it does:** Shortcut buttons to frequently used admin tools.

**Actions available:**
- Function Browser - View all system functions
- Contract Browser - View page/module contracts
- Theme Preview - Preview UI themes
- Page Editor - Edit pages directly
- Review Checklist - Run system verification
- Component Inventory - View UI components
- Navigation Structure - View SSOT navigation
- MNDES Compliance - View compliance guide

**How to use:** Click any button to navigate to that tool.

**Testing:** Test each link to ensure it navigates correctly.

**Troubleshooting:**
- **Link not working:** Check if target file exists at expected path.
- **404 error:** Verify route is registered in `main.py` or router.

---

#### 7. User Search Widget
**What it does:** Search for users by ID, email, or name. View user details and perform admin actions.

**How to use:**
1. Enter search term in input field
2. Click "Search" button
3. Click on a user result to view details
4. Use action buttons: Impersonate, Reset Gates, View Vault

**Admin Actions:**
- **Impersonate:** Log in as the user (all actions logged). Requires confirmation.
- **Reset Gates:** Reset user's onboarding gates (storage_connected, vault_initialized). User must re-complete those steps.
- **View Vault:** View user's vault summary (document count, storage used).

**Testing:**
1. Search for known user ID
2. Verify results display correctly
3. Click user to view details
4. Test each action button (with test user only)

**Troubleshooting:**
- **Search returns 403:** Verify admin role is set in cookie. Check `_guard_role_page()` middleware.
- **No results:** Check if user exists in database. Verify search query logic.
- **Impersonate fails:** Check if impersonation endpoint exists at `/admin-console/api/users/{user_id}/impersonate`.
- **Reset Gates fails:** Verify gate names match valid options: `storage_connected`, `vault_initialized`.
- **Vault summary fails:** Check if vault summary endpoint exists at `/admin-console/api/users/{user_id}/vault-summary`.

---

#### 8. Audit Log Viewer
**What it does:** Displays recent admin actions for accountability and security auditing.

**How to use:** Review recent admin actions. Click "Refresh Audit Log" to load latest entries.

**Testing:** Perform an admin action (e.g., user search), then refresh audit log to verify it appears.

**Troubleshooting:**
- **Log not loading:** Check if audit log endpoint exists at `/admin-console/api/audit-log`.
- **Missing entries:** Verify admin actions are being logged. Check audit middleware.

---

#### 9. System Configuration Card
**What it does:** Shows system tier status, module count, and feature flags.

**Metrics displayed:**
- Tiers: Number of active system tiers
- Modules: Number of loaded modules
- Flags: Number of active feature flags

**How to use:** Monitor system configuration. Click "Modules" to view module manager.

**Testing:** Click "Refresh" to reload configuration. Click "Modules" to open module manager.

**Troubleshooting:**
- **Configuration not loading:** Check if system config endpoint exists at `/admin-console/api/system-config`.
- **Modules button not working:** Verify module manager route exists.

---

#### 10. API Keys Status Card
**What it does:** Shows which environment variables (API keys) are configured vs missing.

**Metrics displayed:**
- Configured: Number of API keys set
- Missing: Number of required API keys not set

**How to use:** Monitor API key configuration. Click "Manage" to view and set missing keys.

**Testing:** Click "Refresh" to reload status. Click "Manage" to open API keys modal.

**Troubleshooting:**
- **Status not loading:** Check if env status endpoint exists at `/admin-console/api/env-status`.
- **Manage button not working:** Verify API keys modal logic exists.

---

#### 11. Analytics Card
**What it does:** Shows user engagement metrics (active users, retention rates).

**Metrics displayed:**
- Active Users: Current active user count
- 7d Retention: 7-day retention percentage
- 30d Retention: 30-day retention percentage

**How to use:** Monitor user engagement. Low retention may indicate UX issues.

**Testing:** Click "Refresh" to reload analytics. Click "Details" to view detailed analytics.

**Troubleshooting:**
- **Analytics not loading:** Check if analytics endpoint exists at `/admin-console/api/analytics`.
- **Zero values:** Check if analytics tracking is enabled. Verify event logging.

---

#### 12. Today's Stats Card
**What it does:** Shows today's activity metrics (signups, uploads, signatures, messages, API requests).

**How to use:** Monitor daily activity volume. Spikes may indicate marketing campaigns or issues.

**Testing:** No switches to test. Data is read-only.

**Troubleshooting:**
- **Stale data:** Stats update every hour. Check if cron job is running.
- **Incorrect counts:** Verify event tracking logic.

---

#### 13. System Status Card
**What it does:** Shows health status of core systems (database, cloud storage, blockchain timestamping).

**Status indicators:**
- All systems operational (green)
- Database: Healthy
- Cloud storage: Connected
- Blockchain timestamping: Active

**How to use:** Verify all systems show green status. Any red indicator requires immediate attention.

**Testing:** No switches to test. Status is read-only from health checks.

**Troubleshooting:**
- **Database unhealthy:** Check database connection. Verify PostgreSQL is running.
- **Cloud storage disconnected:** Check storage provider API keys. Verify OAuth flow.
- **Blockchain inactive:** Check timestamping service. Verify API credentials.

---

## Function Browser

### Location
`/admin/function-browser.html`

### Purpose
Interactive documentation of all Semptify functions. View function details, inputs, settings, and related pages.

### Features

#### 1. Filter by View
**What it does:** Filter functions by page group (Home, Library, Office, Tools, Help).

**How to use:** Click filter buttons to show only functions in that group. Click "All" to show all functions.

**Testing:**
1. Click each filter button
2. Verify only relevant functions display
3. Click "All" to verify all functions return

**Troubleshooting:**
- **Filter not working:** Check JavaScript filter logic in `function-browser.html`.
- **Functions missing:** Verify function database is complete in JavaScript.

---

#### 2. Filter by Role
**What it does:** Filter functions by user role (Tenant, Advocate, Legal, Manager).

**How to use:** Click role filter buttons to show only functions available to that role.

**Testing:**
1. Click each role button
2. Verify only functions with that role display
3. Verify role badges show correctly

**Troubleshooting:**
- **Role filter not working:** Check JavaScript role filter logic.
- **Incorrect roles:** Verify function database has correct role arrays.

---

#### 3. Function Cards
**What it does:** Displays each function as an expandable card with details.

**Card sections:**
- Function name and icon
- Role badges (which roles can access)
- Description
- Inputs (required/optional fields)
- Settings (configurable options)
- Related pages
- Help link
- Context (when/where this function is used)

**How to use:** Click on a function card to expand and view full details.

**Testing:**
1. Click on multiple function cards
2. Verify details expand correctly
3. Verify all sections display properly
4. Click again to collapse

**Troubleshooting:**
- **Card not expanding:** Check JavaScript expand/collapse logic.
- **Details missing:** Verify function database has complete data for that function.
- **Help link broken:** Verify help page exists at expected path.

---

#### 4. Sidebar Navigation
**What it does:** Quick navigation to function groups by category.

**How to use:** Click sidebar items to jump to that function group in the main view.

**Testing:**
1. Click each sidebar item
2. Verify main view scrolls to or filters to that group

**Troubleshooting:**
- **Sidebar not working:** Check JavaScript navigation logic.
- **Items not highlighting:** Verify active state logic.

---

## Contract Browser

### Location
`/admin/contract-browser.html`

### Purpose
View and verify page contracts and module contracts. Check health status and violations.

### Features

#### 1. Search Contracts
**What it does:** Search contracts by title, expectations, scope, or page_id.

**How to use:** Type search term in input field. Results filter in real-time.

**Testing:**
1. Type known contract title
2. Verify only matching contracts display
3. Clear search to show all

**Troubleshooting:**
- **Search not working:** Check JavaScript filter logic.
- **No results:** Verify search term matches contract data.

---

#### 2. Filter by Status
**What it does:** Filter contracts by status (Active, Beta, Coming Soon, Deprecated).

**How to use:** Select status from dropdown. Only contracts with that status display.

**Testing:**
1. Select each status option
2. Verify only matching contracts display
3. Select "All Statuses" to show all

**Troubleshooting:**
- **Filter not working:** Check JavaScript status filter logic.
- **Incorrect status:** Verify contract status in database.

---

#### 3. Filter by Group
**What it does:** Filter contracts by primary/secondary group (Documentation, Security, Functions, Output, Research).

**How to use:** Select group from dropdown. Only contracts in that group display.

**Testing:**
1. Select each group option
2. Verify only matching contracts display

**Troubleshooting:**
- **Filter not working:** Check JavaScript group filter logic.
- **Group not found:** Verify contract has that group in its group arrays.

---

#### 4. Filter by Health
**What it does:** Filter contracts by health status (Has Violations, Clean).

**How to use:** Select health option. Only contracts with that health status display.

**Testing:**
1. Select "Has Violations"
2. Verify only contracts with violations display
3. Select "Clean" to show only healthy contracts

**Troubleshooting:**
- **Health not showing:** Check if health endpoint is returning violations data.
- **Incorrect violations:** Verify contract health check logic.

---

#### 5. Health Bar
**What it does:** Shows overall contract health status (pass/fail) and summary statistics.

**Metrics displayed:**
- Total contracts
- Failed (violations)
- Passed

**How to use:** Monitor overall system health. Green = all contracts healthy. Red = violations detected.

**Testing:**
1. Load page and verify health bar displays
2. Click "Refresh" to reload health data
3. Verify statistics update

**Troubleshooting:**
- **Health not loading:** Check if health endpoint exists at `/api/workflow/health`.
- **Stale data:** Click "Refresh" to reload.
- **Always failing:** Review contract violations. Fix underlying issues.

---

#### 6. Page Contracts Tab
**What it does:** Displays all page contracts with their details and violations.

**Contract details shown:**
- Title and page_id
- Route
- Status badge
- Expectations
- Scope of use
- Coverage matrix (which groups are covered)
- Roles supported
- Entry criteria
- Exit criteria
- AI constraints (if any)
- Violations (if any)

**How to use:** Review each contract to ensure it meets requirements. Fix violations as needed.

**Testing:**
1. Click on Page Contracts tab
2. Verify all page contracts display
3. Click "View JSON" to see full contract data

**Troubleshooting:**
- **Contracts not loading:** Check if contracts endpoint exists at `/api/workflow/contracts`.
- **Violations not showing:** Check if health endpoint returns violations for that page_id.
- **JSON not loading:** Verify modal logic works correctly.

---

#### 7. Module Contracts Tab
**What it does:** Displays all module contracts with their inputs, outputs, and dependencies.

**Module details shown:**
- Title and group name
- Module name
- Description
- Inputs
- Outputs
- Dependencies
- Deterministic flag

**How to use:** Review module contracts to understand module interfaces and dependencies.

**Testing:**
1. Click on Module Contracts tab
2. Verify all module contracts display
3. Click "View JSON" to see full contract data

**Troubleshooting:**
- **Contracts not loading:** Check if module contracts endpoint exists at `/api/workflow/module-contracts`.
- **Missing modules:** Verify all modules have registered contracts.

---

#### 8. View JSON Modal
**What it does:** Displays full contract JSON in a modal for detailed inspection.

**How to use:** Click "View JSON" button on any contract. Copy JSON to clipboard if needed.

**Testing:**
1. Click "View JSON" on a contract
2. Verify modal opens with JSON
3. Click "Copy JSON" to verify clipboard copy
4. Click "Close" to dismiss modal

**Troubleshooting:**
- **Modal not opening:** Check JavaScript modal logic.
- **JSON not displaying:** Verify contract data is valid JSON.
- **Copy not working:** Check clipboard API permissions.

---

## Page Editor

### Location
`/admin/page-editor.html`

### Purpose
Edit static HTML files and Jinja2 templates directly in the browser with live preview.

### Features

#### 1. File Browser Sidebar
**What it does:** Browse and select files to edit (static files or templates).

**Tabs:**
- Static - Static HTML files in `/static/`
- Templates - Jinja2 templates in `/app/templates/`

**How to use:**
1. Select Static or Templates tab
2. Browse folders and files
3. Click on a file to open it in the editor

**Testing:**
1. Switch between Static and Templates tabs
2. Verify file list loads for each tab
3. Click on a file to open it
4. Verify file content displays in editor

**Troubleshooting:**
- **Files not loading:** Check if files endpoint exists at `/api/editor/files`.
- **Tab switching not working:** Check JavaScript tab logic.
- **File not opening:** Verify file path is correct and file exists.

---

#### 2. Search Files
**What it does:** Filter files in the browser by name.

**How to use:** Type search term in search box. File list filters in real-time.

**Testing:**
1. Type known file name
2. Verify only matching files display
3. Clear search to show all files

**Troubleshooting:**
- **Search not working:** Check JavaScript filter logic.
- **No results:** Verify search term matches file names.

---

#### 3. Code Editor
**What it does:** Edit file content with syntax highlighting and line numbers.

**Features:**
- Textarea with monospace font
- Tab support (2 spaces)
- Auto-detect language (HTML, CSS, JS, Python, Jinja2)
- Character count display
- Modified indicator (● on tab)

**How to use:**
1. Open a file
2. Edit content in the textarea
3. Changes are marked as modified (● appears on tab)
4. Save changes with Ctrl+S or Save button

**Testing:**
1. Open a file
2. Make a small edit
3. Verify modified indicator appears
4. Save file
5. Verify modified indicator disappears

**Troubleshooting:**
- **Editor not loading:** Check if file content endpoint exists at `/api/editor/file`.
- **Changes not saving:** Check if save endpoint exists at `/api/editor/save`.
- **Syntax errors:** Editor does not validate syntax. Use browser console for errors.

---

#### 4. Tab Management
**What it does:** Manage multiple open files with tabs.

**Features:**
- Open multiple files in tabs
- Switch between tabs
- Close tabs (with unsaved changes warning)
- Modified indicator on tabs

**How to use:**
1. Open multiple files
2. Click tabs to switch between files
3. Click × to close a tab
4. Confirm if unsaved changes exist

**Testing:**
1. Open 3-4 files
2. Switch between tabs
3. Close a tab with unsaved changes
4. Verify warning appears
5. Close a tab without unsaved changes

**Troubleshooting:**
- **Tabs not switching:** Check JavaScript tab logic.
- **Close not working:** Verify close button event handler.
- **Warning not appearing:** Check unsaved changes detection logic.

---

#### 5. Save File
**What it does:** Save current file changes to the server.

**How to use:** Click Save button or press Ctrl+S. Status bar shows "Saved [filename]" on success.

**Testing:**
1. Make changes to a file
2. Click Save button
3. Verify success message appears
4. Reload file to verify changes persisted

**Troubleshooting:**
- **Save failing:** Check if save endpoint exists at `/api/editor/save`.
- **Changes not persisting:** Verify server is writing to file system.
- **Permission error:** Check file system permissions for the target file.

---

#### 6. Deploy Changes
**What it does:** Deploy all changes to production (pushes to GitHub).

**How to use:** Click Deploy button. Confirm deployment in dialog.

**⚠️ WARNING:** This is a placeholder implementation. Real deployment requires Git integration.

**Testing:**
1. Click Deploy button
2. Verify confirmation dialog appears
3. Confirm and verify "Deployed successfully" message

**Troubleshooting:**
- **Deploy not working:** This is a placeholder. Implement Git integration for real deployment.
- **No confirmation:** Check JavaScript confirm dialog logic.

---

#### 7. Live Preview
**What it does:** Preview HTML files in a side panel as you edit.

**How to use:** Click Preview button or press Ctrl+P. Preview panel opens on the right. Preview updates as you type.

**Testing:**
1. Open an HTML file
2. Click Preview button
3. Verify preview panel opens
4. Make changes to file
5. Verify preview updates

**Troubleshooting:**
- **Preview not opening:** Check JavaScript preview logic.
- **Preview not updating:** Verify change detection logic.
- **Preview blank:** Check if file content is valid HTML.

---

#### 8. Keyboard Shortcuts
**What it does:** Keyboard shortcuts for common actions.

**Shortcuts:**
- Ctrl+S - Save file
- Ctrl+O - Focus search box
- Ctrl+P - Toggle preview
- Ctrl+W - Close current tab
- ? - Show shortcuts help
- Escape - Close shortcuts help

**How to use:** Press key combinations to perform actions quickly.

**Testing:**
1. Test each keyboard shortcut
2. Verify correct action performs
3. Press ? to show help
4. Press Escape to dismiss help

**Troubleshooting:**
- **Shortcuts not working:** Check JavaScript keyboard event handler.
- **Conflict with browser:** Some shortcuts may conflict with browser defaults.

---

## Review Checklist

### Location
`/admin/review-checklist.html`

### Purpose
Run automated verification tests for contracts, routes, SSOT compliance, footer consistency, and security.

### Features

#### 1. Progress Bar
**What it does:** Shows overall completion percentage of checklist items.

**How to use:** Monitor progress as you complete items. Green bar = all items complete.

**Testing:**
1. Complete some checklist items
2. Verify progress bar updates
3. Complete all items
4. Verify bar shows 100%

**Troubleshooting:**
- **Progress not updating:** Check JavaScript progress calculation logic.
- **Incorrect percentage:** Verify total and completed counts are correct.

---

#### 2. Statistics
**What it does:** Shows completed count, total count, and pending count.

**How to use:** Track how many items are completed vs pending.

**Testing:**
1. Complete items
2. Verify counts update correctly
3. Reset all items
4. Verify counts reset

**Troubleshooting:**
- **Counts not updating:** Check JavaScript stats calculation logic.
- **State not persisting:** Check localStorage logic for saving state.

---

#### 3. Filter Bar
**What it does:** Filter checklist items by category (All, Contracts, Routes, Pending).

**How to use:** Click filter buttons to show only items in that category.

**Testing:**
1. Click each filter button
2. Verify only matching items display
3. Click "All" to show all items

**Troubleshooting:**
- **Filter not working:** Check JavaScript filter logic.
- **Search not working:** Check search input event handler.

---

#### 4. Contract Verification Section
**What it does:** Checklist items for verifying page contracts load correctly.

**Items:**
- Returning User Contract - Verify `/returning-user-contract.html` loads
- User Reconnect v2 - Test storage reconnection flow
- Privacy Policy - Confirm no "account" language
- Terms of Service - Verify session-based terminology

**How to use:**
1. Click checkbox to mark item as reviewed
2. Click Test button to run automated test
3. Add notes in notes field
4. View page link if available

**Testing:**
1. Click Test button on each item
2. Verify test passes (green) or fails (red)
3. Check notes field saves automatically

**Troubleshooting:**
- **Test failing:** Check if target page exists and loads correctly.
- **Test error:** Check browser console for error details.
- **Notes not saving:** Check localStorage logic.

---

#### 5. Routes Verification Section
**What it does:** Checklist items for verifying route redirects and accessibility.

**Items:**
- Welcome Page (/) - Root path redirects correctly
- Tenant Dashboard (/tenant/home) - Loads with dynamic data
- Journal Page (/tenant/journal) - CRUD functionality
- Law Library (/law-library) - Loads with rights info
- Storage OAuth Flow - OAuth callback works
- Page Editor - API responds correctly

**How to use:**
1. Click Test button to run route test
2. Verify route returns 200 or 302 (redirect)
3. Mark as reviewed if test passes

**Testing:**
1. Test each route
2. Verify all critical routes pass
3. Check for 404 or 500 errors

**Troubleshooting:**
- **Route not found (404):** Check if route is registered in `main.py` or router.
- **Route error (500):** Check route handler for exceptions.
- **Redirect loop:** Check redirect logic for circular references.

---

#### 6. SSOT Compliance Section
**What it does:** Checklist items for verifying Single Source of Truth architecture compliance.

**Items:**
- No Hardcoded Redirects - Verify `ssot_redirect()` usage
- Navigation Registry Working - SSOT API returns valid paths
- Base Template Uses SSOT - Template uses `navigation.get_path()`

**How to use:**
1. Click Test button to run SSOT verification
2. Some items require manual review (marked as "skip")
3. Check code manually for hardcoded URLs

**Testing:**
1. Test navigation registry endpoint
2. Manually review `main.py` for hardcoded redirects
3. Check templates for hardcoded links

**Troubleshooting:**
- **Hardcoded URLs found:** Replace with `navigation.get_stage()` and `ssot_redirect()`.
- **Navigation API failing:** Check if SSOT navigation endpoint exists.
- **Template not using SSOT:** Update template to use `navigation.get_path()`.

---

#### 7. Footer Consistency Section
**What it does:** Checklist items for verifying footer consistency across pages.

**Items:**
- Welcome Page Footer - Uses unified-footer-loader.js
- Dashboard Footer - Has unified footer
- Legal Advice Disclaimer - All pages have disclaimer
- MN Legal Aid Hotline - Footer includes hotline number

**How to use:**
1. Click Test button to check footer content
2. Verify footer loader script is included
3. Check for disclaimer text
4. Verify hotline number is present

**Testing:**
1. Test each page's footer
2. Verify all pages use unified footer
3. Check disclaimer text is present
4. Verify hotline number is correct

**Troubleshooting:**
- **Footer not loading:** Check if `unified-footer-loader.js` exists.
- **Disclaimer missing:** Add disclaimer to footer template.
- **Hotline missing:** Add hotline number to footer template.

---

#### 8. Security & Privacy Section
**What it does:** Checklist items for verifying security and privacy compliance.

**Items:**
- No User Account References - Pages don't mention "accounts"
- No Tracking Claims - No "users served" statistics
- Property Managers Not Listed - Removed from user roles

**How to use:**
1. Click Test button to scan pages for prohibited language
2. Verify no account references exist
3. Check for tracking/statistics claims
4. Verify property managers are not listed

**Testing:**
1. Test each security item
2. Verify all critical items pass
3. Review any failures manually

**Troubleshooting:**
- **Account references found:** Replace with "session" terminology.
- **Tracking claims found:** Remove statistics from public pages.
- **Property managers listed:** Remove from user roles and About page.

---

#### 9. Run Tests Button
**What it does:** Run all automated tests in sequence and display results.

**How to use:** Click "Run Tests" button. Wait for all tests to complete. Review results panel.

**Testing:**
1. Click Run Tests
2. Verify all tests execute
3. Review results panel
4. Check pass/fail/skip counts

**Troubleshooting:**
- **Tests not running:** Check JavaScript test execution logic.
- **Tests hanging:** Check if any test has infinite loop or timeout.
- **Results not showing:** Verify results panel logic.

---

#### 10. Reset All Button
**What it does:** Reset all checklist items to unreviewed state.

**How to use:** Click "Reset All" button. Confirm reset in dialog.

**Testing:**
1. Complete some items
2. Click Reset All
3. Verify all items are unchecked
4. Verify progress bar resets

**Troubleshooting:**
- **Reset not working:** Check JavaScript reset logic.
- **State not clearing:** Check localStorage clear logic.

---

## Fix-It Bot

### Purpose
Automated issue detection and resolution system that fixes problems without deleting data or functionality.

### Design Principles

1. **Never Delete:** The bot never deletes data, files, or configurations. It only fixes, adds, or modifies.
2. **Root Cause First:** Always identify and fix the root cause, not symptoms.
3. **Safe Rollback:** All changes are logged and can be rolled back if needed.
4. **Human Review:** Critical fixes require human approval before execution.
5. **Explainable:** Every fix includes a clear explanation of what was changed and why.

### Bot Capabilities

#### 1. Automated Health Checks
**What it does:** Continuously monitors system health and detects issues.

**Checks performed:**
- Database connection health
- Storage provider connectivity
- API endpoint availability
- SSL certificate validity
- Disk space usage
- Memory usage
- Error rate monitoring

**How it works:**
- Runs checks every 5 minutes
- Logs results to audit trail
- Alerts on critical failures
- Auto-fixes non-critical issues

**Testing:**
1. Simulate database failure
2. Verify bot detects and alerts
3. Simulate storage failure
4. Verify bot detects and attempts reconnection

**Troubleshooting:**
- **Bot not detecting issues:** Check health check logic. Verify monitoring endpoints.
- **False positives:** Adjust thresholds for health checks.
- **Alerts not sending:** Check notification configuration.

---

#### 2. Contract Violation Auto-Fixer
**What it does:** Automatically fixes common contract violations.

**Fixes applied:**
- Add missing required fields to contracts
- Fix invalid enum values
- Correct malformed JSON
- Add missing role badges
- Fix broken page_id references

**How it works:**
- Scans contracts for violations
- Applies safe fixes automatically
- Logs all changes
- Requires approval for complex fixes

**Testing:**
1. Introduce a contract violation
2. Wait for bot to detect
3. Verify fix is applied
4. Verify contract passes validation

**Troubleshooting:**
- **Bot not fixing:** Check fix logic for that violation type.
- **Fix incorrect:** Review fix logic. Add human approval for that fix type.
- **Contract still failing:** Check if fix addressed the root cause.

---

#### 3. SSOT Violation Detector
**What it does:** Detects hardcoded URLs and SSOT violations in code.

**Detection patterns:**
- Hardcoded `/path` strings in redirects
- Missing `ssot_redirect()` usage
- Direct `RedirectResponse()` calls
- Hardcoded navigation links in templates

**How it works:**
- Scans codebase on each commit
- Reports violations in PR comments
- Suggests fixes using SSOT patterns
- Blocks merge if critical violations found

**Testing:**
1. Add hardcoded URL to a file
2. Commit changes
3. Verify bot detects violation
4. Apply suggested fix
5. Verify violation is resolved

**Troubleshooting:**
- **Bot not detecting:** Check detection patterns. Verify regex matches violations.
- **False positives:** Adjust patterns to exclude valid cases.
- **Fix suggestion incorrect:** Review fix template. Update pattern.

---

#### 4. Dependency Security Scanner
**What it does:** Scans dependencies for known security vulnerabilities.

**Checks performed:**
- Outdated packages with CVEs
- Vulnerable transitive dependencies
- License compliance
- Malicious package indicators

**How it works:**
- Runs daily via cron
- Checks against vulnerability databases
- Reports findings to admin
- Suggests safe upgrade paths

**Testing:**
1. Introduce vulnerable dependency
2. Wait for daily scan
3. Verify vulnerability is detected
4. Apply suggested upgrade
5. Verify vulnerability is resolved

**Troubleshooting:**
- **Bot not scanning:** Check cron job configuration.
- **Vulnerability not detected:** Check vulnerability database connection.
- **Upgrade breaks build:** Test upgrade in staging first.

---

#### 5. Configuration Validator
**What it does:** Validates environment configuration and detects misconfigurations.

**Validations:**
- Required environment variables set
- Valid values for config options
- No conflicting settings
- Secure defaults for sensitive values

**How it works:**
- Validates on startup
- Validates on config changes
- Reports invalid settings
- Suggests corrections

**Testing:**
1. Set invalid environment variable
2. Restart application
3. Verify bot detects misconfiguration
4. Apply suggested fix
5. Verify validation passes

**Troubleshooting:**
- **Bot not validating:** Check startup validation logic.
- **False failures:** Adjust validation rules.
- **Fix suggestion incorrect:** Review fix template.

---

### Bot Commands

#### Manual Trigger
```bash
# Run all health checks
python -m semptify_fixit --check-health

# Scan for SSOT violations
python -m semptify_fixit --scan-ssot

# Scan dependencies
python -m semptify_fixit --scan-deps

# Validate configuration
python -m semptify_fixit --validate-config

# Fix detected issues (auto-fix safe issues only)
python -m semptify_fixit --fix --auto
```

#### Interactive Mode
```bash
# Run in interactive mode (requires approval for all fixes)
python -m semptify_fixit --interactive
```

#### Dry Run
```bash
# Show what would be fixed without applying changes
python -m semptify_fixit --dry-run
```

### Bot Configuration

Configuration file: `.fixit-config.yaml`

```yaml
# Health check interval (minutes)
health_check_interval: 5

# Auto-fix policy
auto_fix_policy:
  safe_fixes: true
  complex_fixes: false
  require_approval: true

# Notification settings
notifications:
  email: admin@semptify.org
  slack: "#admin-alerts"
  critical_only: true

# Rollback settings
rollback:
  enabled: true
  keep_days: 30
  auto_rollback_on_failure: false

# Logging
logging:
  level: INFO
  file: logs/fixit.log
  max_size: 100MB
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Admin Login Fails with 401 Unauthorized

**Symptoms:**
- Admin login returns 401 error
- TOTP code always rejected
- "Invalid credentials" message

**Root Causes:**
1. `ADMIN_PASSWORD` environment variable not set
2. `ADMIN_TOTP_SECRET` environment variable not set
3. Clock drift between authenticator app and server
4. Wrong TOTP code entered

**Troubleshooting Steps:**
1. Check environment variables are set:
   ```bash
   echo $ADMIN_PASSWORD
   echo $ADMIN_TOTP_SECRET
   ```
2. Verify TOTP secret matches authenticator app
3. Check server time is synchronized:
   ```bash
   date
   ```
4. Try TOTP code from a different authenticator app

**Fix:**
- Set missing environment variables in `.env` or Render dashboard
- Sync server time with NTP
- Regenerate TOTP secret if needed

---

#### Issue: Dashboard Metrics Not Loading

**Symptoms:**
- Dashboard shows "Loading..." indefinitely
- Metrics display as zero or dashes
- Console shows 500 errors

**Root Causes:**
1. Database connection failed
2. Metrics query timed out
3. Missing database tables
4. Insufficient permissions

**Troubleshooting Steps:**
1. Check database connection:
   ```bash
   python -c "from app.core.database import get_db_session; print('OK')"
   ```
2. Check database logs for errors
3. Verify tables exist:
   ```bash
   python -c "from app.models.models import User; print('OK')"
   ```
4. Check query performance

**Fix:**
- Fix database connection string
- Create missing tables via Alembic migrations
- Optimize slow queries
- Grant necessary permissions

---

#### Issue: User Search Returns 403 Forbidden

**Symptoms:**
- User search widget shows "Admin access required"
- Console shows 403 error
- Other admin features work

**Root Causes:**
1. Admin role not set in cookie
2. Session expired
3. `_guard_role_page()` middleware blocking
4. Missing admin role in user record

**Troubleshooting Steps:**
1. Check admin cookie:
   ```javascript
   document.cookie
   ```
2. Verify admin role is assigned
3. Check middleware configuration
4. Re-authenticate if session expired

**Fix:**
- Re-login to admin panel
- Ensure admin role is assigned to user
- Check middleware exemption list for admin routes
- Verify cookie is being set correctly

---

#### Issue: Contract Browser Shows No Contracts

**Symptoms:**
- Contract browser shows empty list
- "Loading contracts..." persists
- Health bar shows zero contracts

**Root Causes:**
1. Contracts endpoint not responding
2. Contract database empty
3. API route not registered
4. Authentication failed

**Troubleshooting Steps:**
1. Check contracts endpoint:
   ```bash
   curl https://semptify.org/api/workflow/contracts
   ```
2. Check contract registration in code
3. Verify admin authentication
4. Check server logs for errors

**Fix:**
- Register contracts endpoint in router
- Add contracts to database
- Fix authentication
- Check API route configuration

---

#### Issue: Page Editor Cannot Save Files

**Symptoms:**
- Save button shows error
- "Error saving" message appears
- Changes not persisted

**Root Causes:**
1. File system permissions
2. Save endpoint not responding
3. File path invalid
4. Disk full

**Troubleshooting Steps:**
1. Check file permissions:
   ```bash
   ls -la static/
   ```
2. Check disk space:
   ```bash
   df -h
   ```
3. Test save endpoint:
   ```bash
   curl -X POST https://semptify.org/api/editor/save
   ```
4. Check server logs

**Fix:**
- Grant write permissions to web server user
- Free disk space
- Fix save endpoint
- Validate file path before saving

---

#### Issue: Review Checklist Tests Fail

**Symptoms:**
- Tests show red "Fail" status
- "Error" message appears
- Tests timeout

**Root Causes:**
1. Target page/route not found
2. Network connectivity issues
3. Test logic incorrect
4. Page content changed

**Troubleshooting Steps:**
1. Manually test the failing route:
   ```bash
   curl https://semptify.org/tenant/home
   ```
2. Check browser console for errors
3. Verify test logic matches current implementation
4. Check if page/route still exists

**Fix:**
- Fix missing routes
- Update test logic to match current implementation
- Remove tests for deprecated features
- Fix network connectivity

---

#### Issue: Fix-It Bot Not Running

**Symptoms:**
- Bot not detecting issues
- No bot logs
- Cron job not executing

**Root Causes:**
1. Bot not installed
2. Cron job not configured
3. Python environment missing
4. Dependencies not installed

**Troubleshooting Steps:**
1. Check if bot is installed:
   ```bash
   python -m semptify_fixit --help
   ```
2. Check cron job:
   ```bash
   crontab -l
   ```
3. Check Python environment
4. Check bot logs

**Fix:**
- Install bot package
- Configure cron job
- Install dependencies
- Fix Python environment

---

## Issue Reporting

### How to Report Issues

#### Option 1: GitHub Issues (Recommended)
1. Go to: https://github.com/1semptify-arch/Semptify/issues
2. Click "New Issue"
3. Fill out issue template:
   - **Title:** Brief description of issue
   - **Description:** Detailed steps to reproduce
   - **Expected behavior:** What should happen
   - **Actual behavior:** What actually happened
   - **Screenshots:** If applicable
   - **Environment:** Browser, OS, etc.
4. Submit issue

#### Option 2: Admin Panel Issue Button
1. Click "Report Issue" button on any admin page
2. Fill out issue form:
   - **Page:** Where the issue occurred
   - **Severity:** Critical, High, Medium, Low
   - **Description:** Detailed description
   - **Steps to reproduce:** Step-by-step instructions
3. Submit form

#### Option 3: Email
Send to: admin@semptify.org

Subject: `[Admin Issue] Brief Description`

Include:
- Your admin username
- Page where issue occurred
- Steps to reproduce
- Screenshots if applicable

### Issue Template

```
**Issue Title:** [Brief description]

**Severity:** [Critical/High/Medium/Low]

**Page/Feature:** [Where issue occurred]

**Description:**
[Detailed description of the issue]

**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happened]

**Screenshots:**
[Attach if applicable]

**Environment:**
- Browser: [Chrome/Firefox/Safari + version]
- OS: [Windows/Mac/Linux]
- Admin Panel Version: [if known]

**Additional Context:**
[Any other relevant information]
```

### Severity Levels

- **Critical:** System down, data loss, security breach
- **High:** Major feature broken, significant impact
- **Medium:** Minor feature broken, workaround available
- **Low:** Cosmetic issue, minor inconvenience

### Response Times

- **Critical:** Within 1 hour
- **High:** Within 4 hours
- **Medium:** Within 24 hours
- **Low:** Within 3 days

---

## Appendix

### Environment Variables Reference

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ADMIN_USERNAME` | Yes | Admin username | admin |
| `ADMIN_PASSWORD` | Yes | Admin password | None |
| `ADMIN_TOTP_SECRET` | Yes | TOTP secret for 2FA | None |
| `DATABASE_URL` | Yes | PostgreSQL connection string | None |
| `REDIS_URL` | Yes | Redis connection string | None |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID | None |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret | None |
| `DROPBOX_CLIENT_ID` | Yes | Dropbox OAuth client ID | None |
| `DROPBOX_CLIENT_SECRET` | Yes | Dropbox OAuth client secret | None |

### API Endpoints Reference

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/admin/login` | GET | Admin login page | No |
| `/admin/api/login-step1` | POST | Validate username/password | No |
| `/admin/api/login-step2` | POST | Validate TOTP code | No |
| `/admin/logout` | GET | Admin logout | Yes |
| `/admin-console/api/users` | GET | Search users | Admin |
| `/admin-console/api/users/{id}` | GET | Get user details | Admin |
| `/admin-console/api/users/{id}/impersonate` | POST | Impersonate user | Admin |
| `/admin-console/api/users/{id}/reset-gates` | POST | Reset user gates | Admin |
| `/admin-console/api/users/{id}/vault-summary` | GET | Get vault summary | Admin |
| `/admin-console/api/audit-log` | GET | Get audit log | Admin |
| `/admin-console/api/system-config` | GET | Get system config | Admin |
| `/admin-console/api/env-status` | GET | Get env status | Admin |
| `/admin-console/api/analytics` | GET | Get analytics | Admin |
| `/api/workflow/contracts` | GET | Get page contracts | Admin |
| `/api/workflow/module-contracts` | GET | Get module contracts | Admin |
| `/api/workflow/health` | GET | Get contract health | Admin |
| `/api/editor/files` | GET | Get file list | Admin |
| `/api/editor/file` | GET | Get file content | Admin |
| `/api/editor/save` | POST | Save file | Admin |

### Keyboard Shortcuts Reference

| Shortcut | Action | Context |
|----------|--------|---------|
| Ctrl+S | Save file | Page Editor |
| Ctrl+O | Focus search | Page Editor |
| Ctrl+P | Toggle preview | Page Editor |
| Ctrl+W | Close tab | Page Editor |
| ? | Show shortcuts | Page Editor |
| Escape | Close help/modal | Page Editor |
| Enter | Submit form | Admin Login |
| Ctrl+Shift+R | Hard refresh | All pages |

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-16  
**Maintained By:** Semptify Development Team  
**For questions or updates:** admin@semptify.org
