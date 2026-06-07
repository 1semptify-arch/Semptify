/**
 * Law Linker - Hover popup for legal citations
 * Automatically detects law citations and shows full text on hover
 */

(function() {
    'use strict';

    const lawCache = new Map();
    let popup = null;

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
                <span>Source: revisor.mn.gov</span>
                <a href="#" class="law-linker-full" target="_blank">View Full Law →</a>
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
            }
            .law-linker-full:hover {
                color: #93c5fd;
            }
            .law-linker-loading {
                text-align: center;
                padding: 20px;
                color: #94a3b8;
            }
        `;
        document.head.appendChild(styles);
    }

    function parseCitation(text) {
        const mnMatch = text.match(/(?:Minn\.\s*Stat\.\s*§?\s*|§\s*)?\s*(504B\.\d+(?:\.\d+)?)/i);
        if (mnMatch) {
            return {
                type: 'minnesota',
                number: mnMatch[1],
                id: 'minn_stat_504b_' + mnMatch[1].replace(/\./g, '_')
            };
        }
        return null;
    }

    async function fetchLaw(citation) {
        const cacheKey = citation.id;
        if (lawCache.has(cacheKey)) {
            return lawCache.get(cacheKey);
        }
        try {
            const res = await fetch('/api/law-library/statutes/' + citation.id, {
                credentials: 'include'
            });
            if (!res.ok) throw new Error('Not found');
            const data = await res.json();
            lawCache.set(cacheKey, data);
            return data;
        } catch (e) {
            return null;
        }
    }

    function showPopup(element, citation) {
        if (!popup) popup = createPopup();
        
        const rect = element.getBoundingClientRect();
        popup.querySelector('.law-linker-citation').textContent = 'Minn. Stat. § ' + citation.number;
        popup.querySelector('.law-linker-type').textContent = 'MN Statute';
        popup.querySelector('.law-linker-content').innerHTML = '<div class="law-linker-loading">Loading...</div>';
        popup.querySelector('.law-linker-full').href = 'https://www.revisor.mn.gov/statutes/cite/' + citation.number;
        
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
        
        fetchLaw(citation).then(data => {
            if (!data || !data.statute) {
                popup.querySelector('.law-linker-content').innerHTML = '<p>Could not load law text.</p>';
                return;
            }
            const s = data.statute;
            const fullText = s.full_text.length > 800 ? s.full_text.substring(0, 800) + '...' : s.full_text;
            popup.querySelector('.law-linker-content').innerHTML = `
                <h4>${s.title}</h4>
                <p>${s.summary}</p>
                <div class="law-fulltext">${fullText}</div>
            `;
        });
    }

    function hidePopup() {
        if (popup) popup.classList.remove('visible');
    }

    function processElement(element) {
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
        const nodesToReplace = [];
        let node;
        
        while (node = walker.nextNode()) {
            const text = node.textContent;
            if (!text.match(/504B\.\d+/)) continue;
            if (node.parentElement.closest('.law-linker-cite, #law-linker-popup')) continue;
            
            const regex = /(?:Minn\.\s*Stat\.\s*§?\s*|§\s*)?(504B\.\d+(?:\.\d+)?)/gi;
            const parts = [];
            let lastIndex = 0;
            let match;
            
            while ((match = regex.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
                }
                const fullMatch = match[0];
                const cite = parseCitation(fullMatch);
                parts.push({ type: 'cite', content: fullMatch, citation: cite });
                lastIndex = match.index + fullMatch.length;
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
            parts.forEach(part => {
                if (part.type === 'text') {
                    parent.insertBefore(document.createTextNode(part.content), node);
                } else {
                    const span = document.createElement('span');
                    span.className = 'law-linker-cite';
                    span.textContent = part.content;
                    span.dataset.citation = JSON.stringify(part.citation);
                    span.addEventListener('mouseenter', () => showPopup(span, part.citation));
                    span.addEventListener('mouseleave', hidePopup);
                    parent.insertBefore(span, node);
                }
            });
            parent.removeChild(node);
        });
    }

    window.LawLinker = {
        init: function(selector) {
            initStyles();
            const elements = selector ? 
                document.querySelectorAll(selector) : 
                document.querySelectorAll('[data-law-linker]');
            elements.forEach(el => processElement(el));
        },
        process: processElement
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => LawLinker.init());
    } else {
        LawLinker.init();
    }
})();
