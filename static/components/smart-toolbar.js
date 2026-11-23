/*
 * Smart Toolbar — client-side port for JS-polled pages.
 * =============================================================================
 * Sibling of app/core/smart_toolbar.py (server-side project_toolbar +
 * components/smart_toolbar.html) and of the fleet engine in
 * master-repo/tools/smart_toolbar.py — same contract, keep in sync.
 *
 * Rule: .devin/rules/12-state-driven-actions.md — given an entity state,
 * the engine decides which actions exist. States with no rule (or an empty
 * projection) render NOTHING — never a disabled button.
 *
 * Usage:
 *   SmartToolbar.project(state, actions, rules, maxVisible=3)
 *     actions: {id: {id|action_id, label, endpoint|target, method, confirm,
 *                    confirmation_prompt, danger, cls}}
 *     rules:   {STATE: {primary: 'id', contextual: ['id', ...]}}
 *   SmartToolbar.render(el, projection, opts)
 *     empties el and fills it. GET/link endpoints render <a href>
 *     (data-confirm is emitted so SemptifyFeedback handles prompts);
 *     anything else renders <button> that calls opts.act(action)
 *     (default: fetch POST to action.endpoint).
 *     opts.classes overrides the default class map; per-action .cls wins.
 */
window.SmartToolbar = (function () {
function ent(a, resolve) {
    return {
        id: a.action_id || a.id,
        label: a.label || '',
        endpoint: resolve ? resolve(a) : (a.endpoint || a.target || '#'),
        method: a.method || ((a.action_type || '').split('.').pop().toLowerCase()
            in { navigate: 1, download: 1, share: 1, external: 1, link: 1 } ? 'GET' : 'POST'),
        confirm: a.confirmation_prompt || a.confirm || null,
        danger: !!a.danger,
        cls: a.cls || null,
    };
}
function project(state, actions, rules, maxVisible) {
    var r = rules[state] || rules[String(state).toUpperCase()] || rules[String(state).toLowerCase()];
    if (!r) return { primary: null, visible: [], overflow: [] };
    var pick = function (k) { return k && actions[k] ? ent(actions[k]) : null; };
    var cx = (r.contextual || []).map(pick).filter(Boolean), mv = maxVisible || 3;
    return { primary: pick(r.primary), visible: cx.slice(0, mv), overflow: cx.slice(mv) };
}
function isLink(a) {
    return (a.method || 'GET') === 'GET' || /^https?:|^tel:|^mailto:/.test(a.endpoint);
}
function mkA(a, cls, o) {
    if (isLink(a)) {
        var l = document.createElement('a');
        l.className = cls;
        l.href = a.endpoint;
        l.textContent = a.label;
        if (a.confirm) {
            l.setAttribute('data-confirm', a.confirm);
            if (a.danger) l.setAttribute('data-confirm-danger', '');
        }
        return l;
    }
    var b = document.createElement('button');
    b.type = 'button';
    b.className = cls;
    b.textContent = a.label;
    b.onclick = function () {
        (o.act || function (x) {
            fetch(x.endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: '{}',
            });
        })(a);
    };
    return b;
}
function render(el, proj, o) {
    o = o || {};
    var k = Object.assign({
        wrap: 'smart-toolbar flex gap-3',
        primary: 'btn btn--primary',
        ghost: 'btn btn--ghost',
        danger: 'btn btn--danger',
        summary: 'btn btn--ghost',
        menu: 'smart-toolbar__menu',
        item: 'smart-toolbar__menu-item',
        itemDanger: 'text-error',
    }, o.classes || {});
    el.innerHTML = '';
    if (!proj || (!proj.primary && !(proj.visible || []).length && !(proj.overflow || []).length)) return;
    var w = document.createElement('div');
    w.className = k.wrap;
    w.setAttribute('role', 'toolbar');
    if (proj.primary) w.appendChild(mkA(proj.primary, proj.primary.cls || k.primary, o));
    (proj.visible || []).forEach(function (a) {
        w.appendChild(mkA(a, a.cls || (a.danger ? k.danger : k.ghost), o));
    });
    if ((proj.overflow || []).length) {
        var d = document.createElement('details');
        d.className = 'smart-toolbar__overflow';
        var s = document.createElement('summary');
        s.className = k.summary;
        s.setAttribute('aria-label', 'More actions');
        s.innerHTML = '&#8942;';
        d.appendChild(s);
        var m = document.createElement('div');
        m.className = k.menu;
        proj.overflow.forEach(function (a) {
            m.appendChild(mkA(a, a.cls || k.item + (a.danger ? ' ' + k.itemDanger : ''), o));
        });
        d.appendChild(m);
        w.appendChild(d);
    }
    el.appendChild(w);
}
return { project: project, render: render };
})();
