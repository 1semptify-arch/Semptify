/**
 * Semptify Authentication & User ID Module
 * Single source of truth for user authentication across ALL pages
 * 
 * Usage: Include in any page:
 *   <script src="/static/js/semptify-auth.js"></script>
 *   
 * Then use:
 *   await SemptifyAuth.ensureAuth();      // Redirects to /auth if not logged in
 *   const userId = SemptifyAuth.getUserId();
 *   const headers = SemptifyAuth.getHeaders();
 *   
 * IMPORTANT: This module ONLY uses the `semptify_uid` cookie set by the server.
 * We do NOT use localStorage user IDs or any other sources.
 */

const SemptifyAuth = {
    // The ONE cookie name we use - set by server during OAuth
    COOKIE_NAME: 'semptify_uid',
    
    // Cache the user ID to avoid repeated cookie parsing
    _cachedUserId: null,
    
    /**
     * Get user ID from the server-set cookie
     * @returns {string|null} User ID or null if not authenticated
     */
    getUserId() {
        if (this._cachedUserId) {
            return this._cachedUserId;
        }
        
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === this.COOKIE_NAME && value) {
                this._cachedUserId = decodeURIComponent(value);
                return this._cachedUserId;
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
     * Ensure user is authenticated - redirect to /auth if not
     * Call at the start of any protected page
     * @param {boolean} redirect - Whether to redirect to auth page (default: true)
     * @returns {boolean} True if authenticated
     */
    ensureAuth(redirect = true) {
        const userId = this.getUserId();
        
        if (!userId && redirect) {
            // Save current URL for redirect back after auth
            const returnUrl = window.location.pathname + window.location.search;
            if (returnUrl !== '/auth' && returnUrl !== '/') {
                sessionStorage.setItem('auth_return_url', returnUrl);
            }
            window.location.href = '/auth';
            return false;
        }
        
        return !!userId;
    },
    
    /**
     * Get headers to include in API requests
     * These headers help the server identify the user
     * @returns {Object} Headers object
     */
    getHeaders() {
        const userId = this.getUserId();
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (userId) {
            headers['X-User-ID'] = userId;
        }
        
        return headers;
    },
    
    /**
     * Make an authenticated fetch request
     * Automatically includes auth headers and handles 401s
     * @param {string} url - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>}
     */
    async fetch(url, options = {}) {
        const headers = {
            ...this.getHeaders(),
            ...options.headers
        };
        
        // Remove Content-Type for FormData (browser sets it automatically with boundary)
        if (options.body instanceof FormData) {
            delete headers['Content-Type'];
        }
        
        const response = await fetch(url, {
            ...options,
            headers,
            credentials: 'include'  // Always include cookies
        });
        
        // Handle authentication errors
        if (response.status === 401) {
            console.warn('[SemptifyAuth] Received 401 - session may be expired');
            this._cachedUserId = null;  // Clear cache
            
            // Optionally redirect to auth
            if (options.redirectOn401 !== false) {
                this.ensureAuth();
            }
        }
        
        return response;
    },
    
    /**
     * Make an authenticated JSON fetch request
     * @param {string} url - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} Parsed JSON response
     */
    async fetchJSON(url, options = {}) {
        const response = await this.fetch(url, options);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(error.message || error.error || `Request failed: ${response.status}`);
        }
        
        return response.json();
    },
    
    /**
     * Logout the user
     * @param {string} redirectTo - URL to redirect to after logout (default: '/auth')
     */
    async logout(redirectTo = '/auth') {
        try {
            await fetch('/api/auth/logout', { 
                method: 'POST',
                credentials: 'include'
            });
        } catch (e) {
            console.error('[SemptifyAuth] Logout request failed:', e);
        }
        
        // Clear cached user ID
        this._cachedUserId = null;
        
        // Clear any localStorage user data (legacy cleanup)
        localStorage.removeItem('semptify_user_id');
        localStorage.removeItem('user_id');
        
        // Redirect
        window.location.href = redirectTo;
    },
    
    /**
     * Get user info from the API
     * @returns {Promise<Object|null>} User info or null
     */
    async getUserInfo() {
        try {
            const response = await this.fetch('/api/auth/user');
            if (response.ok) {
                return await response.json();
            }
        } catch (e) {
            console.error('[SemptifyAuth] Failed to get user info:', e);
        }
        return null;
    },
    
    /**
     * Initialize auth state on page load
     * Call this once when the page loads
     */
    init() {
        // Check if we have a stored return URL from auth redirect
        const returnUrl = sessionStorage.getItem('auth_return_url');
        if (returnUrl && this.isAuthenticated()) {
            sessionStorage.removeItem('auth_return_url');
            // Only redirect if we're not already there
            if (window.location.pathname + window.location.search !== returnUrl) {
                window.location.href = returnUrl;
            }
        }
        
        // Log auth state in dev
        if (window.location.hostname === 'localhost') {
            console.log('[SemptifyAuth] User ID:', this.getUserId() || 'Not authenticated');
        }
    }
};

// Auto-initialize when script loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => SemptifyAuth.init());
} else {
    SemptifyAuth.init();
}

// Make available globally
window.SemptifyAuth = SemptifyAuth;
