/* Media Player — Semptify's universal file viewer.
   One borderless, resizable, liquid surface for every format a user can
   pick up: docx (mammoth), pdf, image, plain text, audio, video — and an
   honest fallback for anything the browser genuinely cannot show.
   Client-side only: preview bytes never leave the device. */
(function () {
    'use strict';

    var RE = {
        docx: /\.docx$/i,
        doc: /\.doc$/i,
        pdf: /\.pdf$/i,
        image: /\.(jpe?g|png|gif|webp|bmp|svg|avif)$/i,
        text: /\.(txt|md|markdown|csv|log|json|xml|ya?ml|rtf)$/i,
        audio: /\.(mp3|m4a|wav|ogg|oga|opus|aac|flac)$/i,
        video: /\.(mp4|webm|mov|m4v|mkv)$/i
    };

    var DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

    function classify(name, mime) {
        var n = (name || '').toLowerCase();
        var m = (mime || '').toLowerCase();
        if (RE.docx.test(n) || m === DOCX_MIME) return 'docx';
        if (RE.doc.test(n) || m === 'application/msword') return 'legacy-doc';
        if (RE.pdf.test(n) || m === 'application/pdf') return 'pdf';
        if (RE.image.test(n) || m.indexOf('image/') === 0) return 'image';
        if (RE.audio.test(n) || m.indexOf('audio/') === 0) return 'audio';
        if (RE.video.test(n) || m.indexOf('video/') === 0) return 'video';
        if (RE.text.test(n) || m === 'text/plain' || m === 'text/markdown' || m === 'text/csv') return 'text';
        if (m === 'text/html' || /\.html?$/i.test(n)) return 'html';
        return 'other';
    }

    function el(tag, cls, text) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text != null) e.textContent = text;
        return e;
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function emptyState(msg, hint) {
        var d = el('div', 'mp__empty');
        d.appendChild(el('div', 'mp__empty--icon', '◆'));
        d.appendChild(el('p', null, msg));
        if (hint) d.appendChild(el('p', 'mp__empty-hint', hint));
        return d;
    }

    /* mount(host, opts) → player
       opts: { file|blob|url, name, mime, tools (show docx edit bar),
               fill (host owns height/scroll — DC viewer), onstatus } */
    async function mount(host, opts) {
        opts = opts || {};
        var root = el('div', 'mp' + (opts.fill ? ' mp--fill' : ''));
        var toolsBar = null;
        var surface = el('div', 'mp__surface');
        var status = el('div', 'mp__status');
        status.style.display = 'none';

        var player = {
            kind: 'other', root: root, surface: surface,
            _docEl: null, _editable: false, _source: null,

            say: function (msg, tone) {
                status.style.display = msg ? '' : 'none';
                status.textContent = msg || '';
                status.className = 'mp__status' + (tone === 'err' ? ' mp__status--err' : tone === 'ok' ? ' mp__status--ok' : '');
                if (opts.onstatus) opts.onstatus(msg, tone);
            },

            setEditable: function (on) {
                if (!player._docEl) return;
                player._editable = !!on;
                player._docEl.contentEditable = on ? 'true' : 'false';
                if (toolsBar) {
                    toolsBar.querySelectorAll('[data-mp-when]').forEach(function (b) {
                        b.style.display = b.getAttribute('data-mp-when') === (on ? 'edit' : 'view') ? '' : 'none';
                    });
                }
            },
            isEditable: function () { return player._editable; },

            getHtml: function () {
                return player._docEl ? player._docEl.innerHTML : '';
            },

            /* Edited docx → real OOXML Blob via docx_export.js + jszip.
               Async — returns a Promise<Blob>. */
            exportBlob: function () {
                if (!window.SemptifyDocxExport || !window.JSZip) {
                    return Promise.reject(new Error('docx export library not loaded'));
                }
                return SemptifyDocxExport.fromHtml(player.getHtml()).then(function (blob) {
                    var dropped = SemptifyDocxExport.fromHtml.droppedImages;
                    if (dropped) player.say('Note: ' + dropped + ' embedded image(s) are not carried into the edited copy — text is.', 'err');
                    return blob;
                });
            },

            downloadEdited: function (baseName) {
                return player.exportBlob().then(function (blob) {
                    var a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = (baseName || 'document').replace(/\.docx$/i, '') + '-edited.docx';
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
                });
            },

            destroy: function () { root.remove(); }
        };

        var name = opts.name || (opts.file && opts.file.name) || '';
        var mime = opts.mime || (opts.file && opts.file.type) || '';
        var kind = classify(name, mime);
        player.kind = kind;

        async function blob() {
            if (opts.blob) return opts.blob;
            if (opts.file) return opts.file;
            if (opts.url) {
                var r = await fetch(opts.url, { credentials: 'include' });
                if (!r.ok) throw new Error('Could not load the file (HTTP ' + r.status + ')');
                return await r.blob();
            }
            throw new Error('Nothing to preview');
        }

        host.innerHTML = '';
        host.appendChild(root);
        if (opts.tools && kind === 'docx') {
            toolsBar = el('div', 'mp__tools');
            var bEdit = el('button', 'frame-btn', '✎ Edit');
            bEdit.type = 'button'; bEdit.setAttribute('data-mp-when', 'view');
            var bDone = el('button', 'frame-btn', 'Done editing');
            bDone.type = 'button'; bDone.setAttribute('data-mp-when', 'edit'); bDone.style.display = 'none';
            var bDl = el('button', 'frame-btn', 'Download edited .docx');
            bDl.type = 'button'; bDl.setAttribute('data-mp-when', 'edit'); bDl.style.display = 'none';
            var bSave = null;
            if (opts.saveCopy) {
                bSave = el('button', 'frame-btn', 'Save copy to vault');
                bSave.type = 'button'; bSave.setAttribute('data-mp-when', 'edit'); bSave.style.display = 'none';
                bSave.addEventListener('click', function () {
                    player.say('Saving a copy to your vault…');
                    player.exportBlob()
                        .then(function (blob) { return opts.saveCopy(blob, name); })
                        .then(function () { player.say('Copy saved to your vault.', 'ok'); })
                        .catch(function (e) { player.say('Save failed: ' + (e.message || e), 'err'); });
                });
            }
            bEdit.addEventListener('click', function () { player.setEditable(true); player.say('Editing — your original is untouched until you save a copy.'); });
            bDone.addEventListener('click', function () { player.setEditable(false); player.say(''); });
            bDl.addEventListener('click', function () {
                player.downloadEdited(name)
                    .then(function () { player.say('Edited copy downloaded.', 'ok'); })
                    .catch(function (e) { player.say('Export failed: ' + (e.message || e), 'err'); });
            });
            [bEdit, bDone, bDl, bSave].forEach(function (b) { if (b) toolsBar.appendChild(b); });
            toolsBar.appendChild(el('span', 'mp__state', 'view only until you press Edit'));
            root.appendChild(toolsBar);
        }
        root.appendChild(surface);
        root.appendChild(status);

        try {
            if (kind === 'docx') {
                if (!window.mammoth) throw new Error('docx viewer library not loaded');
                var b = await blob();
                var ab = await b.arrayBuffer();
                var res = await mammoth.convertToHtml({ arrayBuffer: ab });
                var doc = el('div', 'mp__doc');
                doc.innerHTML = res.value || '<p>(This document appears to be empty.)</p>';
                player._docEl = doc;
                surface.appendChild(doc);
                if (res.messages && res.messages.length) {
                    player.say('Shown as plain text layout — some formatting may look different than Word.');
                }
            } else if (kind === 'text') {
                var b2 = await blob();
                var txt = await b2.text();
                surface.appendChild(el('pre', 'mp__text', txt.slice(0, 400000)));
                if (txt.length > 400000) player.say('Showing the first part of a large file.');
            } else if (kind === 'image') {
                var b3 = await blob();
                var img = el('img', 'mp__img');
                img.src = URL.createObjectURL(b3);
                img.alt = name || 'Image';
                surface.appendChild(img);
            } else if (kind === 'audio' || kind === 'video') {
                var b4 = await blob();
                var media = el(kind === 'audio' ? 'audio' : 'video', 'mp__' + kind);
                media.controls = true;
                media.src = URL.createObjectURL(b4);
                surface.appendChild(media);
            } else if (kind === 'pdf' || kind === 'html') {
                var frame = el('iframe', 'mp__frame');
                if (opts.url) { frame.src = opts.url; }
                else { frame.src = URL.createObjectURL(await blob()); }
                surface.appendChild(frame);
            } else {
                surface.appendChild(emptyState(
                    kind === 'legacy-doc'
                        ? 'This is an old Word format (.doc) that cannot be previewed here.'
                        : 'This file type cannot be previewed.',
                    'Check the filename carefully, then upload anyway if it is the right file.'
                ));
            }
        } catch (e) {
            surface.innerHTML = '';
            surface.appendChild(emptyState('Could not preview this file.',
                'It may still upload fine — check the filename and continue if it is the right one.'));
            player.say(e && e.message ? e.message : 'preview failed', 'err');
        }
        return player;
    }

    window.SemptifyMediaPlayer = { mount: mount, classify: classify, escapeHtml: escapeHtml };
})();
