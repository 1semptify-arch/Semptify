/**
 * Semptify Site-Wide Footer Component
 * Include this script on any page to add the standard footer
 * Usage: <script src="/static/js/footer.js"></script>
 */

(function() {
    // Footer HTML template
    const footerHTML = `
    <footer class="semptify-footer">
        <div class="footer-container">
            <div class="footer-main">
                <div class="footer-brand">
                    <span class="footer-tagline">Always Faithful to Tenants</span>
                </div>
                
                <div class="footer-links">
                    <div class="footer-column">
                        <h4>Legal</h4>
                        <a href="/static/privacy.html">Privacy Policy</a>
                        <a href="/static/law_library.html">Law Library</a>
                    </div>
                    <div class="footer-column">
                        <h4>Support</h4>
                        <a href="/static/help.html">Help Center</a>
                        <a href="/static/contacts.html">Contact</a>
                    </div>
                </div>
            </div>
            
            <div class="footer-bottom">
                <span>© 2025 Semptify. 100% Free - Donations Welcome.</span>
                <span class="footer-version">Version 5.0.0</span>
            </div>
        </div>
    </footer>
    `;

    // Footer CSS styles
    const footerCSS = `
    <style id="semptify-footer-styles">
        .semptify-footer {
            background: #1e3a5f;
            color: #fff;
            padding: 2rem 1.5rem 1rem;
            margin-top: auto;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .footer-container {
            max-width: 1000px;
            margin: 0 auto;
        }
        
        .footer-main {
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.15);
        }
        
        .footer-brand {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
        }
        
        .footer-logo {
            width: 60px;
            height: 60px;
            object-fit: contain;
        }
        
        .footer-tagline {
            font-size: 0.9rem;
            color: rgba(255,255,255,0.8);
            font-style: italic;
        }
        
        .footer-links {
            display: flex;
            gap: 3rem;
            flex-wrap: wrap;
        }
        
        .footer-column {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .footer-column h4 {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: rgba(255,255,255,0.6);
            margin: 0 0 0.5rem 0;
            font-weight: 600;
        }
        
        .footer-column a {
            color: #fff;
            text-decoration: none;
            font-size: 0.95rem;
            transition: color 0.2s;
        }
        
        .footer-column a:hover {
            color: #60a5fa;
        }
        
        .footer-bottom {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 1rem;
            font-size: 0.85rem;
            color: rgba(255,255,255,0.7);
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        
        .footer-version {
            background: rgba(255,255,255,0.1);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
        }
        
        /* Mobile responsive */
        @media (max-width: 600px) {
            .footer-main {
                flex-direction: column;
                align-items: center;
                text-align: center;
            }
            
            .footer-brand {
                align-items: center;
            }
            
            .footer-links {
                justify-content: center;
                gap: 2rem;
            }
            
            .footer-bottom {
                flex-direction: column;
                text-align: center;
            }
        }
    </style>
    `;

    // Insert footer when DOM is ready
    function insertFooter() {
        // Don't add if footer already exists
        if (document.querySelector('.semptify-footer')) return;
        
        // Add styles to head if not already present
        if (!document.getElementById('semptify-footer-styles')) {
            document.head.insertAdjacentHTML('beforeend', footerCSS);
        }
        
        // Add footer before closing body tag
        document.body.insertAdjacentHTML('beforeend', footerHTML);
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', insertFooter);
    } else {
        insertFooter();
    }
})();
