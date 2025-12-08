/**
 * Law Linker - Automatically links statute references to the law library
 * Provides clickable links with modals showing full law details
 * Auto-initializes when DOM is ready
 */
class LawLinker {
    constructor() {
        // Comprehensive patterns for statute citations
        this.PATTERNS = {
            // Federal statutes: 42 U.S.C. § 3601, 29 USC 794
            usc: /(\d+)\s*U\.?S\.?C\.?\s*§?\s*(\d+[\w-]*)/gi,
            
            // Code of Federal Regulations: 24 CFR 100.201, 28 C.F.R. § 35.130
            cfr: /(\d+)\s*C\.?F\.?R\.?\s*§?\s*([\d.]+)/gi,
            
            // Minnesota Statutes: Minn. Stat. § 504B.211, M.S. 504B.001
            minn_stat: /(?:Minn\.?\s*Stat\.?|M\.S\.)\s*§?\s*([\d]+[A-Z]?\.[\d]+)/gi,
            
            // Minnesota Rules: Minn. R. 4900.3500
            minn_rule: /Minn\.?\s*R\.?\s*§?\s*([\d.]+)/gi,
            
            // Minnesota Statutes Annotated: MSA § 504B.211
            msa: /MSA\s*§?\s*([\d]+[A-Z]?\.[\d]+)/gi,
            
            // Generic "MN Stat" reference
            mn_stat: /MN\s*Stat\.?\s*§?\s*([\d]+[A-Z]?\.[\d]+)/gi,
            
            // Minneapolis Ordinances: Minneapolis Code § 244.2020, Mpls. Ord. 244
            mpls_ord: /(?:Minneapolis\s*(?:Code|Ord(?:inance)?)|Mpls\.?\s*(?:Code|Ord(?:inance)?))\s*§?\s*([\d.]+)/gi,
            
            // St. Paul Ordinances
            stpaul_ord: /(?:St\.?\s*Paul\s*(?:Code|Ord(?:inance)?))\s*§?\s*([\d.]+)/gi,
            
            // Internal Revenue Code: IRC § 280A, I.R.C. 1031
            irc: /(?:IRC|I\.R\.C\.)\s*§?\s*(\d+[A-Z]?)/gi,
            
            // Public Laws: Pub. L. 90-284
            pub_law: /Pub\.?\s*L\.?\s*([\d-]+)/gi,
            
            // Fair Housing Act references
            fha: /Fair\s+Housing\s+Act/gi,
            
            // Americans with Disabilities Act
            ada: /Americans?\s+with\s+Disabilities\s+Act|ADA\s+Title\s+[IVX]+/gi,
            
            // Section references
            section: /Section\s+(\d+)/gi
        };
        
        // Map citations to law library IDs
        this.LAW_DATABASE = {
            // Federal Housing - 42 USC
            '42_3601': 'fha_title_viii',
            '42_3604': 'fha_amendments_1988',
            '42_3617': 'fha_title_viii',
            '42_3619': 'fha_title_viii',
            
            // Section 504 - 29 USC
            '29_794': 'section_504_rehab',
            
            // VAWA - 34 USC
            '34_12491': 'vawa_housing',
            
            // CFPB/Debt Collection - 15 USC
            '15_1692': 'cfpb_debt_collection',
            '15_1681': 'fcra_tenant_screening',
            '15_1601': 'tila',
            '15_1701': 'interstate_land_sales',
            
            // Civil Rights - 42 USC
            '42_2000d': 'title_vi_civil_rights',
            
            // ADA - 42 USC
            '42_12101': 'ada_title_ii',
            '42_12131': 'ada_title_ii',
            '42_12165': 'ada_title_ii',
            '42_12181': 'ada_title_iii',
            '42_12189': 'ada_title_iii',
            
            // Lead Paint - 42 USC
            '42_4852': 'lead_paint_disclosure',
            '42_4852d': 'lead_paint_disclosure',
            
            // CFR
            '24_100': 'fha_title_viii',
            '24_982': 'fha_title_viii',
            '28_35': 'ada_title_ii',
            '28_36': 'ada_title_iii',
            
            // RESPA/Dodd-Frank - 12 USC
            '12_2601': 'respa',
            '12_5481': 'dodd_frank_mortgage',
            
            // Tax - 26 USC / IRC
            '26_280A': 'irc_280a',
            '280A': 'irc_280a',
            '26_121': 'irc_121',
            '121': 'irc_121',
            '26_1031': 'irc_1031',
            '1031': 'irc_1031',
            '26_469': 'irc_469',
            '469': 'irc_469',
            '26_199A': 'irc_199a',
            '199A': 'irc_199a',
            '26_7701': 'llc_federal',
            '26_3401': 'employer_requirements',
            
            // OSHA/FLSA - 29 USC
            '29_651': 'osha_workplace',
            '29_201': 'flsa',
            
            // Minnesota Statutes
            '504B': 'minn_stat_504b',
            '504B.001': 'minn_stat_504b',
            '504B.161': 'minn_stat_504b_211',
            '504B.178': 'minn_stat_504b',
            '504B.181': 'minn_stat_504b',
            '504B.185': 'minn_stat_504b',
            '504B.195': 'minn_stat_504b',
            '504B.211': 'minn_stat_504b_211',
            '504B.285': 'minn_stat_504b_285',
            '504B.321': 'minn_stat_504b_321',
            '504B.375': 'minn_stat_504b_375',
            '504B.441': 'minn_stat_504b',
            
            // Minnesota Real Estate
            '559.21': 'mn_vendor_purchaser_act',
            '513.52': 'mn_disclosure',
            '513.55': 'mn_disclosure',
            '513.60': 'mn_disclosure',
            '507.34': 'mn_recording_act',
            '580': 'mn_foreclosure',
            '580.01': 'mn_foreclosure',
            '82': 'mn_real_estate_license',
            '82.81': 'mn_real_estate_license',
            '510': 'mn_homestead',
            '510.01': 'mn_homestead',
            
            // Minnesota Tax
            '273.13': 'mn_property_tax',
            '290A': 'mn_renters_credit',
            '290A.19': 'mn_landlord_reporting',
            
            // Minnesota Business
            '322C': 'mn_llc',
            '177.24': 'mn_minimum_wage',
            '176': 'mn_workers_comp',
            '333': 'mn_business_registration',
            '13': 'mn_data_practices',
            
            // Minneapolis
            '244': 'mpls_rental_license',
            '244.2020': 'mpls_rental_license',
            '248': 'mpls_truth_in_housing',
            '259': 'mpls_business_license',
            
            // St. Paul
            '193A': 'stp_rent_stabilization',
            '193A.04': 'stp_rent_stabilization'
        };
        
        this.init();
    }
    
    init() {
        // Add CSS styles
        this.addStyles();
        
        // Create modal
        this.createModal();
        
        // Process existing content after a small delay
        setTimeout(() => {
            this.enhanceAllText();
        }, 500);
        
        // Watch for new content
        this.observeDOM();
        
        console.log('📚 Law Linker initialized');
    }
    
    addStyles() {
        if (document.getElementById('law-linker-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'law-linker-styles';
        style.textContent = `
            .law-link {
                color: var(--primary, #3b82f6);
                text-decoration: underline;
                text-decoration-style: dotted;
                cursor: pointer;
                position: relative;
                transition: all 0.2s ease;
            }
            
            .law-link:hover {
                color: var(--primary-hover, #2563eb);
                text-decoration-style: solid;
                background: rgba(59, 130, 246, 0.1);
                border-radius: 3px;
                padding: 0 2px;
                margin: 0 -2px;
            }
            
            /* Law detail modal */
            .law-modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                z-index: 10001;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            }
            
            .law-modal-overlay.active {
                opacity: 1;
                visibility: visible;
            }
            
            .law-modal {
                background: linear-gradient(135deg, #0f172a, #1e293b);
                border-radius: 16px;
                max-width: 700px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
                padding: 24px;
                color: white;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                transform: scale(0.9);
                transition: transform 0.3s ease;
            }
            
            .law-modal-overlay.active .law-modal {
                transform: scale(1);
            }
            
            .law-modal-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 16px;
                padding-bottom: 16px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .law-modal-title {
                font-size: 20px;
                font-weight: 600;
                color: #60a5fa;
                margin: 0;
            }
            
            .law-modal-citation {
                font-family: 'Courier New', monospace;
                background: rgba(255, 255, 255, 0.1);
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 14px;
                margin-top: 8px;
                display: inline-block;
            }
            
            .law-modal-close {
                width: 36px;
                height: 36px;
                border: none;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                border-radius: 50%;
                cursor: pointer;
                font-size: 18px;
                flex-shrink: 0;
            }
            
            .law-modal-close:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            
            .law-modal-body {
                line-height: 1.7;
            }
            
            .law-modal-section {
                margin-bottom: 16px;
            }
            
            .law-modal-section h4 {
                font-size: 14px;
                color: #94a3b8;
                margin: 0 0 8px 0;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .law-modal-section p {
                margin: 0;
            }
            
            .law-modal-section ul {
                margin: 0;
                padding-left: 20px;
            }
            
            .law-modal-section li {
                margin-bottom: 4px;
            }
            
            .law-modal-category {
                display: inline-block;
                padding: 4px 12px;
                background: rgba(59, 130, 246, 0.2);
                color: #60a5fa;
                border-radius: 20px;
                font-size: 12px;
                margin-right: 8px;
            }
            
            .law-modal-url {
                display: inline-block;
                padding: 10px 20px;
                background: #3b82f6;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 500;
                margin-top: 16px;
            }
            
            .law-modal-url:hover {
                background: #2563eb;
            }
            
            .law-modal-loading {
                text-align: center;
                padding: 40px;
                color: #94a3b8;
            }
            
            .law-modal-error {
                text-align: center;
                padding: 40px;
                color: #ef4444;
            }
            
            /* Full text section */
            .law-full-text-section .law-full-text {
                display: none;
                margin-top: 12px;
                padding: 16px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                font-family: 'Georgia', serif;
                font-size: 14px;
                line-height: 1.8;
                max-height: 400px;
                overflow-y: auto;
                white-space: pre-wrap;
            }
            
            .law-full-text-section.expanded .law-full-text {
                display: block;
            }
            
            .toggle-full-text {
                margin-left: 10px;
                padding: 4px 12px;
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.3);
                color: #60a5fa;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }
            
            .toggle-full-text:hover {
                background: rgba(59, 130, 246, 0.3);
            }
            
            /* Source links */
            .law-source-links {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }
            
            .law-source-link {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 8px 14px;
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                color: #10b981;
                text-decoration: none;
                border-radius: 6px;
                font-size: 13px;
                transition: all 0.2s;
            }
            
            .law-source-link:hover {
                background: rgba(16, 185, 129, 0.2);
                transform: translateY(-1px);
            }
            
            .law-source-link.primary {
                background: rgba(59, 130, 246, 0.2);
                border-color: rgba(59, 130, 246, 0.3);
                color: #60a5fa;
            }
        `;
        document.head.appendChild(style);
    }
    
    createModal() {
        if (document.getElementById('lawModalOverlay')) return;
        
        const overlay = document.createElement('div');
        overlay.className = 'law-modal-overlay';
        overlay.id = 'lawModalOverlay';
        overlay.innerHTML = `
            <div class="law-modal" id="lawModal">
                <div class="law-modal-header">
                    <div>
                        <h3 class="law-modal-title" id="lawModalTitle">Law Title</h3>
                        <div class="law-modal-citation" id="lawModalCitation">Citation</div>
                    </div>
                    <button class="law-modal-close" onclick="window.lawLinker.closeModal()">×</button>
                </div>
                <div class="law-modal-body" id="lawModalBody">
                    <div class="law-modal-loading">Loading law details...</div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        
        // Close on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.closeModal();
            }
        });
        
        // Close on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }
    
    closeModal() {
        const overlay = document.getElementById('lawModalOverlay');
        if (overlay) overlay.classList.remove('active');
    }
    
    showModal(lawId) {
        const overlay = document.getElementById('lawModalOverlay');
        const title = document.getElementById('lawModalTitle');
        const citation = document.getElementById('lawModalCitation');
        const body = document.getElementById('lawModalBody');
        
        // Show loading state
        title.textContent = 'Loading...';
        citation.textContent = '';
        body.innerHTML = '<div class="law-modal-loading">Loading law details...</div>';
        overlay.classList.add('active');
        
        // Fetch full law details
        fetch(`/api/law-library/statutes/${lawId}`)
            .then(r => {
                if (!r.ok) throw new Error('Law not found');
                return r.json();
            })
            .then(law => {
                title.textContent = law.title;
                citation.textContent = law.citation;
                
                let bodyHtml = `
                    <div class="law-modal-section">
                        <h4>Category</h4>
                        <span class="law-modal-category">${law.category}</span>
                        ${law.subcategory ? `<span class="law-modal-category">${law.subcategory}</span>` : ''}
                    </div>
                    <div class="law-modal-section">
                        <h4>Summary</h4>
                        <p>${law.summary}</p>
                    </div>
                `;
                
                if (law.key_points && law.key_points.length > 0) {
                    bodyHtml += `
                        <div class="law-modal-section">
                            <h4>Key Points</h4>
                            <ul>${law.key_points.map(p => `<li>${p}</li>`).join('')}</ul>
                        </div>
                    `;
                }
                
                if (law.full_text) {
                    bodyHtml += `
                        <div class="law-modal-section law-full-text-section">
                            <h4>Full Text <button class="toggle-full-text" onclick="this.parentElement.parentElement.classList.toggle('expanded')">Show/Hide</button></h4>
                            <div class="law-full-text">${law.full_text.replace(/\n/g, '<br>')}</div>
                        </div>
                    `;
                }
                
                if (law.tenant_protections) {
                    bodyHtml += `
                        <div class="law-modal-section">
                            <h4>Tenant Protections</h4>
                            <p>${law.tenant_protections}</p>
                        </div>
                    `;
                }
                
                if (law.landlord_obligations) {
                    bodyHtml += `
                        <div class="law-modal-section">
                            <h4>Landlord Obligations</h4>
                            <p>${law.landlord_obligations}</p>
                        </div>
                    `;
                }
                
                // Add official source links based on citation type
                bodyHtml += `<div class="law-modal-section"><h4>Official Sources</h4><div class="law-source-links">`;
                bodyHtml += this.getOfficialSourceLinks(law.citation, law.id);
                bodyHtml += `</div></div>`;
                
                if (law.url) {
                    bodyHtml += `<a href="${law.url}" target="_blank" class="law-modal-url">📖 View Source Document</a>`;
                }
                
                body.innerHTML = bodyHtml;
            })
            .catch(err => {
                body.innerHTML = `<div class="law-modal-error">❌ Could not load law details<br><small>${err.message}</small></div>`;
            });
    }
    
    enhanceText(element) {
        if (!element || !element.innerHTML) return;
        
        // Skip if already processed or is a script/style/input
        if (element.dataset.lawLinked) return;
        const skipTags = ['SCRIPT', 'STYLE', 'INPUT', 'TEXTAREA', 'CODE', 'PRE', 'A', 'BUTTON'];
        if (skipTags.includes(element.tagName)) return;
        
        // Skip if inside a law-link already
        if (element.closest('.law-link')) return;
        
        let html = element.innerHTML;
        let modified = false;
        
        // Process each pattern
        for (const [patternName, pattern] of Object.entries(this.PATTERNS)) {
            // Reset regex lastIndex
            pattern.lastIndex = 0;
            
            html = html.replace(pattern, (match, ...args) => {
                // Don't re-wrap existing law links
                if (match.includes('class="law-link"')) return match;
                if (match.includes('data-law')) return match;
                
                const lawId = this.getLawId(patternName, args);
                modified = true;
                
                if (lawId) {
                    return `<span class="law-link" data-law-id="${lawId}" onclick="window.lawLinker.showModal('${lawId}')">${match}</span>`;
                } else {
                    return `<span class="law-link" data-citation="${encodeURIComponent(match)}" onclick="window.lawLinker.searchLaw('${encodeURIComponent(match)}')">${match}</span>`;
                }
            });
        }
        
        if (modified) {
            element.innerHTML = html;
            element.dataset.lawLinked = 'true';
        }
    }
    
    getLawId(patternName, matches) {
        // Extract the key based on pattern type
        let key = '';
        
        switch (patternName) {
            case 'usc':
                key = `${matches[0]}_${matches[1]}`;
                break;
            case 'cfr':
                key = `${matches[0]}_${matches[1].split('.')[0]}`;
                break;
            case 'minn_stat':
            case 'msa':
            case 'mn_stat':
                key = matches[0];
                break;
            case 'minn_rule':
                key = matches[0];
                break;
            case 'irc':
                key = matches[0];
                break;
            case 'mpls_ord':
                key = matches[0].split('.')[0];
                break;
            case 'stpaul_ord':
                key = matches[0].split('.')[0];
                break;
            case 'fha':
                return 'fair_housing_act';
            case 'ada':
                return 'ada_title_ii';
            case 'section':
                // Try to match common section numbers
                if (matches[0] === '8') return 'section_8_voucher';
                if (matches[0] === '504') return 'section_504';
                return null;
        }
        
        return this.LAW_DATABASE[key] || null;
    }
    
    searchLaw(citation) {
        // Open law library with search
        window.open(`/law-library?search=${citation}`, '_blank');
    }
    
    enhanceAllText() {
        // Process common content containers
        const selectors = [
            '.card-content', '.content', '.text', '.description', '.summary',
            'p', 'li', 'td', '.message', '.body', '.detail', 'article',
            '.alert', '.notification', '.info', '.librarian-response',
            '.document-content', '.timeline-item', '.case-content',
            '.statute-card', '.law-card', '.defense-description'
        ];
        
        selectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                this.enhanceText(el);
            });
        });
    }
    
    observeDOM() {
        // Watch for dynamically added content
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) { // Element node
                        // Delay slightly to let content render
                        setTimeout(() => {
                            this.enhanceText(node);
                            // Also process children
                            if (node.querySelectorAll) {
                                node.querySelectorAll('p, li, td, div, span, .description, .summary').forEach(el => {
                                    this.enhanceText(el);
                                });
                            }
                        }, 100);
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    // Public method to manually refresh links
    refresh() {
        // Remove existing law-linked markers so content can be re-processed
        document.querySelectorAll('[data-law-linked]').forEach(el => {
            delete el.dataset.lawLinked;
        });
        this.enhanceAllText();
    }
    
    // Generate official source links based on citation
    getOfficialSourceLinks(citation, lawId) {
        let links = [];
        
        // Minnesota Statutes
        if (citation.includes('Minn. Stat.') || citation.includes('M.S.') || lawId.startsWith('minn_stat')) {
            const match = citation.match(/(\d+[A-Z]?)\.(\d+)/);
            if (match) {
                const chapter = match[1];
                const section = match[2];
                links.push({
                    url: `https://www.revisor.mn.gov/statutes/cite/${chapter}.${section}`,
                    label: 'MN Revisor (Official)',
                    icon: '📜',
                    primary: true
                });
                links.push({
                    url: `https://www.lawserver.com/law/state/minnesota/mn-statutes/minnesota_statutes_${chapter}-${section}`,
                    label: 'LawServer',
                    icon: '📖'
                });
            }
        }
        
        // Federal USC
        if (citation.includes('U.S.C.') || citation.includes('USC')) {
            const match = citation.match(/(\d+)\s*U\.?S\.?C\.?\s*§?\s*(\d+)/);
            if (match) {
                const title = match[1];
                const section = match[2];
                links.push({
                    url: `https://www.law.cornell.edu/uscode/text/${title}/${section}`,
                    label: 'Cornell Law (Official)',
                    icon: '⚖️',
                    primary: true
                });
                links.push({
                    url: `https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title${title}-section${section}`,
                    label: 'US House (Official)',
                    icon: '🏛️'
                });
            }
        }
        
        // Code of Federal Regulations
        if (citation.includes('C.F.R.') || citation.includes('CFR')) {
            const match = citation.match(/(\d+)\s*C\.?F\.?R\.?\s*§?\s*([\d.]+)/);
            if (match) {
                const title = match[1];
                const part = match[2].split('.')[0];
                links.push({
                    url: `https://www.ecfr.gov/current/title-${title}/part-${part}`,
                    label: 'eCFR (Official)',
                    icon: '📋',
                    primary: true
                });
            }
        }
        
        // Internal Revenue Code
        if (citation.includes('I.R.C.') || citation.includes('IRC') || citation.includes('26 U.S.C.')) {
            const match = citation.match(/§?\s*(\d+[A-Z]?)/);
            if (match) {
                const section = match[1];
                links.push({
                    url: `https://www.law.cornell.edu/uscode/text/26/${section}`,
                    label: 'Cornell Law (Official)',
                    icon: '⚖️',
                    primary: true
                });
                links.push({
                    url: `https://www.irs.gov/search?search_api_fulltext=${section}`,
                    label: 'IRS Search',
                    icon: '💵'
                });
            }
        }
        
        // Minneapolis Code
        if (citation.includes('Minneapolis') || lawId.startsWith('mpls')) {
            links.push({
                url: 'https://library.municode.com/mn/minneapolis/codes/code_of_ordinances',
                label: 'Minneapolis Code (Official)',
                icon: '🏙️',
                primary: true
            });
        }
        
        // St. Paul Code
        if (citation.includes('St. Paul') || lawId.startsWith('stp')) {
            links.push({
                url: 'https://library.municode.com/mn/st._paul/codes/code_of_ordinances',
                label: 'St. Paul Code (Official)',
                icon: '🏙️',
                primary: true
            });
        }
        
        // Hennepin County
        if (citation.includes('Hennepin') || lawId.includes('hennepin')) {
            links.push({
                url: 'https://www.hennepin.us/your-government/ordinances-and-policies',
                label: 'Hennepin County',
                icon: '🏛️',
                primary: true
            });
        }
        
        // Add generic legal research links
        links.push({
            url: `https://www.google.com/search?q=${encodeURIComponent(citation + ' full text')}`,
            label: 'Google Search',
            icon: '🔍'
        });
        
        // Build HTML
        return links.map(link => 
            `<a href="${link.url}" target="_blank" class="law-source-link ${link.primary ? 'primary' : ''}">${link.icon} ${link.label}</a>`
        ).join('');
    }
}

// Auto-initialize when script loads if DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.lawLinker = new LawLinker();
    });
} else {
    window.lawLinker = new LawLinker();
}
