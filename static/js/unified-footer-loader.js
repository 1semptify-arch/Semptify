/**
 * Unified Footer Loader - Semptify
 *
 * Injects the standardized, minimal footer into any page.
 * Include this script on all static HTML pages for consistent footers.
 *
 * Last Updated: 2026-07-29
 */

(function() {
  'use strict';

  const FOOTER_CONFIG = {
    year: '2026',
    company: 'Semptify',
    upl: 'Semptify is an organizational tool, not a law firm.',
    uplCta: "We can't give legal advice. For legal advice, contact a licensed attorney or your local legal aid society.",
    getHelp: { text: 'Get help', href: '/help' },
    reportProblem: { text: 'Report a problem', href: '/public/feedback.html' }
  };

  const footerStyles = `
    .unified-footer {
      background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
      color: rgba(255, 255, 255, 0.9);
      padding: 1.5rem 1rem;
      margin-top: auto;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      text-align: center;
    }
    .unified-footer a {
      color: rgba(255, 255, 255, 0.9);
      text-decoration: none;
    }
    .unified-footer a:hover {
      text-decoration: underline;
    }
    .footer-container {
      max-width: 960px;
      margin: 0 auto;
    }
    .footer-disclaimer {
      font-size: 0.9rem;
      line-height: 1.5;
      margin-bottom: 0.75rem;
    }
    .footer-disclaimer strong {
      color: #fff;
    }
    .footer-actions {
      font-size: 0.9rem;
      margin-bottom: 0.75rem;
    }
    .footer-actions a {
      margin: 0 0.35rem;
    }
    .footer-bottom {
      font-size: 0.8rem;
      color: rgba(255, 255, 255, 0.7);
    }
    @media (max-width: 640px) {
      .unified-footer { padding: 1.25rem 0.75rem; }
      .footer-disclaimer { font-size: 0.85rem; }
    }
  `;

  function generateFooter() {
    return `
      <style>${footerStyles}</style>
      <footer class="unified-footer" role="contentinfo" aria-label="Site footer">
        <div class="footer-container">
          <p class="footer-disclaimer">
            <strong>${FOOTER_CONFIG.upl}</strong>
            ${FOOTER_CONFIG.uplCta}
          </p>
          <p class="footer-actions">
            <a href="${FOOTER_CONFIG.getHelp.href}">${FOOTER_CONFIG.getHelp.text}</a>
            ·
            <a href="${FOOTER_CONFIG.reportProblem.href}">${FOOTER_CONFIG.reportProblem.text}</a>
          </p>
          <p class="footer-bottom">
            &copy; ${FOOTER_CONFIG.year} ${FOOTER_CONFIG.company} — No cost, always · No advertising · Privacy-first
          </p>
        </div>
      </footer>
    `;
  }

  function injectFooter() {
    const existingFooters = document.querySelectorAll('footer');
    existingFooters.forEach(footer => footer.remove());
    document.body.insertAdjacentHTML('beforeend', generateFooter());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectFooter);
  } else {
    injectFooter();
  }
})();
