/**
 * Core Module JavaScript
 * Provides common utilities and initialization
 */

class CoreApp {
    constructor() {
        this.init();
    }

    init() {
        this.setupTheme();
        this.setupAccessibility();
        this.setupErrorHandling();
        console.log('Semptify Core initialized');
    }

    setupTheme() {
        const theme = localStorage.getItem('theme') || 'auto';
        document.documentElement.setAttribute('data-theme', theme);

        // Theme toggle functionality
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const currentTheme = document.documentElement.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
            });
        }
    }

    setupAccessibility() {
        // Focus management
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });

        // Skip links
        const skipLinks = document.querySelectorAll('.skip-link');
        skipLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    target.focus();
                    target.scrollIntoView();
                }
            });
        });
    }

    setupErrorHandling() {
        window.addEventListener('error', (e) => {
            console.error('JavaScript error:', e.error);
            // TODO: Send to logging service
        });

        window.addEventListener('unhandledrejection', (e) => {
            console.error('Unhandled promise rejection:', e.reason);
            // TODO: Send to logging service
        });
    }

    // Utility methods
    static showAlert(message, type = 'info', duration = 5000) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;

        const container = document.querySelector('.container') || document.body;
        container.insertBefore(alert, container.firstChild);

        if (duration > 0) {
            setTimeout(() => {
                alert.remove();
            }, duration);
        }

        return alert;
    }

    static formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }).format(new Date(date));
    }

    static formatFileSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.semptify = new CoreApp();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CoreApp;
}