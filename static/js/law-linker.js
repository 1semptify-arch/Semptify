/**
 * Law Linker — Universal legal citation linker
 * Detects citations in page text and links them to their official source.
 *
 * Supported citation types (local -> state -> federal):
 *   - Minnesota Statutes (Minn. Stat. § XXXX.XXX) -> revisor.mn.gov
 *   - US Code (XX U.S.C. § XXXX) -> law.cornell.edu
 *   - CFR (XX C.F.R. § XXX.XXX) -> ecfr.gov
 *   - IRS Publications (IRS Publication XXX) -> irs.gov
 *   - Minneapolis Code (Minneapolis Code § XXX) -> library.municode.com
 *   - St. Paul Code (St. Paul Ordinance XX-XX) -> library.municode.com
 *   - Hennepin County Ordinances -> hennepin.us
 *   - US Supreme Court (XXX U.S. XXX (YYYY)) -> courtlistener.com
 *   - Federal Appellate (XXX F.3d XXX (Xth Cir. YYYY)) -> courtlistener.com
 *   - Minnesota Cases (XXX Minn. XX, XXX N.W.2d XXX) -> courtlistener.com
 *
 * Each popup shows: title, summary, full text excerpt, and a clickable
 * "View Official Source →" link to the authoritative source.
 *
 * TODO (post-funding): Build a live-feed verification engine that continuously
 * checks all registered URLs and alerts when a source page moves or a statute
 * is amended. For now, last_verified dates are displayed so users know freshness.
 */

(function() {
    'use strict';

    const lawCache = new Map();
    const MAX_CACHE_SIZE = 50;
    let popup = null;
    let scrollHandler = null;

    // =========================================================================
    // Citation patterns — order matters (most specific first)
    // =========================================================================
    const CITATION_PATTERNS = [
        // Minnesota Statutes — section level (e.g. Minn. Stat. § 504B.321)
        {
            type: 'minnesota_statute',
            label: 'MN Statute',
            regex: /Minn\.\s*Stat\.\s*§?\s*(\d+[A-Z]?\.\d+(?:\.\d+)?)/gi,
            detect: /Minn\.\s*Stat\.\s*§?\s*\d+/i,
            idBuilder: (m) => 'minn_stat_' + m.replace(/\./g, '_').toLowerCase(),
            urlBuilder: (m) => 'https://www.revisor.mn.gov/statutes/cite/' + m,
            displayLabel: (m) => 'Minn. Stat. § ' + m,
            apiPath: '/api/law-library/statutes/'
        },
        // Minnesota Statutes — chapter level (e.g. Minn. Stat. § 504B, § 580)
        {
            type: 'minnesota_statute_chapter',
            label: 'MN Statute Chapter',
            regex: /Minn\.\s*Stat\.\s*§?\s*(\d+[A-Z]?)(?!\.\d)/gi,
            detect: /Minn\.\s*Stat\.\s*§?\s*\d+[A-Z]?(?!\.)/i,
            idBuilder: (m) => 'minn_stat_' + m.toLowerCase(),
            urlBuilder: (m) => 'https://www.revisor.mn.gov/statutes/cite/' + m,
            displayLabel: (m) => 'Minn. Stat. § ' + m,
            apiPath: '/api/law-library/statutes/'
        },
        // US Code (e.g. 42 U.S.C. § 3601)
        {
            type: 'us_code',
            label: 'US Code',
            regex: /(\d+)\s*U\.?S\.?C\.?\s*[§\s]*(\d+(?:-\d+)?)/gi,
            detect: /\d+\s*U\.?S\.?C\.?/i,
            idBuilder: (title, section) => 'usc_' + title + '_' + section,
            urlBuilder: (title, section) => 'https://www.law.cornell.edu/uscode/text/' + title + '/' + section,
            displayLabel: (title, section) => title + ' U.S.C. § ' + section,
            apiPath: '/api/law-library/statutes/'
        },
        // Code of Federal Regulations (e.g. 24 C.F.R. § 100.204)
        {
            type: 'cfr',
            label: 'CFR',
            regex: /(\d+)\s*C\.?F\.?R\.?\s*[§\s]*([\d.]+)/gi,
            detect: /\d+\s*C\.?F\.?R\.?/i,
            idBuilder: (title, section) => 'cfr_' + title + '_' + section.replace(/\./g, '_'),
            urlBuilder: (title, section) => 'https://www.ecfr.gov/current/title-' + title + '/section-' + section,
            displayLabel: (title, section) => title + ' C.F.R. § ' + section,
            apiPath: null
        },
        // IRS Publications (e.g. IRS Publication 527)
        {
            type: 'irs_pub',
            label: 'IRS Publication',
            regex: /IRS\s*Publication\s*(\d+)/gi,
            detect: /IRS\s*Publication\s*\d+/i,
            idBuilder: (num) => 'irs_pub_' + num,
            urlBuilder: (num) => 'https://www.irs.gov/publications/p' + num,
            displayLabel: (num) => 'IRS Publication ' + num,
            apiPath: '/api/law-library/statutes/'
        },
        // Minneapolis Code (e.g. Minneapolis Code § 244)
        {
            type: 'mpls_code',
            label: 'Minneapolis Code',
            regex: /Minneapolis\s*(?:Code|Ordinance)\s*[§\s]*(?:[\w-]+)?/gi,
            detect: /Minneapolis\s*(?:Code|Ordinance)/i,
            idBuilder: () => 'mpls_code',
            urlBuilder: () => 'https://library.municode.com/mn/minneapolis',
            displayLabel: () => 'Minneapolis Code of Ordinances',
            apiPath: '/api/law-library/statutes/'
        },
        // St. Paul Code (e.g. St. Paul Ordinance 21-44)
        {
            type: 'stpaul_code',
            label: 'St. Paul Code',
            regex: /St\.?\s*Paul\s*(?:Ordinance|Legislative\s*Code)\s*[\w-]+/gi,
            detect: /St\.?\s*Paul\s*(?:Ordinance|Legislative)/i,
            idBuilder: () => 'stpaul_code',
            urlBuilder: () => 'https://library.municode.com/mn/st-paul',
            displayLabel: () => 'St. Paul Legislative Code',
            apiPath: '/api/law-library/statutes/'
        },
        // Hennepin County
        {
            type: 'hennepin',
            label: 'Hennepin County',
            regex: /Hennepin\s*County\s*Ordinance/gi,
            detect: /Hennepin\s*County/i,
            idBuilder: () => 'hennepin_county',
            urlBuilder: () => 'https://www.hennepin.us/property-tax',
            displayLabel: () => 'Hennepin County Ordinances',
            apiPath: '/api/law-library/statutes/'
        },
        // US Supreme Court (e.g. 576 U.S. 519 (2015))
        {
            type: 'scotus',
            label: 'SCOTUS Case',
            regex: /(\d+)\s*U\.?\s*S\.?\s*(\d+)\s*\((\d{4})\)/g,
            detect: /\d+\s*U\.?\s*S\.?\s*\d+\s*\(\d{4}\)/i,
            idBuilder: (vol, page, year) => 'scotus_' + vol + '_' + page,
            urlBuilder: (vol, page, year) => 'https://www.courtlistener.com/?q=%22' + vol + '+U.S.+' + page + '%22&type=o',
            displayLabel: (vol, page, year) => vol + ' U.S. ' + page + ' (' + year + ')',
            apiPath: '/api/law-library/case-law/'
        },
        // Federal Appellate (e.g. 343 F.3d 1143 (9th Cir. 2003))
        {
            type: 'federal_appellate',
            label: 'Federal Appeals Case',
            regex: /(\d+)\s*F\.\w*\s*(\d+)\s*\((\w+\s*Cir\.\s*\d{4})\)/g,
            detect: /\d+\s*F\.\w*\s*\d+\s*\(\w+\s*Cir\./i,
            idBuilder: (vol, page, court) => 'fed_app_' + vol + '_' + page,
            urlBuilder: (vol, page, court) => 'https://www.courtlistener.com/?q=%22' + vol + '+F.+' + page + '%22&type=o',
            displayLabel: (vol, page, court) => vol + ' F.3d ' + page + ' (' + court + ')',
            apiPath: '/api/law-library/case-law/'
        },
        // Federal District (e.g. 6 F. Supp. 3d 1272 (S.D. Fla. 2014))
        {
            type: 'federal_district',
            label: 'Federal District Case',
            regex: /(\d+)\s*F\.\s*Supp\.\s*\w*\s*(\d+)\s*\(([^)]+)\)/g,
            detect: /\d+\s*F\.\s*Supp\.\s*\w*\s*\d+/i,
            idBuilder: (vol, page, court) => 'fed_dist_' + vol + '_' + page,
            urlBuilder: (vol, page, court) => 'https://www.courtlistener.com/?q=%22' + vol + '+F.+Supp.+%22&type=o',
            displayLabel: (vol, page, court) => vol + ' F. Supp. ' + page + ' (' + court + ')',
            apiPath: '/api/law-library/case-law/'
        },
        // Minnesota Cases (e.g. 298 Minn. 54, 213 N.W.2d 339 (1973))
        {
            type: 'minnesota_case',
            label: 'MN Case',
            regex: /(\d+)\s*Minn\.\s*(\d+)(?:,\s*\d+\s*N\.?W\.?\w*\s*\d+)?\s*\((\d{4})\)/g,
            detect: /\d+\s*Minn\.\s*\d+/i,
            idBuilder: (vol, page, year) => 'mn_case_' + vol + '_' + page,
            urlBuilder: (vol, page, year) => 'https://www.courtlistener.com/?q=%22' + vol + '+Minn.+' + page + '%22&type=o',
            displayLabel: (vol, page, year) => vol + ' Minn. ' + page + ' (' + year + ')',
            apiPath: '/api/law-library/case-law/'
        }
    ];

    function createPopup() {
        const el = document.createElement('div');
        el.id = 'law-linker-popup';
        el.innerHTML = `
            <div class="law-linker-header">
                <span class="law-linker-citation"></span>
                <span class="law-linker-type"></span>
            </div>
            <div class="law-linker-content"></div>
            <div class="law-linker-footer">
                <span class="law-linker-source-name">Source: —</span>
                <a href="#" class="law-linker-full" target="_blank" rel="noopener noreferrer">View Official Source →</a>
            </div>
        `;
        document.body.appendChild(el);
        return el;
    }

    function initStyles() {
        if (document.getElementById('law-linker-styles')) return;
        const styles = document.createElement('style');
        styles.id = 'law-linker-styles';
        styles.textContent = `
            .law-linker-cite {
                color: #60a5fa;
                border-bottom: 1px dotted #60a5fa;
                cursor: help;
                transition: all 0.2s;
            }
            .law-linker-cite:hover {
                color: #93c5fd;
                background: rgba(96, 165, 250, 0.1);
                border-radius: 2px;
            }
            #law-linker-popup {
                position: fixed;
                z-index: 10000;
                max-width: 450px;
                min-width: 300px;
                background: #1e293b;
                border: 1px solid #475569;
                border-radius: 12px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.4);
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.2s, visibility 0.2s;
                pointer-events: none;
            }
            #law-linker-popup.visible {
                opacity: 1;
                visibility: visible;
                pointer-events: auto;
            }
            .law-linker-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                background: linear-gradient(135deg, #1e3a5f, #1e293b);
                border-radius: 12px 12px 0 0;
                border-bottom: 1px solid #334155;
            }
            .law-linker-citation {
                font-weight: 700;
                color: #f8fafc;
                font-size: 0.95rem;
            }
            .law-linker-type {
                font-size: 0.7rem;
                text-transform: uppercase;
                color: #94a3b8;
                background: #334155;
                padding: 2px 8px;
                border-radius: 99px;
            }
            .law-linker-content {
                padding: 16px;
                max-height: 300px;
                overflow-y: auto;
            }
            .law-linker-content h4 {
                margin: 0 0 8px 0;
                color: #60a5fa;
                font-size: 0.9rem;
            }
            .law-linker-content p {
                margin: 0;
                color: #cbd5e1;
                font-size: 0.85rem;
                line-height: 1.6;
            }
            .law-linker-content .law-fulltext {
                background: #0f172a;
                padding: 12px;
                border-radius: 8px;
                font-size: 0.8rem;
                color: #e2e8f0;
                line-height: 1.7;
                border-left: 3px solid #3b82f6;
                margin-top: 12px;
                white-space: pre-wrap;
            }
            .law-linker-content .law-verified {
                margin-top: 10px;
                font-size: 0.72rem;
                color: #64748b;
                font-style: italic;
            }
            .law-linker-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 16px;
                background: #0f172a;
                border-radius: 0 0 12px 12px;
                border-top: 1px solid #334155;
                font-size: 0.75rem;
                color: #64748b;
            }
            .law-linker-full {
                color: #60a5fa;
                text-decoration: none;
                font-weight: 600;
            }
            .law-linker-full:hover {
                color: #93c5fd;
                text-decoration: underline;
            }
            .law-linker-loading {
                text-align: center;
                padding: 20px;
                color: #94a3b8;
            }
        `;
        document.head.appendChild(styles);
    }

    // =========================================================================
    // Citation parsing — tries each pattern, returns first match
    // =========================================================================
    function parseCitation(text) {
        for (const pattern of CITATION_PATTERNS) {
            if (!pattern.detect.test(text)) continue;
            pattern.detect.lastIndex = 0;
            pattern.regex.lastIndex = 0;
            const m = pattern.regex.exec(text);
            if (m) {
                const args = m.slice(1);
                const id = pattern.idBuilder.apply(null, args);
                const url = pattern.urlBuilder.apply(null, args);
                const label = pattern.displayLabel.apply(null, args);
                return {
                    type: pattern.type,
                    label: pattern.label,
                    id: id,
                    officialUrl: url,
                    displayLabel: label,
                    apiPath: pattern.apiPath,
                    matchedText: m[0]
                };
            }
        }
        return null;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function setCache(key, value) {
        if (lawCache.size >= MAX_CACHE_SIZE) {
            const firstKey = lawCache.keys().next().value;
            lawCache.delete(firstKey);
        }
        lawCache.set(key, value);
    }

    async function fetchLaw(citation) {
        const cacheKey = citation.id;
        if (lawCache.has(cacheKey)) {
            return lawCache.get(cacheKey);
        }
        if (!citation.apiPath) {
            return { error: 'no_api', message: 'No API endpoint for this citation type. Use the official source link.' };
        }
        try {
            const res = await fetch(citation.apiPath + citation.id, {
                credentials: 'include'
            });
            if (!res.ok) {
                if (res.status === 404) {
                    return { error: 'not_found', message: 'Law not found in database. Use the official source link.' };
                }
                throw new Error('HTTP ' + res.status);
            }
            const data = await res.json();
            setCache(cacheKey, data);
            return data;
        } catch (e) {
            console.error('Law Linker fetch error:', e);
            return { error: 'fetch_failed', message: 'Unable to load law text. Use the official source link.' };
        }
    }

    function showPopup(element, citation) {
        if (!popup) popup = createPopup();

        const rect = element.getBoundingClientRect();
        popup.querySelector('.law-linker-citation').textContent = citation.displayLabel;
        popup.querySelector('.law-linker-type').textContent = citation.label;
        popup.querySelector('.law-linker-content').innerHTML = '<div class="law-linker-loading">Loading...</div>';
        popup.querySelector('.law-linker-full').href = citation.officialUrl;
        popup.querySelector('.law-linker-source-name').textContent = 'Source: official';

        let left = rect.left + window.scrollX;
        let top = rect.bottom + window.scrollY + 8;

        if (left + 450 > window.innerWidth) {
            left = window.innerWidth - 460;
        }
        if (top + 300 > window.innerHeight + window.scrollY) {
            top = rect.top + window.scrollY - 308;
        }

        popup.style.left = left + 'px';
        popup.style.top = top + 'px';
        popup.classList.add('visible');
        attachScrollHandler();

        fetchLaw(citation).then(data => {
            if (data && data.error) {
                popup.querySelector('.law-linker-content').innerHTML = '<p>' + escapeHtml(data.message) + '</p>';
                return;
            }
            const s = data.statute || data.case || data.rule;
            if (!s) {
                popup.querySelector('.law-linker-content').innerHTML = '<p>Could not load law text. Use the official source link.</p>';
                return;
            }
            const fullText = s.full_text ? (s.full_text.length > 800 ? s.full_text.substring(0, 800) + '...' : s.full_text) : '';
            const verified = s.last_verified ? '<div class="law-verified">Last verified: ' + escapeHtml(s.last_verified) + '</div>' : '';
            const sourceName = s.source_name || 'official source';
            popup.querySelector('.law-linker-source-name').textContent = 'Source: ' + sourceName;
            if (s.official_url) {
                popup.querySelector('.law-linker-full').href = s.official_url;
            }
            const summary = s.summary || s.holding || '';
            const title = s.title || s.case_name || '';
            popup.querySelector('.law-linker-content').innerHTML = `
                <h4>${escapeHtml(title)}</h4>
                <p>${escapeHtml(summary)}</p>
                ${fullText ? '<div class="law-fulltext">' + escapeHtml(fullText) + '</div>' : ''}
                ${verified}
            `;
        });
    }

    function hidePopup() {
        if (popup) popup.classList.remove('visible');
        if (scrollHandler) {
            window.removeEventListener('scroll', scrollHandler);
            scrollHandler = null;
        }
    }

    function attachScrollHandler() {
        if (scrollHandler) return;
        scrollHandler = () => hidePopup();
        window.addEventListener('scroll', scrollHandler, { passive: true });
    }

    // =========================================================================
    // Process element — scan text nodes for any recognized citation
    // =========================================================================
    function processElement(element) {
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
        const nodesToReplace = [];
        let node;

        while (node = walker.nextNode()) {
            const text = node.textContent;
            // Quick check: does this text contain any citation pattern?
            let hasCitation = false;
            for (const pattern of CITATION_PATTERNS) {
                if (pattern.detect.test(text)) {
                    hasCitation = true;
                    break;
                }
            }
            if (!hasCitation) continue;
            // Reset regex state
            for (const pattern of CITATION_PATTERNS) {
                pattern.detect.lastIndex = 0;
                pattern.regex.lastIndex = 0;
            }
            if (node.parentElement && node.parentElement.closest('.law-linker-cite, #law-linker-popup')) continue;

            // Find all citation matches with their positions
            const matches = [];
            for (const pattern of CITATION_PATTERNS) {
                pattern.regex.lastIndex = 0;
                let m;
                while ((m = pattern.regex.exec(text)) !== null) {
                    const args = m.slice(1);
                    const citation = {
                        type: pattern.type,
                        label: pattern.label,
                        id: pattern.idBuilder.apply(null, args),
                        officialUrl: pattern.urlBuilder.apply(null, args),
                        displayLabel: pattern.displayLabel.apply(null, args),
                        apiPath: pattern.apiPath,
                        matchedText: m[0]
                    };
                    matches.push({ index: m.index, length: m[0].length, citation });
                }
            }

            if (matches.length === 0) continue;

            // Sort matches by position and remove overlaps
            matches.sort((a, b) => a.index - b.index);
            const nonOverlapping = [];
            let lastEnd = -1;
            for (const match of matches) {
                if (match.index >= lastEnd) {
                    nonOverlapping.push(match);
                    lastEnd = match.index + match.length;
                }
            }

            // Build parts array
            const parts = [];
            let lastIndex = 0;
            for (const match of nonOverlapping) {
                if (match.index > lastIndex) {
                    parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
                }
                parts.push({ type: 'cite', content: text.slice(match.index, match.index + match.length), citation: match.citation });
                lastIndex = match.index + match.length;
            }
            if (lastIndex < text.length) {
                parts.push({ type: 'text', content: text.slice(lastIndex) });
            }

            if (parts.length > 1) {
                nodesToReplace.push({ node, parts });
            }
        }

        nodesToReplace.forEach(({ node, parts }) => {
            const parent = node.parentNode;
            if (!parent) return;
            parts.forEach(part => {
                if (part.type === 'text') {
                    parent.insertBefore(document.createTextNode(part.content), node);
                } else {
                    const span = document.createElement('span');
                    span.className = 'law-linker-cite';
                    span.textContent = part.content;
                    span.dataset.citation = JSON.stringify(part.citation);
                    span.title = part.citation.displayLabel + ' — Click to view official source';
                    // Hover popup
                    span.addEventListener('mouseenter', () => showPopup(span, part.citation));
                    span.addEventListener('mouseleave', hidePopup);
                    // Click opens official source in new tab
                    span.addEventListener('click', (e) => {
                        e.preventDefault();
                        if (part.citation.officialUrl) {
                            window.open(part.citation.officialUrl, '_blank', 'noopener,noreferrer');
                        }
                    });
                    parent.insertBefore(span, node);
                }
            });
            parent.removeChild(node);
        });
    }

    // =========================================================================
    // Public API
    // =========================================================================
    window.LawLinker = {
        init: function(selector) {
            initStyles();
            let elements;
            if (selector) {
                elements = document.querySelectorAll(selector);
            } else {
                // Prefer explicitly-marked elements, fall back to main content
                elements = document.querySelectorAll('[data-law-linker]');
                if (elements.length === 0) {
                    elements = document.querySelectorAll('main, article, .law-summary, .law-card, .modal-section, .content, .document-body, .analysis-text');
                }
            }
            elements.forEach(el => processElement(el));
        },
        process: processElement,
        parseCitation: parseCitation
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => LawLinker.init());
    } else {
        LawLinker.init();
    }
})();
