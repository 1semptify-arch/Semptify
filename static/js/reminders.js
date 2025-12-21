/**
 * Semptify Documentation Reminders System
 * Philosophy: "Document Everything First" - Proactive prompts to keep users documenting consistently
 * 
 * Features:
 * - Monthly reminders for rent receipts (1st-5th of month)
 * - Mid-month reminders for maintenance issues (13th-17th)
 * - General documentation prompts after 30 days of inactivity
 * - Dismissable reminders that don't repeat same month
 * 
 * Architecture:
 * - Last document date fetched from user's CLOUD STORAGE via vault API
 * - NO localStorage for user data (Semptify zero-knowledge architecture)
 * - Session-only state for UI preferences (dismissals reset each session)
 * 
 * Usage: Include this script on any page:
 *   <script src="/static/js/reminders.js"></script>
 */

(function() {
    'use strict';
    
    // Session-only state (NOT localStorage - respects Semptify's zero-knowledge architecture)
    // These reset each browser session, which is appropriate for reminder UI state
    let reminderDismissedThisSession = false;
    let reminderShownThisSession = false;
    let cachedLastDocDate = null;
    
    /**
     * Get auth tokens from existing Semptify auth system
     */
    function getAuthHeaders() {
        // Uses window.semptify for auth state (set by auth system)
        const accessToken = window.semptify?.accessToken || window.semptify?.auth?.accessToken;
        const idToken = window.semptify?.idToken || window.semptify?.auth?.idToken;
        
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (accessToken) {
            headers['Authorization'] = `Bearer ${accessToken}`;
        }
        
        return { headers, accessToken };
    }
    
    /**
     * Fetch last document date from vault API (user's cloud storage)
     * Returns the upload date of the most recent document
     */
    async function fetchLastDocumentDate() {
        // Return cached value if already fetched this session
        if (cachedLastDocDate !== null) {
            return cachedLastDocDate;
        }
        
        const { accessToken } = getAuthHeaders();
        
        // Can't check without auth
        if (!accessToken) {
            return null;
        }
        
        try {
            const response = await fetch(`/api/vault/?access_token=${encodeURIComponent(accessToken)}`, {
                method: 'GET',
                credentials: 'include'
            });
            
            if (!response.ok) {
                console.debug('Reminders: Could not fetch vault documents');
                return null;
            }
            
            const data = await response.json();
            
            // Documents are sorted newest first by vault API
            if (data.documents && data.documents.length > 0) {
                cachedLastDocDate = data.documents[0].uploaded_at;
                return cachedLastDocDate;
            }
            
            // No documents yet
            cachedLastDocDate = 'none';
            return null;
        } catch (error) {
            console.debug('Reminders: Error fetching vault documents', error);
            return null;
        }
    }
    
    /**
     * Check if reminder should be shown
     * Async because it may need to fetch from vault API
     */
    async function shouldShowReminder() {
        // Don't show if already shown this session
        if (reminderShownThisSession) return false;
        
        // Don't show if dismissed this session
        if (reminderDismissedThisSession) return false;
        
        // Don't show on document intake page (they're already documenting!)
        if (window.location.pathname.includes('document_intake.html')) return false;
        
        // Don't show on welcome/onboarding pages
        if (window.location.pathname.includes('welcome') || 
            window.location.pathname.includes('onboarding') ||
            window.location.pathname.includes('storage_setup')) return false;
        
        // Need to be authenticated to check vault
        const { accessToken } = getAuthHeaders();
        if (!accessToken) return false;
        
        // Fetch last document date from user's cloud storage
        const lastDoc = await fetchLastDocumentDate();
        
        // Show if never documented
        if (!lastDoc) return true;
        
        // Show if >30 days since last document
        const now = new Date();
        const daysSince = (now - new Date(lastDoc)) / (1000 * 60 * 60 * 24);
        return daysSince > 30;
    }
    
    /**
     * Get contextual reminder message based on time of month
     */
    function getReminderMessage() {
        const day = new Date().getDate();
        
        if (day <= 5) {
            return {
                title: "🧾 Rent Receipt Time!",
                message: "It's the start of the month - save your rent receipt for your records.",
                cta: "Upload Receipt"
            };
        }
        
        if (day >= 13 && day <= 17) {
            return {
                title: "🔧 Maintenance Check",
                message: "Any maintenance issues to document? Photos help protect your rights.",
                cta: "Document Issue"
            };
        }
        
        // Default message
        return {
            title: "📄 Keep Documenting!",
            message: "Keep your case file growing - document something today.",
            cta: "Add Document"
        };
    }
    
    /**
     * Create and show reminder toast
     */
    async function showReminder() {
        const shouldShow = await shouldShowReminder();
        if (!shouldShow) return;
        
        const reminder = getReminderMessage();
        
        // Mark as shown this session
        reminderShownThisSession = true;
        
        // Use existing toast system if available
        if (window.showToast && typeof window.showToast === 'function') {
            window.showToast(reminder.message, 'info', 15000, {
                title: reminder.title,
                action: { 
                    text: reminder.cta, 
                    href: '/static/document_intake.html?source=reminder' 
                },
                onDismiss: dismissReminder
            });
            return;
        }
        
        // Fallback: Create our own toast UI
        createReminderToast(reminder);
    }
    
    /**
     * Fallback toast UI if notification-toast.js isn't available
     */
    function createReminderToast(reminder) {
        // Create toast container if needed
        let container = document.getElementById('reminder-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'reminder-toast-container';
            document.body.appendChild(container);
        }
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'reminder-toast';
        toast.innerHTML = `
            <div class="reminder-toast-icon">📋</div>
            <div class="reminder-toast-content">
                <div class="reminder-toast-title">${reminder.title}</div>
                <div class="reminder-toast-message">${reminder.message}</div>
                <div class="reminder-toast-actions">
                    <a href="/static/document_intake.html?source=reminder" class="reminder-toast-cta">${reminder.cta}</a>
                    <button class="reminder-toast-dismiss" onclick="window.dismissReminder()">Later</button>
                </div>
            </div>
            <button class="reminder-toast-close" onclick="this.parentElement.remove()">&times;</button>
        `;
        
        // Add styles if not present
        if (!document.getElementById('reminder-toast-styles')) {
            const styles = document.createElement('style');
            styles.id = 'reminder-toast-styles';
            styles.textContent = `
                #reminder-toast-container {
                    position: fixed;
                    bottom: 100px;
                    right: 24px;
                    z-index: 1001;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                .reminder-toast {
                    background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
                    color: white;
                    border-radius: 12px;
                    padding: 16px;
                    max-width: 320px;
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
                    display: flex;
                    gap: 12px;
                    align-items: flex-start;
                    animation: reminder-slide-in 0.3s ease;
                    border: 1px solid #334155;
                }
                @keyframes reminder-slide-in {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                .reminder-toast-icon {
                    font-size: 24px;
                    flex-shrink: 0;
                }
                .reminder-toast-content {
                    flex: 1;
                }
                .reminder-toast-title {
                    font-weight: 600;
                    font-size: 0.95rem;
                    margin-bottom: 4px;
                }
                .reminder-toast-message {
                    font-size: 0.85rem;
                    color: #cbd5e1;
                    margin-bottom: 12px;
                    line-height: 1.4;
                }
                .reminder-toast-actions {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                }
                .reminder-toast-cta {
                    background: #3B5998;
                    color: white;
                    padding: 8px 14px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-size: 0.85rem;
                    font-weight: 500;
                    transition: background 0.2s;
                }
                .reminder-toast-cta:hover {
                    background: #2d4a7c;
                    color: white;
                }
                .reminder-toast-dismiss {
                    background: transparent;
                    color: #94a3b8;
                    border: 1px solid #475569;
                    padding: 8px 14px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 0.85rem;
                    transition: all 0.2s;
                }
                .reminder-toast-dismiss:hover {
                    background: #1e293b;
                    color: white;
                }
                .reminder-toast-close {
                    background: none;
                    border: none;
                    color: #64748b;
                    font-size: 20px;
                    cursor: pointer;
                    padding: 0;
                    line-height: 1;
                    flex-shrink: 0;
                }
                .reminder-toast-close:hover {
                    color: white;
                }
                @media (max-width: 600px) {
                    #reminder-toast-container {
                        right: 16px;
                        left: 16px;
                        bottom: 80px;
                    }
                    .reminder-toast {
                        max-width: none;
                    }
                }
            `;
            document.head.appendChild(styles);
        }
        
        container.appendChild(toast);
        
        // Auto-dismiss after 20 seconds
        setTimeout(() => {
            toast.style.animation = 'reminder-slide-out 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 20000);
    }
    
    /**
     * Dismiss reminder for this session
     * No localStorage - just session memory (resets on page refresh/new session)
     */
    function dismissReminder() {
        reminderDismissedThisSession = true;
        
        // Remove toast if present
        const toast = document.querySelector('.reminder-toast');
        if (toast) {
            toast.style.animation = 'reminder-slide-out 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }
    }
    
    /**
     * Mark document as uploaded - invalidates cache so next check uses fresh data
     * Call this from document_intake.html on successful upload
     * The actual last document date is stored in user's CLOUD STORAGE
     */
    function markDocumentUploaded() {
        // Clear cache so next reminder check fetches fresh data from vault
        cachedLastDocDate = null;
        reminderDismissedThisSession = true;
        reminderShownThisSession = false;
    }
    
    /**
     * Get days since last document
     * Async - fetches from user's cloud storage
     * Returns null if not authenticated or no documents
     */
    async function getDaysSinceLastDocument() {
        const lastDoc = await fetchLastDocumentDate();
        if (!lastDoc) return null;
        
        const now = new Date();
        const lastDate = new Date(lastDoc);
        return Math.floor((now - lastDate) / (1000 * 60 * 60 * 24));
    }
    
    // Expose functions globally
    window.dismissReminder = dismissReminder;
    window.markDocumentUploaded = markDocumentUploaded;
    window.getDaysSinceLastDocument = getDaysSinceLastDocument;
    
    // Show reminder after page loads (with slight delay to avoid overwhelming user)
    // Also wait for auth to be ready
    async function init() {
        // Wait for potential auth initialization
        await new Promise(resolve => setTimeout(resolve, 3000));
        await showReminder();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
