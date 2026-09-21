/* Docx export — tiny HTML → real .docx converter.
   Produces genuine OOXML (a zip of word/document.xml + rels) so the output
   opens in Word, LibreOffice, python-docx — AND re-reads cleanly through
   mammoth, which means an edited copy still previews in Semptify.
   (The common html-docx-js approach embeds altChunk HTML — Word-only,
   blank to every real docx reader. That is why this exists.)
   Deliberately light: paragraphs, headings, bold/italic/underline,
   lists-as-bullets, simple tables. Embedded images are dropped —
   noted to the user rather than silently lost. */
(function () {
    'use strict';

    var BLOCK = {
        P: 1, DIV: 1, H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1,
        LI: 1, BLOCKQUOTE: 1, PRE: 1, SECTION: 1, ARTICLE: 1, TR: 1
    };
    var HEADING_SZ = { H1: 56, H2: 48, H3: 40, H4: 32, H5: 28, H6: 24 }; // half-points

    function esc(s) {
        return String(s).replace(/[&<>"]/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
        });
    }

    /* Collect inline runs from a node; fmt = {b,i,u,sz}. */
    function runs(node, fmt, out) {
        node.childNodes.forEach(function (n) {
            if (n.nodeType === 3) { // text
                var t = n.textContent.replace(/\s+/g, ' ');
                if (t) out.push({ t: t, f: fmt });
                return;
            }
            if (n.nodeType !== 1) return;
            var tag = n.tagName;
            if (tag === 'BR') { out.push({ t: null, f: fmt }); return; }
            if (tag === 'IMG') { out.push({ img: true, f: fmt }); return; }
            if (BLOCK[tag]) { // nested block inside inline context — flush as break
                out.push({ t: null, f: fmt });
                runs(n, fmt, out);
                out.push({ t: null, f: fmt });
                return;
            }
            var f = {
                b: fmt.b || tag === 'STRONG' || tag === 'B',
                i: fmt.i || tag === 'EM' || tag === 'I',
                u: fmt.u || tag === 'U' || tag === 'INS',
                sz: fmt.sz
            };
            runs(n, f, out);
        });
    }

    function rPr(f) {
        var s = '';
        if (f.b) s += '<w:b/>';
        if (f.i) s += '<w:i/>';
        if (f.u) s += '<w:u w:val="single"/>';
        if (f.sz) s += '<w:sz w:val="' + f.sz + '"/><w:szCs w:val="' + f.sz + '"/>';
        return s ? '<w:rPr>' + s + '</w:rPr>' : '';
    }

    var droppedImages = 0;

    function paraXml(list, baseFmt) {
        var xml = '';
        var cur = '';
        list.forEach(function (r) {
            if (r.img) { droppedImages++; return; }
            if (r.t === null) { // break → close paragraph, reopen
                xml += '<w:p>' + cur + '</w:p>';
                cur = '';
                return;
            }
            var f = { b: r.f.b || (baseFmt && baseFmt.b), i: r.f.i, u: r.f.u, sz: r.f.sz || (baseFmt && baseFmt.sz) };
            cur += '<w:r>' + rPr(f) + '<w:t xml:space="preserve">' + esc(r.t) + '</w:t></w:r>';
        });
        xml += '<w:p>' + cur + '</w:p>';
        return xml;
    }

    /* Walk the DOM; emit paragraphs for every block. */
    function walk(node, body) {
        node.childNodes.forEach(function (n) {
            if (n.nodeType === 3) {
                if (n.textContent.trim()) body.push(paraXml([{ t: n.textContent.replace(/\s+/g, ' '), f: {} }]));
                return;
            }
            if (n.nodeType !== 1) return;
            var tag = n.tagName;
            if (tag === 'IMG') { droppedImages++; return; }
            if (tag === 'SCRIPT' || tag === 'STYLE') return;
            if (tag === 'UL' || tag === 'OL') {
                n.querySelectorAll(':scope > li').forEach(function (li) {
                    var out = [];
                    runs(li, {}, out);
                    out.unshift({ t: '\u2022 ', f: {} });
                    body.push(paraXml(out));
                });
                return;
            }
            if (tag === 'TABLE' || tag === 'TBODY' || tag === 'THEAD') {
                walk(n, body);
                return;
            }
            if (tag === 'TR') {
                n.querySelectorAll(':scope > td, :scope > th').forEach(function (c) {
                    var out = [];
                    runs(c, { b: c.tagName === 'TH' }, out);
                    body.push(paraXml(out));
                });
                return;
            }
            if (tag === 'HR') { body.push('<w:p/>'); return; }
            if (BLOCK[tag]) {
                var out = [];
                var fmt = { b: /^H[1-6]$/.test(tag), sz: HEADING_SZ[tag] || null };
                runs(n, fmt, out);
                body.push(paraXml(out, fmt));
                return;
            }
            walk(n, body); // inline wrapper (A, SPAN, FONT…) — keep descending
        });
    }

    /* fromHtml(htmlString) → Promise<Blob docx> + .droppedImages */
    function fromHtml(html) {
        droppedImages = 0;
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var body = [];
        walk(doc.body, body);
        if (!body.length) body.push('<w:p/>');

        var documentXml =
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
            '<w:body>' + body.join('') +
            '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>' +
            '</w:body></w:document>';

        var contentTypes =
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
            '<Default Extension="xml" ContentType="application/xml"/>' +
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
            '</Types>';

        var rels =
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>' +
            '</Relationships>';

        var zip = new JSZip();
        zip.file('[Content_Types].xml', contentTypes);
        zip.file('_rels/.rels', rels);
        zip.file('word/document.xml', documentXml);
        return zip.generateAsync({
            type: 'blob',
            mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }).then(function (blob) {
            fromHtml.droppedImages = droppedImages;
            return blob;
        });
    }
    fromHtml.droppedImages = 0;

    window.SemptifyDocxExport = { fromHtml: fromHtml };
})();
