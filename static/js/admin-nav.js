/**
 * Shared Admin Navigation Component
 * Renders consistent admin navigation across all admin pages
 * 
 * Usage: Include this script and call renderAdminNav(containerId, currentPage)
 * 
 * @param {string} containerId - ID of element to render nav into
 * @param {string} currentPage - Current page identifier (e.g., 'dashboard', 'manual')
 */
function renderAdminNav(containerId, currentPage) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const navItems = [
    { id: 'dashboard', label: '🏠 Dashboard', href: '/admin/dashboard.html' },
    { id: 'function-browser', label: '⚙️ Functions', href: '/admin/function-browser.html' },
    { id: 'contract-browser', label: '📋 Contracts', href: '/admin/contract-browser.html' },
    { id: 'page-editor', label: '📝 Editor', href: '/admin/page-editor.html' },
    { id: 'review-checklist', label: '✅ Review', href: '/admin/review-checklist.html' },
    { id: 'manual', label: '📖 Manual', href: '/admin/manual.html' }
  ];

  const navHtml = `
    <nav class="admin-nav">
      ${navItems.map(item => `
        <a href="${item.href}" class="admin-nav__item ${item.id === currentPage ? 'admin-nav__item--active' : ''}">
          ${item.label}
        </a>
      `).join('')}
    </nav>
  `;

  container.innerHTML = navHtml;
}

/**
 * Auto-detect current page from URL and render nav
 * @param {string} containerId - ID of element to render nav into
 */
function renderAdminNavAuto(containerId) {
  const path = window.location.pathname;
  const pageMatch = path.match(/\/admin\/([^\/]+)\.html/);
  const currentPage = pageMatch ? pageMatch[1] : 'dashboard';
  renderAdminNav(containerId, currentPage);
}

// Auto-render if element with ID 'admin-nav-container' exists
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('admin-nav-container')) {
    renderAdminNavAuto('admin-nav-container');
  }
});
