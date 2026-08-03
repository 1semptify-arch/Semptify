/* Context Engine Panel — surfaces verified facts + tenant stories
   Usage: <div id="context-panel" data-subject="eviction"></div>
          <script src="/static/components/context-panel.js"></script>
   Renders: facts (verified) + stories (published) for the given subject.
*/
(function () {
    'use strict';

    function fetchJSON(url) {
        return fetch(url, { credentials: 'include' }).then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });
    }

    function escHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function renderFacts(container, facts) {
        if (!facts || facts.length === 0) {
            container.innerHTML = '<p class="ctx-empty">No verified facts yet for this topic.</p>';
            return;
        }
        var html = facts.slice(0, 5).map(function (f) {
            var source = f.source_url ? '<a href="' + escHtml(f.source_url) + '" target="_blank" rel="noopener" class="ctx-source">Source ▸</a>' : '';
            return '<div class="ctx-fact">' +
                '<div class="ctx-claim">' + escHtml(f.claim) + '</div>' +
                '<div class="ctx-meta">' +
                    '<span class="ctx-jurisdiction">' + escHtml(f.jurisdiction || 'MN') + '</span>' +
                    (f.is_verified ? '<span class="ctx-verified">● Verified</span>' : '<span class="ctx-unverified">Unverified</span>') +
                    source +
                '</div>' +
            '</div>';
        }).join('');
        container.innerHTML = html;
    }

    function renderStories(container, stories) {
        if (!stories || stories.length === 0) {
            container.innerHTML = '<p class="ctx-empty">No tenant stories yet for this topic.</p>';
            return;
        }
        var html = stories.slice(0, 3).map(function (s) {
            var body = s.body || s.circumstance || '';
            var outcome = s.outcome ? '<div class="ctx-story-outcome"><strong>Outcome:</strong> ' + escHtml(s.outcome) + '</div>' : '';
            return '<div class="ctx-story">' +
                '<div class="ctx-story-body">' + escHtml(body) + '</div>' +
                outcome +
                (s.outcome === 'avoided_court' ? '<div class="ctx-story-tag">● Avoided court</div>' : '') +
            '</div>';
        }).join('');
        container.innerHTML = html;
    }

    function loadPanel(el) {
        var subject = el.dataset.subject || 'eviction';
        var jurisdiction = el.dataset.jurisdiction || 'MN';
        var showStories = el.dataset.stories !== 'false';
        var showFacts = el.dataset.facts !== 'false';

        el.innerHTML = '<div class="ctx-loading">Loading context...</div>';

        var promises = [];
        if (showFacts) {
            promises.push(fetchJSON('/api/context/facts?subject=' + encodeURIComponent(subject) + '&jurisdiction=' + encodeURIComponent(jurisdiction)).catch(function () { return []; }));
        } else {
            promises.push(Promise.resolve([]));
        }
        if (showStories) {
            promises.push(fetchJSON('/api/context/stories?subject=' + encodeURIComponent(subject)).catch(function () { return []; }));
        } else {
            promises.push(Promise.resolve([]));
        }

        Promise.all(promises).then(function (results) {
            var facts = results[0] || [];
            var stories = results[1] || [];

            var factsHtml = showFacts ?
                '<div class="ctx-section"><h4 class="ctx-heading">Verified Facts</h4><div id="ctx-facts-' + subject + '"></div></div>' : '';
            var storiesHtml = showStories ?
                '<div class="ctx-section"><h4 class="ctx-heading">Tenant Stories</h4><div id="ctx-stories-' + subject + '"></div></div>' : '';

            el.innerHTML = factsHtml + storiesHtml;

            if (showFacts) {
                var factsEl = el.querySelector('#ctx-facts-' + subject);
                if (factsEl) renderFacts(factsEl, facts.facts || facts);
            }
            if (showStories) {
                var storiesEl = el.querySelector('#ctx-stories-' + subject);
                if (storiesEl) renderStories(storiesEl, stories.stories || stories);
            }
        }).catch(function (err) {
            el.innerHTML = '<p class="ctx-empty">Context unavailable right now.</p>';
            if (window.SemptifyFeedback) {
                SemptifyFeedback.error('Could not load context.', { detail: err.message });
            }
        });
    }

    function init() {
        var panels = document.querySelectorAll('[data-context-panel]');
        panels.forEach(function (el) { loadPanel(el); });
    }

    // Inject styles once
    if (!document.getElementById('ctx-panel-styles')) {
        var style = document.createElement('style');
        style.id = 'ctx-panel-styles';
        style.textContent = [
            '[data-context-panel]{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1.25rem;margin:1.5rem 0}',
            '.ctx-heading{font-size:0.95rem;font-weight:700;color:#1e293b;margin-bottom:0.75rem}',
            '.ctx-section{margin-bottom:1rem}',
            '.ctx-section:last-child{margin-bottom:0}',
            '.ctx-fact{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem}',
            '.ctx-claim{font-size:0.875rem;color:#1e293b;line-height:1.5;margin-bottom:0.4rem}',
            '.ctx-meta{display:flex;align-items:center;gap:0.75rem;font-size:0.75rem;color:#64748b}',
            '.ctx-jurisdiction{background:#e0e7ff;color:#3730a3;padding:0.1rem 0.4rem;border-radius:4px;font-weight:600}',
            '.ctx-verified{color:#059669;font-weight:600}',
            '.ctx-unverified{color:#d97706}',
            '.ctx-source{color:#3b82f6;text-decoration:none;margin-left:auto}',
            '.ctx-source:hover{text-decoration:underline}',
            '.ctx-story{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem}',
            '.ctx-story-body{font-size:0.875rem;color:#78350f;line-height:1.5;margin-bottom:0.4rem;font-style:italic}',
            '.ctx-story-outcome{font-size:0.8rem;color:#92400e}',
            '.ctx-story-tag{display:inline-block;background:#d1fae5;color:#065f46;padding:0.1rem 0.5rem;border-radius:4px;font-size:0.7rem;font-weight:600;margin-top:0.3rem}',
            '.ctx-empty{color:#94a3b8;font-size:0.85rem;padding:0.5rem 0}',
            '.ctx-loading{color:#94a3b8;font-size:0.85rem;padding:0.5rem 0}',
        ].join('\n');
        document.head.appendChild(style);
    }

    window.ContextPanel = { init: init, load: loadPanel };
    if (document.readyState !== 'loading') init();
    else document.addEventListener('DOMContentLoaded', init);
})();
