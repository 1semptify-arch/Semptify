/**
 * Semptify Accessibility Helper
 * WCAG 2.1 AA Compliance Utilities
 * 
 * Provides:
 * - Focus trap for modals
 * - Screen reader announcements
 * - Keyboard navigation
 * - Skip link management
 * - Reduced motion detection
 */

class A11yHelper {
  constructor() {
    this.announcer = null;
    this.focusTrapStack = [];
    this.prefersReducedMotion = false;
    this.init();
  }

  init() {
    this.createAnnouncer();
    this.detectReducedMotion();
    this.setupSkipLinks();
    this.setupEscapeKeyHandling();
    this.enhanceInteractiveElements();
  }

  /**
   * Create screen reader announcer element
   */
  createAnnouncer() {
    // Check if announcer already exists
    this.announcer = document.getElementById('a11y-announcer');
    
    if (!this.announcer) {
      this.announcer = document.createElement('div');
      this.announcer.id = 'a11y-announcer';
      this.announcer.className = 'sr-only';
      this.announcer.setAttribute('aria-live', 'polite');
      this.announcer.setAttribute('aria-atomic', 'true');
      document.body.appendChild(this.announcer);
    }
  }

  /**
   * Announce message to screen readers
   * @param {string} message - Message to announce
   * @param {string} priority - 'polite' or 'assertive'
   */
  announce(message, priority = 'polite') {
    if (!this.announcer) return;
    
    this.announcer.setAttribute('aria-live', priority);
    
    // Clear and re-add to trigger announcement
    this.announcer.textContent = '';
    
    // Use setTimeout to ensure the DOM update triggers announcement
    setTimeout(() => {
      this.announcer.textContent = message;
    }, 100);

    // Clear after announcement
    setTimeout(() => {
      this.announcer.textContent = '';
    }, 5000);
  }

  /**
   * Announce assertive message (interrupts current speech)
   * @param {string} message - Urgent message to announce
   */
  announceUrgent(message) {
    this.announce(message, 'assertive');
  }

  /**
   * Detect if user prefers reduced motion
   */
  detectReducedMotion() {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    this.prefersReducedMotion = mediaQuery.matches;
    
    mediaQuery.addEventListener('change', (e) => {
      this.prefersReducedMotion = e.matches;
      document.documentElement.setAttribute('data-reduced-motion', e.matches);
    });

    document.documentElement.setAttribute('data-reduced-motion', this.prefersReducedMotion);
  }

  /**
   * Check if reduced motion is preferred
   * @returns {boolean}
   */
  shouldReduceMotion() {
    return this.prefersReducedMotion;
  }

  /**
   * Setup skip links functionality
   */
  setupSkipLinks() {
    document.querySelectorAll('.skip-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = link.getAttribute('href')?.slice(1);
        const target = document.getElementById(targetId);
        
        if (target) {
          target.setAttribute('tabindex', '-1');
          target.focus();
          target.scrollIntoView({ behavior: this.prefersReducedMotion ? 'auto' : 'smooth' });
          
          // Remove tabindex after blur
          target.addEventListener('blur', () => {
            target.removeAttribute('tabindex');
          }, { once: true });
        }
      });
    });
  }

  /**
   * Setup escape key handling for modals
   */
  setupEscapeKeyHandling() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.focusTrapStack.length > 0) {
        const currentTrap = this.focusTrapStack[this.focusTrapStack.length - 1];
        if (currentTrap.onEscape) {
          currentTrap.onEscape();
        }
      }
    });
  }

  /**
   * Create focus trap for modal/dialog
   * @param {HTMLElement} container - Container element to trap focus in
   * @param {Function} onEscape - Callback when Escape is pressed
   * @returns {Object} Focus trap controller
   */
  createFocusTrap(container, onEscape = null) {
    if (!container) return null;

    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable]'
    ].join(', ');

    const getFocusableElements = () => {
      return Array.from(container.querySelectorAll(focusableSelectors))
        .filter(el => el.offsetParent !== null); // Visible elements only
    };

    let previouslyFocused = document.activeElement;

    const handleKeydown = (e) => {
      if (e.key !== 'Tab') return;

      const focusable = getFocusableElements();
      if (focusable.length === 0) return;

      const firstEl = focusable[0];
      const lastEl = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };

    const trap = {
      container,
      onEscape,
      handleKeydown,
      activate: () => {
        previouslyFocused = document.activeElement;
        container.addEventListener('keydown', handleKeydown);
        
        // Focus first focusable element
        const focusable = getFocusableElements();
        if (focusable.length > 0) {
          focusable[0].focus();
        } else {
          container.setAttribute('tabindex', '-1');
          container.focus();
        }

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
        
        this.focusTrapStack.push(trap);
      },
      deactivate: () => {
        container.removeEventListener('keydown', handleKeydown);
        
        // Restore body scroll
        if (this.focusTrapStack.length <= 1) {
          document.body.style.overflow = '';
        }

        // Return focus
        if (previouslyFocused && previouslyFocused.focus) {
          previouslyFocused.focus();
        }

        // Remove from stack
        const index = this.focusTrapStack.indexOf(trap);
        if (index > -1) {
          this.focusTrapStack.splice(index, 1);
        }
      }
    };

    return trap;
  }

  /**
   * Enhance interactive elements with proper ARIA
   */
  enhanceInteractiveElements() {
    // Add role="button" to div/span with click handlers
    document.querySelectorAll('[onclick]').forEach(el => {
      if (!el.getAttribute('role') && !['A', 'BUTTON', 'INPUT', 'SELECT'].includes(el.tagName)) {
        el.setAttribute('role', 'button');
        if (!el.hasAttribute('tabindex')) {
          el.setAttribute('tabindex', '0');
        }
      }
    });

    // Make clickable cards keyboard accessible
    document.querySelectorAll('.card[onclick], .card.clickable').forEach(card => {
      if (!card.hasAttribute('tabindex')) {
        card.setAttribute('tabindex', '0');
      }
      if (!card.getAttribute('role')) {
        card.setAttribute('role', 'button');
      }

      // Handle Enter/Space key
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          card.click();
        }
      });
    });
  }

  /**
   * Set loading state with proper ARIA
   * @param {HTMLElement} element - Element to mark as loading
   * @param {boolean} isLoading - Loading state
   * @param {string} message - Loading message for screen readers
   */
  setLoading(element, isLoading, message = 'Loading...') {
    if (!element) return;

    element.setAttribute('aria-busy', isLoading);
    
    if (isLoading) {
      element.classList.add('loading');
      this.announce(message);
    } else {
      element.classList.remove('loading');
    }
  }

  /**
   * Create accessible tabs
   * @param {HTMLElement} tabList - Tab list container
   * @param {Object} options - Tab options
   */
  createTabs(tabList, options = {}) {
    if (!tabList) return;

    const tabs = Array.from(tabList.querySelectorAll('[role="tab"]'));
    const panels = tabs.map(tab => 
      document.getElementById(tab.getAttribute('aria-controls'))
    );

    tabList.setAttribute('role', 'tablist');

    const selectTab = (index) => {
      tabs.forEach((tab, i) => {
        const selected = i === index;
        tab.setAttribute('aria-selected', selected);
        tab.setAttribute('tabindex', selected ? '0' : '-1');
        
        if (panels[i]) {
          panels[i].hidden = !selected;
        }
      });

      tabs[index].focus();
      
      if (options.onChange) {
        options.onChange(index);
      }
    };

    tabList.addEventListener('keydown', (e) => {
      const currentIndex = tabs.findIndex(t => t === document.activeElement);
      
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        selectTab((currentIndex + 1) % tabs.length);
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        selectTab((currentIndex - 1 + tabs.length) % tabs.length);
      } else if (e.key === 'Home') {
        e.preventDefault();
        selectTab(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        selectTab(tabs.length - 1);
      }
    });

    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => selectTab(index));
    });

    return { selectTab };
  }

  /**
   * Create accessible accordion
   * @param {HTMLElement} container - Accordion container
   * @param {Object} options - Accordion options
   */
  createAccordion(container, options = {}) {
    if (!container) return;

    const buttons = Array.from(container.querySelectorAll('[data-accordion-trigger]'));
    
    buttons.forEach((button, index) => {
      const panelId = button.getAttribute('aria-controls');
      const panel = document.getElementById(panelId);
      
      if (!panel) return;

      button.setAttribute('aria-expanded', 'false');
      panel.hidden = true;

      button.addEventListener('click', () => {
        const isExpanded = button.getAttribute('aria-expanded') === 'true';
        
        if (options.singleOpen) {
          // Close all others
          buttons.forEach(btn => {
            btn.setAttribute('aria-expanded', 'false');
            const p = document.getElementById(btn.getAttribute('aria-controls'));
            if (p) p.hidden = true;
          });
        }

        button.setAttribute('aria-expanded', !isExpanded);
        panel.hidden = isExpanded;
      });

      button.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          buttons[(index + 1) % buttons.length].focus();
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          buttons[(index - 1 + buttons.length) % buttons.length].focus();
        } else if (e.key === 'Home') {
          e.preventDefault();
          buttons[0].focus();
        } else if (e.key === 'End') {
          e.preventDefault();
          buttons[buttons.length - 1].focus();
        }
      });
    });
  }

  /**
   * Announce form validation errors
   * @param {HTMLFormElement} form - Form element
   * @param {Array} errors - Array of error objects {field, message}
   */
  announceFormErrors(form, errors) {
    if (errors.length === 0) return;

    const message = errors.length === 1
      ? `Error: ${errors[0].message}`
      : `${errors.length} errors found. First error: ${errors[0].message}`;

    this.announceUrgent(message);

    // Focus first error field
    if (errors[0].field) {
      const field = form.querySelector(`[name="${errors[0].field}"]`);
      if (field) {
        field.focus();
        field.setAttribute('aria-invalid', 'true');
      }
    }
  }

  /**
   * Create live region for dynamic content
   * @param {string} id - Element ID
   * @param {string} politeness - 'polite' or 'assertive'
   * @returns {HTMLElement}
   */
  createLiveRegion(id, politeness = 'polite') {
    let region = document.getElementById(id);
    
    if (!region) {
      region = document.createElement('div');
      region.id = id;
      region.className = 'sr-only';
      region.setAttribute('aria-live', politeness);
      region.setAttribute('aria-atomic', 'true');
      document.body.appendChild(region);
    }

    return region;
  }

  /**
   * Update live region content
   * @param {string} id - Region ID
   * @param {string} content - New content
   */
  updateLiveRegion(id, content) {
    const region = document.getElementById(id);
    if (region) {
      region.textContent = content;
    }
  }
}

// Create global instance
window.a11y = new A11yHelper();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = A11yHelper;
}
