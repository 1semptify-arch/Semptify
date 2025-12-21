/**
 * Semptify Session Router
 * Smart routing based on user session state
 * 
 * Routes users to appropriate pages based on:
 * - Whether they have a session (user_id cookie)
 * - Whether they have an active case
 * - Current page context
 * 
 * Usage: Include on pages that need routing logic:
 *   <script src="/static/js/session-router.js"></script>
 */

const SemptifyRouter = {
    // Configuration
    config: {
        welcomePage: '/static/welcome.html',
        homePage: '/static/home.html',
        intakePage: '/static/document_intake.html',
        dashboardPage: '/static/dashboard.html',
        // Pages that should redirect if not authenticated
        protectedPages: [
            '/static/briefcase.html',
            '/static/vault.html',
            '/static/timeline.html',
            '/static/calendar.html',
            '/static/eviction_answer.html',
            '/static/court_packet.html',
        ],
        // Pages where we don't auto-redirect
        publicPages: [
            '/static/welcome.html',
            '/static/crisis_intake.html',
            '/static/help.html',
            '/static/privacy.html',
            '/',
            '/static/index.html',
        ]
    },

    /**
     * Get user ID from cookie
     */
    getUserId() {
        const value = `; ${document.cookie}`;
        const parts = value.split('; semptify_user_id=');
        if (parts.length === 2) return parts.pop().split(';').shift();
        
        // Also check localStorage as fallback
        return localStorage.getItem('semptify_user_id');
    },

    /**
     * Check if user has an active case
     */
    hasActiveCase() {
        return localStorage.getItem('semptify_active_case') !== null;
    },

    /**
     * Check if user has completed onboarding
     */
    hasCompletedOnboarding() {
        return localStorage.getItem('semptify_onboarding_complete') === 'true';
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
        return this.config.protectedPages.some(page => current.includes(page));
    },

    /**
     * Check if current page is public
     */
    isPublicPage() {
        const current = this.getCurrentPage();
        return this.config.publicPages.some(page => current === page || current.includes(page));
    },

    /**
     * Determine the best page for the user
     */
    getBestPage() {
        const userId = this.getUserId();
        const hasCase = this.hasActiveCase();
        
        if (!userId) {
            // No session → Welcome
            return this.config.welcomePage;
        }
        
        if (!hasCase) {
            // Has session but no case → Intake
            return this.config.intakePage;
        }
        
        // Has session and case → Home/Dashboard
        return this.config.homePage;
    },

    /**
     * Smart route based on current state
     * Only redirects if necessary
     */
    route(options = {}) {
        const { force = false, showToast = true } = options;
        const current = this.getCurrentPage();
        const userId = this.getUserId();
        const bestPage = this.getBestPage();

        // Don't redirect on public pages unless forced
        if (this.isPublicPage() && !force) {
            return;
        }

        // Redirect from protected pages if not authenticated
        if (this.isProtectedPage() && !userId) {
            console.log('[Router] Protected page without auth, redirecting to welcome');
            window.location.href = this.config.welcomePage;
            return;
        }

        // On welcome page with active session → redirect to home
        if (current.includes('welcome.html') && userId && this.hasActiveCase()) {
            console.log('[Router] Returning user on welcome, redirecting to home');
            window.location.href = this.config.homePage;
            return;
        }

        // Show helpful toast if user is on wrong page
        if (showToast && userId && !this.hasActiveCase() && !current.includes('document_intake')) {
            this.showGuidanceToast();
        }
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
     * Mark onboarding as complete
     */
    completeOnboarding() {
        localStorage.setItem('semptify_onboarding_complete', 'true');
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

        // Calculate overall progress percentage
        let steps = 0;
        let completed = 0;

        // Step 1: Documents (need at least 1)
        steps++;
        if (progress.documents > 0) completed++;

        // Step 2: Timeline (need at least 3 events)
        steps++;
        if (progress.timelineEvents >= 3) completed++;

        // Step 3: Answer filed
        steps++;
        if (progress.hasAnswer) completed++;

        // Step 4: Court packet
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
     * Initialize - run on page load
     */
    init(options = {}) {
        // Don't auto-route by default, let pages opt-in
        if (options.autoRoute) {
            this.route(options);
        }
    }
};

// Expose globally
window.SemptifyRouter = SemptifyRouter;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Pages can call SemptifyRouter.route() explicitly if needed
    console.log('[Router] Ready. User:', SemptifyRouter.getUserId() ? 'authenticated' : 'guest');
});
