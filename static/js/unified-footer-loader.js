/**
 * Unified Footer Loader - Semptify
 *
 * Injects the canonical footer from the server-rendered Jinja partial.
 * Pages that already load /static/css/ssot-design-system.css get the
 * styled footer markup directly. Pages without SSOT get a minimal fallback
 * stylesheet so the legal disclaimer and links remain visible.
 *
 * Last Updated: 2026-09-08
 */

(function () {
  'use strict';

  const FOOTER_ENDPOINT = '/components/footer';

  // Mirror of the footer section in /static/css/ssot-design-system.css,
  // injected only when SSOT styles are not already available.
  // Keep this fallback in sync with the canonical SSOT footer styles.
  const FALLBACK_CSS = `
    .unified-footer {
      background: linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-calm-dark) 100%);
      color: color-mix(in srgb, var(--color-white), transparent 10%);
      padding: 2rem 1.5rem 1.5rem;
      margin-top: auto;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .unified-footer a {
      color: color-mix(in srgb, var(--color-white), transparent 20%);
      text-decoration: none;
      transition: color 0.15s ease;
    }
    .unified-footer a:hover { color: var(--color-warning); }
    .footer-container { max-width: 1200px; margin: 0 auto; }
    .footer-disclaimer {
      background: color-mix(in srgb, var(--bg-card), transparent 90%);
      border: 1px solid color-mix(in srgb, var(--bg-card), transparent 80%);
      border-radius: 6px;
      padding: 1.25rem;
      margin-bottom: 2rem;
      text-align: center;
    }
    .footer-disclaimer-icon { font-size: 1.5rem; margin-bottom: 0.5rem; }
    .footer-disclaimer-title {
      font-weight: 700;
      font-size: 1.125rem;
      color: var(--color-warning);
      margin-bottom: 0.5rem;
    }
    .footer-disclaimer-text {
      font-size: 1rem;
      line-height: 1.6;
      max-width: 800px;
      margin: 0 auto;
      color: color-mix(in srgb, var(--color-white), transparent 10%);
    }
    .footer-nav {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
      font-size: 1rem;
    }
    .footer-nav a { padding: 0.25rem 0.5rem; }
    .footer-divider {
      height: 1px;
      background: color-mix(in srgb, var(--bg-card), transparent 80%);
      margin: 1.5rem auto;
      max-width: 600px;
    }
    .footer-bottom {
      text-align: center;
      font-size: 0.875rem;
      color: color-mix(in srgb, var(--color-white), transparent 30%);
    }
    .footer-copyright { margin-bottom: 0.5rem; }
    .footer-mandates { font-weight: 600; color: var(--color-warning); }
    .footer-help { margin-top: 0.75rem; font-size: 0.75rem; }
    .locale-selector { margin-top: 0.75rem; }
    .locale-selector label,
    .locale-selector select,
    .locale-selector button {
      font-size: 0.875rem;
      padding: 0.25rem;
    }
    @media (max-width: 640px) {
      .unified-footer { padding: 2rem 1rem 1.25rem; }
      .footer-nav { gap: 1rem; font-size: 0.875rem; }
      .footer-disclaimer-text { font-size: 0.875rem; }
    }
  `;

  function ssotFooterIsStyled() {
    try {
      for (const sheet of document.styleSheets) {
        const rules = sheet.cssRules || sheet.rules || [];
        for (const rule of rules) {
          if (rule.selectorText && /\.unified-footer/.test(rule.selectorText)) {
            return true;
          }
        }
      }
    } catch (e) {
      // Cross-origin or restricted stylesheets may throw.
    }
    return false;
  }

  function injectFallbackCss() {
    if (document.getElementById('unified-footer-fallback-css')) return;
    const style = document.createElement('style');
    style.id = 'unified-footer-fallback-css';
    style.textContent = FALLBACK_CSS;
    document.head.appendChild(style);
  }

  async function loadFooter() {
    try {
      const response = await fetch(FOOTER_ENDPOINT, {
        credentials: 'same-origin',
        cache: 'no-cache',
      });
      if (!response.ok) {
        throw new Error(`Footer endpoint returned ${response.status}`);
      }
      const html = await response.text();
      if (!html.trim()) {
        throw new Error('Footer endpoint returned empty markup');
      }

      // Remove any previously injected footer so only the canonical one appears.
      document.querySelectorAll('footer').forEach((footer) => footer.remove());

      const wrapper = document.createElement('div');
      wrapper.innerHTML = html.trim();
      const footer = wrapper.querySelector('footer');
      if (!footer) {
        throw new Error('Footer partial did not contain a <footer> element');
      }

      document.body.appendChild(footer);

      if (!ssotFooterIsStyled()) {
        injectFallbackCss();
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('Semptify unified footer failed to load:', err.message);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadFooter);
  } else {
    loadFooter();
  }
})();
