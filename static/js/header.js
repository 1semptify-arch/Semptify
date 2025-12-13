/**
 * Semptify Site-Wide Header Component
 * Include this script on any page to add the standard header with navigation
 * Usage: <script src="/static/js/header.js"></script>
 * 
 * NOTE: This header is DISABLED on pages using shared-nav.js
 * The shared nav component provides navigation for app pages.
 * This header is only for public/landing pages without the sidebar.
 */

(function() {
    // Skip if shared nav is present (app pages use sidebar navigation)
    if (document.getElementById('semptify-nav') || document.body.classList.contains('has-nav')) {
        console.log('Header skipped - using shared nav component');
        return;
    }

    // Header HTML template
    const headerHTML = `
    <header class="semptify-header">
        <div class="header-container">
            <a href="/static/welcome.html" class="header-logo">
                <img src="/static/logo.png" alt="Semptify">
            </a>
            <nav class="header-nav">
                <a href="/static/welcome.html">Home</a>
                <a href="/static/dashboard.html">Dashboard</a>
                <a href="/static/document_intake.html">Documents</a>
                <a href="/static/crisis_intake.html">Crisis Help</a>
            </nav>
        </div>
    </header>
    `;

    // Header CSS styles - dark theme to match app
    const headerCSS = `
    <style id="semptify-header-styles">
        .semptify-header {
            background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
            border-bottom: 1px solid #334155;
            padding: 1rem 1.5rem;
            position: sticky;
            top: 0;
            z-index: 1000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .header-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }
        
        .header-logo {
            display: flex;
            align-items: center;
            text-decoration: none;
        }
        
        .header-logo img {
            height: 50px;
            width: auto;
            object-fit: contain;
        }
        
        .header-nav {
            display: flex;
            gap: 1.5rem;
            align-items: center;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .header-nav a {
            color: #f1f5f9;
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            padding: 0.5rem 0.75rem;
            border-radius: 4px;
            transition: all 0.2s;
        }
        
        .header-nav a:hover {
            background: rgba(59, 130, 246, 0.2);
            color: #3b82f6;
        }
        
        .header-nav a.active {
            background: #3b82f6;
            color: white;
        }
        
        /* Mobile responsive */
        @media (max-width: 600px) {
            .header-container {
                flex-direction: column;
                gap: 0.75rem;
            }
            
            .header-logo img {
                height: 40px;
            }
            
            .header-nav {
                gap: 0.5rem;
            }
            
            .header-nav a {
                font-size: 0.8rem;
                padding: 0.375rem 0.5rem;
            }
        }
    </style>
    `;

    // Insert header when DOM is ready
    function insertHeader() {
        // Don't add if header already exists
        if (document.querySelector('.semptify-header')) return;
        
        // Add styles to head if not already present
        if (!document.getElementById('semptify-header-styles')) {
            document.head.insertAdjacentHTML('beforeend', headerCSS);
        }
        
        // Add header at the start of body
        document.body.insertAdjacentHTML('afterbegin', headerHTML);
        
        // Highlight current page in nav
        const currentPath = window.location.pathname;
        document.querySelectorAll('.header-nav a').forEach(link => {
            if (currentPath.includes(link.getAttribute('href').replace('/static/', ''))) {
                link.classList.add('active');
            }
        });
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', insertHeader);
    } else {
        insertHeader();
    }
})();
