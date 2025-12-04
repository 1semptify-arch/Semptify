/**
 * Semptify Performance Utilities
 * 
 * Provides:
 * - Lazy loading for images and components
 * - Resource hints management
 * - Performance monitoring
 * - Cache management
 */

class PerformanceManager {
  constructor() {
    this.observers = new Map();
    this.loadedResources = new Set();
    this.metrics = {};
    this.init();
  }

  init() {
    this.measureCoreWebVitals();
    this.setupIntersectionObserver();
    this.setupResourceHints();
    this.setupIdleCallback();
  }

  /**
   * Measure Core Web Vitals
   */
  measureCoreWebVitals() {
    // First Contentful Paint (FCP)
    if ('PerformanceObserver' in window) {
      try {
        const paintObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.name === 'first-contentful-paint') {
              this.metrics.fcp = entry.startTime;
              console.log(`[Perf] FCP: ${entry.startTime.toFixed(0)}ms`);
            }
          }
        });
        paintObserver.observe({ entryTypes: ['paint'] });
      } catch (e) {
        // PerformanceObserver not fully supported
      }

      // Largest Contentful Paint (LCP)
      try {
        const lcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const lastEntry = entries[entries.length - 1];
          this.metrics.lcp = lastEntry.startTime;
          console.log(`[Perf] LCP: ${lastEntry.startTime.toFixed(0)}ms`);
        });
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
      } catch (e) {
        // LCP not supported
      }

      // First Input Delay (FID)
      try {
        const fidObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            this.metrics.fid = entry.processingStart - entry.startTime;
            console.log(`[Perf] FID: ${this.metrics.fid.toFixed(0)}ms`);
          }
        });
        fidObserver.observe({ entryTypes: ['first-input'] });
      } catch (e) {
        // FID not supported
      }

      // Cumulative Layout Shift (CLS)
      try {
        let clsValue = 0;
        const clsObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) {
              clsValue += entry.value;
            }
          }
          this.metrics.cls = clsValue;
        });
        clsObserver.observe({ entryTypes: ['layout-shift'] });
      } catch (e) {
        // CLS not supported
      }
    }

    // DOM Content Loaded time
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        this.metrics.domContentLoaded = performance.now();
        console.log(`[Perf] DOMContentLoaded: ${this.metrics.domContentLoaded.toFixed(0)}ms`);
      });
    }

    // Load time
    window.addEventListener('load', () => {
      this.metrics.load = performance.now();
      console.log(`[Perf] Load: ${this.metrics.load.toFixed(0)}ms`);
    });
  }

  /**
   * Setup Intersection Observer for lazy loading
   */
  setupIntersectionObserver() {
    if (!('IntersectionObserver' in window)) {
      console.warn('[Perf] IntersectionObserver not supported, loading all images immediately');
      return;
    }

    // Image lazy loading observer
    this.observers.set('images', new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          this.loadImage(img);
          this.observers.get('images').unobserve(img);
        }
      });
    }, {
      rootMargin: '50px 0px',
      threshold: 0.01
    }));

    // Component lazy loading observer
    this.observers.set('components', new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const component = entry.target;
          this.loadComponent(component);
          this.observers.get('components').unobserve(component);
        }
      });
    }, {
      rootMargin: '100px 0px',
      threshold: 0.01
    }));
  }

  /**
   * Setup resource hints for critical resources
   */
  setupResourceHints() {
    // Preconnect to common origins
    const origins = [
      'https://fonts.googleapis.com',
      'https://fonts.gstatic.com',
      'https://cdnjs.cloudflare.com'
    ];

    origins.forEach(origin => {
      if (!document.querySelector(`link[rel="preconnect"][href="${origin}"]`)) {
        const link = document.createElement('link');
        link.rel = 'preconnect';
        link.href = origin;
        link.crossOrigin = 'anonymous';
        document.head.appendChild(link);
      }
    });
  }

  /**
   * Schedule low-priority work during idle time
   */
  setupIdleCallback() {
    if ('requestIdleCallback' in window) {
      // Preload non-critical resources during idle time
      requestIdleCallback(() => {
        this.preloadNonCriticalResources();
      }, { timeout: 5000 });
    }
  }

  /**
   * Preload non-critical resources
   */
  preloadNonCriticalResources() {
    // Preload other page CSS
    const pagesToPreload = [
      '/static/documents-v2.html',
      '/static/calendar-v2.html',
      '/static/timeline-v2.html'
    ];

    pagesToPreload.forEach(page => {
      if (!this.loadedResources.has(page)) {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = page;
        document.head.appendChild(link);
        this.loadedResources.add(page);
      }
    });
  }

  /**
   * Load lazy image
   */
  loadImage(img) {
    const src = img.dataset.src || img.dataset.lazySrc;
    const srcset = img.dataset.srcset;
    
    if (src) {
      // Create temporary image to preload
      const tempImg = new Image();
      tempImg.onload = () => {
        img.src = src;
        if (srcset) img.srcset = srcset;
        img.classList.remove('lazy');
        img.classList.add('loaded');
      };
      tempImg.onerror = () => {
        img.classList.add('error');
        console.warn(`[Perf] Failed to load image: ${src}`);
      };
      tempImg.src = src;
    }
  }

  /**
   * Load lazy component
   */
  loadComponent(component) {
    const loadFn = component.dataset.loadFn;
    
    if (loadFn && typeof window[loadFn] === 'function') {
      window[loadFn](component);
    }

    component.classList.remove('lazy-component');
    component.classList.add('loaded');
  }

  /**
   * Initialize lazy loading for elements
   */
  initLazyLoading() {
    // Lazy load images with data-src
    document.querySelectorAll('img[data-src], img.lazy').forEach(img => {
      if (!img.src || img.src.includes('placeholder')) {
        this.observers.get('images')?.observe(img);
      }
    });

    // Lazy load components
    document.querySelectorAll('.lazy-component, [data-load-fn]').forEach(component => {
      this.observers.get('components')?.observe(component);
    });
  }

  /**
   * Dynamically load a script
   */
  loadScript(src, options = {}) {
    return new Promise((resolve, reject) => {
      if (this.loadedResources.has(src)) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = src;
      script.async = options.async !== false;
      script.defer = options.defer === true;

      if (options.integrity) {
        script.integrity = options.integrity;
        script.crossOrigin = 'anonymous';
      }

      script.onload = () => {
        this.loadedResources.add(src);
        resolve();
      };

      script.onerror = () => {
        reject(new Error(`Failed to load script: ${src}`));
      };

      document.head.appendChild(script);
    });
  }

  /**
   * Dynamically load a stylesheet
   */
  loadStylesheet(href, options = {}) {
    return new Promise((resolve, reject) => {
      if (this.loadedResources.has(href)) {
        resolve();
        return;
      }

      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;

      if (options.media) {
        link.media = options.media;
      }

      if (options.integrity) {
        link.integrity = options.integrity;
        link.crossOrigin = 'anonymous';
      }

      link.onload = () => {
        this.loadedResources.add(href);
        resolve();
      };

      link.onerror = () => {
        reject(new Error(`Failed to load stylesheet: ${href}`));
      };

      document.head.appendChild(link);
    });
  }

  /**
   * Debounce function
   */
  debounce(fn, delay) {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  /**
   * Throttle function
   */
  throttle(fn, limit) {
    let inThrottle;
    return (...args) => {
      if (!inThrottle) {
        fn.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }

  /**
   * Get performance metrics
   */
  getMetrics() {
    return {
      ...this.metrics,
      memory: performance.memory ? {
        usedJSHeapSize: performance.memory.usedJSHeapSize,
        totalJSHeapSize: performance.memory.totalJSHeapSize
      } : null,
      navigation: {
        type: performance.getEntriesByType('navigation')[0]?.type,
        transferSize: performance.getEntriesByType('navigation')[0]?.transferSize
      }
    };
  }

  /**
   * Report metrics to server
   */
  reportMetrics() {
    const metrics = this.getMetrics();
    
    // Send to analytics endpoint
    if (window.api && typeof window.api.post === 'function') {
      window.api.post('/api/analytics/performance', metrics).catch(() => {
        // Silently fail - performance reporting is non-critical
      });
    }

    return metrics;
  }
}

// Create global instance
window.perf = new PerformanceManager();

// Initialize lazy loading when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => window.perf.initLazyLoading());
} else {
  window.perf.initLazyLoading();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PerformanceManager;
}
