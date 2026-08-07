# SSOT Design System

**Single Source of Truth for all Semptify UI styling**

## Philosophy

This design system eliminates visual inconsistency by providing:
- **One CSS file** with all design tokens (colors, spacing, typography)
- **Utility classes** for rapid layout composition
- **Component classes** for common UI patterns
- **Template examples** showing best practices

## Quick Start

```html
<!DOCTYPE html>
<html>
<head>
  <!-- Link the SSOT Design System -->
  <link rel="stylesheet" href="/static/css/ssot-design-system.css">
</head>
<body>
  <!-- Use utility classes for layout -->
  <div class="container py-6">
    <div class="card">
      <div class="card__header">
        <h3 class="card__title">Title</h3>
      </div>
      <div class="card__body">
        <p>Content using design system components</p>
        <button class="btn btn--primary">Action</button>
      </div>
    </div>
  </div>
</body>
</html>
```

## File Structure

```
static/
├── css/
│   └── ssot-design-system.css    # Main design system (ONE FILE)
├── templates/
│   ├── page-shell.html           # Base template with all patterns
│   ├── component-examples.html   # Visual reference guide
│   └── journal-refactored.html   # Real-world example
└── tenant/
    └── dashboard.html            # Existing pages (refactor target)
```

## Design Tokens (CSS Variables)

### Colors
```css
--color-primary: #1e3a5f;        /* Brand primary */
--color-primary-light: #2c5aa0;  /* Hover states */
--color-accent: #fbbf24;         /* CTAs, highlights */
--color-success: #10b981;        /* Success states */
--color-warning: #f59e0b;        /* Warnings */
--color-error: #ef4444;          /* Errors */

/* Usage: */
.my-element {
  color: var(--color-primary);
  background: var(--color-accent);
}
```

### Spacing (8px base)
```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */

/* Usage: */
.my-element {
  padding: var(--space-4);
  gap: var(--space-2);
}
```

### Typography
```css
--text-xs: 0.75rem;   /* 12px */
--text-sm: 0.875rem;  /* 14px */
--text-base: 1rem;    /* 16px */
--text-lg: 1.125rem;  /* 18px */
--text-xl: 1.25rem;   /* 20px */
--text-2xl: 1.5rem;   /* 24px */
--text-3xl: 1.875rem; /* 30px */
```

## Utility Classes

### Layout
```html
<!-- Container -->
<div class="container">         <!-- Max-width 1280px, centered -->
<div class="container-sm">      <!-- Max-width 768px -->

<!-- Display -->
<div class="flex">              <!-- display: flex -->
<div class="grid">              <!-- display: grid -->
<div class="hidden">            <!-- display: none -->

<!-- Flexbox -->
<div class="flex items-center">  <!-- align-items: center -->
<div class="flex justify-between"> <!-- justify-content: space-between -->
<div class="flex-col">          <!-- flex-direction: column -->
<div class="gap-4">             <!-- gap: 1rem -->

<!-- Spacing -->
<div class="p-4">               <!-- padding: 1rem -->
<div class="px-4 py-2">         <!-- padding x/y separately -->
<div class="m-4">               <!-- margin: 1rem -->
<div class="mt-4 mb-2">         <!-- margin top/bottom -->
<div class="mx-auto">           <!-- margin auto horizontal -->

<!-- Text -->
<p class="text-sm">             <!-- font-size: 0.875rem -->
<p class="font-bold">           <!-- font-weight: 700 -->
<p class="text-center">          <!-- text-align: center -->
<p class="text-secondary">      <!-- color: var(--text-secondary) -->
<p class="truncate">            <!-- overflow: ellipsis -->
```

## Component Classes

### Buttons
```html
<!-- Variants -->
<button class="btn btn--primary">Primary</button>
<button class="btn btn--secondary">Secondary</button>
<button class="btn btn--accent">Accent (CTA)</button>
<button class="btn btn--ghost">Ghost</button>
<button class="btn btn--danger">Danger</button>

<!-- Sizes -->
<button class="btn btn--primary btn--sm">Small</button>
<button class="btn btn--primary">Default</button>
<button class="btn btn--primary btn--lg">Large</button>

<!-- With icon -->
<button class="btn btn--primary">
  <span>➕</span>
  <span>Add</span>
</button>

<!-- State -->
<button class="btn btn--primary" disabled>Disabled</button>
```

### Cards
```html
<!-- Basic -->
<div class="card">
  <div class="card__body">
    <p>Card content</p>
  </div>
</div>

<!-- With header -->
<div class="card">
  <div class="card__header">
    <h3 class="card__title">Title</h3>
    <p class="card__subtitle">Subtitle</p>
  </div>
  <div class="card__body">
    <p>Content</p>
  </div>
</div>

<!-- With footer (actions) -->
<div class="card">
  <div class="card__body">
    <p>Content</p>
  </div>
  <div class="card__footer">
    <button class="btn btn--secondary">Cancel</button>
    <button class="btn btn--primary">Save</button>
  </div>
</div>

<!-- Variants -->
<div class="card card--compact">  <!-- Less padding -->
<div class="card card--flat">     <!-- No shadow, border only -->
```

### Forms
```html
<!-- Form group with label and input -->
<div class="form-group">
  <label class="form-label form-label--required" for="name">Name</label>
  <input type="text" id="name" class="form-input" placeholder="Enter name">
  <p class="form-hint">Helper text</p>
</div>

<!-- With error -->
<div class="form-group">
  <label class="form-label form-label--required" for="email">Email</label>
  <input type="email" id="email" class="form-input" value="invalid">
  <p class="form-error">⚠️ Please enter a valid email</p>
</div>

<!-- Input types -->
<input type="text" class="form-input">
<input type="email" class="form-input">
<input type="password" class="form-input">
<input type="number" class="form-input">
<input type="date" class="form-input">

<select class="form-select">
  <option>Option</option>
</select>

<textarea class="form-textarea" rows="4"></textarea>

<!-- Input group (with prepend/append) -->
<div class="form-group">
  <label class="form-label">Amount</label>
  <div class="input-group">
    <span class="input-group__prepend">$</span>
    <input type="number" class="form-input" placeholder="0.00">
    <span class="input-group__append">USD</span>
  </div>
</div>
```

### Badges
```html
<span class="badge badge--primary">Primary</span>
<span class="badge badge--secondary">Secondary</span>
<span class="badge badge--success">Success</span>
<span class="badge badge--warning">Warning</span>
<span class="badge badge--error">Error</span>
<span class="badge badge--accent">Accent</span>
```

### Alerts
```html
<div class="alert alert--info">
  <span>ℹ️</span>
  <div><strong>Info</strong><p class="text-sm">Message</p></div>
</div>

<div class="alert alert--success">
  <span>✅</span>
  <div><strong>Success!</strong><p class="text-sm">Message</p></div>
</div>

<div class="alert alert--warning">
  <span>⚠️</span>
  <div><strong>Warning</strong><p class="text-sm">Message</p></div>
</div>

<div class="alert alert--error">
  <span>❌</span>
  <div><strong>Error</strong><p class="text-sm">Message</p></div>
</div>
```

### Navigation
```html
<!-- Horizontal -->
<nav class="nav nav--horizontal">
  <a href="#" class="nav__link nav__link--active">Active</a>
  <a href="#" class="nav__link">Link</a>
  <a href="#" class="nav__link">Link</a>
</nav>

<!-- Vertical -->
<nav class="nav nav--vertical">
  <a href="#" class="nav__link">Item 1</a>
  <a href="#" class="nav__link">Item 2</a>
</nav>
```

## Layout Patterns

### Page Layout (Sidebar + Content)
```html
<div class="container py-6">
  <div class="page-layout">           <!-- Grid: 280px sidebar + 1fr content -->
    <aside class="sidebar">           <!-- Sticky sidebar -->
      <!-- Sidebar content -->
    </aside>
    <section class="main-content">    <!-- Main content area -->
      <!-- Page content -->
    </section>
  </div>
</div>
```

### Page Header
```html
<header class="page-header">          <!-- Gradient background, white text -->
  <div class="container">
    <h1 class="page-header__title">Title</h1>
    <p class="page-header__subtitle">Subtitle</p>
  </div>
</header>
```

### Responsive Behavior
```html
<!-- Hide on mobile -->
<div class="hide-mobile">Desktop only</div>

<!-- Hide on tablet -->
<div class="hide-tablet">Not on tablet</div>

<!-- Hide on desktop -->
<div class="hide-desktop">Mobile only</div>

<!-- Responsive grid -->
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
  <!-- Cards auto-adjust columns based on width -->
</div>
```

## Migration Guide

### From Old Patterns to SSOT

**Before (inconsistent):**
```html
<div style="background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 16px;">
  <h3 style="font-size: 18px; font-weight: 600; margin-bottom: 12px;">Title</h3>
  <p style="color: #666;">Content</p>
  <button style="background: #2c5aa0; color: white; padding: 8px 16px; border: none; border-radius: 4px;">
    Action
  </button>
</div>
```

**After (SSOT compliant):**
```html
<div class="card">
  <div class="card__body">
    <h3 class="text-lg font-semibold mb-3">Title</h3>
    <p class="text-secondary">Content</p>
    <button class="btn btn--primary">Action</button>
  </div>
</div>
```

### Benefits
1. **Consistency** - Same styles across all pages
2. **Maintainability** - Change in one place, applies everywhere
3. **Accessibility** - Built-in focus states, ARIA support
4. **Performance** - One cached CSS file
5. **Developer speed** - Copy-paste working patterns

## Best Practices

### DO:
- ✅ Use the design system CSS file
- ✅ Use utility classes for layout
- ✅ Use component classes for UI elements
- ✅ Use CSS variables for custom values
- ✅ Keep page-specific CSS minimal
- ✅ Test responsive behavior

### DON'T:
- ❌ Inline styles (`style="..."`)
- ❌ Hardcoded colors (`color: #2c5aa0`)
- ❌ Arbitrary spacing (`margin: 17px`)
- ❌ Duplicate component CSS in each file
- ❌ Use `!important` to override

## Examples

See these reference files:
- `/static/templates/component-examples.html` - Visual catalog of all components
- `/static/templates/journal-refactored.html` - Real page using the design system
- `/static/templates/page-shell.html` - Starting template for new pages

## Maintenance

When adding new patterns:
1. Check if existing component fits the need
2. If not, add to `ssot-design-system.css`
3. Document in this file
4. Add to `component-examples.html`
5. Refactor existing pages to use new pattern

---

**Semptify Design System v1.0**
One source. All pages. Consistent experience.
