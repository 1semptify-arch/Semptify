/* SemptifyFeedback — Unified Action Feedback Helper (standalone JS)
   Load via: <script src="/static/components/feedback.js"></script>
   Provides: start(), done(), success(), error(), info(), story()
   Reuses .btn--loading class from loading-overlay.html
*/
(function () {
    'use strict';

    // Inject styles once
    if (!document.getElementById('se-pt-styles')) {
        var style = document.createElement('style');
        style.id = 'se-pt-styles';
        style.textContent = [
            '.se-pt-container{position:fixed;bottom:1.5rem;right:1.5rem;z-index:10000;display:flex;flex-direction:column-reverse;gap:0.5rem;max-width:22rem;pointer-events:none}',
            '.se-pt{pointer-events:auto;border-radius:var(--radius-md,8px);padding:0.9rem 1.1rem;box-shadow:0 6px 20px rgba(0,0,0,0.18);font-size:0.875rem;line-height:1.4;color:var(--color-text-primary,#fff);background:var(--color-bg-card,#1e293b);border:1px solid var(--color-border,#334155);display:flex;align-items:flex-start;gap:0.6rem;cursor:pointer;transition:opacity 0.3s ease,transform 0.3s ease;opacity:0;transform:translateY(8px);animation:se-pt-in 0.25s ease forwards}',
            '@keyframes se-pt-in{to{opacity:1;transform:translateY(0)}}',
            '.se-pt.se-pt-leaving{opacity:0;transform:translateY(8px)}',
            '.se-pt-icon{flex-shrink:0;font-size:1.1rem;line-height:1;margin-top:0.1rem}',
            '.se-pt-body{flex:1;min-width:0}',
            '.se-pt-title{font-weight:600;margin-bottom:0.15rem}',
            '.se-pt-detail{color:var(--color-text-secondary,#94a3b8);font-size:0.8rem;margin-top:0.25rem;word-break:break-word}',
            '.se-pt-dismiss{flex-shrink:0;color:var(--color-text-secondary,#94a3b8);font-size:1rem;line-height:1;background:none;border:none;cursor:pointer;padding:0;margin:0}',
            '.se-pt--success{border-left:3px solid #10b981}',
            '.se-pt--error{border-left:3px solid #ef4444}',
            '.se-pt--info{border-left:3px solid #3b82f6}',
            '.se-pt--story{border-left:3px solid #f59e0b;background:#2d2410;border-color:#5c4a1a}',
            '.se-pt--story .se-pt-title{color:#fbbf24}',
            '@media (max-width:640px){.se-pt-container{bottom:0.75rem;right:0.75rem;left:0.75rem;max-width:none}}',
        ].join('\n');
        document.head.appendChild(style);
    }

    // Inject container once
    var container = document.getElementById('se-pt-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'se-pt-container';
        container.className = 'se-pt-container';
        container.setAttribute('aria-live', 'polite');
        container.setAttribute('aria-atomic', 'false');
        document.body.appendChild(container);
    }

    var MAX_VISIBLE = 3;
    var SUCCESS_TIMEOUT = 5000;
    var INFO_TIMEOUT = 5000;
    var queue = [];
    var visible = [];

    function makeToast(kind, title, message, opts) {
        var el = document.createElement('div');
        el.className = 'se-pt se-pt--' + kind;
        el.setAttribute('role', kind === 'error' ? 'alert' : 'status');

        var icon = document.createElement('span');
        icon.className = 'se-pt-icon';
        icon.textContent = ({ success: '✓', error: '!', info: 'i', story: '📖' })[kind] || '';
        el.appendChild(icon);

        var body = document.createElement('div');
        body.className = 'se-pt-body';

        var t = document.createElement('div');
        t.className = 'se-pt-title';
        t.textContent = title;
        body.appendChild(t);

        if (message) {
            var m = document.createElement('div');
            m.className = 'se-pt-detail';
            m.textContent = message;
            body.appendChild(m);
        }
        el.appendChild(body);

        var close = document.createElement('button');
        close.className = 'se-pt-dismiss';
        close.textContent = '×';
        close.setAttribute('aria-label', 'Dismiss');
        close.addEventListener('click', function () { dismissToast(el); });
        el.appendChild(close);

        el.addEventListener('click', function () { dismissToast(el); });
        return el;
    }

    function dismissToast(el) {
        if (!el || !el.parentNode) return;
        el.classList.add('se-pt-leaving');
        setTimeout(function () {
            if (el.parentNode) el.parentNode.removeChild(el);
            visible = visible.filter(function (v) { return v !== el; });
            drainQueue();
        }, 300);
    }

    function showToast(kind, title, message, opts) {
        opts = opts || {};
        var el = makeToast(kind, title, message, opts);
        container.appendChild(el);
        visible.push(el);

        if (kind === 'success' || kind === 'info') {
            var ttl = opts.timeout || (kind === 'success' ? SUCCESS_TIMEOUT : INFO_TIMEOUT);
            setTimeout(function () { dismissToast(el); }, ttl);
        }

        while (visible.length > MAX_VISIBLE) {
            var oldest = visible.shift();
            dismissToast(oldest);
        }
    }

    function drainQueue() {
        while (visible.length < MAX_VISIBLE && queue.length > 0) {
            var item = queue.shift();
            showToast(item.kind, item.title, item.message, item.opts);
        }
    }

    function enqueue(kind, title, message, opts) {
        if (visible.length < MAX_VISIBLE) {
            showToast(kind, title, message, opts);
        } else {
            queue.push({ kind: kind, title: title, message: message, opts: opts });
        }
    }

    function start(button, text) {
        if (!button) return;
        button.dataset.sePtOriginalText = button.textContent;
        button.classList.add('btn--loading');
        button.disabled = true;
        if (text) button.dataset.loadingText = text;
    }

    function done(button) {
        if (!button) return;
        button.classList.remove('btn--loading');
        button.disabled = false;
        if (button.dataset.sePtOriginalText !== undefined) {
            button.textContent = button.dataset.sePtOriginalText;
        }
    }

    function story(payload) {
        if (!payload) return;
        var title = payload.title || 'A story from another tenant';
        var body = payload.body || payload.circumstance || '';
        enqueue('story', title, body, { timeout: 0 });
    }

    window.SemptifyFeedback = {
        start: start,
        done: done,
        success: function (msg, opts) { enqueue('success', 'Success', msg, opts); },
        error:   function (msg, opts) { enqueue('error',   'Error',   msg, opts); },
        info:    function (msg, opts) { enqueue('info',    'Tip',     msg, opts); },
        story:   story,
    };
})();
