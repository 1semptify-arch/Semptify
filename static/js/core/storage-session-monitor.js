/**
 * Storage Session Monitor
 *
 * Background reconnect cycle for the storage-connection indicator that lives
 * in the header on every page (see app/templates/base.html).
 *
 * Rules this module follows (Semptify CORE_CONTEXT):
 * - No popups, no alerts, no dead ends.
 * - Silent by default. Only becomes actionable when the user truly must
 *   re-authenticate (server-side auto-refresh already failed).
 * - Hidden entirely for visitors who have never connected storage, so it
 *   never confuses someone in crisis who hasn't started onboarding.
 *
 * Lifecycle:
 * - Runs on every full page load (this is a server-rendered app, not an SPA,
 *   so "page load" IS "session start" for that page).
 * - Checks /storage/status immediately on load (that endpoint auto-refreshes
 *   the token server-side when possible, so a normal "connected" response
 *   already means the silent reconnect succeeded).
 * - Re-checks on a background timer for as long as the page stays open, and
 *   again whenever the tab regains visibility, so the indicator stays
 *   accurate without the user doing anything.
 */
(function () {
    'use strict';

    var CHECK_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
    var LAST_CHECK_KEY = 'semptify_storage_check_last';

    var PROVIDER_NAMES = {
        google_drive: 'Google Drive',
        dropbox: 'Dropbox',
        onedrive: 'OneDrive',
    };

    var indicatorEl = null;
    var dotEl = null;
    var labelEl = null;
    var intervalHandle = null;

    function cacheElements() {
        indicatorEl = document.getElementById('storage-session-indicator');
        dotEl = document.getElementById('storage-session-dot');
        labelEl = document.getElementById('storage-session-label');
    }

    function show() {
        if (indicatorEl) indicatorEl.style.display = 'inline-flex';
    }

    function hide() {
        if (indicatorEl) indicatorEl.style.display = 'none';
    }

    function setState(state, label, reconnectHref) {
        if (!indicatorEl) return;
        indicatorEl.setAttribute('data-state', state);
        if (labelEl) labelEl.textContent = label || '';

        if (reconnectHref) {
            indicatorEl.setAttribute('data-reconnect-href', reconnectHref);
            indicatorEl.classList.add('storage-session-indicator--actionable');
            indicatorEl.title = 'Click to reconnect your storage';
        } else {
            indicatorEl.removeAttribute('data-reconnect-href');
            indicatorEl.classList.remove('storage-session-indicator--actionable');
            indicatorEl.title = 'Storage connection status';
        }
    }

    function markChecked() {
        try {
            sessionStorage.setItem(LAST_CHECK_KEY, String(Date.now()));
        } catch (e) {
            // sessionStorage unavailable (e.g. private mode edge cases) — non-fatal,
            // it only affects throttling of the visibilitychange re-check.
        }
    }

    async function checkStatus() {
        markChecked();

        try {
            var res = await fetch('/storage/status', { credentials: 'include' });
            var data = await res.json();

            if (!data || typeof data.authenticated === 'undefined') {
                show();
                setState('unknown', 'Storage status unknown');
                return;
            }

            if (data.authenticated) {
                var providerName = PROVIDER_NAMES[data.provider] || 'Storage';
                show();
                setState('connected', providerName + ' connected');
                return;
            }

            if (!data.user_id) {
                // No storage session has ever been started on this device/browser.
                // Stay invisible — nothing to reconnect, nothing to alarm about.
                hide();
                setState('none', '');
                return;
            }

            if (data.needs_reauth) {
                var returnTo = encodeURIComponent(window.location.pathname + window.location.search);
                show();
                setState('reconnect', 'Reconnect storage', '/storage/reconnect?return_to=' + returnTo);
                return;
            }

            show();
            setState('unknown', 'Storage status unknown');
        } catch (e) {
            // Network hiccup — keep whatever was last shown, don't alarm the user.
        }
    }

    function schedule() {
        if (intervalHandle) clearInterval(intervalHandle);
        intervalHandle = setInterval(checkStatus, CHECK_INTERVAL_MS);
    }

    function recheckIfStale() {
        if (document.visibilityState !== 'visible') return;
        var last = 0;
        try {
            last = parseInt(sessionStorage.getItem(LAST_CHECK_KEY) || '0', 10);
        } catch (e) {
            last = 0;
        }
        if (Date.now() - last >= CHECK_INTERVAL_MS / 2) {
            checkStatus();
        }
    }

    function onIndicatorClick() {
        var href = indicatorEl.getAttribute('data-reconnect-href');
        if (href) {
            window.location.href = href;
        }
    }

    function init() {
        cacheElements();
        if (!indicatorEl) return;

        indicatorEl.addEventListener('click', onIndicatorClick);
        document.addEventListener('visibilitychange', recheckIfStale);

        checkStatus(); // Every page load starts a fresh, accurate check.
        schedule();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
