/**
 * Semptify Site-Wide Header Component
 * Include this script on any page to add the standard header with navigation
 * Usage: <script src="/static/js/header.js"></script>
 */

(function() {
    // Header HTML template
    const headerHTML = `
    <header class="semptify-header">
        <div class="header-container">
            <a href="/static/welcome.html" class="header-logo">
                <img src="/static/logo.png" alt="Semptify">
            </a>
            <nav class="header-nav">
                <a href="/static/welcome.html">Home</a>
                <a href="/static/mission_control.html">Dashboard</a>
                <a href="/static/document_intake.html">Documents</a>
                <a href="/static/crisis_intake.html">Crisis Help</a>
            </nav>
        </div>
    </header>
    `;

    // Header CSS styles
    const headerCSS = `
    <style id="semptify-header-styles">
        .semptify-header {
            background: #fff;
            border-bottom: 1px solid #e5e5e5;
            padding: 1rem 1.5rem;
            position: sticky;
            top: 0;
            z-index: 1000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .header-container {
            max-width: 1000px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.75rem;
        }
        
        .header-logo {
            display: flex;
            align-items: center;
            text-decoration: none;
        }
        
        .header-logo img {
            height: 80px;
            width: auto;
            object-fit: contain;
        }
        
        .header-nav {
            display: flex;
            gap: 2rem;
            align-items: center;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .header-nav a {
            color: #1e3a5f;
            text-decoration: none;
            font-size: 0.95rem;
            font-weight: 500;
            padding: 0.5rem 0;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }
        
        .header-nav a:hover {
            color: #3B5998;
            border-bottom-color: #3B5998;
        }
        
        .header-nav a.active {
            color: #3B5998;
            border-bottom-color: #3B5998;
        }
        
        /* Mobile responsive */
        @media (max-width: 600px) {
            .header-container {
                gap: 0.5rem;
            }
            
            .header-logo img {
                height: 60px;
            }
            
            .header-nav {
                gap: 1rem;
            }
            
            .header-nav a {
                font-size: 0.85rem;
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
