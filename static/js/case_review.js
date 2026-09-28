/**
 * Case Review — Evidence Index page controller.
 *
 * Flow (task order): check unlock → pick case → tag documents → edit legend
 * → write linked notes → copy the paste-ready index. All reads/writes go to
 * /api/case-review/*; document bytes stream read-only from /api/dc.
 */
(function () {
    'use strict';

    var API = '/api/case-review';
    var DC_VIEW = '/api/dc/document/';

    var state = {
        unlocked: false,
        cases: [],
        caseId: null,
        documents: [],
        legend: [],
        notes: [],
        currentDocId: null
    };

    function $(id) { return document.getElementById(id); }

    function api(path, opts) {
        opts = opts || {};
        opts.credentials = 'include';
        if (opts.body && typeof opts.body !== 'string') {
            opts.body = JSON.stringify(opts.body);
            opts.headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
        }
        return fetch(API + path, opts).then(function (r) {
            if (r.status === 403) {
                state.unlocked = false;
                renderGate();
                throw new Error('locked');
            }
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });
    }

    // ---- Gate ---------------------------------------------------------------

    function renderGate() {
        $('crLocked').hidden = state.unlocked;
        $('crShell').style.display = state.unlocked ? '' : 'none';
    }

    function initGate() {
        $('crUnlockBtn').addEventListener('click', function () {
            api('/share-initialized', { method: 'POST', body: {} })
                .then(function () {
                    state.unlocked = true;
                    renderGate();
                    loadCases();
                })
                .catch(function () {});
        });
    }

    // ---- Cases --------------------------------------------------------------

    function loadCases() {
        api('/cases').then(function (data) {
            state.cases = data.cases || [];
            var sel = $('crCasePicker');
            sel.innerHTML = '<option value="">— Choose a case —</option>';
            state.cases.forEach(function (c) {
                var o = document.createElement('option');
                o.value = c.incident_id;
                o.textContent = c.title || ('Case ' + c.incident_id);
                sel.appendChild(o);
            });
        }).catch(function () {});
    }

    function selectCase(caseId) {
        state.caseId = caseId;
        state.currentDocId = null;
        if (!caseId) return;
        loadDocuments();
        loadLegend();
        loadNotes();
    }

    // ---- Documents (left pane) ----------------------------------------------

    var CATEGORY_ORDER = ['foundational', 'discovery', 'motion', 'evidence', 'misc'];
    var CATEGORY_HEADS = {
        foundational: 'Foundational',
        discovery: 'Discovery',
        motion: 'Motions',
        evidence: 'Evidence',
        misc: 'Misc'
    };

    function loadDocuments() {
        api('/cases/' + state.caseId + '/documents').then(function (data) {
            state.documents = data.documents || [];
            renderDocGroups();
        }).catch(function () {});
    }

    function renderDocGroups() {
        var host = $('crDocGroups');
        host.innerHTML = '';
        var tagged = {}, untagged = [];
        state.documents.forEach(function (d) {
            if (d.tagged) {
                (tagged[d.category] = tagged[d.category] || []).push(d);
            } else {
                untagged.push(d);
            }
        });
        CATEGORY_ORDER.forEach(function (cat) {
            if (tagged[cat] && tagged[cat].length) {
                host.appendChild(groupEl(CATEGORY_HEADS[cat], tagged[cat]));
            }
        });
        if (untagged.length) {
            host.appendChild(groupEl('Not in this index yet', untagged));
        }
    }

    function groupEl(title, docs) {
        var g = document.createElement('div');
        g.className = 'cr-group';
        var h = document.createElement('div');
        h.className = 'cr-group-head';
        h.textContent = title;
        g.appendChild(h);
        docs.forEach(function (d) { g.appendChild(docEl(d)); });
        return g;
    }

    function docEl(d) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'cr-doc' + (d.id === state.currentDocId ? ' cr-active' : '');
        var name = document.createElement('span');
        name.className = 'cr-doc-name';
        name.textContent = d.name;
        b.appendChild(name);
        var meta = document.createElement('span');
        meta.className = 'cr-doc-meta';
        var bits = [];
        if (d.evidence_type && d.evidence_type !== 'none') bits.push(d.evidence_type);
        if (d.uploaded_at) bits.push(String(d.uploaded_at).slice(0, 10));
        meta.textContent = bits.join(' · ');
        b.appendChild(meta);
        b.addEventListener('click', function () { focusDoc(d); });
        return b;
    }

    // ---- Viewer (center pane) ------------------------------------------------

    function focusDoc(d) {
        state.currentDocId = d.id;
        $('crDocTitle').textContent = d.name;
        var url = DC_VIEW + encodeURIComponent(d.id) + '/view';
        var f = $('crViewer');
        f.src = url;
        f.hidden = false;
        $('crViewerEmpty').style.display = 'none';
        var full = $('crOpenFull');
        full.href = url;
        full.hidden = false;
        var bar = $('crTagBar');
        bar.hidden = false;
        $('crTagCategory').value = d.category || '';
        $('crTagEvidence').value = d.evidence_type || 'none';
        renderDocGroups();
    }

    function initTagBar() {
        $('crTagCategory').addEventListener('change', saveTag);
        $('crTagEvidence').addEventListener('change', saveTag);
    }

    function saveTag() {
        if (!state.caseId || !state.currentDocId) return;
        var cat = $('crTagCategory').value;
        var doc = currentDoc();
        if (!cat) {
            api('/cases/' + state.caseId + '/documents/' + encodeURIComponent(state.currentDocId) + '/tag',
                { method: 'DELETE' }).then(loadDocuments).catch(function () {});
            return;
        }
        api('/cases/' + state.caseId + '/documents/' + encodeURIComponent(state.currentDocId) + '/tag', {
            method: 'PUT',
            body: {
                category: cat,
                evidence_type: $('crTagEvidence').value,
                name: doc ? doc.name : null,
                vault_path: doc ? doc.vault_path : null
            }
        }).then(loadDocuments).catch(function () {});
    }

    function currentDoc() {
        return state.documents.filter(function (d) { return d.id === state.currentDocId; })[0] || null;
    }

    // ---- Legend + notes (right pane) -----------------------------------------

    function loadLegend() {
        api('/cases/' + state.caseId + '/legend').then(function (data) {
            state.legend = data.entries || [];
            renderLegend();
        }).catch(function () {});
    }

    function renderLegend() {
        var host = $('crLegend');
        host.innerHTML = '';
        $('crLegendSave').hidden = true;
        state.legend.forEach(function (e, i) {
            var row = document.createElement('div');
            row.className = 'cr-legend-row';
            var color = document.createElement('input');
            color.type = 'color';
            color.value = /^#[0-9a-fA-F]{6}$/.test(e.color) ? e.color : '#f2d16b';
            color.setAttribute('aria-label', 'Color for ' + e.label);
            color.addEventListener('input', function () { $('crLegendSave').hidden = false; });
            var label = document.createElement('input');
            label.type = 'text';
            label.value = e.label;
            label.setAttribute('aria-label', 'Legend label ' + (i + 1));
            label.addEventListener('input', function () { $('crLegendSave').hidden = false; });
            row.appendChild(color);
            row.appendChild(label);
            host.appendChild(row);
        });
        var add = document.createElement('button');
        add.type = 'button';
        add.className = 'cr-btn';
        add.textContent = '+ Add label';
        add.addEventListener('click', function () {
            state.legend.push({ label: 'New label', color: '#f2d16b' });
            renderLegend();
            $('crLegendSave').hidden = false;
        });
        host.appendChild(add);
        // Note composer label options
        var sel = $('crNoteLegend');
        sel.innerHTML = '<option value="">— label —</option>';
        state.legend.forEach(function (e) {
            var o = document.createElement('option');
            o.value = e.label;
            o.textContent = e.label;
            sel.appendChild(o);
        });
    }

    function saveLegend() {
        var rows = document.querySelectorAll('#crLegend .cr-legend-row');
        var entries = [];
        rows.forEach(function (row) {
            var inputs = row.querySelectorAll('input');
            entries.push({ label: inputs[1].value.trim(), color: inputs[0].value });
        });
        api('/cases/' + state.caseId + '/legend', { method: 'PUT', body: { entries: entries } })
            .then(function (data) {
                state.legend = data.entries || [];
                renderLegend();
            }).catch(function () {});
    }

    function loadNotes() {
        api('/cases/' + state.caseId + '/notes').then(function (data) {
            state.notes = data.notes || [];
            renderNotes();
        }).catch(function () {});
    }

    function legendColor(label) {
        for (var i = 0; i < state.legend.length; i++) {
            if (state.legend[i].label === label) return state.legend[i].color;
        }
        return 'var(--zone-surface-3)';
    }

    function renderNotes() {
        var host = $('crNoteList');
        host.innerHTML = '';
        if (!state.notes.length) {
            var p = document.createElement('p');
            p.className = 'cr-doc-meta';
            p.style.padding = '0.5rem';
            p.textContent = 'No notes yet — pick a document, then add one below.';
            host.appendChild(p);
            return;
        }
        state.notes.forEach(function (n) {
            var div = document.createElement('div');
            div.className = 'cr-note';
            if (n.legend_label) {
                var lbl = document.createElement('span');
                lbl.className = 'cr-note-label';
                lbl.style.background = legendColor(n.legend_label);
                lbl.textContent = n.legend_label;
                div.appendChild(lbl);
            }
            var t = document.createElement('div');
            t.textContent = n.text;
            div.appendChild(t);
            if (n.links && n.links.length) {
                var links = document.createElement('div');
                links.className = 'cr-note-links';
                links.textContent = n.links.map(function (l) {
                    return (l.name || l.document_id) + (l.location ? ', ' + l.location : '');
                }).join('  ·  ');
                div.appendChild(links);
            }
            var actions = document.createElement('div');
            actions.className = 'cr-note-actions';
            var del = document.createElement('button');
            del.type = 'button';
            del.className = 'cr-btn cr-btn-danger';
            del.textContent = 'Remove';
            del.addEventListener('click', function () {
                api('/cases/' + state.caseId + '/notes/' + encodeURIComponent(n.id), { method: 'DELETE' })
                    .then(loadNotes).catch(function () {});
            });
            actions.appendChild(del);
            div.appendChild(actions);
            host.appendChild(div);
        });
    }

    function initNoteForm() {
        $('crNoteForm').addEventListener('submit', function (ev) {
            ev.preventDefault();
            var text = $('crNoteText').value.trim();
            if (!text || !state.caseId) return;
            var links = [];
            if (state.currentDocId) {
                var doc = currentDoc();
                links.push({
                    document_id: state.currentDocId,
                    vault_path: doc ? doc.vault_path : null,
                    name: doc ? doc.name : null,
                    location: $('crNoteLocation').value.trim() || null
                });
            }
            api('/cases/' + state.caseId + '/notes', {
                method: 'POST',
                body: { text: text, links: links, legend_label: $('crNoteLegend').value || null }
            }).then(function () {
                $('crNoteText').value = '';
                $('crNoteLocation').value = '';
                loadNotes();
            }).catch(function () {});
        });
    }

    // ---- Export ---------------------------------------------------------------

    function initExport() {
        $('crExportBtn').addEventListener('click', function () {
            if (!state.caseId) return;
            fetch(API + '/cases/' + state.caseId + '/export', { credentials: 'include' })
                .then(function (r) { return r.text(); })
                .then(function (text) {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(text).then(function () {
                            $('crExportMsg').textContent = 'Copied — paste it into an email or doc.';
                        });
                    } else {
                        var w = window.open('', '_blank');
                        if (w) { w.document.write('<pre>' + text.replace(/</g, '&lt;') + '</pre>'); }
                        $('crExportMsg').textContent = 'Opened in a new tab — select all and copy.';
                    }
                })
                .catch(function () { $('crExportMsg').textContent = 'Export failed — try again.'; });
        });
    }

    // ---- Boot -----------------------------------------------------------------

    document.addEventListener('DOMContentLoaded', function () {
        initGate();
        initTagBar();
        initNoteForm();
        initExport();
        $('crLegendSave').addEventListener('click', saveLegend);
        $('crCasePicker').addEventListener('change', function (e) { selectCase(e.target.value); });
        api('/status').then(function (data) {
            state.unlocked = !!(data && data.unlocked);
            renderGate();
            if (state.unlocked) loadCases();
        }).catch(function () { renderGate(); });
    });
})();
