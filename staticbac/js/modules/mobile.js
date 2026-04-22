/**
 * Semptify Mobile & Touch Utilities
 * 
 * Provides:
 * - Touch gesture handling
 * - Mobile sidebar management
 * - Pull-to-refresh
 * - Viewport management
 * - Device detection
 */

class MobileManager {
  constructor() {
    this.isTouchDevice = false;
    this.isIOS = false;
    this.isAndroid = false;
    this.isMobile = false;
    this.isTablet = false;
    this.viewportHeight = window.innerHeight;
    this.touchStartY = 0;
    this.touchEndY = 0;
    
    this.init();
  }

  init() {
    this.detectDevice();
    this.fixViewportHeight();
    this.initSidebar();
    this.initGestures();
    this.initPullToRefresh();
    this.handleOrientationChange();
    
    console.log('[Mobile] Initialized:', {
      isMobile: this.isMobile,
      isTablet: this.isTablet,
      isTouchDevice: this.isTouchDevice,
      isIOS: this.isIOS,
      isAndroid: this.isAndroid
    });
  }

  /**
   * Detect device type and capabilities
   */
  detectDevice() {
    const ua = navigator.userAgent.toLowerCase();
    
    this.isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    this.isIOS = /ipad|iphone|ipod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    this.isAndroid = /android/.test(ua);
    this.isMobile = /android|webos|iphone|ipod|blackberry|iemobile|opera mini/.test(ua);
    this.isTablet = /ipad|android(?!.*mobile)/.test(ua) || (this.isIOS && window.innerWidth >= 768);

    // Set CSS classes on document
    document.documentElement.classList.toggle('touch-device', this.isTouchDevice);
    document.documentElement.classList.toggle('mobile-device', this.isMobile);
    document.documentElement.classList.toggle('tablet-device', this.isTablet);
    document.documentElement.classList.toggle('ios-device', this.isIOS);
    document.documentElement.classList.toggle('android-device', this.isAndroid);
  }

  /**
   * Fix viewport height for mobile browsers (iOS Safari 100vh issue)
   */
  fixViewportHeight() {
    const setViewportHeight = () => {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--vh', `${vh}px`);
      this.viewportHeight = window.innerHeight;
    };

    setViewportHeight();
    window.addEventListener('resize', debounce(setViewportHeight, 100));

    // Also update on orientation change
    window.addEventListener('orientationchange', () => {
      setTimeout(setViewportHeight, 200);
    });
  }

  /**
   * Initialize mobile sidebar
   */
  initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('mobile-menu-toggle');
    const overlay = this.createOverlay();

    if (!sidebar) return;

    // Toggle button click
    menuToggle?.addEventListener('click', () => {
      this.toggleSidebar();
    });

    // Overlay click closes sidebar
    overlay.addEventListener('click', () => {
      this.closeSidebar();
    });

    // Close on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && sidebar.classList.contains('open')) {
        this.closeSidebar();
      }
    });

    // Close sidebar when clicking a link on mobile
    sidebar.querySelectorAll('.sidebar-link').forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth < 768) {
          this.closeSidebar();
        }
      });
    });
  }

  /**
   * Create overlay element
   */
  createOverlay() {
    let overlay = document.querySelector('.mobile-menu-overlay');
    
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'mobile-menu-overlay';
      overlay.setAttribute('aria-hidden', 'true');
      document.body.appendChild(overlay);
    }

    return overlay;
  }

  /**
   * Toggle sidebar open/closed
   */
  toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.mobile-menu-overlay');
    const menuToggle = document.getElementById('mobile-menu-toggle');

    if (!sidebar) return;

    const isOpen = sidebar.classList.contains('open');
    
    if (isOpen) {
      this.closeSidebar();
    } else {
      sidebar.classList.add('open');
      overlay?.classList.add('active');
      menuToggle?.classList.add('active');
      menuToggle?.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';

      // Focus first link for accessibility
      const firstLink = sidebar.querySelector('.sidebar-link');
      firstLink?.focus();

      // Announce to screen readers
      if (window.a11y) {
        window.a11y.announce('Navigation menu opened');
      }
    }
  }

  /**
   * Close sidebar
   */
  closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.mobile-menu-overlay');
    const menuToggle = document.getElementById('mobile-menu-toggle');

    sidebar?.classList.remove('open');
    overlay?.classList.remove('active');
    menuToggle?.classList.remove('active');
    menuToggle?.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';

    // Return focus to toggle button
    menuToggle?.focus();

    if (window.a11y) {
      window.a11y.announce('Navigation menu closed');
    }
  }

  /**
   * Initialize touch gestures
   */
  initGestures() {
    if (!this.isTouchDevice) return;

    // Swipe to open/close sidebar
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;

    document.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
      touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
      touchEndX = e.changedTouches[0].screenX;
      touchEndY = e.changedTouches[0].screenY;
      this.handleSwipe(touchStartX, touchStartY, touchEndX, touchEndY);
    }, { passive: true });
  }

  /**
   * Handle swipe gesture
   */
  handleSwipe(startX, startY, endX, endY) {
    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const minSwipeDistance = 50;

    // Ensure horizontal swipe is dominant
    if (Math.abs(deltaX) < Math.abs(deltaY)) return;
    if (Math.abs(deltaX) < minSwipeDistance) return;

    const sidebar = document.getElementById('sidebar');
    const isOpen = sidebar?.classList.contains('open');

    // Swipe right from left edge to open sidebar
    if (deltaX > 0 && startX < 30 && !isOpen) {
      this.toggleSidebar();
    }

    // Swipe left to close sidebar
    if (deltaX < 0 && isOpen) {
      this.closeSidebar();
    }
  }

  /**
   * Initialize pull-to-refresh (optional feature)
   */
  initPullToRefresh() {
    if (!this.isTouchDevice) return;

    let startY = 0;
    let pulling = false;
    const threshold = 80;

    const mainContent = document.querySelector('.main-content');
    if (!mainContent) return;

    // Check if pull-to-refresh is enabled
    if (!mainContent.hasAttribute('data-pull-refresh')) return;

    let indicator = document.createElement('div');
    indicator.className = 'pull-to-refresh-indicator';
    indicator.innerHTML = '<i class="fas fa-sync-alt"></i>';
    indicator.style.cssText = `
      position: absolute;
      top: -50px;
      left: 50%;
      transform: translateX(-50%);
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--color-bg-primary);
      box-shadow: var(--shadow-lg);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s;
      z-index: 1000;
    `;
    mainContent.style.position = 'relative';
    mainContent.prepend(indicator);

    mainContent.addEventListener('touchstart', (e) => {
      if (mainContent.scrollTop === 0) {
        startY = e.touches[0].clientY;
        pulling = true;
      }
    }, { passive: true });

    mainContent.addEventListener('touchmove', (e) => {
      if (!pulling) return;

      const currentY = e.touches[0].clientY;
      const pullDistance = Math.min(currentY - startY, threshold * 1.5);

      if (pullDistance > 0) {
        indicator.style.transform = `translateX(-50%) translateY(${pullDistance}px) rotate(${pullDistance * 2}deg)`;
      }
    }, { passive: true });

    mainContent.addEventListener('touchend', (e) => {
      if (!pulling) return;
      pulling = false;

      const endY = e.changedTouches[0].clientY;
      const pullDistance = endY - startY;

      indicator.style.transform = 'translateX(-50%) translateY(-50px)';

      if (pullDistance > threshold) {
        this.triggerRefresh();
      }
    }, { passive: true });
  }

  /**
   * Trigger page refresh
   */
  triggerRefresh() {
    if (window.a11y) {
      window.a11y.announce('Refreshing page');
    }

    // Fire custom event for app to handle
    const event = new CustomEvent('pulltorefresh');
    document.dispatchEvent(event);

    // Default behavior: reload page
    setTimeout(() => {
      if (!event.defaultPrevented) {
        window.location.reload();
      }
    }, 500);
  }

  /**
   * Handle orientation changes
   */
  handleOrientationChange() {
    window.addEventListener('orientationchange', () => {
      // Small delay to allow browser to update
      setTimeout(() => {
        this.fixViewportHeight();
        
        // Close sidebar on orientation change
        if (document.getElementById('sidebar')?.classList.contains('open')) {
          this.closeSidebar();
        }

        // Fire custom event
        document.dispatchEvent(new CustomEvent('orientationchanged', {
          detail: {
            orientation: window.screen.orientation?.type || 
                        (window.innerWidth > window.innerHeight ? 'landscape' : 'portrait')
          }
        }));
      }, 200);
    });
  }

  /**
   * Get current breakpoint
   */
  getBreakpoint() {
    const width = window.innerWidth;
    
    if (width < 480) return 'xs';
    if (width < 640) return 'sm';
    if (width < 768) return 'md';
    if (width < 1024) return 'lg';
    if (width < 1280) return 'xl';
    return '2xl';
  }

  /**
   * Check if current viewport matches breakpoint
   */
  matchesBreakpoint(breakpoint) {
    const breakpoints = {
      xs: 0,
      sm: 480,
      md: 640,
      lg: 768,
      xl: 1024,
      '2xl': 1280
    };

    const width = window.innerWidth;
    const min = breakpoints[breakpoint] || 0;
    const breakpointKeys = Object.keys(breakpoints);
    const nextIndex = breakpointKeys.indexOf(breakpoint) + 1;
    const max = nextIndex < breakpointKeys.length ? breakpoints[breakpointKeys[nextIndex]] - 1 : Infinity;

    return width >= min && width <= max;
  }

  /**
   * Add breakpoint change listener
   */
  onBreakpointChange(callback) {
    let currentBreakpoint = this.getBreakpoint();

    window.addEventListener('resize', debounce(() => {
      const newBreakpoint = this.getBreakpoint();
      if (newBreakpoint !== currentBreakpoint) {
        const oldBreakpoint = currentBreakpoint;
        currentBreakpoint = newBreakpoint;
        callback(newBreakpoint, oldBreakpoint);
      }
    }, 100));
  }

  /**
   * Scroll to element with offset
   */
  scrollToElement(element, offset = 0) {
    if (!element) return;

    const headerHeight = document.querySelector('.header')?.offsetHeight || 0;
    const targetPosition = element.getBoundingClientRect().top + window.pageYOffset - headerHeight - offset;

    window.scrollTo({
      top: targetPosition,
      behavior: window.a11y?.shouldReduceMotion() ? 'auto' : 'smooth'
    });
  }

  /**
   * Lock body scroll (for modals, overlays)
   */
  lockScroll() {
    const scrollY = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollY}px`;
    document.body.style.width = '100%';
    document.body.dataset.scrollLock = scrollY;
  }

  /**
   * Unlock body scroll
   */
  unlockScroll() {
    const scrollY = document.body.dataset.scrollLock || 0;
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.width = '';
    window.scrollTo(0, parseInt(scrollY));
    delete document.body.dataset.scrollLock;
  }
}

// Debounce helper
function debounce(fn, delay) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn.apply(this, args), delay);
  };
}

// Create global instance
window.mobile = new MobileManager();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MobileManager;
}
