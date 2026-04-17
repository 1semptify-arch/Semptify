/**
 * Semptify Design System JavaScript
 * Unified component initialization and utilities
 */

// Import all component modules
import { DesignSystem } from './components/index.js';

// Initialize the design system when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    DesignSystem.init();
});

// Export for manual initialization if needed
window.SemptifyDesignSystem = DesignSystem;