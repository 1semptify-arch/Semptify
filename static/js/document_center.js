/* Document Center — page logic extracted from document_center.html (task
 * document-center-js-extraction, 2026-09-18). Loaded at end of body after
 * pdf.js; runs as an IIFE with DOM ready. No Jinja — plain browser JS. */
(function () {
    if (window.pdfjsLib) {
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }
    const docList = document.getElementById('dcDocList');
    const docEmpty = document.getElementById('dcDocEmpty');
    const docName = document.getElementById('dcDocName');
    const typeSelect = document.getElementById('dcTypeSelect');
    const statusSelect = document.getElementById('dcStatusSelect');
    const downloadBtn = document.getElementById('dcDownloadBtn');
    const viewer = document.getElementById('dcViewer');
    const viewerEmpty = document.getElementById('dcViewerEmpty');
    const overlayList = document.getElementById('dcOverlayList');
    const overlayEmpty = document.getElementById('dcOverlayEmpty');
    const unlocksDiv = document.getElementById('dcUnlocks');
    const overallSpan = document.getElementById('dcOverall');
    let currentDoc = null;
    let allDocs = [];
    let currentFilter = 'all';
    let previousUnlocks = null;
    let documentTypes = {};
    let currentTab = 'overlays';
    let fieldConfirmState = {};  // {vault_id: {field_name: 'confirmed'|'corrected'|'pending'}}
    let intakeSession = null;    // live /api/dc/intake session for currentDoc (null → mock walk)
    let intakeWordBoxes = null;  // {doc_id, boxes[]} cache for source-span highlight
    let activeMobilePane = 'left';

    function setMobilePane(pane) {
        if (!['left', 'center', 'right'].includes(pane)) return;
        activeMobilePane = pane;
        document.querySelectorAll('.dc-pane').forEach(el => {
            el.classList.toggle('dc-pane--active', el.dataset.pane === pane);
        });
        document.querySelectorAll('.dc-mobile-tab').forEach(btn => {
            if (btn.dataset.pane === pane) {
                btn.style.background = 'var(--color-calm-100)';
                btn.style.fontWeight = '600';
            } else {
                btn.style.background = '';
                btn.style.fontWeight = '';
            }
        });
    }

    async function loadDocumentTypes() {
        try {
            const r = await fetch('/api/dc/document-types', { credentials: 'include' });
            if (!r.ok) return;
            const data = await r.json();
            (data.types || []).forEach(t => { documentTypes[t.key] = t; });
        } catch (e) { /* silent */ }
    }

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }
    function showValueModal(title, initial) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;inset:0;background:color-mix(in srgb, var(--color-black), transparent 30%);z-index:200;display:flex;align-items:center;justify-content:center;';
            const box = document.createElement('div');
            box.style.cssText = 'background:var(--zone-surface-2);padding:1rem;max-width:400px;width:90%;border-radius:0.375rem;';
            const h = document.createElement('h4');
            h.style.cssText = 'color:var(--text-primary);margin-bottom:0.5rem;font-size:0.875rem;';
            h.textContent = title;
            const input = document.createElement('input');
            input.type = 'text';
            input.value = initial || '';
            input.style.cssText = 'width:100%;padding:0.5rem;margin-bottom:0.75rem;background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border-color);border-radius:0.25rem;';
            const btns = document.createElement('div');
            btns.style.cssText = 'display:flex;gap:0.5rem;justify-content:flex-end;';
            const ok = document.createElement('button');
            ok.className = 'frame-btn';
            ok.textContent = 'OK';
            const cancel = document.createElement('button');
            cancel.className = 'frame-btn';
            cancel.textContent = 'Cancel';
            function cleanup() { if (modal.parentNode) modal.remove(); }
            ok.addEventListener('click', () => { cleanup(); resolve(input.value); });
            cancel.addEventListener('click', () => { cleanup(); resolve(null); });
            input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { cleanup(); resolve(input.value); } if (e.key === 'Escape') { cleanup(); resolve(null); } });
            btns.appendChild(cancel);
            btns.appendChild(ok);
            box.appendChild(h);
            box.appendChild(input);
            box.appendChild(btns);
            modal.appendChild(box);
            document.body.appendChild(modal);
            input.focus();
        });
    }
    function fmtDate(s) {
        if (!s) return '';
        try {
            const d = new Date(s);
            if (isNaN(d.getTime())) return s;
            return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
        } catch (e) { return s; }
    }
    function statusIcon(s) {
        if (s === 'verified') return '●';
        if (s === 'review') return '◆';
        if (s === 'mismatched') return '▸';
        return '○';
    }

    function statusBadge(s) {
        const badges = {
            new: { label: 'Unverified', color: 'var(--text-muted)', bg: 'var(--color-gray-100)' },
            review: { label: 'In Review', color: 'var(--color-warning-800)', bg: 'var(--color-warning-50)' },
            verified: { label: 'Verified', color: 'var(--color-success-800)', bg: 'var(--color-success-50)' },
            mismatched: { label: 'Mismatched', color: 'var(--color-error-800)', bg: 'var(--color-error-50)' }
        };
        const b = badges[s] || badges.new;
        return b;
    }

    function computeMismatched(doc) {
        if (!doc.document_type || !documentTypes[doc.document_type]) return false;
        const state = fieldConfirmState[doc.id] || {};
        const def = documentTypes[doc.document_type];
        const required = def.fields.filter(f => f.required);
        const corrected = required.filter(f => state[f.name] === 'corrected');
        const confirmed = required.filter(f => state[f.name] === 'confirmed');
        return corrected.length > 0 && corrected.length >= confirmed.length;
    }

    function effectiveStatus(doc) {
        const state = fieldConfirmState[doc.id] || {};
        if (state.manual_status) return state.manual_status;
        if (computeMismatched(doc)) return 'mismatched';
        return doc.verification_status || 'new';
    }

    async function loadReviewState(doc) {
        if (!doc) return;
        try {
            const r = await fetch('/api/dc/document/' + encodeURIComponent(doc.id) + '/review-state', { credentials: 'include' });
            if (!r.ok) return;
            const data = await r.json();
            fieldConfirmState[doc.id] = data.field_confirm_state || {};
            fieldConfirmState[doc.id].manual_status = data.manual_status || '';
            if (statusSelect) statusSelect.value = data.effective_status || 'new';
        } catch (e) { /* silent */ }
    }

    async function saveReviewState(doc) {
        if (!doc) return;
        const state = Object.assign({}, fieldConfirmState[doc.id] || {});
        const manual = state.manual_status;
        delete state.manual_status;
        const payload = { field_confirm_state: state };
        if (manual) payload.manual_status = manual;
        try {
            const r = await fetch('/api/dc/document/' + encodeURIComponent(doc.id) + '/review-state', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                credentials: 'include'
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const data = await r.json();
            currentDoc.verification_status = data.effective_status;
            await loadDocs();
        } catch (err) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Could not save review state: ' + err.message);
        }
    }

    async function loadDocs() {
        try {
            const r = await fetch('/api/dc/list', { credentials: 'include' });
            if (!r.ok) {
                if (r.status === 401) {
                    docEmpty.querySelector('p').textContent = 'Sign in to see your documents.';
                    updateGuidanceRail();
                    return;
                }
                throw new Error('HTTP ' + r.status);
            }
            const data = await r.json();
            allDocs = data.documents || [];
            renderDocs();
        } catch (e) {
            docEmpty.querySelector('p').textContent = 'Could not load documents.';
            const hint = docEmpty.querySelector('.frame-empty--hint');
            if (hint) hint.textContent = e.message;
        }
        updateGuidanceRail();
    }

    function renderDocs() {
        const filtered = currentFilter === 'all'
            ? allDocs
            : allDocs.filter(d => effectiveStatus(d) === currentFilter);
        docList.innerHTML = '';
        if (!filtered.length) {
            docList.appendChild(docEmpty);
            docEmpty.querySelector('p').textContent = currentFilter === 'all' ? 'No documents yet.' : 'No ' + currentFilter + ' documents.';
            return;
        }
        filtered.forEach(d => {
            const row = document.createElement('div');
            row.className = 'frame-item';
            row.style.cursor = 'pointer';
            if (currentDoc && currentDoc.id === d.id) {
                row.style.background = 'var(--color-calm-100)';
            }
            const effStatus = effectiveStatus(d);
            const icon = document.createElement('div');
            icon.className = 'frame-item--icon';
            icon.textContent = statusIcon(effStatus);
            const main = document.createElement('div');
            main.className = 'frame-item--main';
            const title = document.createElement('div');
            title.className = 'frame-item--title';
            title.textContent = d.filename || 'Untitled';
            title.style.fontSize = '0.875rem';
            const meta = document.createElement('div');
            meta.className = 'frame-item--meta';
            const typeLabel = d.document_type ? d.document_type.replace(/_/g, ' ') : '—';
            meta.textContent = fmtDate(d.uploaded_at) + ' · ' + typeLabel;
            main.appendChild(title);
            main.appendChild(meta);
            const badge = document.createElement('span');
            const b = statusBadge(effStatus);
            badge.style.display = 'inline-block';
            badge.style.padding = '0.125rem 0.375rem';
            badge.style.fontSize = '0.625rem';
            badge.style.fontWeight = '600';
            badge.style.color = b.color;
            badge.style.background = b.bg;
            badge.style.borderRadius = '0.25rem';
            badge.style.textTransform = 'uppercase';
            badge.style.letterSpacing = '0.04em';
            badge.style.marginTop = '0.25rem';
            badge.textContent = b.label;
            main.appendChild(badge);
            row.appendChild(icon);
            row.appendChild(main);
            row.addEventListener('click', () => selectDoc(d));
            docList.appendChild(row);
        });
    }

    async function selectDoc(d) {
        currentDoc = d;
        renderDocs();
        docName.textContent = d.filename || 'Untitled';
        typeSelect.style.display = '';
        typeSelect.value = d.document_type || '';
        statusSelect.style.display = '';
        statusSelect.value = d.verification_status || 'new';
        downloadBtn.style.display = '';
        await loadReviewState(d);
        await startIntake(d);
        document.getElementById('dcAnnotTools').style.display = 'flex';
        document.getElementById('dcProcessBtn').style.display = '';
        document.getElementById('dcExplainBtn').style.display = '';
        document.getElementById('dcShareBtn').style.display = '';
        resetMeaningPane();
        const fname = (d.filename || '').toLowerCase();
        const isPdf = fname.endsWith('.pdf');
        const isImage = /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/.test(fname);
        try {
            if (isPdf && window.pdfjsLib) {
                await renderPdf(d);
            } else if (isImage) {
                renderImage(d);
            } else {
                showIframeViewer(d);
            }
        } catch (viewErr) {
            // A missing/unreadable file must not kill the rest of the
            // selection flow — checklist, rail, and tools still update.
            console.warn('Document view failed:', viewErr);
            const viewer = document.getElementById('dcViewer');
            const emptyEl = document.getElementById('dcViewerEmpty');
            if (viewer && emptyEl) {
                emptyEl.style.display = '';
                emptyEl.innerHTML = '<div class="frame-empty--icon">◆</div><p>Could not load this file.</p><p style="font-size:0.8rem;opacity:0.7;">The record exists — the file itself could not be fetched.</p>';
            }
        }
        loadOverlays(d.id);
        renderChecklist(d);
        setMobilePane('center');
    }

    function renderImage(doc) {
        const container = document.getElementById('dcPdfContainer');
        const empty = document.getElementById('dcViewerEmpty');
        const iframe = document.getElementById('dcIframeFallback');
        empty.style.display = 'none';
        iframe.style.display = 'none';
        container.style.display = 'flex';
        container.style.position = 'relative';
        container.innerHTML = '';
        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        wrapper.style.maxWidth = '100%';
        wrapper.style.background = 'var(--zone-surface-inverse)';
        const img = document.createElement('img');
        img.src = '/api/dc/document/' + encodeURIComponent(doc.id) + '/view';
        img.style.display = 'block';
        img.style.maxWidth = '100%';
        img.style.height = 'auto';
        img.style.background = 'var(--bg-card)';
        img.draggable = false;
        img.addEventListener('load', () => {
            applyImageHighlights(doc, wrapper, img);
        });
        wrapper.appendChild(img);
        const overlay = document.createElement('div');
        overlay.className = 'dc-image-overlay';
        overlay.style.position = 'absolute';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.pointerEvents = 'none';
        wrapper.appendChild(overlay);
        container.appendChild(wrapper);
    }

    function applyImageHighlights(doc, wrapper, img) {
        if (!currentDoc || !doc || doc.id !== currentDoc.id) return;
        const overlay = wrapper.querySelector('.dc-image-overlay');
        if (!overlay) return;
        fetch('/api/dc/document/' + encodeURIComponent(doc.id) + '/overlays', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data || !data.overlays) return;
                const terms = [];
                (data.overlays || []).forEach(ov => {
                    (ov.items || []).forEach(item => {
                        const s = String(item).trim();
                        if (s.length >= 3) terms.push({ term: s, overlay: ov.name, icon: ov.icon });
                    });
                });
                if (!terms.length) return;
                if (window.SemptifyFeedback) {
                    SemptifyFeedback.info('Image loaded. ' + terms.length + ' extracted item(s) found in overlays. Use Process now to run OCR on this image.', { timeout: 6000 });
                }
            })
            .catch(() => {});
        loadUserAnnotations(doc);
    }

    let currentWordBoxes = [];
    let wordBoxVisible = false;

    function showIframeViewer(d) {
        document.getElementById('dcViewerEmpty').style.display = 'none';
        document.getElementById('dcPdfContainer').style.display = 'none';

        var mime = (d.mime_type || '').toLowerCase();
        var isImage = mime.startsWith('image/');

        if (isImage) {
            showImageViewer(d);
        } else {
            document.getElementById('dcImageContainer').style.display = 'none';
            document.getElementById('dcWordBoxToggle').style.display = 'none';
            var iframe = document.getElementById('dcIframeFallback');
            iframe.style.display = '';
            iframe.src = '/api/dc/document/' + encodeURIComponent(d.id) + '/view';
        }
    }

    function showImageViewer(d) {
        var iframe = document.getElementById('dcIframeFallback');
        var container = document.getElementById('dcImageContainer');
        var img = document.getElementById('dcImageEl');
        var canvas = document.getElementById('dcWordBoxCanvas');
        var toggle = document.getElementById('dcWordBoxToggle');

        iframe.style.display = 'none';
        container.style.display = 'flex';
        toggle.style.display = 'none';
        currentWordBoxes = [];
        wordBoxVisible = false;

        img.onload = function() {
            canvas.width = img.naturalWidth;
            canvas.height = img.naturalHeight;
            canvas.style.width = img.clientWidth + 'px';
            canvas.style.height = img.clientHeight + 'px';
            loadWordBoxes(d);
        };
        img.src = '/api/dc/document/' + encodeURIComponent(d.id) + '/view';
    }

    async function loadWordBoxes(d) {
        var toggle = document.getElementById('dcWordBoxToggle');
        try {
            var resp = await fetch('/api/dc/document/' + encodeURIComponent(d.id) + '/word-boxes');
            if (!resp.ok) { toggle.style.display = 'none'; return; }
            var data = await resp.json();
            if (!data.word_boxes || data.word_boxes.length === 0) {
                toggle.style.display = 'none';
                return;
            }
            currentWordBoxes = data.word_boxes;
            toggle.style.display = '';
            toggle.textContent = '◆ Word highlights (' + data.word_boxes.length + ')';
            // Auto-show on first load
            wordBoxVisible = true;
            toggle.style.opacity = '1';
            drawWordBoxes();
        } catch (e) {
            toggle.style.display = 'none';
        }
    }

    function drawWordBoxes() {
        var canvas = document.getElementById('dcWordBoxCanvas');
        var img = document.getElementById('dcImageEl');
        if (!canvas || !img || !img.naturalWidth) return;
        var ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (!wordBoxVisible || currentWordBoxes.length === 0) return;

        var scaleX = canvas.width / img.naturalWidth;
        var scaleY = canvas.height / img.naturalHeight;
        // Canvas is set to natural dimensions; scale boxes 1:1
        ctx.fillStyle = 'rgba(255, 204, 0, 0.25)';
        ctx.strokeStyle = 'rgba(255, 180, 0, 0.6)';
        ctx.lineWidth = 1;
        for (var i = 0; i < currentWordBoxes.length; i++) {
            var wb = currentWordBoxes[i];
            var b = wb.bbox;
            if (!b) continue;
            ctx.fillRect(b.left, b.top, b.width, b.height);
            ctx.strokeRect(b.left, b.top, b.width, b.height);
        }
    }

    document.getElementById('dcWordBoxToggle').addEventListener('click', function() {
        wordBoxVisible = !wordBoxVisible;
        this.style.opacity = wordBoxVisible ? '1' : '0.5';
        drawWordBoxes();
    });

    // Redraw word boxes on resize so canvas CSS dimensions match the image
    window.addEventListener('resize', function() {
        var canvas = document.getElementById('dcWordBoxCanvas');
        var img = document.getElementById('dcImageEl');
        if (canvas && img && img.clientWidth > 0) {
            canvas.style.width = img.clientWidth + 'px';
            canvas.style.height = img.clientHeight + 'px';
        }
    });

    let currentPdfDoc = null;
    let currentExtractedText = [];

    async function renderPdf(doc) {
        const container = document.getElementById('dcPdfContainer');
        const empty = document.getElementById('dcViewerEmpty');
        const iframe = document.getElementById('dcIframeFallback');
        const imgContainer = document.getElementById('dcImageContainer');
        const toggle = document.getElementById('dcWordBoxToggle');
        empty.style.display = 'none';
        iframe.style.display = 'none';
        imgContainer.style.display = 'none';
        toggle.style.display = 'none';
        container.style.display = 'flex';
        container.innerHTML = '<div style="color:var(--text-muted); padding:2rem;">Loading PDF…</div>';
        try {
            const url = '/api/dc/document/' + encodeURIComponent(doc.id) + '/view';
            const loadingTask = pdfjsLib.getDocument(url);
            currentPdfDoc = await loadingTask.promise;
            container.innerHTML = '';
            currentExtractedText = [];
            for (let pageNum = 1; pageNum <= currentPdfDoc.numPages; pageNum++) {
                const page = await currentPdfDoc.getPage(pageNum);
                const viewport = page.getViewport({ scale: 1.5 });
                const pageWrapper = document.createElement('div');
                pageWrapper.style.position = 'relative';
                pageWrapper.style.marginBottom = '1rem';
                pageWrapper.style.background = 'var(--zone-surface-inverse)';
                const canvas = document.createElement('canvas');
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                canvas.style.display = 'block';
                canvas.style.background = 'var(--bg-card)';
                pageWrapper.appendChild(canvas);
                const textLayerDiv = document.createElement('div');
                textLayerDiv.className = 'dc-text-layer';
                textLayerDiv.style.position = 'absolute';
                textLayerDiv.style.top = '0';
                textLayerDiv.style.left = '0';
                textLayerDiv.style.width = viewport.width + 'px';
                textLayerDiv.style.height = viewport.height + 'px';
                textLayerDiv.style.overflow = 'hidden';
                textLayerDiv.style.pointerEvents = 'auto';
                pageWrapper.appendChild(textLayerDiv);
                container.appendChild(pageWrapper);
                const renderContext = { canvasContext: canvas.getContext('2d'), viewport: viewport };
                await page.render(renderContext).promise;
                const textContent = await page.getTextContent();
                textContent.items.forEach(item => {
                    const tx = pdfjsLib.Util.transform(viewport.transform, item.transform);
                    const span = document.createElement('span');
                    span.textContent = item.str;
                    span.style.position = 'absolute';
                    span.style.left = tx[4] + 'px';
                    span.style.top = (tx[5] - item.height * viewport.scale) + 'px';
                    span.style.fontSize = (item.height * viewport.scale) + 'px';
                    span.style.fontFamily = 'sans-serif';
                    span.style.color = 'transparent';
                    span.style.whiteSpace = 'pre';
                    span.dataset.text = item.str;
                    span.dataset.page = pageNum;
                    textLayerDiv.appendChild(span);
                    if (item.str.trim()) currentExtractedText.push({ text: item.str, page: pageNum, span: span });
                });
            }
            applyHighlights(doc);
            loadUserAnnotations(doc);
        } catch (err) {
            container.innerHTML = '<div style="color:var(--color-error-800); padding:2rem;">Could not render PDF: ' + escapeHtml(err.message) + '</div>';
        }
    }

    function applyHighlights(doc) {
        if (!currentDoc || !doc || doc.id !== currentDoc.id) return;
        fetch('/api/dc/document/' + encodeURIComponent(doc.id) + '/overlays', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data || !data.overlays) return;
                const searchTerms = [];
                (data.overlays || []).forEach(ov => {
                    (ov.items || []).forEach(item => {
                        const s = String(item).trim();
                        if (s.length >= 3) searchTerms.push({ term: s, overlay: ov.name, icon: ov.icon });
                    });
                });
                searchTerms.forEach(term => {
                    const normalized = term.term.toLowerCase();
                    currentExtractedText.forEach(entry => {
                        if (entry.text.toLowerCase().includes(normalized)) {
                            const span = entry.span;
                            if (span.dataset.highlighted) return;
                            span.dataset.highlighted = '1';
                            span.style.background = 'color-mix(in srgb, var(--color-warning), transparent 65%)';
                            span.style.borderRadius = '2px';
                            span.style.cursor = 'pointer';
                            span.style.color = 'transparent';
                            span.addEventListener('click', function (e) {
                                e.stopPropagation();
                                showHighlightPopover(span, term);
                            });
                        }
                    });
                });
            })
            .catch(() => {});
    }

    // Load saved user annotations (highlights, notes, references) from overlays
    async function loadUserAnnotations(doc) {
        if (!doc) return;
        try {
            const r = await fetch('/api/unified-overlays/list?document_id=' + encodeURIComponent(doc.id), { credentials: 'include' });
            if (!r.ok) return;
            const data = await r.json();
            const overlays = data.overlays || [];
            const container = document.getElementById('dcPdfContainer');
            if (!container) return;
            const isPdf = /\.pdf$/i.test(doc.filename || '');
            const isImage = /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test((doc.filename || '').toLowerCase());

            overlays.forEach(ov => {
                const type = ov.overlay_type || ov.type || '';
                const payload = ov.payload || {};

                if (type === 'highlight' && payload.range) {
                    if (isPdf && payload.range.text) {
                        const normalized = String(payload.range.text).toLowerCase();
                        currentExtractedText.forEach(entry => {
                            if (entry.text.toLowerCase().includes(normalized) && !entry.span.dataset.userHighlight) {
                                const span = entry.span;
                                span.dataset.userHighlight = '1';
                                span.style.background = 'color-mix(in srgb, var(--color-info), transparent 60%)';
                                span.style.borderRadius = '2px';
                            }
                        });
                    } else if (isImage && payload.range.image) {
                        const wrapper = container.querySelector('div[style*="position: relative"]');
                        if (!wrapper) return;
                        const overlay = wrapper.querySelector('.dc-image-overlay');
                        if (!overlay) return;
                        const x = payload.range.x || 0;
                        const y = payload.range.y || 0;
                        const w = payload.range.width || 4;
                        const h = payload.range.height || 4;
                        const box = document.createElement('div');
                        box.style.position = 'absolute';
                        box.style.left = (x - w / 2) + '%';
                        box.style.top = (y - h / 2) + '%';
                        box.style.width = w + '%';
                        box.style.height = h + '%';
                        box.style.background = 'color-mix(in srgb, var(--color-info), transparent 80%)';
                        box.style.border = '1px solid var(--color-info)';
                        box.style.borderRadius = '2px';
                        box.style.pointerEvents = 'auto';
                        box.style.cursor = 'pointer';
                        overlay.appendChild(box);
                    }
                } else if (type === 'note' && payload.content) {
                    const range = payload.range || {};
                    const pin = document.createElement('div');
                    pin.style.position = 'absolute';
                    pin.style.width = '20px';
                    pin.style.height = '20px';
                    pin.style.background = 'var(--color-info)';
                    pin.style.borderRadius = '50%';
                    pin.style.cursor = 'pointer';
                    pin.style.zIndex = '50';
                    pin.style.display = 'flex';
                    pin.style.alignItems = 'center';
                    pin.style.justifyContent = 'center';
                    pin.style.color = 'var(--text-inverse)';
                    pin.style.fontSize = '0.6875rem';
                    pin.textContent = '●';
                    pin.title = payload.content;
                    pin.addEventListener('click', function (ev) {
                        ev.stopPropagation();
                        if (window.SemptifyFeedback) SemptifyFeedback.info(payload.content, { timeout: 10000 });
                    });
                    if (range.x !== undefined && range.y !== undefined) {
                        pin.style.left = range.x + 'px';
                        pin.style.top = range.y + 'px';
                        container.style.position = 'relative';
                        container.appendChild(pin);
                    }
                } else if (type === 'communication' && ov.metadata && ov.metadata.annotation_kind === 'reference' && payload.reference_target) {
                    const pin = document.createElement('div');
                    pin.style.position = 'absolute';
                    pin.style.width = '20px';
                    pin.style.height = '20px';
                    pin.style.background = 'var(--color-info)';
                    pin.style.borderRadius = '50%';
                    pin.style.cursor = 'pointer';
                    pin.style.zIndex = '50';
                    pin.style.display = 'flex';
                    pin.style.alignItems = 'center';
                    pin.style.justifyContent = 'center';
                    pin.style.color = 'var(--text-inverse)';
                    pin.style.fontSize = '0.6875rem';
                    pin.textContent = '●';
                    pin.title = 'References: ' + payload.reference_target;
                    pin.addEventListener('click', function (ev) {
                        ev.stopPropagation();
                        if (window.SemptifyFeedback) SemptifyFeedback.info('References: ' + payload.reference_target, { timeout: 10000 });
                    });
                    if (payload.x !== undefined && payload.y !== undefined) {
                        pin.style.left = payload.x + 'px';
                        pin.style.top = payload.y + 'px';
                        container.style.position = 'relative';
                        container.appendChild(pin);
                    }
                }
            });
        } catch (e) {
            // Silently fail — annotations are non-critical
        }
    }

    let activePopover = null;
    function showHighlightPopover(span, term) {
        if (activePopover) activePopover.remove();
        const popover = document.createElement('div');
        popover.style.position = 'fixed';
        popover.style.zIndex = '200';
        popover.style.background = 'var(--zone-surface-3)';
        popover.style.padding = '0.75rem';
        popover.style.maxWidth = '300px';
        const rect = span.getBoundingClientRect();
        popover.style.left = rect.left + 'px';
        popover.style.top = (rect.bottom + 8) + 'px';
        const title = document.createElement('div');
        title.style.color = 'var(--color-warning-800)';
        title.style.fontSize = '0.75rem';
        title.style.marginBottom = '0.25rem';
        title.textContent = (term.icon || '◆') + ' ' + term.overlay + ' — extracted';
        popover.appendChild(title);
        const value = document.createElement('div');
        value.style.color = 'var(--text-primary)';
        value.style.fontSize = '0.875rem';
        value.style.marginBottom = '0.5rem';
        value.style.wordBreak = 'break-word';
        value.textContent = term.term;
        popover.appendChild(value);
        const actions = document.createElement('div');
        actions.style.display = 'flex';
        actions.style.gap = '0.25rem';
        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'frame-btn';
        confirmBtn.style.flex = '1';
        confirmBtn.style.padding = '0.25rem 0.5rem';
        confirmBtn.style.fontSize = '0.75rem';
        confirmBtn.textContent = '● Confirm';
        confirmBtn.addEventListener('click', () => {
            span.style.background = 'color-mix(in srgb, var(--color-success), transparent 65%)';
            span.dataset.confirmed = '1';
            if (window.SemptifyFeedback) SemptifyFeedback.success('Extraction confirmed: ' + term.term);
            popover.remove();
            activePopover = null;
        });
        const correctBtn = document.createElement('button');
        correctBtn.className = 'frame-btn';
        correctBtn.style.flex = '1';
        correctBtn.style.padding = '0.25rem 0.5rem';
        correctBtn.style.fontSize = '0.75rem';
        correctBtn.textContent = '◆ Correct';
        correctBtn.addEventListener('click', async () => {
            const corrected = await showValueModal('Correct value:', term.term);
            if (corrected !== null && corrected !== term.term) {
                span.style.background = 'color-mix(in srgb, var(--color-info), transparent 65%)';
                span.dataset.corrected = '1';
                if (window.SemptifyFeedback) SemptifyFeedback.success('Corrected to: ' + corrected);
            }
            popover.remove();
            activePopover = null;
        });
        actions.appendChild(confirmBtn);
        actions.appendChild(correctBtn);
        popover.appendChild(actions);
        const closeBtn = document.createElement('button');
        closeBtn.className = 'frame-btn';
        closeBtn.style.width = '100%';
        closeBtn.style.marginTop = '0.25rem';
        closeBtn.style.padding = '0.25rem';
        closeBtn.style.fontSize = '0.75rem';
        closeBtn.textContent = 'Close';
        closeBtn.addEventListener('click', () => { popover.remove(); activePopover = null; });
        popover.appendChild(closeBtn);
        document.body.appendChild(popover);
        activePopover = popover;
        setTimeout(() => {
            if (activePopover === popover) { popover.remove(); activePopover = null; }
        }, 10000);
    }

    document.addEventListener('click', () => {
        if (activePopover) { activePopover.remove(); activePopover = null; }
    });

    // =========================================================================
    // Slice 6 — User Annotation Tools (Highlight, Note, Reference)
    // =========================================================================
    let activeAnnotTool = 'none';

    document.querySelectorAll('.dc-annot-tool').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            activeAnnotTool = btn.dataset.tool;
            document.querySelectorAll('.dc-annot-tool').forEach(b => b.style.background = '');
            if (activeAnnotTool !== 'none') btn.style.background = 'var(--color-calm-100)';
            const container = document.getElementById('dcPdfContainer');
            container.style.cursor = activeAnnotTool === 'none' ? '' : 'crosshair';
            if (activeAnnotTool !== 'none' && window.SemptifyFeedback) {
                const hints = {
                    highlight: 'Click a word in the PDF to highlight it.',
                    note: 'Click anywhere on the PDF to place a note.',
                    reference: 'Click anywhere on the PDF to link a reference.'
                };
                SemptifyFeedback.info(hints[activeAnnotTool] || '', { timeout: 4000 });
            }
        });
    });

    document.getElementById('dcPdfContainer').addEventListener('click', function (e) {
        if (activeAnnotTool === 'none' || !currentDoc) return;
        if (e.target.tagName === 'BUTTON') return;
        e.stopPropagation();
        if (activeAnnotTool === 'highlight') handleHighlightClick(e);
        else if (activeAnnotTool === 'note') handleNoteClick(e);
        else if (activeAnnotTool === 'reference') handleReferenceClick(e);
    });

    // Image-based annotation handlers (for non-PDF images)
    function handleImageHighlight(e) {
        const img = e.target.closest('img');
        if (!img) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Click on the image to highlight a region.');
            return;
        }
        const wrapper = img.parentElement;
        const overlay = wrapper.querySelector('.dc-image-overlay');
        const rect = img.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        const box = document.createElement('div');
        box.style.position = 'absolute';
        box.style.left = (x - 2) + '%';
        box.style.top = (y - 2) + '%';
        box.style.width = '4%';
        box.style.height = '4%';
        box.style.background = 'color-mix(in srgb, var(--color-info), transparent 80%)';
        box.style.border = '1px solid var(--color-info)';
        box.style.borderRadius = '2px';
        box.style.pointerEvents = 'auto';
        box.style.cursor = 'pointer';
        box.title = 'User highlight';
        overlay.appendChild(box);
        const rangeData = { page: 1, text: '', x: Math.round(x), y: Math.round(y), width: 4, height: 4, image: true };
        fetch('/api/unified-overlays/annotations/highlight?document_id=' + encodeURIComponent(currentDoc.id) + '&vault_path=' + encodeURIComponent(currentDoc.vault_path || currentDoc.id) + '&color=blue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(rangeData),
            credentials: 'include'
        }).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
          .then(() => { if (window.SemptifyFeedback) SemptifyFeedback.success('Highlight saved.'); })
          .catch(err => { if (window.SemptifyFeedback) SemptifyFeedback.error('Could not save highlight: ' + err.message); box.remove(); });
    }

    // Route image clicks to image handlers when in tool mode
    document.getElementById('dcPdfContainer').addEventListener('click', function (e) {
        if (activeAnnotTool === 'none' || !currentDoc) return;
        if (e.target.tagName === 'BUTTON') return;
        const isImage = e.target.tagName === 'IMG';
        if (isImage) {
            e.stopPropagation();
            if (activeAnnotTool === 'highlight') handleImageHighlight(e);
            else if (activeAnnotTool === 'note') handleNoteClick(e);
            else if (activeAnnotTool === 'reference') handleReferenceClick(e);
        }
    }, true);

    async function handleHighlightClick(e) {
        const span = e.target.closest('span[data-text]');
        if (!span) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Click directly on a word in the PDF text.');
            return;
        }
        const text = span.dataset.text || '';
        if (!text.trim()) return;
        span.style.background = 'color-mix(in srgb, var(--color-info), transparent 60%)';
        span.style.borderRadius = '2px';
        span.dataset.userHighlight = '1';
        const page = span.dataset.page || 1;
        const rect = span.getBoundingClientRect();
        const rangeData = {
            page: parseInt(page, 10),
            text: text,
            x: Math.round(rect.left),
            y: Math.round(rect.top),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
        };
        try {
            const r = await fetch('/api/unified-overlays/annotations/highlight?document_id=' + encodeURIComponent(currentDoc.id) + '&vault_path=' + encodeURIComponent(currentDoc.vault_path || currentDoc.id) + '&color=blue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(rangeData),
                credentials: 'include'
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const data = await r.json();
            if (window.SemptifyFeedback) SemptifyFeedback.success('Highlight saved.');
        } catch (err) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Could not save highlight: ' + err.message);
        }
    }

    async function handleNoteClick(e) {
        const text = await showValueModal('Note:', '');
        if (text === null || !text.trim()) return;
        const container = document.getElementById('dcPdfContainer');
        const containerRect = container.getBoundingClientRect();
        const x = e.clientX - containerRect.left + container.scrollLeft;
        const y = e.clientY - containerRect.top + container.scrollTop;
        const pin = document.createElement('div');
        pin.style.position = 'absolute';
        pin.style.left = x + 'px';
        pin.style.top = y + 'px';
        pin.style.width = '20px';
        pin.style.height = '20px';
        pin.style.background = 'var(--color-info)';
        pin.style.borderRadius = '50%';
        pin.style.cursor = 'pointer';
        pin.style.zIndex = '50';
        pin.style.display = 'flex';
        pin.style.alignItems = 'center';
        pin.style.justifyContent = 'center';
        pin.style.color = 'var(--text-inverse)';
        pin.style.fontSize = '0.6875rem';
        pin.style.fontWeight = 'bold';
        pin.textContent = '●';
        pin.title = text;
        pin.addEventListener('click', function (ev) {
            ev.stopPropagation();
            if (window.SemptifyFeedback) SemptifyFeedback.info(text, { timeout: 10000 });
        });
        container.style.position = 'relative';
        container.appendChild(pin);
        try {
            const r = await fetch('/api/unified-overlays/annotations/note?document_id=' + encodeURIComponent(currentDoc.id) + '&vault_path=' + encodeURIComponent(currentDoc.vault_path || currentDoc.id) + '&content=' + encodeURIComponent(text) + '&note_type=user&priority=normal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
                credentials: 'include'
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            if (window.SemptifyFeedback) SemptifyFeedback.success('Note saved.');
        } catch (err) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Could not save note: ' + err.message);
            pin.remove();
        }
    }

    async function handleReferenceClick(e) {
        const target = await showValueModal('Reference target (document name or ID):', '');
        if (target === null || !target.trim()) return;
        const container = document.getElementById('dcPdfContainer');
        const containerRect = container.getBoundingClientRect();
        const x = e.clientX - containerRect.left + container.scrollLeft;
        const y = e.clientY - containerRect.top + container.scrollTop;
        const pin = document.createElement('div');
        pin.style.position = 'absolute';
        pin.style.left = x + 'px';
        pin.style.top = y + 'px';
        pin.style.width = '20px';
        pin.style.height = '20px';
        pin.style.background = 'var(--color-info)';
        pin.style.borderRadius = '50%';
        pin.style.cursor = 'pointer';
        pin.style.zIndex = '50';
        pin.style.display = 'flex';
        pin.style.alignItems = 'center';
        pin.style.justifyContent = 'center';
        pin.style.color = 'var(--text-inverse)';
        pin.style.fontSize = '0.6875rem';
        pin.textContent = '●';
        pin.title = 'References: ' + target;
        pin.addEventListener('click', function (ev) {
            ev.stopPropagation();
            if (window.SemptifyFeedback) SemptifyFeedback.info('References: ' + target, { timeout: 10000 });
        });
        container.style.position = 'relative';
        container.appendChild(pin);
        try {
            const r = await fetch('/api/unified-overlays/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    overlay_type: 'communication',
                    document_id: currentDoc.id,
                    vault_path: currentDoc.vault_path || currentDoc.id,
                    payload: { reference_target: target, x: x, y: y },
                    metadata: { annotation_kind: 'reference', created_by_tool: 'dc_gui' },
                    ephemeral: false
                }),
                credentials: 'include'
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            if (window.SemptifyFeedback) SemptifyFeedback.success('Reference saved.');
        } catch (err) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Could not save reference: ' + err.message);
            pin.remove();
        }
    }

    async function loadOverlays(vaultId) {
        overlayList.innerHTML = '';
        overlayList.appendChild(overlayEmpty);
        try {
            const r = await fetch('/api/dc/document/' + encodeURIComponent(vaultId) + '/overlays', { credentials: 'include' });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const data = await r.json();
            renderOverlays(data);
        } catch (e) {
            overlayEmpty.querySelector('p').textContent = 'Could not load overlays.';
        }
    }

    function renderOverlays(data) {
        overlayList.innerHTML = '';
        overallSpan.textContent = '';
        if (!data.has_data || !data.overlays || !data.overlays.length) {
            const empty = document.createElement('div');
            empty.className = 'frame-empty';
            const statusIcon = (data.status === 'failed' || data.status === 'needs_reprocess') ? '▸' : (data.status === 'processing' ? '◆' : '○');
            const hint = data.detail ? escapeHtml(data.detail) : 'Process the document to see progress.';
            empty.innerHTML = '<div class="frame-empty--icon">' + statusIcon + '</div><p>' + escapeHtml(data.message || 'No overlays yet.') + '</p><p class="frame-empty--hint">' + hint + '</p>';
            overlayList.appendChild(empty);
            return;
        }
        data.overlays.forEach(ov => {
            const row = document.createElement('div');
            row.className = 'frame-item';
            row.style.flexDirection = 'column';
            row.style.alignItems = 'stretch';
            row.style.padding = '0.5rem';
            row.style.marginBottom = '0.5rem';
            row.style.background = 'var(--zone-surface-2)';
            row.style.borderRadius = '0.375rem';
            const header = document.createElement('div');
            header.style.display = 'flex';
            header.style.alignItems = 'center';
            header.style.gap = '0.5rem';
            header.style.marginBottom = '0.25rem';
            const icon = document.createElement('span');
            icon.textContent = ov.icon || '○';
            const name = document.createElement('strong');
            name.style.color = 'var(--text-primary)';
            name.style.fontSize = '0.8125rem';
            name.style.flex = '1';
            name.textContent = ov.name;
            const pct = document.createElement('span');
            pct.style.color = 'var(--text-muted)';
            pct.style.fontSize = '0.75rem';
            pct.textContent = ov.pct + '%';
            header.appendChild(icon);
            header.appendChild(name);
            header.appendChild(pct);
            const bar = document.createElement('div');
            bar.style.background = 'var(--color-gray-200)';
            bar.style.height = '4px';
            bar.style.borderRadius = '2px';
            bar.style.overflow = 'hidden';
            bar.style.marginBottom = '0.25rem';
            const fill = document.createElement('div');
            fill.style.background = ov.pct >= 100 ? 'var(--color-success)' : (ov.pct > 0 ? 'var(--color-warning)' : 'var(--color-gray-200)');
            fill.style.height = '100%';
            fill.style.width = ov.pct + '%';
            fill.style.transition = 'width 0.3s';
            bar.appendChild(fill);
            const goal = document.createElement('div');
            goal.style.color = 'var(--text-muted)';
            goal.style.fontSize = '0.75rem';
            goal.textContent = ov.goal || '';
            row.appendChild(header);
            row.appendChild(bar);
            if (ov.goal) row.appendChild(goal);
            if (ov.items && ov.items.length) {
                const detail = document.createElement('div');
                detail.style.color = 'var(--text-muted)';
                detail.style.fontSize = '0.75rem';
                detail.style.marginTop = '0.25rem';
                detail.style.whiteSpace = 'pre-wrap';
                detail.textContent = ov.items.slice(0, 5).join('\n');
                row.appendChild(detail);
            }
            overlayList.appendChild(row);
        });
        if (data.overall_pct !== undefined) {
            overallSpan.textContent = 'Overall: ' + data.overall_pct + '%';
        }
    }

    async function loadUnlocks() {
        try {
            const r = await fetch('/api/dc/unlocks', { credentials: 'include' });
            if (!r.ok) return;
            const data = await r.json();
            const unlocks = data.unlocks || [];
            unlocksDiv.innerHTML = '';
            unlocks.forEach(u => {
                const line = document.createElement('div');
                line.style.marginBottom = '0.25rem';
                line.textContent = (u.unlocked ? '◆' : '○') + ' ' + u.name + ' — ' + (u.unlocked ? 'unlocked' : u.progress);
                unlocksDiv.appendChild(line);
            });
            if (previousUnlocks !== null) {
                unlocks.forEach(u => {
                    const prev = previousUnlocks.find(p => p.name === u.name);
                    const wasUnlocked = prev ? prev.unlocked : false;
                    if (u.unlocked && !wasUnlocked) {
                        if (window.SemptifyFeedback) {
                            SemptifyFeedback.success(u.name + ' is now available.', { timeout: 7000 });
                        }
                    }
                });
            }
            previousUnlocks = unlocks.map(u => ({ name: u.name, unlocked: u.unlocked }));
        } catch (e) { /* silent */ }
    }

    // ── "What does this mean?" — plain-English document explanation ──────
    // Flagship Phase B: GET /api/dc/document/{vault_id}/explain returns the
    // cached (or freshly computed) DocumentIntelligence result. Rendered in
    // the "Meaning" right-pane tab — no popups, nothing hidden.
    function resetMeaningPane() {
        const pane = document.getElementById('dcMeaning');
        pane.innerHTML = '<div class="frame-empty"><div class="frame-empty--icon">◆</div>' +
            '<p>Select a document, then press "What does this mean?" for a plain-English explanation.</p></div>';
    }

    async function loadMeaning() {
        if (!currentDoc) return;
        const pane = document.getElementById('dcMeaning');
        pane.innerHTML = '<div class="frame-empty"><p style="color:var(--text-muted);">Reading your document…</p></div>';
        // Switch to the Meaning tab so the tenant sees the answer where they asked.
        document.querySelector('.dc-tab[data-tab="meaning"]').click();
        try {
            const r = await fetch('/api/dc/document/' + encodeURIComponent(currentDoc.id) + '/explain', { credentials: 'include' });
            const data = await r.json().catch(() => ({}));
            if (!r.ok) {
                pane.innerHTML = '<div class="frame-empty"><p style="color:var(--text-muted);">' +
                    escapeHtml(data.message || data.detail || 'No explanation is available for this document yet.') + '</p></div>';
                return;
            }
            let html = '';
            if (data.title) html += '<div style="color:var(--text-primary); font-weight:600; font-size:0.875rem; margin-bottom:0.375rem;">' + escapeHtml(data.title) + '</div>';
            if (data.urgency && (data.urgency.level === 'critical' || data.urgency.level === 'high')) {
                html += '<div style="background:var(--color-error-800); color:var(--color-error-50); font-size:0.75rem; padding:0.375rem 0.5rem; margin-bottom:0.5rem;">' +
                    '<strong>Time-sensitive:</strong> ' + escapeHtml(data.urgency.reason || 'This document may carry a deadline.') + '</div>';
            }
            if (data.plain_english) html += '<p style="color:var(--text-primary); font-size:0.8125rem; line-height:1.55; margin-bottom:0.75rem;">' + escapeHtml(data.plain_english) + '</p>';
            if (data.summary && data.summary !== data.plain_english) html += '<p style="color:var(--text-muted); font-size:0.75rem; line-height:1.5; margin-bottom:0.75rem;">' + escapeHtml(data.summary) + '</p>';
            const items = data.action_items || [];
            if (items.length) {
                html += '<div style="color:var(--text-muted); font-size:0.75rem; font-weight:600; margin-bottom:0.25rem;">What to do next</div>';
                items.forEach(function (it) {
                    const t = typeof it === 'string' ? it : (it.title || it.description || '');
                    if (t) html += '<div style="color:var(--text-primary); font-size:0.75rem; padding:0.375rem 0; border-bottom:1px solid var(--border-color);">' + escapeHtml(t) + '</div>';
                });
            }
            if (!html) html = '<div class="frame-empty"><p style="color:var(--text-muted);">This document was processed but produced no explanation.</p></div>';
            // IO expansion (ADR-0008): at high intensity or on a first visit,
            // prepend the contextual explanation if one was retrieved; otherwise
            // fall back to a short orientation line.
            if (html && (data.intensity_level >= 3 || data.exposure_count <= 1)) {
                if (data.explanation) {
                    html = '<p style="color:var(--text-muted); font-size:0.75rem; font-style:italic; margin-bottom:0.5rem;">' +
                        escapeHtml(data.explanation) + '</p>' + html;
                } else {
                    html = '<p style="color:var(--text-muted); font-size:0.75rem; font-style:italic; margin-bottom:0.5rem;">' +
                        'This is a plain-English read of what your document says and what it likely means for you — a starting point, not legal advice.</p>' + html;
                }
            }
            pane.innerHTML = html;
        } catch (e) {
            pane.innerHTML = '<div class="frame-empty"><p style="color:var(--text-muted);">Could not load the explanation. Your document is safe — try again.</p></div>';
        }
    }

    document.getElementById('dcExplainBtn').addEventListener('click', loadMeaning);

    // Tab switching
    document.querySelectorAll('.dc-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.dc-tab').forEach(b => b.style.background = '');
            btn.style.background = 'var(--color-calm-100)';
            currentTab = btn.dataset.tab;
            document.getElementById('dcOverlayList').style.display = currentTab === 'overlays' ? '' : 'none';
            document.getElementById('dcChecklist').style.display = currentTab === 'checklist' ? '' : 'none';
            document.getElementById('dcMeaning').style.display = currentTab === 'meaning' ? '' : 'none';
        });
    });

    function renderChecklist(doc) {
        const checklist = document.getElementById('dcChecklist');
        checklist.innerHTML = '';
        if (!doc.document_type || !documentTypes[doc.document_type]) {
            const empty = document.createElement('div');
            empty.className = 'frame-empty';
            empty.innerHTML = '<div class="frame-empty--icon">◆</div><p>Declare a document type to see its verification checklist.</p>';
            checklist.appendChild(empty);
            updateGuidanceRail();
            return;
        }
        const def = documentTypes[doc.document_type];
        const state = fieldConfirmState[doc.id] || {};
        const required = def.fields.filter(f => f.required);
        const optional = def.fields.filter(f => !f.required);
        const confirmedCount = required.filter(f => state[f.name] === 'confirmed' || state[f.name] === 'corrected').length;
        const overallPct = required.length ? Math.round(confirmedCount / required.length * 100) : 0;

        const header = document.createElement('div');
        header.style.marginBottom = '0.5rem';
        header.innerHTML = '<div style="color:var(--text-primary); font-size:0.875rem; font-weight:600; margin-bottom:0.25rem;">' + escapeHtml(def.label) + '</div>' +
            '<div style="color:var(--text-muted); font-size:0.75rem; margin-bottom:0.5rem;">' + escapeHtml(def.description) + '</div>' +
            '<div style="background:var(--zone-surface-inverse); height:6px; overflow:hidden;"><div style="background:' + (overallPct >= 100 ? 'var(--color-success)' : overallPct > 0 ? 'var(--color-warning)' : 'var(--color-gray-200)') + '; height:100%; width:' + overallPct + '%; transition:width 0.3s;"></div></div>' +
            '<div style="color:var(--text-muted); font-size:0.75rem; margin-top:0.25rem;">' + confirmedCount + '/' + required.length + ' required fields confirmed · ' + overallPct + '%</div>';
        checklist.appendChild(header);

        const reqSection = document.createElement('div');
        reqSection.style.marginBottom = '0.75rem';
        const reqTitle = document.createElement('div');
        reqTitle.style.color = 'var(--text-muted)';
        reqTitle.style.fontSize = '0.75rem';
        reqTitle.style.marginBottom = '0.25rem';
        reqTitle.style.textTransform = 'uppercase';
        reqTitle.style.letterSpacing = '0.05em';
        reqTitle.textContent = 'Required';
        reqSection.appendChild(reqTitle);
        required.forEach(f => reqSection.appendChild(renderFieldRow(doc, f, state)));
        checklist.appendChild(reqSection);

        if (optional.length) {
            const optSection = document.createElement('div');
            const optTitle = document.createElement('div');
            optTitle.style.color = 'var(--text-muted)';
            optTitle.style.fontSize = '0.75rem';
            optTitle.style.marginBottom = '0.25rem';
            optTitle.style.textTransform = 'uppercase';
            optTitle.style.letterSpacing = '0.05em';
            optTitle.textContent = 'Optional';
            optSection.appendChild(optTitle);
            optional.forEach(f => optSection.appendChild(renderFieldRow(doc, f, state)));
            checklist.appendChild(optSection);
        }

        if (overallPct >= 100) {
            const verified = document.createElement('div');
            verified.style.marginTop = '0.5rem';
            verified.style.padding = '0.5rem';
            verified.style.background = 'var(--color-success-50)';
            verified.style.borderRadius = '0.375rem';
            verified.style.color = 'var(--color-success-800)';
            verified.style.fontSize = '0.8125rem';
            verified.textContent = '● All required fields verified.';
            checklist.appendChild(verified);
        }
        updateGuidanceRail();
    }

    function renderFieldRow(doc, field, state) {
        const status = state[field.name] || 'pending';
        const row = document.createElement('div');
        row.style.padding = '0.5rem';
        row.style.marginBottom = '0.25rem';
        row.style.background = 'var(--zone-surface-2)';
        row.style.borderRadius = '0.375rem';
        const top = document.createElement('div');
        top.style.display = 'flex';
        top.style.alignItems = 'center';
        top.style.gap = '0.5rem';
        const icon = document.createElement('span');
        icon.textContent = status === 'confirmed' ? '●' : status === 'corrected' ? '◆' : '○';
        const label = document.createElement('span');
        label.style.color = 'var(--text-primary)';
        label.style.fontSize = '0.8125rem';
        label.style.flex = '1';
        label.textContent = field.label;
        const typeBadge = document.createElement('span');
        typeBadge.style.color = 'var(--text-muted)';
        typeBadge.style.fontSize = '0.6875rem';
        typeBadge.textContent = field.field_type;
        top.appendChild(icon);
        top.appendChild(label);
        top.appendChild(typeBadge);
        row.appendChild(top);
        const hint = document.createElement('div');
        hint.style.color = 'var(--text-muted)';
        hint.style.fontSize = '0.6875rem';
        hint.style.marginTop = '0.25rem';
        hint.textContent = 'Looks for: ' + field.ocr_target;
        row.appendChild(hint);
        const actions = document.createElement('div');
        actions.style.display = 'flex';
        actions.style.gap = '0.25rem';
        actions.style.marginTop = '0.5rem';
        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'frame-btn';
        confirmBtn.style.flex = '1';
        confirmBtn.style.padding = '0.25rem 0.5rem';
        confirmBtn.style.fontSize = '0.75rem';
        confirmBtn.textContent = '● Confirm';
        confirmBtn.addEventListener('click', () => setFieldState(doc, field.name, 'confirmed'));
        const correctBtn = document.createElement('button');
        correctBtn.className = 'frame-btn';
        correctBtn.style.flex = '1';
        correctBtn.style.padding = '0.25rem 0.5rem';
        correctBtn.style.fontSize = '0.75rem';
        correctBtn.textContent = '◆ Correct';
        correctBtn.addEventListener('click', () => promptCorrect(doc, field));
        actions.appendChild(confirmBtn);
        actions.appendChild(correctBtn);
        row.appendChild(actions);
        return row;
    }

    async function promptCorrect(doc, field) {
        const current = (fieldConfirmState[doc.id] && fieldConfirmState[doc.id][field.name + '_value']) || '';
        const input = await showValueModal('Correct value for ' + field.label + ':', current);
        if (input === null) return;
        if (!fieldConfirmState[doc.id]) fieldConfirmState[doc.id] = {};
        fieldConfirmState[doc.id][field.name] = 'corrected';
        fieldConfirmState[doc.id][field.name + '_value'] = input;
        renderChecklist(doc);
        renderDocs();
        await saveReviewState(doc);
        if (window.SemptifyFeedback) SemptifyFeedback.success(field.label + ' corrected.');
    }

    async function setFieldState(doc, fieldName, state) {
        if (!fieldConfirmState[doc.id]) fieldConfirmState[doc.id] = {};
        fieldConfirmState[doc.id][fieldName] = state;
        renderChecklist(doc);
        renderDocs();
        await saveReviewState(doc);
        if (state === 'confirmed' && window.SemptifyFeedback) {
            SemptifyFeedback.success('Field confirmed.');
        }
    }

    // Filter buttons
    document.querySelectorAll('.dc-filter').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.dc-filter').forEach(b => b.style.background = '');
            btn.style.background = 'var(--color-calm-100)';
            currentFilter = btn.dataset.filter;
            renderDocs();
        });
    });

    // Type select
    typeSelect.addEventListener('change', async () => {
        if (!currentDoc) return;
        const newType = typeSelect.value;
        try {
            const r = await fetch('/api/dc/document/' + encodeURIComponent(currentDoc.id) + '/type', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ document_type: newType }),
                credentials: 'include',
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const data = await r.json();
            currentDoc.document_type = newType;
            renderDocs();
            if (data.overlays) renderOverlays(data.overlays);
            renderChecklist(currentDoc);
            hideTypeSuggestion();
            if (newType && window.SemptifyFeedback) {
                SemptifyFeedback.info('Type set to ' + (documentTypes[newType] ? documentTypes[newType].label : newType) + '. Checklist updated.');
            }
        } catch (e) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Could not update type: ' + e.message);
        }
    });

    // Status select
    statusSelect.addEventListener('change', async () => {
        if (!currentDoc) return;
        const newStatus = statusSelect.value;
        if (!newStatus) return;
        if (!fieldConfirmState[currentDoc.id]) fieldConfirmState[currentDoc.id] = {};
        fieldConfirmState[currentDoc.id].manual_status = newStatus;
        currentDoc.verification_status = newStatus;
        renderDocs();
        await saveReviewState(currentDoc);
        if (window.SemptifyFeedback) SemptifyFeedback.success('Status set to ' + newStatus + '.');
    });

    // Semptify-suggested document type — banner with Accept/Dismiss
    function typeLabel(value) {
        const map = {
            lease: 'Lease Agreement',
            notice_to_vacate: 'Notice to Vacate',
            repair_request: 'Repair Request',
            rent_receipt: 'Rent Receipt',
            move_in_inspection: 'Move-in Inspection',
            court_summons: 'Court Summons',
            correspondence: 'Correspondence',
            other: 'Other'
        };
        return map[value] || (value ? value.replace(/_/g, ' ') : 'Unknown');
    }

    function showTypeSuggestion(suggestedType) {
        const banner = document.getElementById('dcTypeSuggest');
        const label = document.getElementById('dcSuggestedType');
        if (!banner || !label) return;
        label.textContent = typeLabel(suggestedType);
        banner.dataset.suggested = suggestedType;
        banner.style.display = 'flex';
    }

    function hideTypeSuggestion() {
        const banner = document.getElementById('dcTypeSuggest');
        if (banner) banner.style.display = 'none';
    }

    document.getElementById('dcAcceptSuggest').addEventListener('click', async () => {
        const banner = document.getElementById('dcTypeSuggest');
        const suggested = banner.dataset.suggested;
        if (!suggested || !currentDoc) return;
        typeSelect.value = suggested;
        try {
            const r = await fetch('/api/dc/document/' + encodeURIComponent(currentDoc.id) + '/type', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ document_type: suggested }),
                credentials: 'include',
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            currentDoc.document_type = suggested;
            renderDocs();
            renderChecklist(currentDoc);
            if (window.SemptifyFeedback) SemptifyFeedback.success('Type set to ' + typeLabel(suggested) + '.');
        } catch (e) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Could not apply suggestion: ' + e.message);
        }
        hideTypeSuggestion();
    });

    document.getElementById('dcDismissSuggest').addEventListener('click', () => {
        hideTypeSuggestion();
        if (window.SemptifyFeedback) SemptifyFeedback.info('Suggestion dismissed. You can still pick a type manually.');
    });

    // Download
    downloadBtn.addEventListener('click', () => {
        if (!currentDoc) return;
        window.location.href = '/api/vault/' + encodeURIComponent(currentDoc.id) + '/download';
    });

    // Process now — triggers OCR + extraction on demand
    const processBtn = document.getElementById('dcProcessBtn');
    processBtn.addEventListener('click', async () => {
        if (!currentDoc) return;
        if (processBtn.disabled) return;
        processBtn.disabled = true;
        processBtn.textContent = '◆ Processing…';
        if (window.SemptifyFeedback) SemptifyFeedback.info('Processing started. This may take a few moments.', { timeout: 5000 });
        try {
            const r = await fetch('/api/intake/process/vault/' + encodeURIComponent(currentDoc.id), {
                method: 'POST',
                credentials: 'include',
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const data = await r.json();
            if (window.SemptifyFeedback) SemptifyFeedback.success('Processing complete. Overlays updated.');
            await loadOverlays(currentDoc.id);
            await loadDocs();
            renderChecklist(currentDoc);
            if (window.pdfjsLib && /\.pdf$/i.test(currentDoc.filename || '')) {
                applyHighlights(currentDoc);
            }
            loadUserAnnotations(currentDoc);
            // Semptify suggests a document type from classification
            if (data.doc_type && data.doc_type !== 'unknown' && data.doc_type !== currentDoc.document_type) {
                showTypeSuggestion(data.doc_type);
            }
        } catch (err) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Processing failed: ' + err.message);
        } finally {
            processBtn.disabled = false;
            processBtn.textContent = '◆ Process now';
        }
    });

    // Share dialog — 5th verb of Document Center
    const shareBtn = document.getElementById('dcShareBtn');
    const shareModal = document.getElementById('dcShareModal');
    const shareCancel = document.getElementById('dcShareCancel');
    const shareForm = document.getElementById('dcShareForm');
    async function loadShares(doc) {
        if (!doc) return;
        const listEl = document.getElementById('dcShareList');
        const itemsEl = document.getElementById('dcShareListItems');
        try {
            const r = await fetch('/api/dc/document/' + encodeURIComponent(doc.id) + '/shares', { credentials: 'include' });
            if (!r.ok) return;
            const data = await r.json();
            const shares = data.shares || [];
            if (!shares.length) {
                listEl.style.display = 'none';
                return;
            }
            itemsEl.innerHTML = shares.map(s =>
                '<div style="margin-bottom:0.375rem; padding:0.375rem; background:var(--zone-surface-2); border-radius:0.25rem;">' +
                '<div>' + escapeHtml(s.recipient) + ' · ' + escapeHtml(s.scope) + '</div>' +
                '<a href="' + escapeHtml(s.share_url) + '" style="color:var(--color-info); font-size:0.6875rem; word-break:break-all;">' + escapeHtml(s.share_url) + '</a>' +
                '</div>'
            ).join('');
            listEl.style.display = '';
        } catch (e) { /* silent */ }
    }

    shareBtn.addEventListener('click', () => {
        if (!currentDoc) return;
        document.getElementById('dcShareDocName').textContent = currentDoc.filename || 'Untitled';
        document.getElementById('dcShareResult').style.display = 'none';
        shareForm.style.display = '';
        shareForm.reset();
        loadShares(currentDoc);
        shareModal.style.display = 'flex';
    });
    shareCancel.addEventListener('click', () => { shareModal.style.display = 'none'; });
    shareModal.addEventListener('click', (e) => {
        if (e.target === shareModal) shareModal.style.display = 'none';
    });
    shareForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!currentDoc) return;
        const recipient = document.getElementById('dcShareRecipient').value.trim();
        const message = document.getElementById('dcShareMessage').value.trim();
        const scope = document.getElementById('dcShareScope').value;
        if (!recipient) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Enter a recipient.');
            return;
        }
        const submitBtn = shareForm.querySelector('button[type=submit]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sharing…';
        try {
            const r = await fetch('/api/dc/document/' + encodeURIComponent(currentDoc.id) + '/share', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipient: recipient,
                    message: message,
                    scope: scope
                }),
                credentials: 'include'
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const data = await r.json();
            document.getElementById('dcShareUrl').value = window.location.origin + data.share_url;
            document.getElementById('dcShareResult').style.display = '';
            if (window.SemptifyFeedback) SemptifyFeedback.success('Share link created for ' + recipient + '.');
            loadShares(currentDoc);
        } catch (err) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Share failed: ' + err.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Share';
        }
    });

    // Upload modal
    const uploadBtn = document.getElementById('dcUploadBtn');
    const uploadModal = document.getElementById('dcUploadModal');
    const uploadCancel = document.getElementById('dcUploadCancel');
    const uploadForm = document.getElementById('dcUploadForm');
    const fileInput = document.getElementById('dcFileInput');
    const dropZone = document.getElementById('dcDropZone');
    const dropTitle = document.getElementById('dcDropTitle');
    const dropHint = document.getElementById('dcDropHint');
    const uploadStatus = document.getElementById('dcUploadStatus');
    const uploadSubmit = document.getElementById('dcUploadSubmit');
    let selectedFile = null;

    uploadBtn.addEventListener('click', () => { uploadModal.style.display = 'flex'; });
    const emptyUploadBtn = document.getElementById('dcEmptyUploadBtn');
    if (emptyUploadBtn) emptyUploadBtn.addEventListener('click', () => { uploadModal.style.display = 'flex'; });
    uploadCancel.addEventListener('click', () => {
        uploadModal.style.display = 'none';
        resetUpload();
    });
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        selectedFile = fileInput.files && fileInput.files[0];
        if (selectedFile) {
            dropTitle.textContent = selectedFile.name;
            dropHint.textContent = (selectedFile.size / 1024).toFixed(1) + ' KB';
            uploadSubmit.disabled = false;
        }
    });
    ['dragenter', 'dragover'].forEach(ev => dropZone.addEventListener(ev, e => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--color-info)';
    }));
    ['dragleave', 'drop'].forEach(ev => dropZone.addEventListener(ev, e => {
        e.preventDefault();
        dropZone.style.borderColor = '';
    }));
    dropZone.addEventListener('drop', e => {
        if (e.dataTransfer.files && e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            fileInput.dispatchEvent(new Event('change'));
        }
    });

    function resetUpload() {
        selectedFile = null;
        fileInput.value = '';
        dropTitle.textContent = 'Tap here to choose a file';
        dropHint.textContent = 'Photos, letters, PDFs, screenshots — anything about your tenancy.';
        uploadStatus.textContent = '';
        uploadSubmit.disabled = true;
    }

    // Show the picked file on the work surface while upload + intake run —
    // the spec's live-intake rule: the user watches their document, not a
    // modal spinner. Images get the overlay wrapper so Pass 0 regions can
    // paint on the same layer once the session resolves; everything else
    // previews through the browser's native renderer.
    function previewLocalFile(file) {
        const url = URL.createObjectURL(file);
        const container = document.getElementById('dcPdfContainer');
        const empty = document.getElementById('dcViewerEmpty');
        const iframe = document.getElementById('dcIframeFallback');
        const imageContainer = document.getElementById('dcImageContainer');
        if (empty) empty.style.display = 'none';
        if (iframe) iframe.style.display = 'none';
        if (imageContainer) imageContainer.style.display = 'none';
        if (file.type && file.type.startsWith('image/')) {
            container.style.display = 'flex';
            container.style.position = 'relative';
            container.innerHTML = '';
            const wrapper = document.createElement('div');
            wrapper.style.position = 'relative';
            wrapper.style.maxWidth = '100%';
            wrapper.style.background = 'var(--zone-surface-inverse)';
            const img = document.createElement('img');
            img.src = url;
            img.style.display = 'block';
            img.style.maxWidth = '100%';
            img.style.height = 'auto';
            img.draggable = false;
            wrapper.appendChild(img);
            const overlay = document.createElement('div');
            overlay.className = 'dc-image-overlay';
            overlay.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;';
            wrapper.appendChild(overlay);
            container.appendChild(wrapper);
        } else {
            container.style.display = 'none';
            if (iframe) { iframe.style.display = ''; iframe.src = url; }
        }
    }

    function showIntakeStripNote(title, text) {
        const strip = document.getElementById('dcFieldWalk');
        if (!strip) return;
        strip.hidden = false;
        strip.innerHTML = '<div class="dc-fieldcard"><div class="dc-fieldcard-label">' + escapeHtml(title) + '</div><div class="dc-fieldcard-value">' + escapeHtml(text) + '</div></div>';
    }

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedFile) return;
        const file = selectedFile;
        // The work surface takes over immediately — document visible while
        // the upload posts, then the intake session drives the strip.
        uploadModal.style.display = 'none';
        resetUpload();
        previewLocalFile(file);
        showIntakeStripNote('Uploading', 'Your document is on its way to your vault — then Semptify starts reading it.');
        const fd = new FormData();
        fd.append('file', file);
        fd.append('user_id', (document.cookie.match(/(^|; )semptify_uid=([^;]+)/) || [,'',''])[2] || 'anon');
        fd.append('username', 'tenant');
        fd.append('storage_provider', 'local');
        try {
            const r = await fetch('/api/intake/upload/auto', {
                method: 'POST',
                body: fd,
                credentials: 'include',
            });
            const data = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(data.detail || data.message || 'HTTP ' + r.status);

            if (data.error === 'reconnect_required' || data.error === 'token_expired' || data.error === 'storage_required') {
                uploadModal.style.display = 'flex';
                uploadStatus.innerHTML = '<span style="color:var(--color-warning-800);">' + escapeHtml(data.message || 'Storage needs reconnecting.') + '</span> <a href="/storage/reconnect?return_to=/dc" class="frame-btn" style="margin-left:0.5rem;">Reconnect</a>';
                uploadSubmit.disabled = false;
                uploadSubmit.textContent = 'Upload';
                return;
            }

            await loadDocs();
            await loadUnlocks();
            const newDocId = data.vault_id || data.id;
            if (newDocId) {
                const uploadedDoc = allDocs.find(d => d.id === newDocId);
                if (uploadedDoc) await selectDoc(uploadedDoc);
            }
        } catch (err) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Upload failed: ' + (err.message || 'unknown error'));
            showIntakeStripNote('Upload failed', (err.message || 'Something went wrong — the document did not reach your vault. Try again.'));
        }
    });

    // ---- Guidance rail: goal / progress / about / next-step / field walk ----
    // Driven by real state only: doc.verification_status, documentTypes field
    // defs, fieldConfirmState, and overlay progress. Nothing decorative.

    const PROGRESS_STEPS = ['Added', 'Type set', 'Fields confirmed', 'Verified', 'Ready to use'];
    let snoozedFields = {};  // {doc_id: {field_name: true}} — "not now" for this session

    function dcFieldCounts(doc) {
        const def = doc && doc.document_type ? documentTypes[doc.document_type] : null;
        if (!def) return { required: [], confirmed: 0, total: 0 };
        const state = fieldConfirmState[doc.id] || {};
        const required = def.fields.filter(f => f.required);
        const confirmed = required.filter(f => state[f.name] === 'confirmed' || state[f.name] === 'corrected').length;
        return { required, confirmed, total: required.length };
    }

    function dcStepStates(doc) {
        // Each step is independently true — a later status (e.g. a doc marked
        // verified before its type was set) must not mark earlier steps done.
        // 'current' is the first step still undone.
        if (!doc) return { steps: [false, false, false, false, false], current: -1, fieldsDone: 0, fieldsTotal: 0 };
        const fc = dcFieldCounts(doc);
        const status = effectiveStatus(doc);
        const steps = [
            true,                                                                   // Added
            !!doc.document_type,                                                    // Type set
            !!doc.document_type && (fc.total === 0 || fc.confirmed >= fc.total),    // Fields confirmed
            status === 'verified',                                                  // Verified
            false,                                                                  // Ready to use (below)
        ];
        steps[4] = steps[0] && steps[1] && steps[2] && steps[3];
        const current = steps.findIndex(s => !s);
        return { steps, current, fieldsDone: fc.confirmed, fieldsTotal: fc.total };
    }

    function updateGuidanceRail() {
        const prog = document.getElementById('dcProgressList');
        const about = document.getElementById('dcAboutDoc');
        const next = document.getElementById('dcNextStep');
        if (!prog || !about || !next) return;
        const doc = currentDoc;
        const st = dcStepStates(doc);
        prog.innerHTML = '';
        PROGRESS_STEPS.forEach((label, i) => {
            const li = document.createElement('li');
            const done = st.steps[i], isCurrent = i === st.current;
            li.className = 'dc-step' + (done ? ' dc-step--done' : isCurrent ? ' dc-step--current' : '');
            li.innerHTML = '<span class="dc-step-dot">' + (done ? '●' : isCurrent ? '◆' : '○') + '</span><span>' + label +
                (i === 2 && st.fieldsTotal ? ' <span style="color:var(--text-muted);font-weight:400;">(' + st.fieldsDone + ' of ' + st.fieldsTotal + ')</span>' : '') + '</span>';
            prog.appendChild(li);
        });
        if (!doc) {
            about.innerHTML = '<div class="shell-status-row"><span class="shell-status-label">Status</span><span class="shell-status-value">Nothing selected</span></div>';
            next.textContent = allDocs.length ? 'Pick a document from your vault below — it opens on the right.' : 'Upload your first document with the button below.';
            renderFieldWalk();
            return;
        }
        const b = statusBadge(effectiveStatus(doc));
        const typeLabel = doc.document_type ? doc.document_type.replace(/_/g, ' ') : 'not set';
        about.innerHTML =
            '<div class="shell-status-row"><span class="shell-status-label">Type</span><span class="shell-status-value">' + escapeHtml(typeLabel) + '</span></div>' +
            '<div class="shell-status-row"><span class="shell-status-label">Status</span><span class="shell-status-value" style="color:' + b.color + ';">' + escapeHtml(b.label) + '</span></div>' +
            '<div class="shell-status-row"><span class="shell-status-label">Fields confirmed</span><span class="shell-status-value">' + st.fieldsDone + ' of ' + (st.fieldsTotal || '—') + '</span></div>' +
            '<div class="shell-status-row"><span class="shell-status-label">Added</span><span class="shell-status-value">' + escapeHtml(fmtDate(doc.uploaded_at) || '—') + '</span></div>';
        const pending = st.fieldsTotal ? (st.fieldsTotal - st.fieldsDone) : 0;
        if (!doc.document_type) next.textContent = 'Set the document type in the toolbar — that tells Semptify which details to check.';
        else if (pending > 0) next.textContent = 'Confirm or fix ' + pending + ' detail' + (pending === 1 ? '' : 's') + ' — the cards above the document walk you through them.';
        else if (effectiveStatus(doc) !== 'verified') next.textContent = 'All details confirmed. Set status to Verified in the toolbar, or leave it — confirmed is enough.';
        else next.textContent = 'Nothing needed — this document is verified and ready to use in packets and timelines.';
        renderFieldWalk();
    }

    // --- OCR intake confirm loop (vault-backed session) -------------------
    // When the vault + intake pipeline are available, the field walk is
    // driven by a real /api/dc/intake session: OCR proposes values with
    // source spans, the user answers yes / no / fix per field, and finalize
    // writes the reviewed fields into the tenant's vault.db. When intake
    // can't start (local doc, unprovisioned vault), the checklist walk
    // below stays as the fallback — same strip, same controls.

    let intakePollTimer = null;

    function stopIntakePoll() {
        if (intakePollTimer) { clearInterval(intakePollTimer); intakePollTimer = null; }
    }

    async function pollIntake() {
        if (!intakeSession || intakeSession.status !== 'processing') { stopIntakePoll(); return; }
        try {
            const r = await fetch('/api/dc/intake/' + encodeURIComponent(intakeSession.session_id), { credentials: 'include' });
            if (!r.ok) { stopIntakePoll(); intakeSession = null; renderFieldWalk(); return; }
            intakeSession = await r.json();
            renderRegions();
            renderFieldWalk();
            if (intakeSession.status !== 'processing') stopIntakePoll();
        } catch (e) { /* transient — keep polling */ }
    }

    async function startIntake(doc) {
        stopIntakePoll();
        intakeSession = null;
        intakeWordBoxes = null;
        document.querySelectorAll('.dc-region').forEach(el => el.remove());
        const state = fieldConfirmState[doc.id] || {};
        if (state.manual_status === 'verified') return;  // already finalized
        try {
            const r = await fetch('/api/dc/intake/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vault_id: doc.id }),
                credentials: 'include',
            });
            if (!r.ok) return;
            const session = await r.json();
            intakeSession = session;
            renderRegions();
            renderFieldWalk();
            if (session.status === 'processing') {
                intakePollTimer = setInterval(pollIntake, 1500);
            } else if (!session.fields || !session.fields.length) {
                intakeSession = null;
            }
        } catch (e) { /* silent — fallback walk handles it */ }
    }

    async function answerIntakeField(doc, field, answer, value) {
        try {
            const r = await fetch('/api/dc/intake/' + encodeURIComponent(intakeSession.session_id) + '/answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field_id: field.id, answer: answer, value: value || null }),
                credentials: 'include',
            });
            const data = await r.json().catch(() => ({}));
            if (!r.ok) {
                if (window.SemptifyFeedback) SemptifyFeedback.error(data.error === 'session_not_found' ? 'That review session expired — reopen the document to restart it.' : ('Could not save the answer: ' + (data.error || 'HTTP ' + r.status)));
                if (r.status === 404) { intakeSession = null; renderFieldWalk(); }
                return;
            }
            field.answer = data.field.answer;
            field.final_value = data.field.final_value;
            intakeSession.fields_answered = data.fields_answered;
            renderFieldWalk();
        } catch (e) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Could not save the answer: ' + e.message);
        }
    }

    async function finalizeIntake(doc) {
        try {
            const r = await fetch('/api/dc/intake/' + encodeURIComponent(intakeSession.session_id) + '/finalize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
                credentials: 'include',
            });
            const data = await r.json().catch(() => ({}));
            if (r.status === 422 && data.error === 'unreviewed_fields') {
                if (window.SemptifyFeedback) SemptifyFeedback.info('A few details still need an answer — they are back in the walk above.');
                renderFieldWalk();
                return;
            }
            if (!r.ok || !data.success) throw new Error(data.error || 'HTTP ' + r.status);
            intakeSession = null;
            const label = data.verification_state === 'verified' ? 'verified' : (data.verification_state === 'mismatched' ? 'flagged as mismatched' : 'saved for review');
            if (window.SemptifyFeedback) SemptifyFeedback.success('Saved to your vault — document ' + label + '.');
            await loadReviewState(doc);
            await loadDocs();
            renderFieldWalk();
        } catch (e) {
            if (window.SemptifyFeedback) SemptifyFeedback.error('Could not save to the vault: ' + e.message);
        }
    }

    function clearIntakeHighlights() {
        document.querySelectorAll('.dc-intake-hl').forEach(el => el.remove());
    }

    async function highlightFieldSpan(doc, field) {
        clearIntakeHighlights();
        const span = field && field.source_span_key;
        if (!span || !span.startsWith('word:')) return;
        const idx = parseInt(span.split(':')[2], 10);
        if (!Number.isFinite(idx)) return;
        if (!intakeWordBoxes || intakeWordBoxes.doc_id !== doc.id) {
            try {
                const r = await fetch('/api/dc/document/' + encodeURIComponent(doc.id) + '/word-boxes', { credentials: 'include' });
                const data = r.ok ? await r.json() : null;
                intakeWordBoxes = { doc_id: doc.id, boxes: (data && data.word_boxes) || [] };
            } catch (e) { return; }
        }
        const wb = intakeWordBoxes.boxes[idx];
        if (!wb || !wb.bbox) return;
        const overlay = document.querySelector('#dcViewer .dc-image-overlay');
        if (!overlay) return;
        const img = overlay.parentElement ? overlay.parentElement.querySelector('img') : null;
        if (!img || !img.naturalWidth) return;
        const scaleX = overlay.clientWidth / img.naturalWidth;
        const scaleY = overlay.clientHeight / img.naturalHeight;
        const hl = document.createElement('div');
        hl.className = 'dc-intake-hl';
        hl.style.cssText = 'position:absolute;pointer-events:none;background:rgba(255,205,60,0.4);border-radius:2px;'
            + 'left:' + (wb.bbox.left * scaleX) + 'px;top:' + (wb.bbox.top * scaleY) + 'px;'
            + 'width:' + Math.max(wb.bbox.width * scaleX, 6) + 'px;height:' + Math.max(wb.bbox.height * scaleY, 6) + 'px;';
        overlay.appendChild(hl);
    }

    async function promptIntakeEdit(doc, field) {
        const input = await showValueModal('Correct value for ' + field.label + ':', field.proposed_value || '');
        if (input === null) return;
        await answerIntakeField(doc, field, 'edit', input);
    }

    // --- Pass 0 region painting -------------------------------------------
    // Regions arrive on the session as the segmentation passes run. Those
    // with bounding boxes paint onto the same overlay layer the field
    // highlights use — pending regions show a neutral outline, resolved
    // ones calm green, and anything flagged for manual review amber.
    // The original document is never touched; this draws on the overlay.

    function renderRegions() {
        document.querySelectorAll('.dc-region').forEach(el => el.remove());
        if (!intakeSession || !Array.isArray(intakeSession.regions)) return;
        const overlay = document.querySelector('#dcViewer .dc-image-overlay');
        if (!overlay) return;
        const img = overlay.parentElement ? overlay.parentElement.querySelector('img') : null;
        if (!img || !img.naturalWidth) return;
        const scaleX = overlay.clientWidth / img.naturalWidth;
        const scaleY = overlay.clientHeight / img.naturalHeight;
        intakeSession.regions.forEach(region => {
            if (!region.bbox || region.status === 'no_data') return;
            const el = document.createElement('div');
            el.className = 'dc-region dc-region--' + (region.status || 'pending');
            el.title = region.label + (region.status === 'manual_review' ? ' — needs a look' : '');
            el.style.cssText = 'position:absolute;pointer-events:none;border-radius:3px;'
                + 'left:' + (region.bbox.left * scaleX) + 'px;top:' + (region.bbox.top * scaleY) + 'px;'
                + 'width:' + Math.max(region.bbox.width * scaleX, 8) + 'px;height:' + Math.max(region.bbox.height * scaleY, 8) + 'px;';
            overlay.appendChild(el);
        });
    }

    function renderIntakeProgress(strip) {
        const card = document.createElement('div');
        card.className = 'dc-fieldcard';
        const regions = intakeSession.regions || [];
        const resolved = regions.filter(r => r.status === 'resolved').length;
        card.innerHTML = '<div class="dc-fieldcard-label">Reading your document</div>' +
            '<div class="dc-fieldcard-value">Semptify is checking the page in passes — details to confirm will appear here.</div>' +
            (regions.length ? '<div class="shell-note" style="font-size:0.75rem;">' + resolved + ' of ' + regions.length + ' areas read so far</div>' : '');
        strip.appendChild(card);
    }

    function renderIntakeError(strip) {
        const card = document.createElement('div');
        card.className = 'dc-fieldcard';
        card.innerHTML = '<div class="dc-fieldcard-label">Reading stopped</div>' +
            '<div class="dc-fieldcard-value">' + escapeHtml(intakeSession.status_detail || 'Semptify could not finish reading this document.') + '</div>' +
            '<div class="shell-note" style="font-size:0.75rem;">The document is safe in your vault — you can reopen it to try again.</div>';
        strip.appendChild(card);
    }

    function renderIntakeWalk(strip, doc) {
        const fields = intakeSession.fields;
        const answered = fields.filter(f => f.answer).length;
        const pending = fields.filter(f => !f.answer);
        const snoozed = snoozedFields[doc.id] || {};

        const counter = document.createElement('div');
        counter.className = 'dc-fieldcard-count';
        counter.textContent = answered + ' of ' + fields.length + ' confirmed';
        strip.appendChild(counter);

        if (intakeSession.manual_review_count) {
            const flag = document.createElement('div');
            flag.className = 'dc-fieldcard-more';
            flag.textContent = intakeSession.manual_review_count + ' area' + (intakeSession.manual_review_count === 1 ? '' : 's') + ' on the page need a look — outlined in amber.';
            strip.appendChild(flag);
        }
        if (intakeSession.overlay_status === 'error') {
            const ow = document.createElement('div');
            ow.className = 'dc-fieldcard-more';
            ow.textContent = 'The region overlay could not be saved — your review still works; reopen the document to retry saving it.';
            strip.appendChild(ow);
        }

        if (!pending.length) {
            const card = document.createElement('div');
            card.className = 'dc-fieldcard';
            card.innerHTML = '<div class="dc-fieldcard-label">All details reviewed</div>' +
                '<div class="dc-fieldcard-value">Save the confirmed details to your vault.</div>';
            const actions = document.createElement('div');
            actions.className = 'dc-fieldcard-actions';
            const save = document.createElement('button');
            save.className = 'frame-btn';
            save.style.flex = '1';
            save.style.fontSize = '0.75rem';
            save.style.padding = '0.25rem 0.4rem';
            save.style.background = 'var(--color-success-50)';
            save.style.color = 'var(--color-success-800)';
            save.textContent = 'Save to vault';
            save.addEventListener('click', () => finalizeIntake(doc));
            actions.appendChild(save);
            card.appendChild(actions);
            strip.appendChild(card);
            return;
        }

        // "Not now" rotates a field to the back — every field must be
        // answered before save, so snoozed fields resurface rather than
        // disappear.
        const field = pending.find(f => !snoozed[f.id]) || pending[0];
        const card = document.createElement('div');
        card.className = 'dc-fieldcard';
        const read = field.proposed_value
            ? 'We read: ' + escapeHtml(field.proposed_value)
            : 'We could not read this — type it in with "Fix it".';
        card.innerHTML =
            '<div class="dc-fieldcard-label">' + escapeHtml(field.label) + (field.required ? '' : ' · optional') + '</div>' +
            '<div class="dc-fieldcard-value">' + read + '</div>';
        const actions = document.createElement('div');
        actions.className = 'dc-fieldcard-actions';

        const ok = document.createElement('button');
        ok.className = 'frame-btn'; ok.style.flex = '1'; ok.style.fontSize = '0.75rem'; ok.style.padding = '0.25rem 0.4rem';
        ok.style.background = 'var(--color-success-50)'; ok.style.color = 'var(--color-success-800)';
        ok.textContent = 'Looks right';
        ok.addEventListener('click', () => answerIntakeField(doc, field, 'yes'));

        const fix = document.createElement('button');
        fix.className = 'frame-btn'; fix.style.flex = '1'; fix.style.fontSize = '0.75rem'; fix.style.padding = '0.25rem 0.4rem';
        fix.textContent = 'Fix it';
        fix.addEventListener('click', () => promptIntakeEdit(doc, field));

        const wrong = document.createElement('button');
        wrong.className = 'frame-btn'; wrong.style.flex = '1'; wrong.style.fontSize = '0.75rem'; wrong.style.padding = '0.25rem 0.4rem';
        wrong.title = 'Not right — flags the document as mismatched';
        wrong.textContent = 'Not right';
        wrong.addEventListener('click', () => answerIntakeField(doc, field, 'no'));

        const later = document.createElement('button');
        later.className = 'frame-btn'; later.style.fontSize = '0.75rem'; later.style.padding = '0.25rem 0.4rem';
        later.title = 'Ask me after the next one';
        later.textContent = 'Not now';
        later.addEventListener('click', () => {
            if (!snoozedFields[doc.id]) snoozedFields[doc.id] = {};
            snoozedFields[doc.id][field.id] = true;
            renderFieldWalk();
        });

        actions.appendChild(ok); actions.appendChild(fix); actions.appendChild(wrong); actions.appendChild(later);
        card.appendChild(actions);
        strip.appendChild(card);
        highlightFieldSpan(doc, field);

        if (pending.length > 1) {
            const more = document.createElement('div');
            more.className = 'dc-fieldcard-more';
            more.textContent = '+ ' + (pending.length - 1) + ' more after this';
            strip.appendChild(more);
        }
    }

    function renderFieldWalk() {
        const strip = document.getElementById('dcFieldWalk');
        if (!strip) return;
        strip.innerHTML = '';
        const doc = currentDoc;
        if (!doc) { strip.hidden = true; return; }
        if (intakeSession && intakeSession.vault_id === doc.id) {
            strip.hidden = false;
            if (intakeSession.status === 'processing') { renderIntakeProgress(strip); return; }
            if (intakeSession.status === 'error') { renderIntakeError(strip); return; }
            renderIntakeWalk(strip, doc);
            return;
        }
        const def = doc.document_type ? documentTypes[doc.document_type] : null;
        if (!def) {
            strip.hidden = false;
            const card = document.createElement('div');
            card.className = 'dc-fieldcard';
            card.innerHTML = '<div class="dc-fieldcard-label">Verification</div><div class="dc-fieldcard-value">What kind of document is this?</div>' +
                '<div class="shell-note" style="font-size:0.75rem;">Pick a type in the toolbar — the right checklist appears here.</div>';
            strip.appendChild(card);
            return;
        }
        const state = fieldConfirmState[doc.id] || {};
        const snoozed = snoozedFields[doc.id] || {};
        const pending = def.fields.filter(f => (state[f.name] !== 'confirmed' && state[f.name] !== 'corrected') && !snoozed[f.name]);
        if (!pending.length) { strip.hidden = true; return; }
        strip.hidden = false;
        // One question at a time — the current field card plus a count.
        // The rest queue quietly; nothing crowds the document.
        const done = def.fields.length - pending.length;
        const counter = document.createElement('div');
        counter.className = 'dc-fieldcard-count';
        counter.textContent = done + ' of ' + def.fields.length + ' confirmed';
        strip.appendChild(counter);
        const f = pending[0];
        const card = document.createElement('div');
        card.className = 'dc-fieldcard';
        const corrected = state[f.name + '_value'];
        const weRead = corrected || '';
        card.innerHTML =
            '<div class="dc-fieldcard-label">' + escapeHtml(f.label) + (f.required ? '' : ' · optional') + '</div>' +
            '<div class="dc-fieldcard-value">' + (weRead ? 'You set: ' + escapeHtml(weRead) : 'We look for: ' + escapeHtml(f.ocr_target || f.label)) + '</div>';
        const actions = document.createElement('div');
        actions.className = 'dc-fieldcard-actions';
        const ok = document.createElement('button');
        ok.className = 'frame-btn'; ok.style.flex = '1'; ok.style.fontSize = '0.75rem'; ok.style.padding = '0.25rem 0.4rem';
        ok.style.background = 'var(--color-success-50)'; ok.style.color = 'var(--color-success-800)';
        ok.textContent = 'Looks right';
        ok.addEventListener('click', () => setFieldState(doc, f.name, 'confirmed'));
        const fix = document.createElement('button');
        fix.className = 'frame-btn'; fix.style.flex = '1'; fix.style.fontSize = '0.75rem'; fix.style.padding = '0.25rem 0.4rem';
        fix.textContent = 'Fix it';
        fix.addEventListener('click', () => promptCorrect(doc, f));
        const later = document.createElement('button');
        later.className = 'frame-btn'; later.style.fontSize = '0.75rem'; later.style.padding = '0.25rem 0.4rem';
        later.title = 'Not now — stays on the checklist';
        later.textContent = 'Not now';
        later.addEventListener('click', () => {
            if (!snoozedFields[doc.id]) snoozedFields[doc.id] = {};
            snoozedFields[doc.id][f.name] = true;
            updateGuidanceRail();
        });
        actions.appendChild(ok); actions.appendChild(fix); actions.appendChild(later);
        card.appendChild(actions);
        strip.appendChild(card);
        if (pending.length > 1) {
            const more = document.createElement('div');
            more.className = 'dc-fieldcard-more';
            more.textContent = '+ ' + (pending.length - 1) + ' more after this';
            strip.appendChild(more);
        }
    }

    // Mobile tab switching
    document.querySelectorAll('.dc-mobile-tab').forEach(btn => {
        btn.addEventListener('click', () => setMobilePane(btn.dataset.pane));
    });

    function checkMobile() {
        const isMobile = window.innerWidth < 768;
        const tabs = document.getElementById('dcMobileTabs');
        if (tabs) tabs.style.display = isMobile ? 'flex' : 'none';
        document.getElementById('dcShell').classList.toggle('dc-shell--mobile', isMobile);
        setMobilePane(activeMobilePane);
    }
    window.addEventListener('resize', checkMobile);

    // Init
    checkMobile();
    loadDocumentTypes().then(() => {
        loadDocs();
        loadUnlocks();
    });
})();