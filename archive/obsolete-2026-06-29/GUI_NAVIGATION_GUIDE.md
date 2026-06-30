# 🎨 Semptify 5.0 - GUI Navigation Guide

## Central Hub
**Location**: `/static/admin/gui_navigation_hub.html`  
**Purpose**: Master landing page with links to all GUIs  
**Features**: 
- Quick access buttons
- Organized by category
- Smooth scrolling navigation
- Mobile responsive

---

## ⚙️ SETTINGS & CONFIGURATION

### 1. Easy Mode Selector
- **URL**: `/static/admin/easy_mode_selector.html`
- **For**: Everyone (beginners, non-technical users)
- **Features**:
  - Colorful, simple interface
  - 6 easy questions with emojis
  - Perfect for anybody
  - Auto-saves settings
- **Key Controls**:
  - Light/Dark theme
  - Simple/Everything mode
  - Where are you (phase)
  - Auto help toggle
  - Feeling (mood)
  - Hints toggle

### 2. Advanced Mode Selector
- **URL**: `/static/admin/mode_selector.html`
- **For**: Power users, administrators
- **Features**:
  - 28+ configuration options
  - Toggle switches & radio buttons
  - Live preview dashboard
  - Export/Import settings
  - Save to localStorage
- **Key Controls**:
  - Workflow mode (Guided/Pipeline/Assistant)
  - Dashboard adaptation
  - Theme selection
  - 7 Auto mode features
  - 5 Display options
  - 4 Performance settings

---

## 📊 DASHBOARDS & VIEWS

### 3. Main Dashboard
- **URL**: `/` (root)
- **For**: All users (daily use)
- **Features**:
  - Adaptive UI by emotional state
  - Real-time status updates
  - Auto-mode orchestration
  - Task management
  - Multi-device responsive
  - Crisis mode support

### 4. Mission Control
- **URL**: `/static/admin/mission_control.html`
- **For**: Administrators only
- **Features**:
  - Crisis mode detection
  - Emotional state indicators
  - Developer mode toggle
  - System diagnostics
  - Admin console

### 5. API Documentation
- **URL**: `/api/docs`
- **For**: Developers, API users
- **Features**:
  - Swagger/OpenAPI interface
  - Test endpoints live
  - 40+ endpoints documented
  - Generate API keys

### 6. Welcome Page
- **URL**: `/static/welcome.html`
- **For**: First-time users
- **Features**:
  - Getting started guide
  - Feature overview
  - Quick tutorial
  - Help resources

---

## 🛠️ TOOLS & UTILITIES

### 7. Document Upload
- **URL**: `/api/vault/upload`
- **For**: All users
- **Features**:
  - Drag & drop
  - Multi-file support
  - Auto-processing
  - Progress tracking

### 8. Form Generator
- **URL**: `/api/forms/`
- **For**: All users
- **Features**:
  - Adaptive forms
  - Auto-population
  - Validation
  - Save drafts
  - Export to PDF

### 9. Timeline Editor
- **URL**: `/api/timeline/`
- **For**: All users
- **Features**:
  - Visual timeline
  - Drag-to-add events
  - Auto-extract dates
  - Color-coded priority

### 10. Legal Research Tool
- **URL**: `/api/laws/`
- **For**: All users
- **Features**:
  - Full-text search
  - Jurisdiction filters
  - Case law references
  - Statute citations

### 11. AI Copilot
- **URL**: `/api/copilot/`
- **For**: All users
- **Features**:
  - Chat interface
  - Case analysis
  - Strategy recommendations
  - 24/7 availability

### 12. System Health
- **URL**: `/healthz`
- **For**: Administrators
- **Features**:
  - Server status
  - Database check
  - Performance metrics
  - Uptime tracking

---

## 📱 QUICK ACCESS LINKS

| Purpose | Beginner | Advanced | Admin |
|---------|----------|----------|-------|
| Home | `/` | `/` | `/` |
| Settings (Easy) | `/static/admin/easy_mode_selector.html` | - | - |
| Settings (Advanced) | - | `/static/admin/mode_selector.html` | ✓ |
| Mission Control | - | - | `/static/admin/mission_control.html` |
| API Docs | - | `/api/docs` | ✓ |
| Dashboard | ✓ | ✓ | ✓ |
| Navigation Hub | ✓ | ✓ | ✓ |

---

## 🗺️ SITE MAP

```
Semptify 5.0
│
├── Home (/)
│   ├── Main Dashboard
│   └── Auto Mode Orchestrator
│
├── Navigation Hub (/static/admin/gui_navigation_hub.html)
│   ├── Settings Section
│   │   ├── Easy Mode Selector (beginner)
│   │   └── Advanced Mode Selector (power user)
│   ├── Dashboards Section
│   │   ├── Mission Control (admin)
│   │   ├── API Docs (developer)
│   │   └── Welcome Page (onboarding)
│   └── Tools Section
│       ├── Document Upload
│       ├── Form Generator
│       ├── Timeline Editor
│       ├── Legal Research
│       ├── AI Copilot
│       └── System Health
│
├── API Layer (/api/*)
│   ├── Vault (documents)
│   ├── Forms
│   ├── Timeline
│   ├── Calendar
│   ├── Legal Library
│   ├── Copilot
│   ├── Auto Mode
│   ├── Health Check
│   └── 32+ more services
│
└── Admin Panel (/static/admin/*)
    ├── mission_control.html
    ├── mode_selector.html
    ├── easy_mode_selector.html
    └── gui_navigation_hub.html (YOU ARE HERE)
```

---

## 🎯 USER JOURNEY BY ROLE

### 👶 Beginner User
1. Land on welcome page → `/static/welcome.html`
2. Setup settings → `/static/admin/easy_mode_selector.html`
3. Use dashboard → `/`
4. Upload documents → `/api/vault/upload`
5. Generate forms → `/api/forms/`
6. Chat with AI → `/api/copilot/`

### 🧠 Power User / Advocate
1. Dashboard home → `/`
2. Customize settings → `/static/admin/mode_selector.html`
3. Access all tools → Use navigation hub → `/static/admin/gui_navigation_hub.html`
4. Manage timeline → `/api/timeline/`
5. Research laws → `/api/laws/`
6. Use copilot → `/api/copilot/`

### 👨‍💼 Administrator
1. Mission Control → `/static/admin/mission_control.html`
2. Check system health → `/healthz`
3. API documentation → `/api/docs`
4. Monitor dashboards → `/`
5. Manage users → Admin API endpoints
6. View diagnostics → Mission Control dev mode

---

## 💾 NAVIGATION INTEGRATION

### Add to Header Navigation
```html
<nav class="main-nav">
    <a href="/">Home</a>
    <a href="/static/admin/gui_navigation_hub.html">Navigation Hub</a>
    <a href="/static/admin/easy_mode_selector.html">Settings</a>
    <a href="/api/docs">API Docs</a>
</nav>
```

### Add to User Menu
```html
<div class="user-menu">
    <a href="/static/admin/easy_mode_selector.html">⚙️ Easy Settings</a>
    <a href="/static/admin/mode_selector.html">🧠 Advanced Settings</a>
    <a href="/static/admin/mission_control.html">🎯 Mission Control (Admin)</a>
</div>
```

---

## 🔐 ACCESS CONTROL

| Page | Public | Authenticated | Admin |
|------|--------|---------------|-------|
| Easy Mode Selector | ✓ | ✓ | ✓ |
| Advanced Mode Selector | ✓ | ✓ | ✓ |
| Dashboard | ✓ | ✓ | ✓ |
| Navigation Hub | ✓ | ✓ | ✓ |
| Mission Control | - | - | ✓ |
| API Docs | ✓ | ✓ | ✓ |
| Admin Tools | - | - | ✓ |

---

## 🚀 LAUNCHING THE HUB

**Main Entry Points:**

1. **For Everyone**: `/static/admin/gui_navigation_hub.html`
   - Central hub with all options
   - Links to all GUIs
   - Organized by category
   - Mobile responsive

2. **For Quick Setup**: `/static/admin/easy_mode_selector.html`
   - Get started immediately
   - No learning curve
   - Save choices instantly

3. **For Advanced Users**: `/static/admin/mode_selector.html`
   - Full customization
   - Export/import settings
   - Live preview

4. **For Daily Use**: `/`
   - Main dashboard
   - Adaptive interface
   - All tools accessible

---

## 📊 STATISTICS

- **Total GUI Pages**: 12 main interfaces
- **Configuration Options**: 28+ settings
- **API Endpoints**: 40+ documented routes
- **Auto-toggle Features**: 18+ features
- **Supported Languages**: HTML, CSS, JavaScript
- **Mobile Support**: 100% responsive
- **Accessibility**: WCAG compliant

---

## 🎓 GETTING STARTED

**Step 1**: Visit the Navigation Hub
```
http://localhost:8000/static/admin/gui_navigation_hub.html
```

**Step 2**: Choose your path:
- **Beginner?** → Click "Easy Settings"
- **Experienced?** → Click "Advanced Settings"  
- **Admin?** → Click "Mission Control"
- **Developer?** → Click "API Docs"

**Step 3**: Explore the interface
- Click any card to open that tool
- Use quick links in the toolbar
- Scroll to see all available options

**Done!** You're ready to use Semptify.

---

**Last Updated**: March 23, 2026  
**Version**: 5.0.0  
**Status**: Production Ready ✅
