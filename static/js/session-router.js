/**
 * Semptify Session Router
 * PRODUCTION-ENFORCED security routing
 * 
 * Uses SemptifyAuth as the ONLY source of truth for authentication.
 * NO localStorage fallbacks - cookie-based auth ONLY.
 * 
 * Usage: Include AFTER semptify-auth.js on pages:
 *   <script src="/static/js/semptify-auth.js"></script>
 *   <script src="/static/js/session-router.js"></script>
 */

const SemptifyRouter = {
    // Configuration
    config: {
        authPage: '/auth',
        homePage: '/',
        intakePage: '/static/document_intake.html',
        // Pages that REQUIRE authentication - NO EXCEPTIONS
        protectedPages: [
            '/static/briefcase.html',
            '/static/vault.html',
            '/static/timeline.html',
            '/static/calendar.html',
            '/static/eviction_answer.html',
            '/static/court_packet.html',
            '/static/document_intake.html',
            '/static/dashboard.html',
            '/static/letter_builder.html',
            '/static/counterclaim.html',
            '/static/home.html',
        ],
        // Pages that allow unauthenticated access
        publicPages: [
            '/auth',
            '/static/welcome.html',
            '/static/crisis_intake.html',
            '/static/help.html',
            '/static/privacy.html',
        ]
    },

    /**
     * Get user ID from SemptifyAuth - THE ONLY SOURCE OF TRUTH
     * @returns {string|null}
     */
    getUserId() {
        if (typeof SemptifyAuth !== 'undefined') {
            return SemptifyAuth.getUserId();
        }
        // Fallback cookie check if SemptifyAuth not loaded yet
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'semptify_uid' && value) {
                return decodeURIComponent(value);
            }
        }
        return null;
    },

    /**
     * Check if user is authenticated
     * @returns {boolean}
     */
    isAuthenticated() {
        return this.getUserId() !== null;
    },

    /**
     * Check if user has an active case
     */
    hasActiveCase() {
        return localStorage.getItem('semptify_active_case') !== null;
    },

    /**
     * Get current page path
     */
    getCurrentPage() {
        return window.location.pathname;
    },

    /**
     * Check if current page is protected
     */
    isProtectedPage() {
        const current = this.getCurrentPage();
        return this.config.protectedPages.some(page => 
            current === page || current.endsWith(page.split('/').pop())
        );
    },

    /**
     * Check if current page is public
     */
    isPublicPage() {
        const current = this.getCurrentPage();
        if (current === '/' || current === '/auth') return true;
        return this.config.publicPages.some(page => 
            current === page || current.includes(page)
        );
    },

    /**
     * ENFORCE authentication - redirect to /auth if not authenticated
     * This is the main security gate
     */
    enforceAuth() {
        const current = this.getCurrentPage();
        const isAuthenticated = this.isAuthenticated();

        console.log(`[Router] Page: ${current}, Authenticated: ${isAuthenticated}`);

        // Skip for public pages
        if (this.isPublicPage()) {
            console.log('[Router] Public page - no auth required');
            return true;
        }

        // ENFORCE: Protected pages REQUIRE authentication
        if (this.isProtectedPage() && !isAuthenticated) {
            console.warn('[Router] 🚨 UNAUTHORIZED ACCESS BLOCKED - Redirecting to /auth');
            
            // Save return URL for redirect after auth
            const returnUrl = window.location.pathname + window.location.search;
            sessionStorage.setItem('auth_return_url', returnUrl);
            
            // Hard redirect to auth - NO EXCEPTIONS
            window.location.replace('/auth');
            return false;
        }

        // Default behavior for other pages
        if (!isAuthenticated && !this.isPublicPage()) {
            console.warn('[Router] Unauthenticated on non-public page - enforcing auth');
            window.location.replace('/auth');
            return false;
        }

        return true;
    },

    /**
     * Show a helpful toast guiding the user
     */
    showGuidanceToast() {
        if (typeof window.showToast === 'function') {
            window.showToast(
                "Start by uploading your documents to build your case",
                'info',
                8000,
                {
                    title: "👋 Let's get started!",
                    action: {
                        text: "Upload Documents",
                        href: this.config.intakePage
                    }
                }
            );
        }
    },

    /**
     * Set active case
     */
    setActiveCase(caseId) {
        localStorage.setItem('semptify_active_case', caseId);
    },

    /**
     * Clear active case
     */
    clearActiveCase() {
        localStorage.removeItem('semptify_active_case');
    },

    /**
     * Get case progress (for progress indicators)
     */
    getCaseProgress() {
        const progress = {
            documents: parseInt(localStorage.getItem('semptify_doc_count') || '0'),
            timelineEvents: parseInt(localStorage.getItem('semptify_timeline_count') || '0'),
            hasAnswer: localStorage.getItem('semptify_has_answer') === 'true',
            hasCounterclaim: localStorage.getItem('semptify_has_counterclaim') === 'true',
            hasCourtPacket: localStorage.getItem('semptify_has_court_packet') === 'true',
        };

        let steps = 0;
        let completed = 0;

        steps++;
        if (progress.documents > 0) completed++;
        steps++;
        if (progress.timelineEvents >= 3) completed++;
        steps++;
        if (progress.hasAnswer) completed++;
        steps++;
        if (progress.hasCourtPacket) completed++;

        progress.percentage = Math.round((completed / steps) * 100);
        progress.currentStep = completed + 1;
        progress.totalSteps = steps;

        return progress;
    },

    /**
     * Update progress counters
     */
    updateProgress(key, value) {
        localStorage.setItem(`semptify_${key}`, value.toString());
    },

    /**
     * Initialize - AUTOMATICALLY ENFORCE AUTH on page load
     */
    init() {
        // ALWAYS enforce auth on initialization
        this.enforceAuth();
    }
};

// Expose globally
window.SemptifyRouter = SemptifyRouter;

// CRITICAL: Auto-enforce auth when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    SemptifyRouter.init();
});
