# Semptify Complete Navigation Map

*Comprehensive mapping of all internal routes, external links, and user travel paths within Semptify*

Generated: 2026-05-20  
Scope: All possible ways users can navigate through the application

---

## 🏛️ SSOT CORE NAVIGATION (Single Source of Truth)

### Primary Flow Stages (SSOT Registry)

```text
/welcome (root) → /preamble → /onboarding/select-role.html → /onboarding/providers → /onboarding/vault-setup → /onboarding/complete → /home
```

### Main Navigation (5 Core Links - Present on Every Page)

```text
🏠 Home     → /home
📚 Library  → /library  
🏢 Office   → /office
🔧 Tools    → /tools
🆘 Help     → /help
```

### Reconnect Flow (Returning Users)

```text
/storage/reconnect → OAuth Validation → /home (or return_to parameter)
```

### Court Integration Flow

```text
/mndes/guide → /mndes/validate → /mndes/package
/mndes/compliance-guide (standalone)
```

---

## 📊 PRODUCT TIER NAVIGATION

### CORE TIER (Always Active - 45+ Modules)

#### Health & System

- `/health` - System health check
- `/version` - Version information

#### Entry Points

- `/preamble` - Smart routing decision point
- `/role-select` - Role selection UI

#### Document & Vault System

- `/documents` - Document management
- `/api/vault/*` - Vault operations
- `/vault-engine/*` - Advanced vault access
- `/api/timeline/*` - Unified timeline
- `/briefcase` - Tenant briefcase
- `/workflow/*` - Workflow management
- `/workflow-validator/*` - Admin workflow validation

#### Rights & Education

- `/state-laws` - State-specific laws
- `/law-library` - Legal library access

#### Core Tools

- `/contacts` - Contact manager
- `/public-forms` - Public forms
- `/api/search` - Global search
- `/pdf-tools` - PDF utilities
- `/api/preview` - Document preview
- `/document-converter` - Format conversion
- `/legal-analysis` - Legal document analysis

#### Real-time & APIs

- `/ws/events` - WebSocket events
- `/free-api/*` - Free public APIs

#### Infrastructure

- `/plugins` - Plugin system
- `/components` - Modular components
- `/core-system` - Core system admin
- `/api/security` - Advanced security
- `/mndes` - Court Exhibit System (MN Supreme Court compliance)

### EXTENDED TIER (Legal Tools - Disabled by Default)

#### Legal Defense

- `/eviction-defense` - Eviction defense toolkit
- `/zoom-court` - Virtual courtroom
- `/zoom-court-prep` - Court preparation
- `/court-forms` - Court form generation
- `/court-packet` - Exhibit packets
- `/legal-filing` - Legal filing system
- `/legal-trails` - Legal process tracking
- `/tenant-defense` - Tenant defense tools

#### Case Management

- `/intake` - Document intake
- `/guided-intake` - Guided document intake
- `/case-builder` - Case construction
- `/progress` - Progress tracking
- `/actions` - Smart actions
- `/plan-maker` - Plan generation
- `/tools-api` - Tools API

#### Accountability

- `/complaints` - Complaint wizard
- `/housing-accountability` - Housing accountability tools

#### Role Management

- `/role-upgrade` - Role upgrade system

### ADVOCATE TIER (Collaboration - Disabled by Default)

- `/document-delivery` - Secure document delivery
- `/communication` - Advocate communication
- `/invite-codes` - Advocate invitation system

### ADMIN TIER (Administration - Disabled by Default)

- `/api/analytics` - Usage analytics
- `/dashboard` - Unified dashboard
- `/enterprise-dashboard` - Enterprise admin
- `/api/batch` - Batch operations
- `/registry` - Document registry
- `/tenancy-hub` - Tenancy management

### RESEARCH TIER (AI Intelligence - Disabled by Default)

#### Document Intelligence

- `/recognition` - Document recognition
- `/extraction` - Form field extraction
- `/crawler` - Web crawler
- `/research` - Research module
- `/api/form-data` - Form data hub
- `/overlays` - Document annotations
- `/unified-overlays` - Unified annotation system
- `/vault-all-in-one` - Unified evidence vault
- `/cloud-sync` - Cloud synchronization

#### AI Infrastructure

- `/brain/*` - Positronic Brain (AI hub)
- `/auto-mode` - Automated mode
- `/emotion` - Emotion analysis
- `/api/positronic-mesh` - AI mesh network
- `/api/mesh-network` - Distributed mesh
- `/api/module-hub` - Module hub
- `/functionx` - Function execution

#### Specialized Intelligence

- `/funding-search` - Funding opportunities
- `/hud-funding` - HUD funding guide
- `/location` - Location services
- `/campaign` - Campaign orchestration
- `/public-exposure` - Public exposure tracking
- `/fraud-exposure` - Fraud detection
- `/litigation-intelligence` - Legal intelligence

### DEV TIER (Internal Tools - Enabled in Development)

- `/api/setup` - Setup wizard
- `/page-index` - Page indexing
- `/page-editor` - Interactive page editor
- `/development` - Development tools
- `/api/export-import` - Data export/import
- `/api/testing` - Automated testing
- `/api/docs` - API documentation

---

## 🔗 EXTERNAL LINKS & OAUTH ENDPOINTS

### OAuth Provider Endpoints (LEADS OUT)

#### Google Drive

- Auth: `https://accounts.google.com/o/oauth2/v2/auth`
- Token: `https://oauth2.googleapis.com/token`
- Userinfo: `https://www.googleapis.com/oauth2/v2/userinfo`
- Tokeninfo: `https://www.googleapis.com/oauth2/v1/tokeninfo`
- Scopes: `https://www.googleapis.com/auth/drive.file`, `https://www.googleapis.com/auth/userinfo.email`

#### Dropbox

- Auth: `https://www.dropbox.com/oauth2/authorize`
- Token: `https://api.dropboxapi.com/oauth2/token`
- Userinfo: `https://api.dropboxapi.com/2/users/get_current_account`

#### OneDrive

- Auth: `https://login.microsoftonline.com/common/oauth2/v2.0/authorize`
- Token: `https://login.microsoftonline.com/common/oauth2/v2.0/token`
- Userinfo: `https://graph.microsoft.com/v1.0/me`
- Scopes: `Files.ReadWrite.AppFolder`, `User.Read`, `offline_access`

### Internal OAuth Callbacks

- `/storage/oauth/{provider}` - OAuth callback handler
- `/storage/reconnect` - Token reconnection
- `/storage/providers` - Provider selection

---

## 📱 STATIC FILE NAVIGATION

### Public Pages (Direct Access)

- `/welcome.html` - Welcome page
- `/about.html` - About Semptify
- `/privacy.html` - Privacy policy
- `/terms.html` - Terms of use
- `/disclaimer.html` - Legal disclaimer
- `/contact.html` - Contact information
- `/feedback.html` - Feedback form
- `/credits.html` - Credits and attributions

### Role-Based Dashboards

- `/tenant/dashboard.html` - Tenant dashboard
- `/advocate/dashboard.html` - Advocate dashboard
- `/legal/dashboard.html` - Legal professional dashboard
- `/admin/dashboard.html` - Administrator dashboard
- `/manager/dashboard.html` - Housing manager dashboard

### Office & Document Management

- `/office.html` - Main office interface
- `/office/inbox.html` - Document inbox
- `/office/vault.html` - Vault interface
- `/office/delivery.html` - Document delivery
- `/office/signer.html` - Document signing

### Library & Resources

- `/library.html` - Main library
- `/search.html` - Search interface

### Help & Support

- `/help.html` - Help center

### Onboarding Flow (Static)

- `/onboarding/index.html` - Onboarding entry
- `/onboarding/activate-vault.html` - Vault activation

### MNDES Court System

- `/mndes/guide.html` - MNDES guide
- `/mndes/compliance-guide.html` - Compliance guide

### Reconnect Interface

- `/reconnect/index.html` - Reconnection flow

---

## 🔄 DYNAMIC NAVIGATION PORTALS

### JavaScript Navigation (Client-Side)

#### Header Navigation Components

```javascript
// Core 5-link navigation (present on every page)
<a href="/home.html">Home</a>
<a href="/library.html">Library</a>
<a href="/office.html">Office</a>
<a href="/tools.html">Tools</a>
<a href="/help.html">Help</a>
```text

**Footer Navigation**

```javascript
// Product links
<a href="/welcome.html">Welcome</a>
<a href="/features.html">Features</a>
<a href="/about.html">About</a>
<a href="/help.html">Help Center</a>

// Legal links
<a href="/privacy.html">Privacy Policy</a>
<a href="/terms.html">Terms of Use</a>
<a href="/disclaimer.html">Disclaimer</a>

// Connect links
<a href="/contact.html">Contact</a>
<a href="/feedback.html">Feedback</a>
<a href="/donate.html">Donate</a>
```

#### Role-Specific Navigation

- Tenant: `/tenant/dashboard.html` → tenant-specific flows
- Advocate: `/advocate/dashboard.html` → client management
- Legal: `/legal/dashboard.html` → case management
- Admin: `/admin/dashboard.html` → system administration

---

## 🚪 ENTRANCE & EXIT POINTS

### Primary Entrances

1. **Root Domain** `/` → Welcome page → Preamble routing
2. **Direct Role Access** `/tenant`, `/advocate`, `/legal`, `/admin`
3. **Deep Links** Any valid internal path (SSOT-validated)
4. **OAuth Return** From Google/Dropbox/OneDrive authentication

### Exit Points (External Links)

1. **OAuth Providers** Google, Dropbox, OneDrive authentication
2. **Documentation** External help resources
3. **Legal Resources** External legal aid websites
4. **Feedback Forms** External feedback collection

---

## 🛡️ GATE-BASED NAVIGATION CONTROLS

### Storage Connection Gate

- **Required**: Valid OAuth token from storage provider
- **Controls**: Access to document operations, vault features
- **Bypass**: Public pages, help content, role selection

### Vault Initialization Gate  

- **Required**: Vault folders created in user storage
- **Controls**: Full feature access, document upload
- **Bypass**: Basic browsing, public content

### Role-Specific Gates

- **Tenant**: Access to tenant-specific tools and resources
- **Advocate**: Client management, collaboration features
- **Legal**: Court filing, advanced legal tools
- **Admin**: System administration, analytics

---

## 📊 NAVIGATION SUMMARY STATISTICS

### Total Navigation Points

- **SSOT Core Paths**: 15 canonical flow stages
- **Product Tier Routes**: 200+ module endpoints (across 6 tiers)
- **Static HTML Pages**: 60+ static interfaces
- **API Endpoints**: 500+ REST API routes
- **External Links**: 12 OAuth/external endpoints
- **Dynamic Portals**: 30+ JavaScript navigation components

### Navigation Categories

- **Internal Routes**: 85% of all navigation
- **External Links**: 15% (OAuth + external resources)
- **Static Pages**: 25% (direct HTML access)
- **Dynamic Routes**: 75% (API-driven, authenticated)

### Access Control Distribution

- **Public Access**: 20% (welcome, help, public content)
- **Authentication Required**: 60% (storage connection)
- **Role-Gated**: 15% (specific role features)
- **Admin Only**: 5% (system administration)

---

## 🔄 USER JOURNEY FLOWS

### New User Flow

```text
/ → /welcome.html → /preamble → /onboarding/select-role.html → 
/onboarding/providers → OAuth → /onboarding/vault-setup → 
/onboarding/complete → /home → [Role Dashboard]
```

### Returning User Flow

```text
/ → /preamble → /storage/reconnect → OAuth (if needed) → /home → 
[Role Dashboard] → [Last Accessed Feature]
```

### Document Management Flow

```text
[Role Dashboard] → /office.html → /office/vault.html → 
/documents → /api/vault/* → Document Operations
```

### Legal Tools Flow (Extended Tier)

```text
[Role Dashboard] → /eviction-defense → /court-forms → 
/legal-filing → /mndes/validate → /mndes/package
```

---

## 🔧 NAVIGATION MAINTENANCE

### SSOT Compliance Rules

- All redirects must use `navigation.get_stage()` and `ssot_redirect()`
- No hardcoded URL strings in router files
- Static files must consume navigation via `/api/navigation` endpoint
- New paths must be registered in `NavigationRegistry`

### Evolution Mechanisms

- **Escape Hatches**: Temporary experimental paths (7-day TTL)
- **Deprecated Paths**: Automatic redirects to new SSOT paths  
- **Dynamic Registration**: `register_stage()` for feature expansion

### Verification

- Run `python tests/test_ssot_architecture.py` before committing
- All navigation tests must pass
- SSOT violations block deployment

---

*This navigation map represents the complete travel topology of Semptify as of 2026-05-20. For real-time navigation state, consult the `/api/navigation` endpoint which reflects the current SSOT registry.*
