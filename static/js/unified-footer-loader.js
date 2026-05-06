/**
 * Unified Footer Loader - Semptify
 * 
 * This script automatically injects the standardized footer into any page.
 * Include this script on all static HTML pages for consistent footers.
 * 
 * Usage:
 *   <script src="/js/unified-footer-loader.js"></script>
 * 
 * The footer will be inserted at the end of <body>, replacing any existing footer.
 * 
 * Last Updated: 2026-05-06
 */

(function() {
  'use strict';

  // Footer configuration - Single Source of Truth
  const FOOTER_CONFIG = {
    year: '2024-2026',
    company: 'Semptify',
    hotline: '1-800-292-4150',
    links: [
      { text: 'Home', href: '/' },
      { text: 'Privacy', href: '/public/privacy.html' },
      { text: 'Terms', href: '/public/terms.html' },
      { text: 'Disclaimer', href: '/public/disclaimer.html' },
      { text: 'About', href: '/public/about.html' },
      { text: 'Contact', href: '/public/contact.html' },
      { text: 'Credits', href: '/public/credits.html' }
    ]
  };

  // Footer CSS styles
  const footerStyles = `
    .unified-footer {
      background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
      color: rgba(255, 255, 255, 0.9);
      padding: 2.5rem 1.5rem 1.5rem;
      margin-top: auto;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .unified-footer a {
      color: rgba(255, 255, 255, 0.8);
      text-decoration: none;
      transition: color 0.2s ease;
    }
    .unified-footer a:hover {
      color: #fbbf24;
    }
    .footer-container {
      max-width: 1200px;
      margin: 0 auto;
    }
    .footer-disclaimer {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 8px;
      padding: 1.25rem;
      margin-bottom: 2rem;
      text-align: center;
    }
    .footer-disclaimer-icon {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }
    .footer-disclaimer-title {
      font-weight: 700;
      font-size: 1.1rem;
      color: #fbbf24;
      margin-bottom: 0.5rem;
    }
    .footer-disclaimer-text {
      font-size: 0.95rem;
      line-height: 1.6;
      max-width: 800px;
      margin: 0 auto;
    }
    .footer-nav {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
      font-size: 0.95rem;
    }
    .footer-nav a {
      padding: 0.25rem 0.5rem;
    }
    .footer-divider {
      height: 1px;
      background: rgba(255, 255, 255, 0.2);
      margin: 1.5rem auto;
      max-width: 600px;
    }
    .footer-bottom {
      text-align: center;
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.7);
    }
    .footer-copyright {
      margin-bottom: 0.5rem;
    }
    .footer-mandates {
      font-weight: 600;
      color: #fbbf24;
    }
    .footer-help {
      margin-top: 0.75rem;
      font-size: 0.8rem;
    }
    .footer-hotline {
      display: inline-block;
      background: rgba(251, 191, 36, 0.15);
      border: 1px solid rgba(251, 191, 36, 0.3);
      border-radius: 6px;
      padding: 0.5rem 1rem;
      margin-top: 0.75rem;
      font-weight: 600;
      color: #fbbf24;
    }
    @media (max-width: 640px) {
      .unified-footer {
        padding: 2rem 1rem 1.25rem;
      }
      .footer-nav {
        gap: 1rem;
        font-size: 0.9rem;
      }
      .footer-disclaimer-text {
        font-size: 0.9rem;
      }
    }
  `;

  // Generate navigation links HTML
  function generateNavLinks() {
    return FOOTER_CONFIG.links.map(link => 
      `<a href="${link.href}">${link.text}</a>`
    ).join('');
  }

  // Generate footer HTML
  function generateFooter() {
    return `
      <style>${footerStyles}</style>
      <footer class="unified-footer" role="contentinfo" aria-label="Site footer">
        <div class="footer-container">
          <div class="footer-disclaimer">
            <div class="footer-disclaimer-icon">⚖️</div>
            <div class="footer-disclaimer-title">Not Legal Advice</div>
            <div class="footer-disclaimer-text">
              Semptify provides educational tools and document organization only. 
              We are not a law firm. Nothing on this site constitutes legal advice, 
              legal opinion, or attorney-client relationship. Always consult a 
              qualified attorney for your specific legal situation.
            </div>
          </div>
          <nav class="footer-nav" aria-label="Footer navigation">
            ${generateNavLinks()}
          </nav>
          <div class="footer-divider"></div>
          <div class="footer-bottom">
            <div class="footer-copyright">
              © ${FOOTER_CONFIG.year} ${FOOTER_CONFIG.company} — Free forever · No advertising · Privacy-first
            </div>
            <div class="footer-mandates">
              Built to protect tenant rights
            </div>
            <div class="footer-help">
              Need legal help? 
              <a href="tel:${FOOTER_CONFIG.hotline}" class="footer-hotline">
                MN Legal Aid: ${FOOTER_CONFIG.hotline}
              </a>
            </div>
          </div>
        </div>
      </footer>
    `;
  }

  // Inject footer into page
  function injectFooter() {
    // Remove any existing footer
    const existingFooters = document.querySelectorAll('footer');
    existingFooters.forEach(footer => footer.remove());

    // Insert new footer at end of body
    const footerHTML = generateFooter();
    document.body.insertAdjacentHTML('beforeend', footerHTML);
  }

  // Run when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectFooter);
  } else {
    injectFooter();
  }
})();
