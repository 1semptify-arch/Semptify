/**
 * Shared fetch helpers.
 *
 * fetchWithCSRF(url, options) — fetch() that always sends cookies and, when
 * a csrf_token field or cookie is present, forwards it as X-CSRF-Token so
 * endpoints that opt into validate_csrf keep working.
 *
 * showFlash(message, type) — minimal toast. type: 'success' | 'error' | 'info'.
 * Falls back to alert() only if document.body is unavailable.
 */
(function () {
    "use strict";

    function csrfToken() {
        const field = document.querySelector('input[name="csrf_token"]');
        if (field && field.value) return field.value;
        const match = document.cookie.match(/(^|; )csrf_token=([^;]+)/);
        return match ? decodeURIComponent(match[2]) : "";
    }

    window.fetchWithCSRF = function (url, options) {
        const opts = options || {};
        opts.credentials = opts.credentials || "include";
        const token = csrfToken();
        if (token) {
            opts.headers = Object.assign({}, opts.headers, { "X-CSRF-Token": token });
        }
        return fetch(url, opts);
    };

    window.showFlash = function (message, type) {
        if (!document.body) {
            alert(message);
            return;
        }
        let host = document.getElementById("flashHost");
        if (!host) {
            host = document.createElement("div");
            host.id = "flashHost";
            host.style.cssText =
                "position:fixed;bottom:1rem;left:50%;transform:translateX(-50%);" +
                "z-index:9999;display:flex;flex-direction:column;gap:0.5rem;max-width:min(30rem,90vw);";
            document.body.appendChild(host);
        }
        const note = document.createElement("div");
        const bg = type === "error" ? "#7a3d34" : type === "success" ? "#4a6b4a" : "#4d5f74";
        note.style.cssText =
            "background:" + bg + ";color:#fff;padding:0.625rem 1rem;border-radius:8px;" +
            "font-size:0.875rem;box-shadow:0 2px 8px rgba(0,0,0,0.18);";
        note.setAttribute("role", "status");
        note.textContent = message;
        host.appendChild(note);
        setTimeout(() => note.remove(), 6000);
    };
})();
