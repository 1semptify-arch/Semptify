/**
 * Semptify Notification Toast System
 * ===================================
 * 
 * A beautiful, accessible notification system with emotional awareness.
 * Integrates with the 7-Dimensional Emotion Engine for adaptive messaging.
 * 
 * Usage:
 *   SemptifyToast.success('Document uploaded!');
 *   SemptifyToast.info('Processing your file...');
 *   SemptifyToast.warning('Court date in 3 days!');
 *   SemptifyToast.error('Upload failed');
 *   SemptifyToast.milestone('Evidence Gathered', 'You completed a key milestone!');
 */

const SemptifyToast = {
    // Configuration
    config: {
        position: 'top-right',  // top-right, top-left, bottom-right, bottom-left, top-center, bottom-center
        duration: 5000,         // Default duration in ms
        maxVisible: 5,          // Max toasts visible at once
        pauseOnHover: true,     // Pause timer on hover
        showProgress: true,     // Show progress bar
        enableSounds: false,    // Play notification sounds
        enableHaptics: true,    // Enable haptic feedback on mobile
    },

    // Toast container
    container: null,
    
    // Active toasts
    activeToasts: [],

    // Toast counter for unique IDs
    counter: 0,

    /**
     * Initialize the toast system
     */
    init(options = {}) {
        // Merge options
        Object.assign(this.config, options);

        // Create container if it doesn't exist
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'semptify-toast-container';
            this.container.className = `toast-container toast-${this.config.position}`;
            document.body.appendChild(this.container);
        }

        // Add styles
        this.injectStyles();

        console.log('🔔 SemptifyToast initialized');
        return this;
    },

    /**
     * Show a success toast
     */
    success(message, options = {}) {
        return this.show({
            type: 'success',
            icon: '✅',
            message,
            ...options
        });
    },

    /**
     * Show an info toast
     */
    info(message, options = {}) {
        return this.show({
            type: 'info',
            icon: 'ℹ️',
            message,
            ...options
        });
    },

    /**
     * Show a warning toast
     */
    warning(message, options = {}) {
        return this.show({
            type: 'warning',
            icon: '⚠️',
            message,
            duration: 7000,  // Warnings stay longer
            ...options
        });
    },

    /**
     * Show an error toast
     */
    error(message, options = {}) {
        return this.show({
            type: 'error',
            icon: '❌',
            message,
            duration: 10000,  // Errors stay longest
            ...options
        });
    },

    /**
     * Show a milestone celebration toast
     */
    milestone(title, description, options = {}) {
        return this.show({
            type: 'milestone',
            icon: '🏆',
            title,
            message: description,
            duration: 8000,
            showConfetti: true,
            ...options
        });
    },

    /**
     * Show a progress toast (for long-running operations)
     */
    progress(message, options = {}) {
        return this.show({
            type: 'progress',
            icon: '⏳',
            message,
            duration: 0,  // Don't auto-dismiss
            showSpinner: true,
            ...options
        });
    },

    /**
     * Show an encouragement toast (emotion-aware)
     */
    encourage(message, options = {}) {
        return this.show({
            type: 'encourage',
            icon: '💪',
            message,
            duration: 6000,
            ...options
        });
    },

    /**
     * Show a custom toast
     */
    show(options) {
        // Initialize if not done
        if (!this.container) {
            this.init();
        }

        const id = `toast-${++this.counter}`;
        const toast = this.createToastElement(id, options);

        // Limit visible toasts
        while (this.activeToasts.length >= this.config.maxVisible) {
            this.dismiss(this.activeToasts[0].id);
        }

        // Add to container
        this.container.appendChild(toast.element);
        this.activeToasts.push(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.element.classList.add('toast-visible');
        });

        // Play sound if enabled
        if (this.config.enableSounds && options.type !== 'progress') {
            this.playSound(options.type);
        }

        // Trigger haptic feedback
        if (this.config.enableHaptics && navigator.vibrate) {
            const patterns = {
                success: [50],
                error: [100, 50, 100],
                warning: [75, 50, 75],
                milestone: [50, 50, 100, 50, 50],
                default: [25]
            };
            navigator.vibrate(patterns[options.type] || patterns.default);
        }

        // Show confetti for milestones
        if (options.showConfetti && window.SemptifyConfetti) {
            window.SemptifyConfetti.celebrate();
        }

        // Auto-dismiss after duration
        if (options.duration !== 0) {
            const duration = options.duration || this.config.duration;
            toast.timeout = setTimeout(() => {
                this.dismiss(id);
            }, duration);

            // Setup progress bar
            if (this.config.showProgress) {
                toast.element.style.setProperty('--toast-duration', `${duration}ms`);
            }
        }

        return {
            id,
            dismiss: () => this.dismiss(id),
            update: (newOptions) => this.update(id, newOptions)
        };
    },

    /**
     * Create toast DOM element
     */
    createToastElement(id, options) {
        const toast = document.createElement('div');
        toast.id = id;
        toast.className = `toast toast-${options.type || 'info'}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');

        // Build content
        let html = `
            <div class="toast-content">
                <span class="toast-icon">${options.icon || 'ℹ️'}</span>
                <div class="toast-text">
                    ${options.title ? `<strong class="toast-title">${options.title}</strong>` : ''}
                    <span class="toast-message">${options.message}</span>
                </div>
                ${options.showSpinner ? '<div class="toast-spinner"></div>' : ''}
                <button class="toast-close" aria-label="Dismiss notification">&times;</button>
            </div>
            ${this.config.showProgress && options.duration !== 0 ? '<div class="toast-progress"></div>' : ''}
        `;

        // Add action button if provided
        if (options.action) {
            html = html.replace('</div>\n            ', `
                <button class="toast-action">${options.action.label}</button>
            </div>
            `);
        }

        toast.innerHTML = html;

        // Add event listeners
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.dismiss(id));

        if (options.action) {
            const actionBtn = toast.querySelector('.toast-action');
            actionBtn.addEventListener('click', () => {
                options.action.callback();
                this.dismiss(id);
            });
        }

        // Pause on hover
        if (this.config.pauseOnHover) {
            toast.addEventListener('mouseenter', () => {
                toast.classList.add('toast-paused');
            });
            toast.addEventListener('mouseleave', () => {
                toast.classList.remove('toast-paused');
            });
        }

        return { id, element: toast, options };
    },

    /**
     * Update an existing toast
     */
    update(id, newOptions) {
        const toast = this.activeToasts.find(t => t.id === id);
        if (!toast) return;

        // Update message
        if (newOptions.message) {
            const msgEl = toast.element.querySelector('.toast-message');
            if (msgEl) msgEl.textContent = newOptions.message;
        }

        // Update icon
        if (newOptions.icon) {
            const iconEl = toast.element.querySelector('.toast-icon');
            if (iconEl) iconEl.textContent = newOptions.icon;
        }

        // Update type/styling
        if (newOptions.type) {
            toast.element.className = `toast toast-${newOptions.type} toast-visible`;
        }

        // Remove spinner if present
        if (newOptions.showSpinner === false) {
            const spinner = toast.element.querySelector('.toast-spinner');
            if (spinner) spinner.remove();
        }

        // Set auto-dismiss if duration provided
        if (newOptions.duration && newOptions.duration > 0) {
            clearTimeout(toast.timeout);
            toast.timeout = setTimeout(() => {
                this.dismiss(id);
            }, newOptions.duration);
        }
    },

    /**
     * Dismiss a toast
     */
    dismiss(id) {
        const index = this.activeToasts.findIndex(t => t.id === id);
        if (index === -1) return;

        const toast = this.activeToasts[index];
        clearTimeout(toast.timeout);

        // Animate out
        toast.element.classList.remove('toast-visible');
        toast.element.classList.add('toast-dismissing');

        // Remove after animation
        setTimeout(() => {
            toast.element.remove();
        }, 300);

        // Remove from active list
        this.activeToasts.splice(index, 1);
    },

    /**
     * Dismiss all toasts
     */
    dismissAll() {
        [...this.activeToasts].forEach(toast => {
            this.dismiss(toast.id);
        });
    },

    /**
     * Play notification sound
     */
    playSound(type) {
        // Simplified - would use actual audio files
        const frequencies = {
            success: [523, 659, 784],
            error: [392, 330],
            warning: [440, 440],
            milestone: [523, 659, 784, 1047],
            default: [440]
        };

        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const notes = frequencies[type] || frequencies.default;
            
            notes.forEach((freq, i) => {
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.frequency.value = freq;
                oscillator.type = 'sine';
                
                gainNode.gain.setValueAtTime(0.1, audioContext.currentTime + i * 0.1);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + (i + 1) * 0.1);
                
                oscillator.start(audioContext.currentTime + i * 0.1);
                oscillator.stop(audioContext.currentTime + (i + 1) * 0.1);
            });
        } catch (e) {
            // Audio not supported
        }
    },

    /**
     * Inject toast styles
     */
    injectStyles() {
        if (document.getElementById('semptify-toast-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'semptify-toast-styles';
        styles.textContent = `
            .toast-container {
                position: fixed;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
                padding: 1rem;
                pointer-events: none;
                max-height: 100vh;
                overflow: hidden;
            }

            .toast-top-right { top: 0; right: 0; align-items: flex-end; }
            .toast-top-left { top: 0; left: 0; align-items: flex-start; }
            .toast-bottom-right { bottom: 0; right: 0; align-items: flex-end; }
            .toast-bottom-left { bottom: 0; left: 0; align-items: flex-start; }
            .toast-top-center { top: 0; left: 50%; transform: translateX(-50%); align-items: center; }
            .toast-bottom-center { bottom: 0; left: 50%; transform: translateX(-50%); align-items: center; }

            .toast {
                display: flex;
                flex-direction: column;
                min-width: 300px;
                max-width: 450px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15), 0 4px 12px rgba(0, 0, 0, 0.1);
                pointer-events: auto;
                opacity: 0;
                transform: translateX(100%) scale(0.9);
                transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
                overflow: hidden;
            }

            .toast-top-left .toast,
            .toast-bottom-left .toast {
                transform: translateX(-100%) scale(0.9);
            }

            .toast-top-center .toast,
            .toast-bottom-center .toast {
                transform: translateY(-100%) scale(0.9);
            }

            .toast-bottom-center .toast,
            .toast-bottom-left .toast,
            .toast-bottom-right .toast {
                transform: translateY(100%) scale(0.9);
            }

            .toast-visible {
                opacity: 1;
                transform: translateX(0) translateY(0) scale(1);
            }

            .toast-dismissing {
                opacity: 0;
                transform: translateX(100%) scale(0.9);
            }

            .toast-content {
                display: flex;
                align-items: flex-start;
                gap: 0.75rem;
                padding: 1rem 1.25rem;
            }

            .toast-icon {
                font-size: 1.5rem;
                line-height: 1;
                flex-shrink: 0;
            }

            .toast-text {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }

            .toast-title {
                font-weight: 600;
                color: #1a1a2e;
                font-size: 1rem;
            }

            .toast-message {
                color: #4a4a5a;
                font-size: 0.9rem;
                line-height: 1.4;
            }

            .toast-close {
                background: none;
                border: none;
                font-size: 1.5rem;
                color: #999;
                cursor: pointer;
                padding: 0;
                line-height: 1;
                opacity: 0.5;
                transition: opacity 0.2s;
            }

            .toast-close:hover {
                opacity: 1;
            }

            .toast-action {
                background: transparent;
                border: none;
                color: var(--toast-accent);
                font-weight: 600;
                cursor: pointer;
                padding: 0.5rem 0;
                font-size: 0.85rem;
                margin-left: auto;
            }

            .toast-action:hover {
                text-decoration: underline;
            }

            .toast-spinner {
                width: 20px;
                height: 20px;
                border: 2px solid #e0e0e0;
                border-top-color: var(--toast-accent, #3b82f6);
                border-radius: 50%;
                animation: toast-spin 0.8s linear infinite;
            }

            @keyframes toast-spin {
                to { transform: rotate(360deg); }
            }

            .toast-progress {
                height: 4px;
                background: rgba(0, 0, 0, 0.1);
                position: relative;
            }

            .toast-progress::after {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                height: 100%;
                width: 100%;
                background: var(--toast-accent, #3b82f6);
                animation: toast-progress var(--toast-duration, 5000ms) linear forwards;
            }

            .toast-paused .toast-progress::after {
                animation-play-state: paused;
            }

            @keyframes toast-progress {
                from { width: 100%; }
                to { width: 0%; }
            }

            /* Toast Types */
            .toast-success {
                --toast-accent: #10b981;
                border-left: 4px solid #10b981;
            }

            .toast-info {
                --toast-accent: #3b82f6;
                border-left: 4px solid #3b82f6;
            }

            .toast-warning {
                --toast-accent: #f59e0b;
                border-left: 4px solid #f59e0b;
            }

            .toast-error {
                --toast-accent: #ef4444;
                border-left: 4px solid #ef4444;
            }

            .toast-milestone {
                --toast-accent: #8b5cf6;
                border-left: 4px solid #8b5cf6;
                background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
            }

            .toast-progress-type {
                --toast-accent: #6366f1;
                border-left: 4px solid #6366f1;
            }

            .toast-encourage {
                --toast-accent: #ec4899;
                border-left: 4px solid #ec4899;
                background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%);
            }

            /* Dark mode */
            @media (prefers-color-scheme: dark) {
                .toast {
                    background: #1a1a2e;
                }
                .toast-title {
                    color: #f0f0f0;
                }
                .toast-message {
                    color: #a0a0b0;
                }
                .toast-close {
                    color: #666;
                }
                .toast-milestone {
                    background: linear-gradient(135deg, #2d1f47 0%, #3b2961 100%);
                }
                .toast-encourage {
                    background: linear-gradient(135deg, #3d1f35 0%, #4a2545 100%);
                }
            }

            /* Mobile responsive */
            @media (max-width: 480px) {
                .toast-container {
                    padding: 0.5rem;
                }
                .toast {
                    min-width: calc(100vw - 1rem);
                    max-width: calc(100vw - 1rem);
                }
                .toast-top-right,
                .toast-top-left,
                .toast-top-center {
                    left: 0;
                    right: 0;
                    transform: none;
                    align-items: stretch;
                }
            }

            /* Reduced motion */
            @media (prefers-reduced-motion: reduce) {
                .toast {
                    transition: opacity 0.2s;
                    transform: none !important;
                }
                .toast-progress::after {
                    animation: none;
                    width: 0;
                }
            }
        `;
        document.head.appendChild(styles);
    }
};

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => SemptifyToast.init());
} else {
    SemptifyToast.init();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SemptifyToast;
}
