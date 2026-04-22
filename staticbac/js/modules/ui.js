/**
 * ============================================================================
 * SEMPTIFY UI UTILITIES
 * ============================================================================
 * 
 * Centralized UI components and utilities:
 * - Toast notifications
 * - Modal dialogs
 * - Loading states
 * - Confirmation dialogs
 * - Form validation
 * - Accessibility helpers
 */

// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================

const ToastType = {
  SUCCESS: 'success',
  ERROR: 'danger',
  WARNING: 'warning',
  INFO: 'info'
};

class ToastManager {
  constructor() {
    this.container = null;
    this.toasts = new Map();
    this.defaultDuration = 5000;
    this.init();
  }

  init() {
    // Create container if it doesn't exist
    this.container = document.getElementById('toast-container');
    
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'toast-container';
      this.container.setAttribute('role', 'region');
      this.container.setAttribute('aria-label', 'Notifications');
      document.body.appendChild(this.container);
    }
  }

  /**
   * Show a toast notification
   */
  show(message, type = ToastType.INFO, options = {}) {
    const {
      duration = this.defaultDuration,
      title = null,
      action = null,
      dismissible = true,
      id = `toast-${Date.now()}`
    } = options;

    // Create toast element
    const toast = document.createElement('div');
    toast.id = id;
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');

    // Icon based on type
    const icons = {
      success: '<svg viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" /></svg>',
      danger: '<svg viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd" /></svg>',
      warning: '<svg viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5"><path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" /></svg>',
      info: '<svg viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" /></svg>'
    };

    toast.innerHTML = `
      <span class="toast-icon" style="color: var(--color-${type}-500)">${icons[type] || icons.info}</span>
      <div class="toast-content">
        ${title ? `<div class="toast-title font-semibold">${title}</div>` : ''}
        <div class="toast-message">${message}</div>
        ${action ? `<button class="toast-action btn btn-sm btn-ghost mt-2">${action.label}</button>` : ''}
      </div>
      ${dismissible ? `
        <button class="toast-close btn btn-ghost btn-icon" aria-label="Dismiss">
          <svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      ` : ''}
    `;

    // Add event listeners
    if (dismissible) {
      const closeBtn = toast.querySelector('.toast-close');
      closeBtn?.addEventListener('click', () => this.dismiss(id));
    }

    if (action?.onClick) {
      const actionBtn = toast.querySelector('.toast-action');
      actionBtn?.addEventListener('click', () => {
        action.onClick();
        if (action.dismissOnClick !== false) {
          this.dismiss(id);
        }
      });
    }

    // Add to container
    this.container.appendChild(toast);
    this.toasts.set(id, toast);

    // Auto dismiss
    if (duration > 0) {
      setTimeout(() => this.dismiss(id), duration);
    }

    return id;
  }

  /**
   * Dismiss a toast
   */
  dismiss(id) {
    const toast = this.toasts.get(id);
    
    if (!toast) return;

    // Animate out
    toast.style.animation = 'toast-out 0.3s ease forwards';
    
    setTimeout(() => {
      toast.remove();
      this.toasts.delete(id);
    }, 300);
  }

  /**
   * Dismiss all toasts
   */
  dismissAll() {
    for (const id of this.toasts.keys()) {
      this.dismiss(id);
    }
  }

  // Convenience methods
  success(message, options = {}) {
    return this.show(message, ToastType.SUCCESS, options);
  }

  error(message, options = {}) {
    return this.show(message, ToastType.ERROR, { duration: 8000, ...options });
  }

  warning(message, options = {}) {
    return this.show(message, ToastType.WARNING, options);
  }

  info(message, options = {}) {
    return this.show(message, ToastType.INFO, options);
  }
}

// Add toast-out animation style
const toastStyles = document.createElement('style');
toastStyles.textContent = `
  @keyframes toast-out {
    to {
      opacity: 0;
      transform: translateX(100%);
    }
  }
  .toast-icon { width: 1.25rem; height: 1.25rem; flex-shrink: 0; }
  .toast-content { flex: 1; min-width: 0; }
  .toast-message { word-wrap: break-word; }
`;
document.head.appendChild(toastStyles);

// ============================================================================
// MODAL DIALOGS
// ============================================================================

class ModalManager {
  constructor() {
    this.activeModals = [];
    this.init();
  }

  init() {
    // Handle escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.activeModals.length > 0) {
        const topModal = this.activeModals[this.activeModals.length - 1];
        if (topModal.options.closeOnEscape !== false) {
          this.close(topModal.id);
        }
      }
    });
  }

  /**
   * Open a modal
   */
  open(options = {}) {
    const {
      id = `modal-${Date.now()}`,
      title = '',
      content = '',
      footer = null,
      size = 'md', // sm, md, lg, xl, full
      closeOnEscape = true,
      closeOnBackdrop = true,
      onClose = null,
      className = ''
    } = options;

    // Size classes
    const sizeClasses = {
      sm: 'max-w-sm',
      md: 'max-w-lg',
      lg: 'max-w-2xl',
      xl: 'max-w-4xl',
      full: 'max-w-full mx-4'
    };

    // Create modal structure
    const backdrop = document.createElement('div');
    backdrop.id = id;
    backdrop.className = 'modal-backdrop';
    backdrop.innerHTML = `
      <div class="modal ${sizeClasses[size] || sizeClasses.md} ${className}" role="dialog" aria-modal="true" aria-labelledby="${id}-title">
        <div class="modal-header">
          <h2 class="modal-title" id="${id}-title">${title}</h2>
          <button class="modal-close" aria-label="Close dialog">
            <svg viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>
        <div class="modal-body">
          ${typeof content === 'string' ? content : ''}
        </div>
        ${footer ? `<div class="modal-footer">${footer}</div>` : ''}
      </div>
    `;

    // Handle content as DOM element
    if (content instanceof HTMLElement) {
      const body = backdrop.querySelector('.modal-body');
      body.innerHTML = '';
      body.appendChild(content);
    }

    // Event listeners
    backdrop.querySelector('.modal-close').addEventListener('click', () => this.close(id));

    if (closeOnBackdrop) {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) {
          this.close(id);
        }
      });
    }

    // Add to DOM
    document.body.appendChild(backdrop);
    document.body.style.overflow = 'hidden';

    // Store modal info
    this.activeModals.push({ id, backdrop, options: { closeOnEscape, onClose } });

    // Trigger animation
    requestAnimationFrame(() => {
      backdrop.classList.add('active');
    });

    // Focus trap
    const focusableElements = backdrop.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    return {
      id,
      close: () => this.close(id),
      getElement: () => backdrop.querySelector('.modal')
    };
  }

  /**
   * Close a modal
   */
  close(id) {
    const index = this.activeModals.findIndex(m => m.id === id);
    
    if (index === -1) return;

    const { backdrop, options } = this.activeModals[index];

    // Call onClose callback
    if (options.onClose) {
      options.onClose();
    }

    // Animate out
    backdrop.classList.remove('active');

    setTimeout(() => {
      backdrop.remove();
      this.activeModals.splice(index, 1);

      // Restore body scroll if no more modals
      if (this.activeModals.length === 0) {
        document.body.style.overflow = '';
      }
    }, 200);
  }

  /**
   * Close all modals
   */
  closeAll() {
    [...this.activeModals].forEach(modal => this.close(modal.id));
  }

  /**
   * Confirmation dialog
   */
  confirm(options = {}) {
    const {
      title = 'Confirm',
      message = 'Are you sure?',
      confirmText = 'Confirm',
      cancelText = 'Cancel',
      confirmVariant = 'primary', // primary, danger, success
      icon = null
    } = options;

    return new Promise((resolve) => {
      const footer = `
        <button class="btn btn-secondary modal-cancel">${cancelText}</button>
        <button class="btn btn-${confirmVariant} modal-confirm">${confirmText}</button>
      `;

      const content = `
        ${icon ? `<div class="mb-4 text-center">${icon}</div>` : ''}
        <p class="text-secondary">${message}</p>
      `;

      const modal = this.open({
        title,
        content,
        footer,
        size: 'sm',
        onClose: () => resolve(false)
      });

      const backdrop = document.getElementById(modal.id);
      
      backdrop.querySelector('.modal-cancel').addEventListener('click', () => {
        resolve(false);
        this.close(modal.id);
      });

      backdrop.querySelector('.modal-confirm').addEventListener('click', () => {
        resolve(true);
        this.close(modal.id);
      });
    });
  }

  /**
   * Alert dialog
   */
  alert(options = {}) {
    const {
      title = 'Alert',
      message = '',
      buttonText = 'OK'
    } = options;

    return new Promise((resolve) => {
      const footer = `<button class="btn btn-primary modal-ok">${buttonText}</button>`;

      const modal = this.open({
        title,
        content: `<p>${message}</p>`,
        footer,
        size: 'sm',
        onClose: () => resolve()
      });

      const backdrop = document.getElementById(modal.id);
      backdrop.querySelector('.modal-ok').addEventListener('click', () => {
        resolve();
        this.close(modal.id);
      });
    });
  }

  /**
   * Prompt dialog
   */
  prompt(options = {}) {
    const {
      title = 'Input',
      message = '',
      placeholder = '',
      defaultValue = '',
      inputType = 'text',
      confirmText = 'OK',
      cancelText = 'Cancel'
    } = options;

    return new Promise((resolve) => {
      const content = `
        ${message ? `<p class="mb-4">${message}</p>` : ''}
        <input type="${inputType}" class="form-input modal-input" placeholder="${placeholder}" value="${defaultValue}">
      `;

      const footer = `
        <button class="btn btn-secondary modal-cancel">${cancelText}</button>
        <button class="btn btn-primary modal-confirm">${confirmText}</button>
      `;

      const modal = this.open({
        title,
        content,
        footer,
        size: 'sm',
        onClose: () => resolve(null)
      });

      const backdrop = document.getElementById(modal.id);
      const input = backdrop.querySelector('.modal-input');
      
      input.focus();
      input.select();

      // Submit on Enter
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          resolve(input.value);
          this.close(modal.id);
        }
      });

      backdrop.querySelector('.modal-cancel').addEventListener('click', () => {
        resolve(null);
        this.close(modal.id);
      });

      backdrop.querySelector('.modal-confirm').addEventListener('click', () => {
        resolve(input.value);
        this.close(modal.id);
      });
    });
  }
}

// ============================================================================
// LOADING STATES
// ============================================================================

class LoadingManager {
  constructor() {
    this.overlays = new Map();
  }

  /**
   * Show loading overlay on an element
   */
  show(target = document.body, options = {}) {
    const {
      message = 'Loading...',
      spinner = true,
      id = `loading-${Date.now()}`
    } = options;

    const element = typeof target === 'string' ? document.querySelector(target) : target;
    
    if (!element) return null;

    // Create overlay
    const overlay = document.createElement('div');
    overlay.id = id;
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
      <div class="loading-content">
        ${spinner ? '<div class="spinner"></div>' : ''}
        ${message ? `<p class="loading-message mt-4 text-secondary">${message}</p>` : ''}
      </div>
    `;

    // Position relative to target
    const targetPosition = window.getComputedStyle(element).position;
    if (targetPosition === 'static') {
      element.style.position = 'relative';
    }

    element.appendChild(overlay);
    this.overlays.set(id, { overlay, element });

    // Fade in
    requestAnimationFrame(() => {
      overlay.classList.add('active');
    });

    return id;
  }

  /**
   * Hide loading overlay
   */
  hide(id) {
    const entry = this.overlays.get(id);
    
    if (!entry) return;

    const { overlay } = entry;
    overlay.classList.remove('active');

    setTimeout(() => {
      overlay.remove();
      this.overlays.delete(id);
    }, 200);
  }

  /**
   * Show full-page loading
   */
  showPage(message = 'Loading...') {
    return this.show(document.body, { message, id: 'page-loading' });
  }

  /**
   * Hide full-page loading
   */
  hidePage() {
    this.hide('page-loading');
  }

  /**
   * Show button loading state
   */
  buttonLoading(button, loading = true) {
    if (loading) {
      button.disabled = true;
      button.dataset.originalText = button.innerHTML;
      button.innerHTML = `<span class="spinner" style="width: 1rem; height: 1rem;"></span>`;
    } else {
      button.disabled = false;
      button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
  }
}

// Add loading overlay styles
const loadingStyles = document.createElement('style');
loadingStyles.textContent = `
  .loading-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: rgba(255, 255, 255, 0.9);
    z-index: 100;
    opacity: 0;
    transition: opacity 0.2s ease;
  }
  .loading-overlay.active { opacity: 1; }
  .loading-content { text-align: center; }
  [data-theme="dark"] .loading-overlay {
    background-color: rgba(15, 23, 42, 0.9);
  }
`;
document.head.appendChild(loadingStyles);

// ============================================================================
// FORM VALIDATION
// ============================================================================

class FormValidator {
  constructor(form, rules = {}) {
    this.form = typeof form === 'string' ? document.querySelector(form) : form;
    this.rules = rules;
    this.errors = {};
    
    if (this.form) {
      this.init();
    }
  }

  init() {
    // Add novalidate to use custom validation
    this.form.setAttribute('novalidate', '');

    // Validate on submit
    this.form.addEventListener('submit', (e) => {
      if (!this.validate()) {
        e.preventDefault();
        this.focusFirstError();
      }
    });

    // Live validation on blur
    this.form.querySelectorAll('input, textarea, select').forEach(field => {
      field.addEventListener('blur', () => {
        this.validateField(field.name);
        this.showFieldError(field.name);
      });

      // Clear error on input
      field.addEventListener('input', () => {
        this.clearFieldError(field.name);
      });
    });
  }

  /**
   * Add validation rules
   */
  setRules(rules) {
    this.rules = { ...this.rules, ...rules };
  }

  /**
   * Validate a single field
   */
  validateField(name) {
    const field = this.form.elements[name];
    const fieldRules = this.rules[name];
    
    if (!field || !fieldRules) return true;

    const value = field.value.trim();
    delete this.errors[name];

    for (const rule of fieldRules) {
      const error = this.checkRule(rule, value, field);
      if (error) {
        this.errors[name] = error;
        return false;
      }
    }

    return true;
  }

  /**
   * Check a single rule
   */
  checkRule(rule, value, field) {
    if (typeof rule === 'function') {
      return rule(value, field);
    }

    const { type, message, ...params } = rule;

    switch (type) {
      case 'required':
        if (!value) return message || 'This field is required';
        break;

      case 'email':
        if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
          return message || 'Please enter a valid email address';
        }
        break;

      case 'minLength':
        if (value && value.length < params.min) {
          return message || `Minimum ${params.min} characters required`;
        }
        break;

      case 'maxLength':
        if (value && value.length > params.max) {
          return message || `Maximum ${params.max} characters allowed`;
        }
        break;

      case 'pattern':
        if (value && !params.regex.test(value)) {
          return message || 'Invalid format';
        }
        break;

      case 'match':
        const matchField = this.form.elements[params.field];
        if (matchField && value !== matchField.value) {
          return message || `Fields do not match`;
        }
        break;

      case 'custom':
        if (params.validator) {
          return params.validator(value, field);
        }
        break;
    }

    return null;
  }

  /**
   * Validate entire form
   */
  validate() {
    this.errors = {};

    for (const name in this.rules) {
      this.validateField(name);
    }

    // Show all errors
    for (const name in this.errors) {
      this.showFieldError(name);
    }

    return Object.keys(this.errors).length === 0;
  }

  /**
   * Show error for a field
   */
  showFieldError(name) {
    const field = this.form.elements[name];
    if (!field) return;

    // Remove existing error
    this.clearFieldError(name);

    const error = this.errors[name];
    if (!error) {
      field.classList.remove('form-input-error');
      return;
    }

    field.classList.add('form-input-error');
    field.setAttribute('aria-invalid', 'true');

    // Create error element
    const errorEl = document.createElement('div');
    errorEl.className = 'form-error';
    errorEl.id = `${name}-error`;
    errorEl.textContent = error;

    // Link to field for accessibility
    field.setAttribute('aria-describedby', errorEl.id);

    // Insert after field
    field.parentNode.insertBefore(errorEl, field.nextSibling);
  }

  /**
   * Clear error for a field
   */
  clearFieldError(name) {
    const field = this.form.elements[name];
    if (!field) return;

    field.classList.remove('form-input-error');
    field.removeAttribute('aria-invalid');
    field.removeAttribute('aria-describedby');

    const existingError = field.parentNode.querySelector(`#${name}-error`);
    if (existingError) {
      existingError.remove();
    }

    delete this.errors[name];
  }

  /**
   * Focus first field with error
   */
  focusFirstError() {
    const firstErrorField = Object.keys(this.errors)[0];
    if (firstErrorField) {
      const field = this.form.elements[firstErrorField];
      if (field) field.focus();
    }
  }

  /**
   * Get all errors
   */
  getErrors() {
    return { ...this.errors };
  }

  /**
   * Check if form is valid
   */
  isValid() {
    return Object.keys(this.errors).length === 0;
  }

  /**
   * Get form data
   */
  getData() {
    const formData = new FormData(this.form);
    const data = {};
    
    for (const [key, value] of formData.entries()) {
      data[key] = value;
    }
    
    return data;
  }
}

// ============================================================================
// ACCESSIBILITY HELPERS
// ============================================================================

const a11y = {
  /**
   * Announce message to screen readers
   */
  announce(message, priority = 'polite') {
    let announcer = document.getElementById('a11y-announcer');
    
    if (!announcer) {
      announcer = document.createElement('div');
      announcer.id = 'a11y-announcer';
      announcer.className = 'sr-only';
      announcer.setAttribute('aria-live', priority);
      announcer.setAttribute('aria-atomic', 'true');
      document.body.appendChild(announcer);
    }

    announcer.setAttribute('aria-live', priority);
    announcer.textContent = '';
    
    // Force reannounce
    setTimeout(() => {
      announcer.textContent = message;
    }, 100);
  },

  /**
   * Trap focus within an element
   */
  trapFocus(element) {
    const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const focusableElements = element.querySelectorAll(focusableSelector);
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    const trapHandler = (e) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable.focus();
        }
      } else {
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable.focus();
        }
      }
    };

    element.addEventListener('keydown', trapHandler);

    return () => element.removeEventListener('keydown', trapHandler);
  },

  /**
   * Make element focusable and add keyboard navigation
   */
  makeClickable(element, onClick) {
    element.setAttribute('role', 'button');
    element.setAttribute('tabindex', '0');

    element.addEventListener('click', onClick);
    element.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick(e);
      }
    });
  }
};

// ============================================================================
// SINGLETON INSTANCES
// ============================================================================

const toast = new ToastManager();
const modal = new ModalManager();
const loading = new LoadingManager();

// ============================================================================
// EXPORTS
// ============================================================================

// Global exports
window.toast = toast;
window.modal = modal;
window.loading = loading;
window.FormValidator = FormValidator;
window.a11y = a11y;
window.ToastType = ToastType;

// ES Module exports
export {
  ToastManager,
  ToastType,
  ModalManager,
  LoadingManager,
  FormValidator,
  a11y,
  toast,
  modal,
  loading
};
