/**
 * ============================================================================
 * DESIGN SYSTEM COMPONENTS
 * ============================================================================
 *
 * Reusable UI components that follow the design tokens.
 */

@import url('./buttons.css');
@import url('./forms.css');
@import url('./cards.css');
@import url('./navigation.css');
@import url('./modals.css');
@import url('./toasts.css');
@import url('./loading.css');

/**
 * Design System JavaScript Components
 */
export class DesignSystem {
    static init() {
        // Initialize all components
        this.initButtons();
        this.initForms();
        this.initModals();
        this.initToasts();
        this.initNavigation();
    }

    static initButtons() {
        // Button enhancements
        document.querySelectorAll('.btn').forEach(btn => {
            // Add loading state support
            if (btn.classList.contains('btn-loading')) {
                btn.innerHTML = '<span class="spinner"></span>' + btn.innerHTML;
            }
        });
    }

    static initForms() {
        // Form validation
        document.querySelectorAll('.form-input, .form-textarea').forEach(input => {
            input.addEventListener('blur', this.validateField);
            input.addEventListener('input', this.clearFieldError);
        });
    }

    static initModals() {
        // Modal functionality
        document.querySelectorAll('[data-modal]').forEach(trigger => {
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                const modalId = trigger.dataset.modal;
                this.showModal(modalId);
            });
        });
    }

    static initToasts() {
        // Toast notifications
        this.toastContainer = document.getElementById('toast-container');
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'toast-container';
            this.toastContainer.className = 'toast-container';
            document.body.appendChild(this.toastContainer);
        }
    }

    static initNavigation() {
        // Navigation enhancements
        // This will be extended when we integrate with shared-nav.js
    }

    static validateField(e) {
        const field = e.target;
        const value = field.value.trim();
        const isRequired = field.hasAttribute('required');

        if (isRequired && !value) {
            DesignSystem.showFieldError(field, 'This field is required');
            return false;
        }

        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                DesignSystem.showFieldError(field, 'Please enter a valid email address');
                return false;
            }
        }

        DesignSystem.clearFieldError(field);
        return true;
    }

    static showFieldError(field, message) {
        field.classList.add('error');
        let errorEl = field.parentNode.querySelector('.field-error');
        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.className = 'field-error text-danger text-sm mt-1';
            field.parentNode.appendChild(errorEl);
        }
        errorEl.textContent = message;
    }

    static clearFieldError(field) {
        field.classList.remove('error');
        const errorEl = field.parentNode.querySelector('.field-error');
        if (errorEl) {
            errorEl.remove();
        }
    }

    static showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('open');
            document.body.classList.add('modal-open');
        }
    }

    static hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('open');
            document.body.classList.remove('modal-open');
        }
    }

    static showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-message">${message}</span>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        this.toastContainer.appendChild(toast);

        // Auto remove
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, duration);
    }
}