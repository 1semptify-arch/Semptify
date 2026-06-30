# Semptify 5.0 - HTML & Frontend Standards

## Document Purpose
Working log and standards for onboarding HTML pages and frontend design.

---

## Folder Structure (Current)

```
static/
├── public/                    # Public-facing pages (no auth required)
│   ├── welcome.html          # Entry point - New/Returning User buttons
│   ├── about.html            # About Semptify
│   ├── privacy.html          # Privacy policy
│   └── terms.html            # Terms of service
│
├── onboarding/               # Onboarding flow pages
│   ├── role-select.html      # Step 1: Role selection (3 roles)
│   └── validation/           # Role validation pages (future)
│
├── tenant/                   # Tenant dashboard (post-auth)
├── advocate/                 # Advocate dashboard (post-auth)
├── legal/                    # Legal dashboard (post-auth)
├── manager/                  # Manager dashboard (post-auth)
├── admin/                    # Admin panel (post-auth)
├── components/               # Reusable UI components
├── css/                      # Stylesheets
└── js/                       # JavaScript modules

staticbac/                    # BACKUP - Old reference files
└── onboarding/               # DO NOT EDIT - Reference only
    ├── welcome.html
    └── select-role.html
```

---

## Page Standards

### 1. Welcome Page (`static/public/welcome.html`)
**Purpose**: Entry point for all users
**Flow**: 
- New User → `/onboarding/role-select`
- Returning User → `/storage/reconnect`

**Required Elements**:
- Semptify branding/logo
- Clear value proposition
- Two CTA buttons side by side
- Privacy/Terms links

### 2. Role Selection Page (`static/onboarding/role-select.html`)
**Purpose**: First step of onboarding
**Flow**: Select role → Continue → Storage OAuth

**Required Elements**:
- Header with back link to `/`
- Step indicator (Step 1 of 3)
- 3 role cards:
  - Tenant (no verification)
  - Housing Advocate (invite code)
  - Licensed Attorney (bar verification)
- Selection checkmarks
- Continue button (disabled until selected)

### 3. Design System

**Colors**:
- Primary Green: `#10b981` (emerald-500)
- Dark Green: `#064e3b` (emerald-900)
- Light Green: `#065f46` (emerald-800)
- Accent: `#a7f3d0` (emerald-200)
- Background: Linear gradient `#064e3b` → `#065f46`

**Typography**:
- Font: System font stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`)
- Headings: 1.5rem - 2rem
- Body: 0.9rem - 1rem
- Small: 0.85rem

**Components**:
- Cards: `border-radius: 16px`, semi-transparent white background
- Buttons: Gradient or solid, `border-radius: 12px`
- Selection indicators: Circular checkmarks

---

## Route Mapping

| URL | File | Description |
|-----|------|-------------|
| `/` | `static/public/welcome.html` | Entry point |
| `/onboarding/role-select` | `static/onboarding/role-select.html` | Role selection |
| `/storage/reconnect` | API endpoint | Returning user OAuth |
| `/storage/providers` | API endpoint | Storage provider selection |

---

## Working Log

### 2026-04-22 - Initial Setup
- Created `static/onboarding/role-select.html` with 3 roles
- Updated `static/public/welcome.html` with New/Returning User buttons
- Updated `main.py` root route to serve from `static/public/welcome.html`
- Updated `main.py` to mount `/onboarding` from `static/onboarding/`
- Updated `start-semptify.ps1` to show correct welcome URL
- Removed `staticbac` references from main.py (kept as backup reference)

### Next Steps
- [ ] Create storage provider selection page
- [ ] Create validation pages for Advocate/Legal roles
- [ ] Test OAuth flow end-to-end
- [ ] Add responsive breakpoints for mobile

---

## Code Standards

### HTML Template
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Page] - Semptify</title>
    <style>
        /* Use design system colors */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #064e3b 0%, #065f46 100%);
            color: #fff;
        }
    </style>
</head>
<body>
    <!-- Header with back link -->
    <div class="header">
        <a href="/" class="back-link">← Back</a>
        <span class="step-indicator">Step X of Y</span>
    </div>
    
    <!-- Content -->
    
    <script>
        // JavaScript logic
    </script>
</body>
</html>
```

### CSS Standards
- Use CSS custom properties for colors (to be added)
- Mobile-first responsive design
- Flexbox/Grid for layouts
- Transition effects for interactivity

### JavaScript Standards
- Plain vanilla JS (no frameworks for static pages)
- Event delegation for dynamic elements
- URL parameter parsing for state management

---

## Notes
- `staticbac` folder is READ-ONLY backup - do not edit
- All new work goes in `static/` folder
- Test at `http://localhost:8000/` after running `start-semptify.ps1`
