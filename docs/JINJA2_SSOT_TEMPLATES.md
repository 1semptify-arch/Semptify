# Jinja2 SSOT Template System

**Single Source of Truth for all Semptify page templates**

## Overview

This system uses Jinja2 template inheritance to ensure:
- **One base template** for consistent layout across all pages
- **Reusable blocks** for page-specific content
- **SSOT navigation registry** integration for all links
- **Automatic accessibility** (ARIA labels, skip links, focus states)
- **Semptify mandates compliance** (privacy-first, no ads, tenant rights focused)

## File Structure

```
app/templates/
├── base_ssot.html                    # SSOT Base template (extends this!)
├── pages/
│   ├── journal_ssot.html              # Example: Journal page
│   ├── dashboard_ssot.html            # Example: Dashboard page
│   └── [your_page]_ssot.html          # Your new pages
└── base.html                          # Legacy template (not SSOT)

static/css/
└── ssot-design-system.css             # SSOT styling (linked in base)
```

## Quick Start: Creating a New Page

### 1. Create Template File

Create `app/templates/pages/my_page_ssot.html`:

```html
{% extends "base_ssot.html" %}

{% block title %}My Page Title{% endblock %}
{% block meta_description %}Description for SEO{% endblock %}
{% block role %}tenant{% endblock %}

{% block page_header %}
  <h1 class="page-header__title">My Page</h1>
  <p class="page-header__subtitle">Page subtitle here</p>
{% endblock %}

{% block content %}
  <!-- Your page content using SSOT components -->
  <div class="card">
    <div class="card__body">
      <p>Content here</p>
      <button class="btn btn--primary">Action</button>
    </div>
  </div>
{% endblock %}
```

### 2. Create Route

In your router file:

```python
from fastapi import Request
from fastapi.templating import Jinja2Templates

# Get templates instance from app state
# or import from main.py

@app.get("/tenant/my-page")
async def my_page(request: Request):
    return templates.TemplateResponse(
        "pages/my_page_ssot.html",
        {
            "request": request,
            # Template variables
            "user_name": "John",
            "items": [...],
        }
    )
```

### 3. Add to Navigation Registry

In `app/core/navigation.py`:

```python
navigation.register_stage(FlowStage(
    id="tenant_my_page",
    name="My Page",
    path="/tenant/my-page",
    role=UserRole.TENANT,
    category="primary",
    icon="📝",
    description="Description here",
    requires_storage=True,
))
```

## Available Blocks

### Required Blocks

| Block | Description | Example |
|-------|-------------|---------|
| `title` | Page title (browser tab) | `{% block title %}Journal{% endblock %}` |
| `role` | User role for navigation | `{% block role %}tenant{% endblock %}` |
| `content` | Main page content | `{% block content %}...{% endblock %}` |

### Optional Blocks

| Block | Description | Default |
|-------|-------------|---------|
| `meta_description` | SEO description | "Semptify - Free tenant rights..." |
| `page_header` | Header title/subtitle | Shows page title |
| `page_title` | Just the H1 title | "Semptify" |
| `page_subtitle` | Just the subtitle | "Tenant Rights Protection" |
| `sidebar` | Sidebar content | Default sidebar with quick links |
| `sidebar_actions` | Quick action buttons | New Entry, Upload, etc. |
| `sidebar_context` | Context info | Storage status, stats |
| `extra_css` | Page-specific styles | Empty |
| `extra_js` | Page-specific JavaScript | Empty |

## Template Variables

### Automatically Available

From `navigation` context processor:
- `navigation` - Navigation registry instance
- `request` - FastAPI Request object
- `csrf_token` - CSRF token for forms

### You Must Provide

- `user_name` - Display name
- `entries` / `documents` / `deadlines` - Data arrays
- Any page-specific variables

## Using Navigation Registry in Templates

### Link to Another Page

```html
<a href="{{ navigation.get_path('tenant_journal') }}">
  Go to Journal
</a>
```

### Get Current Page Info

```html
{# Check if we're on the journal page #}
{% if request.url.path == navigation.get_path('tenant_journal') %}
  <span class="active">Journal</span>
{% endif %}
```

### Navigation Links with Active State

```html
<nav class="nav nav--vertical">
  {% for item in navigation.get_nav_items(role) %}
    <a href="{{ item.path }}" 
       class="nav__link {% if request.url.path == item.path %}nav__link--active{% endif %}">
      {{ item.icon }} {{ item.name }}
    </a>
  {% endfor %}
</nav>
```

## SSOT Design System Components

### Buttons
```html
<button class="btn btn--primary">Primary</button>
<button class="btn btn--secondary">Secondary</button>
<button class="btn btn--accent">Accent</button>
<button class="btn btn--ghost">Ghost</button>
<button class="btn btn--danger">Danger</button>

<!-- Sizes -->
<button class="btn btn--primary btn--sm">Small</button>
<button class="btn btn--primary btn--lg">Large</button>
```

### Cards
```html
<div class="card">
  <div class="card__header">
    <h3 class="card__title">Title</h3>
    <p class="card__subtitle">Subtitle</p>
  </div>
  <div class="card__body">
    <p>Content</p>
  </div>
  <div class="card__footer">
    <button class="btn btn--secondary">Cancel</button>
    <button class="btn btn--primary">Save</button>
  </div>
</div>
```

### Forms
```html
<div class="form-group">
  <label class="form-label form-label--required" for="name">Name</label>
  <input type="text" id="name" class="form-input" required>
  <p class="form-hint">Helper text</p>
</div>

<div class="form-group">
  <label class="form-label" for="email">Email</label>
  <input type="email" id="email" class="form-input" value="invalid">
  <p class="form-error">⚠️ Please enter a valid email</p>
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
  <div>
    <strong>Information</strong>
    <p class="text-sm">Details here</p>
  </div>
</div>
```

## Layout Patterns

### Standard Page with Sidebar
```html
{% extends "base_ssot.html" %}

{% block content %}
  <!-- Content goes in main area -->
  <!-- Sidebar is automatically included -->
{% endblock %}
```

### Full-Width Page (No Sidebar)
```html
{% extends "base_ssot.html" %}

{% block sidebar %}{% endblock %}  {# Empty sidebar #}

{% block content %}
  <!-- Full-width content -->
{% endblock %}
```

### Custom Sidebar
```html
{% extends "base_ssot.html" %}

{% block sidebar %}
<aside class="sidebar hide-mobile">
  <div class="sidebar__section">
    <h3 class="sidebar__title">My Section</h3>
    <!-- Custom content -->
  </div>
</aside>
{% endblock %}
```

## Jinja2 Control Flow

### If/Else
```html
{% if entries|length > 0 %}
  {% for entry in entries %}
    <div class="card">{{ entry.title }}</div>
  {% endfor %}
{% else %}
  <p>No entries found.</p>
{% endif %}
```

### For Loops
```html
{% for deadline in deadlines %}
  <div class="{% if loop.first %}first{% endif %} {% if loop.last %}last{% endif %}">
    {{ loop.index }}. {{ deadline.title }}
  </div>
{% endfor %}
```

### Filters
```html
{{ name|upper }}           {# Uppercase #}
{{ text|truncate(100) }}   {# Truncate #}
{{ date|date("%Y-%m-%d") }} {# Format date #}
{{ html|safe }}            {# Render as HTML #}
{{ value|default("N/A") }} {# Default value #}
```

### Set Variable
```html
{% set total = entries|length %}
<p>Total: {{ total }}</p>
```

## Example: Complete Journal Page

```html
{% extends "base_ssot.html" %}

{% block title %}Journal{% endblock %}
{% block role %}tenant{% endblock %}

{% block page_header %}
  <h1 class="page-header__title">Journal</h1>
  <p class="page-header__subtitle">Document your tenancy journey</p>
{% endblock %}

{% block sidebar_actions %}
  <button class="btn btn--primary w-full mb-2" onclick="showAddModal()">
    ➕ New Entry
  </button>
{% endblock %}

{% block sidebar_context %}
  <div class="sidebar__section">
    <h3 class="sidebar__title">Stats</h3>
    <div class="flex items-center justify-between text-sm">
      <span class="text-secondary">Entries</span>
      <span class="badge badge--secondary">{{ entries|length }}</span>
    </div>
  </div>
{% endblock %}

{% block content %}
  {% if entries %}
    {% for entry in entries %}
      <article class="card">
        <div class="card__body">
          <h4>{{ entry.title }}</h4>
          <p>{{ entry.description }}</p>
        </div>
      </article>
    {% endfor %}
  {% else %}
    <div class="card">
      <div class="card__body text-center py-12">
        <p class="text-secondary">No entries yet.</p>
        <button class="btn btn--primary mt-4" onclick="showAddModal()">
          Create First Entry
        </button>
      </div>
    </div>
  {% endif %}
{% endblock %}

{% block extra_js %}
  function showAddModal() {
    // Your JavaScript
  }
{% endblock %}
```

## Semptify Mandates Compliance

### ✅ Free Forever, No Ads
- No ad-related code in templates
- No tracking pixels
- No sponsored content areas

### ✅ Privacy-First
- "Privacy note" included in forms
- Data stored in user cloud (not our servers)
- Minimal data collection

### ✅ Tenant Rights Focus
- Law Library links prominent
- Legal aid hotline in footer
- Rights-focused language

### ✅ Evidence Preservation
- Document upload emphasized
- Journal for timeline tracking
- Clear action guidance

### ✅ Accessibility
- ARIA labels on all interactive elements
- Skip links for keyboard navigation
- Focus states on all buttons/links
- Semantic HTML structure

## Testing Your Template

### 1. Verify Compilation
```bash
python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('app/templates')); env.get_template('pages/my_page_ssot.html').render()"
```

### 2. Check Responsiveness
- Resize browser to test mobile/desktop
- Verify hamburger menu appears on mobile
- Check sidebar hides on mobile

### 3. Test Accessibility
- Tab through all interactive elements
- Verify focus indicators visible
- Check ARIA labels present
- Test with screen reader

### 4. Validate SSOT Compliance
- No inline styles (`style="..."`)
- No hardcoded colors
- Uses `navigation.get_path()` for all links
- Uses SSOT component classes

## Migration from Legacy Templates

### Before (Legacy)
```html
<!DOCTYPE html>
<html>
<head>
  <title>Page Title</title>
  <style>
    /* Page-specific styles */
    .custom { color: #2c5aa0; }
  </style>
</head>
<body>
  <div style="background: white; padding: 16px;">
    <h1>Title</h1>
    <a href="/hardcoded/path">Link</a>
  </div>
</body>
</html>
```

### After (SSOT)
```html
{% extends "base_ssot.html" %}

{% block title %}Page Title{% endblock %}
{% block role %}tenant{% endblock %}

{% block content %}
  <div class="card">
    <div class="card__body">
      <h1 class="text-2xl font-bold">Title</h1>
      <a href="{{ navigation.get_path('target_page') }}">Link</a>
    </div>
  </div>
{% endblock %}
```

## Best Practices

### DO:
- ✅ Extend `base_ssot.html`
- ✅ Use `{% block %}` for all content
- ✅ Use SSOT component classes (`btn`, `card`, etc.)
- ✅ Use `navigation.get_path()` for links
- ✅ Add `role` block for navigation
- ✅ Keep page-specific CSS minimal
- ✅ Use semantic HTML

### DON'T:
- ❌ Copy/paste full HTML structure
- ❌ Use inline styles
- ❌ Hardcode URLs
- ❌ Skip the `role` block
- ❌ Add redundant CSS that's in design system
- ❌ Forget accessibility attributes

---

## Summary

1. **One base template** = consistent layout
2. **Jinja2 blocks** = page customization
3. **SSOT navigation** = no broken links
4. **SSOT design system** = consistent styling
5. **Semptify mandates** = built into every page

**Start every new page with:**
```html
{% extends "base_ssot.html" %}
{% block title %}Title{% endblock %}
{% block role %}tenant{% endblock %}
{% block content %}
  <!-- Your content -->
{% endblock %}
```
