/* SemptifyFeedback — Unified Action Feedback Helper (standalone JS)
   Load via: <script src="/static/components/feedback.js"></script>
   Provides: start(), done(), success(), error(), info(), story(),
             confirm(), prompt()
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
            '.se-pt{pointer-events:auto;border-radius:var(--radius-md,8px);padding:0.9rem 1.1rem;box-shadow:0 6px 20px color-mix(in srgb, var(--color-black), transparent 82%);font-size:0.875rem;line-height:1.4;color:var(--color-text-primary,var(--text-inverse));background:var(--color-bg-card,var(--color-primary-dark));border:1px solid var(--color-border,var(--color-calm-dark));display:flex;align-items:flex-start;gap:0.6rem;cursor:pointer;transition:opacity 0.3s ease,transform 0.3s ease;opacity:0;transform:translateY(8px);animation:se-pt-in 0.25s ease forwards}',
            '@keyframes se-pt-in{to{opacity:1;transform:translateY(0)}}',
            '.se-pt.se-pt-leaving{opacity:0;transform:translateY(8px)}',
            '.se-pt-icon{flex-shrink:0;font-size:1.1rem;line-height:1;margin-top:0.1rem}',
            '.se-pt-body{flex:1;min-width:0}',
            '.se-pt-title{font-weight:600;margin-bottom:0.15rem}',
            '.se-pt-detail{color:var(--color-text-secondary,var(--color-calm-light));font-size:0.8rem;margin-top:0.25rem;word-break:break-word}',
            '.se-pt-dismiss{flex-shrink:0;color:var(--color-text-secondary,var(--color-calm-light));font-size:1rem;line-height:1;background:none;border:none;cursor:pointer;padding:0;margin:0}',
            '.se-pt--success{border-left:3px solid var(--color-success)}',
            '.se-pt--error{border-left:3px solid var(--color-error)}',
            '.se-pt--info{border-left:3px solid var(--color-info)}',
            '.se-pt--story{border-left:3px solid var(--color-warning);background:var(--color-primary-dark);border-color:var(--color-primary)}',
            '.se-pt--story .se-pt-title{color:var(--color-warning)}',
            '.btn--loading{position:relative;color:transparent !important;pointer-events:none}',
            '.btn--loading::after{content:"";position:absolute;top:50%;left:50%;width:20px;height:20px;margin-top:-10px;margin-left:-10px;border:2px solid color-mix(in srgb, var(--bg-card), transparent 70%);border-top-color:var(--color-accent, var(--color-info));border-radius:50%;animation:se-pt-loading-spin 1s linear infinite}',
            '@keyframes se-pt-loading-spin{to{transform:rotate(360deg)}}',
            '.se-cf-backdrop{position:fixed;top:0;left:0;right:0;bottom:0;z-index:10001;background:color-mix(in srgb, var(--color-black), transparent 55%);display:flex;align-items:center;justify-content:center;padding:1rem;animation:se-cf-fade 0.15s ease}',
            '@keyframes se-cf-fade{from{opacity:0}to{opacity:1}}',
            '.se-cf{background:var(--color-bg-card,var(--bg-card,#fff));color:var(--color-text-primary,var(--text-primary,inherit));border:1px solid var(--color-border,var(--border-color,#e5e5e5));border-radius:var(--radius-md,8px);box-shadow:0 12px 40px color-mix(in srgb, var(--color-black), transparent 70%);max-width:26rem;width:100%;padding:1.25rem 1.5rem}',
            '.se-cf-title{font-weight:600;font-size:1rem;margin:0 0 0.5rem}',
            '.se-cf-msg{font-size:0.9rem;line-height:1.5;margin:0 0 1.25rem;color:var(--color-text-secondary,var(--text-secondary,inherit));white-space:pre-line}',
            '.se-cf-actions{display:flex;justify-content:flex-end;gap:0.5rem}',
            '.se-cf-btn{padding:0.5rem 1rem;border-radius:var(--radius-input,6px);font-size:0.875rem;font-weight:500;cursor:pointer;border:1px solid var(--color-border,var(--border-color,#d5d5d5));background:none;color:inherit;font-family:inherit}',
            '.se-cf-btn--confirm{background:var(--color-primary);border-color:transparent;color:var(--text-inverse,#fff)}',
            '.se-cf-btn--danger{background:var(--color-error,var(--color-primary));border-color:transparent;color:var(--text-inverse,#fff)}',
            '.se-cf-input{display:block;width:100%;box-sizing:border-box;margin:0 0 1.25rem;padding:0.5rem 0.75rem;font-size:0.875rem;font-family:inherit;color:inherit;background:var(--color-bg,var(--bg-card,#fff));border:1px solid var(--color-border,var(--border-color,#d5d5d5));border-radius:var(--radius-input,6px)}',
            '.se-cf-input:focus{outline:2px solid var(--color-primary,var(--color-info));outline-offset:1px}',
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

    // ---- in-app dialogs (se-cf) — Promise-based replacements for native confirm()/prompt() ----
    var confirmQueue = [];
    var confirmBackdrop = null;
    var confirmResolve = null;
    var confirmPrevFocus = null;
    var confirmInput = null;

    function confirmKeyHandler(e) {
        if (e.key === 'Escape') {
            e.stopPropagation();
            closeConfirm(false);
        }
    }

    function closeConfirm(result) {
        var backdrop = confirmBackdrop;
        var resolve = confirmResolve;
        var input = confirmInput;
        confirmBackdrop = null;
        confirmResolve = null;
        confirmInput = null;
        document.removeEventListener('keydown', confirmKeyHandler, true);
        if (backdrop && backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
        if (confirmPrevFocus && confirmPrevFocus.focus) {
            try { confirmPrevFocus.focus(); } catch (e) { /* element may be gone */ }
        }
        confirmPrevFocus = null;
        if (resolve) resolve(input ? (result ? input.value : null) : result);
        drainConfirmQueue();
    }

    function openConfirm(item) {
        var opts = item.opts;
        confirmResolve = item.resolve;
        confirmPrevFocus = document.activeElement;

        var backdrop = document.createElement('div');
        backdrop.className = 'se-cf-backdrop';
        backdrop.addEventListener('click', function (e) {
            if (e.target === backdrop) closeConfirm(false);
        });

        var dialog = document.createElement('div');
        dialog.className = 'se-cf';
        dialog.setAttribute('role', 'dialog');
        dialog.setAttribute('aria-modal', 'true');
        dialog.setAttribute('aria-labelledby', 'se-cf-title');
        dialog.setAttribute('aria-describedby', 'se-cf-msg');

        var title = document.createElement('h2');
        title.className = 'se-cf-title';
        title.id = 'se-cf-title';
        title.textContent = opts.title || (item.isPrompt ? 'Input' : 'Confirm');
        dialog.appendChild(title);

        var msg = document.createElement('p');
        msg.className = 'se-cf-msg';
        msg.id = 'se-cf-msg';
        msg.textContent = item.message;
        dialog.appendChild(msg);

        var input = null;
        if (item.isPrompt) {
            input = document.createElement('input');
            input.type = 'text';
            input.className = 'se-cf-input';
            input.value = opts.defaultValue != null ? opts.defaultValue : '';
            if (opts.placeholder) input.placeholder = opts.placeholder;
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    closeConfirm(true);
                }
            });
            dialog.appendChild(input);
            confirmInput = input;
        }

        var actions = document.createElement('div');
        actions.className = 'se-cf-actions';

        var cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'se-cf-btn';
        cancelBtn.textContent = opts.cancelLabel || 'Cancel';
        cancelBtn.addEventListener('click', function () { closeConfirm(false); });
        actions.appendChild(cancelBtn);

        var okBtn = document.createElement('button');
        okBtn.type = 'button';
        okBtn.className = 'se-cf-btn ' + (opts.danger ? 'se-cf-btn--danger' : 'se-cf-btn--confirm');
        okBtn.textContent = opts.confirmLabel || 'OK';
        okBtn.addEventListener('click', function () { closeConfirm(true); });
        actions.appendChild(okBtn);

        dialog.appendChild(actions);
        backdrop.appendChild(dialog);
        document.body.appendChild(backdrop);
        confirmBackdrop = backdrop;

        document.addEventListener('keydown', confirmKeyHandler, true);
        if (input) {
            input.focus();
            input.select();
        } else {
            (opts.danger ? cancelBtn : okBtn).focus();
        }
    }

    function drainConfirmQueue() {
        if (confirmResolve !== null || confirmQueue.length === 0) return;
        openConfirm(confirmQueue.shift());
    }

    function confirm(message, opts) {
        return new Promise(function (resolve) {
            confirmQueue.push({ message: message, opts: opts || {}, resolve: resolve, isPrompt: false });
            drainConfirmQueue();
        });
    }

    // Promise-based replacement for native prompt() — resolves the entered
    // string (possibly ''), or null on Cancel/Escape/backdrop click.
    // Second arg may be an opts object { title, defaultValue, placeholder,
    // confirmLabel, cancelLabel } or a plain string defaultValue for
    // drop-in replacement of prompt(message, defaultValue).
    function prompt(message, opts) {
        if (typeof opts === 'string') opts = { defaultValue: opts };
        return new Promise(function (resolve) {
            confirmQueue.push({ message: message, opts: opts || {}, resolve: resolve, isPrompt: true });
            drainConfirmQueue();
        });
    }

    window.SemptifyFeedback = {
        start: start,
        done: done,
        success: function (msg, opts) { enqueue('success', 'Success', msg, opts); },
        error:   function (msg, opts) { enqueue('error',   'Error',   msg, opts); },
        info:    function (msg, opts) { enqueue('info',    'Tip',     msg, opts); },
        story:   story,
        confirm: confirm,
        prompt:  prompt,
    };
})();

// ---- [data-confirm] delegation ---------------------------------------------
// Declarative confirmations for the smart toolbar (rule 12): any
// <form data-confirm="..."> or <a data-confirm="..."> routes through
// SemptifyFeedback.confirm — the canonical in-app dialog. Native confirm()
// is banned repo-wide. Add data-confirm-danger for the destructive style.
(function () {
    if (!window.SemptifyFeedback || !window.SemptifyFeedback.confirm) return;

    document.addEventListener('submit', function (e) {
        var f = e.target.closest('form[data-confirm]');
        if (!f) return;
        if (f.dataset.confirmed === '1') { delete f.dataset.confirmed; return; }
        e.preventDefault();
        window.SemptifyFeedback
            .confirm(f.dataset.confirm, { danger: f.hasAttribute('data-confirm-danger') })
            .then(function (ok) {
                if (!ok) return;
                f.dataset.confirmed = '1';
                if (f.requestSubmit) f.requestSubmit(); else f.submit();
            });
    });

    document.addEventListener('click', function (e) {
        var a = e.target.closest('a[data-confirm]');
        if (!a) return;
        if (a.dataset.confirmed === '1') { delete a.dataset.confirmed; return; }
        e.preventDefault();
        window.SemptifyFeedback
            .confirm(a.dataset.confirm, { danger: a.hasAttribute('data-confirm-danger') })
            .then(function (ok) {
                if (!ok) return;
                a.dataset.confirmed = '1';
                a.click();
            });
    });
})();
