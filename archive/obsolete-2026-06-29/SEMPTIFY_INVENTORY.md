# Semptify 5.0 - Complete Feature Inventory

**Generated:** April 29, 2026  
**Purpose:** Categorize all functions, routes, modules, and services  
**Categories:** Library | Office | Tools | Help | Misc | Uncategorized

---

## 📚 LIBRARY - Rights, Laws, Education, Guides

### Routers
| File | Routes | Purpose |
|------|--------|---------|
| `law_library.py` | /api/law-library/* | State laws, statutes, legal references |
| `state_laws.py` | /api/state-laws/* | State-specific tenant rights |
| `documentation.py` | /api/docs/* | API documentation, guides |
| `page_index.py` | /api/pages/* | Page registry, navigation |
| `registry.py` | /api/registry/* | Resource registry |

### Core Modules
| File | Purpose |
|------|---------|
| `document_hub.py` | Document organization hub |
| `page_contracts.py` | Page contract definitions |
| `page_manifest.py` | Page manifest/registry |

### Services
- (None specifically identified)

---

## 🏢 OFFICE - Document Management, Journal, Vault, Storage

### Routers (Core)
| File | Routes | Purpose | Status |
|------|--------|---------|--------|
| `documents.py` | /api/documents/* | Document upload, processing, lifecycle | Core |
| `vault.py` | /api/vault/* | Document vault management | Core |
| `vault_engine.py` | /api/vault-engine/* | Vault engine API | Core |
| `storage.py` | /storage/*, /api/storage/* | Cloud storage OAuth, connections | Core |
| `timeline_unified.py` | /api/timeline-unified/* | Unified timeline viewer | ✅ **Core** |
| `briefcase.py` | /api/briefcase/* | Tenant briefcase (documents + timeline) | ✅ **Core** |
| `pdf_tools.py` | /api/pdf-tools/* | PDF manipulation | Core |
| `preview.py` | /api/preview/* | Document preview | Core |
| `document_converter.py` | /api/convert/* | Format conversion | Core |

### Routers (Extended)
| File | Routes | Purpose |
|------|--------|---------|
| `vault_all_in_one.py` | /api/vault-all-in-one/* | Unified vault operations |
| `timeline.py` | /api/timeline/* | Legacy timeline (deprecated) |
| `overlays.py` | /api/overlays/* | Document overlays, annotations |
| `unified_overlays.py` | /api/unified-overlays/* | Unified overlay system |
| `intake.py` | /api/intake/* | Document intake pipeline |
| `extraction.py` | /api/extraction/* | Document text/OCR extraction |
| `recognition.py` | /api/recognition/* | Document type recognition |
| `cloud_sync.py` | /api/cloud-sync/* | Cloud synchronization |
| `batch.py` | /api/batch/* | Batch document operations |
| `export_import.py` | /api/export/*, /api/import/* | Data export/import |
| `document_delivery.py` | /api/delivery/* | Document delivery to third parties |

### Core Modules
| File | Purpose |
|------|---------|
| `tenant_briefcase.py` | Tenant briefcase data model |
| `vault_paths.py` | Vault path definitions |
| `unified_overlay_manager.py` | Overlay management |
| `storage_middleware.py` | Storage requirement enforcement |
| `file_validator.py` | File validation |
| `preview_generator.py` | Document preview generation |
| `oauth_token_manager.py` | OAuth token management |

### Services (in templates/services/)
| File | Purpose |
|------|---------|
| `vault_upload_service.py` | Vault upload handling |
| `ocr_service.py` | OCR processing |
| `recognition_service.py` | Document recognition |
| `preview_service.py` | Preview generation |

---

## 🔧 TOOLS - Calculators, Generators, Utilities, Analysis

### Routers (Core)
| File | Routes | Purpose | Status |
|------|--------|---------|--------|
| `legal_analysis.py` | /api/legal-analysis/* | Evidence classification, merit assessment | ✅ **Core** - Brain optional |
| `tools_api.py` | /api/tools/* | Tools API endpoints | Core |
| `contacts.py` | /api/contacts/* | Contact management | Core |
| `search.py` | /api/search/* | Global search | Core |
| `pdf_tools.py` | /api/pdf-tools/* | PDF manipulation | Core |
| `preview.py` | /api/preview/* | Document preview | Core |
| `document_converter.py` | /api/convert/* | Format conversion | Core |

### Routers (Extended)
| File | Routes | Purpose |
|------|--------|---------|
| `calendar.py` | /api/calendar/* | Deadline tracking, calendar |
| `form_data.py` | /api/form-data/* | Form data handling |
| `plan_maker.py` | /api/plan/* | Planning tools |
| `tactics.py` | /api/tactics/* | Response tactics |
| `location.py` | /api/location/* | Location services |
| `dashboard.py` | /api/dashboard/* | Dashboard data |

### Core Modules
| File | Purpose |
|------|---------|
| `calendar_service.py` | Calendar/deadline tracking |
| `plan_maker_service.py` | Planning utilities |
| `functionx.py` | Extended functions |

### Services
| File | Purpose |
|------|---------|
| `functionx_service.py` | Function extensions |
| `location_service.py` | Location utilities |

---

## 🆘 HELP - Support, Guidance, Resources

### Routers
| File | Routes | Purpose |
|------|--------|---------|
| `help.html` | /help.html | Help page (static) |
| `guided_intake.py` | /api/guided-intake/* | Guided user intake |
| `role_ui.py` | /ui/* | UI routing, role selection |
| `onboarding.py` | /onboarding/* | Onboarding flow |
| `workflow.py` | /api/workflow/* | Workflow engine |
| `health.py` | /health, /api/health/* | Health checks |

### Core Modules
| File | Purpose |
|------|---------|
| `workflow_engine.py` | Central workflow routing |
| `checkpoint_middleware.py` | Smart checkpoint gate |
| `process_registry.py` | Process registration |
| `error_handling.py` | Error handling |

---

## 🔬 RESEARCH/INTELLIGENCE (Misc Category)

### Routers
| File | Routes | Purpose |
|------|--------|---------|
| `legal_analysis.py` | /api/legal-analysis/* | AI legal analysis |
| `legal_trails.py` | /api/legal-trails/* | Legal trail tracking |
| `litigation_intelligence.py` | /api/litigation/* | Litigation data |
| `research.py` | /api/research/* | Research tools |
| `crawler.py` | /api/crawler/* | Web crawling |
| `extraction.py` | /api/extraction/* | Data extraction |
| `recognition.py` | /api/recognition/* | Document recognition |

### Core Modules
| File | Purpose |
|------|---------|
| `timeline_extraction.py` | Timeline data extraction |

---

## ⚖️ LEGAL/COURT (Advanced - NOT in welcome page promises)

### Routers
| File | Routes | Purpose |
|------|--------|---------|
| `court_forms.py` | /api/court-forms/* | Court form generation |
| `court_packet.py` | /api/court-packet/* | Court packet assembly |
| `legal_filing.py` | /api/legal-filing/* | Legal filing assistance |
| `eviction_defense.py` | /api/eviction/* | Eviction defense tools |
| `eviction/` | /api/eviction/* | Eviction procedures, flows, forms, learning |
| `case_builder.py` | /api/case-builder/* | Case building |
| `complaints.py` | /api/complaints/* | Complaint filing |
| `housing_accountability.py` | /api/accountability/* | Housing accountability |

### Core Modules
| File | Purpose |
|------|---------|
| `legal_filing_service.py` | Legal filing services |

---

## 🤖 AI/BRAIN/CO-PILOT (Advanced - NOT in welcome page)

### Routers
| File | Routes | Purpose |
|------|--------|---------|
| `brain.py` | /api/brain/* | AI brain engine |
| `copilot.py` | /api/copilot/* | AI copilot |
| `emotion.py` | /api/emotion/* | Emotion detection |
| `auto_mode.py` | /api/auto/* | Auto-pilot mode |
| `context_loop.py` | /api/context/* | Context loop |
| `positronic_mesh.py` | /api/positronic/* | Positronic mesh |
| `mesh.py` | /api/mesh/* | Mesh network |
| `mesh_network.py` | /api/mesh-network/* | Mesh networking |

### Core Modules
| File | Purpose |
|------|---------|
| `positronic_mesh.py` | Positronic mesh core |
| `mesh_config.py` | Mesh configuration |
| `mesh_deferral.py` | Mesh deferral |
| `mesh_integration.py` | Mesh integration |
| `mesh_network.py` | Mesh network core |
| `distributed_mesh.py` | Distributed mesh |

### Services
| File | Purpose |
|------|---------|
| `auto_mode_summary_service.py` | Auto-mode summaries |

---

## 📊 ANALYTICS/DASHBOARD (Enterprise/Advanced)

### Routers
| File | Routes | Purpose |
|------|--------|---------|
| `analytics.py` | /api/analytics/* | Usage analytics |
| `enterprise_dashboard.py` | /api/enterprise/* | Enterprise dashboard |
| `tenancy_hub.py` | /api/tenancy-hub/* | Tenancy hub |
| `progress.py` | /api/progress/* | Progress tracking |
| `search.py` | /api/search/* | Search functionality |

### Core Modules
| File | Purpose |
|------|---------|
| `analytics_engine.py` | Analytics processing |
| `performance_monitor.py` | Performance monitoring |

---

## 👥 MULTI-USER/COLLABORATION (Advocate/Legal/Manager roles)

### Routers
| File | Routes | Purpose |
|------|--------|---------|
| `communication.py` | /api/communication/* | Messaging, notifications |
| `document_delivery.py` | /api/delivery/* | Document delivery |
| `invite_codes.py` | /api/invite/* | Invite code management |
| `role_upgrade.py` | /api/roles/* | Role upgrade requests |

### Core Modules
| File | Purpose |
|------|---------|
| `invite_codes.py` | Invite code system |

### Services
| File | Purpose |
|------|---------|
| `communication_service.py` | Communication handling |
| `document_delivery_service.py` | Document delivery |
| `user_service.py` | User management |

---

## 🔧 ADMIN/DEVELOPMENT (Internal)

### Routers
| File | Routes | Purpose |
|------|--------|---------|
| `auth.py` | /api/auth/* | Authentication |
| `security.py` | /api/security/* | Security endpoints |
| `testing.py` | /api/testing/* | Testing utilities |
| `development.py` | /api/dev/* | Development tools |
| `setup.py` | /api/setup/* | Setup/configuration |
| `components.py` | /api/components/* | Component management |
| `plugins.py` | /api/plugins/* | Plugin system |
| `module_hub.py` | /api/module-hub/* | Module hub |
| `free_api.py` | /api/free/* | Free API tier |
| `funding_search.py` | /api/funding/* | Funding search |
| `hud_funding.py` | /api/hud/* | HUD funding resources |

### Core Modules
| File | Purpose |
|------|---------|
| `config.py` | Configuration management |
| `database.py` | Database connection |
| `cache.py` | Caching |
| `cache_manager.py` | Cache management |
| `security.py` | Security utilities |
| `advanced_security.py` | Advanced security |
| `advanced_rate_limiter.py` | Rate limiting |
| `audit.py` | Audit logging |
| `audit_logger.py` | Audit log processing |
| `gdpr_compliance.py` | GDPR compliance |
| `compliance.py` | Compliance framework |
| `data_deletion.py` | Data deletion |
| `logging_config.py` | Logging configuration |
| `logging_middleware.py` | Request logging |
| `features.py` | Feature flags |
| `id_gen.py` | ID generation |
| `user_context.py` | User context/roles |
| `cookie_auth.py` | Cookie authentication |

---

## 🚫 NOT IN ANY CATEGORY (Remove/Defer)

### Public Exposure/Campaign (Contradicts "quiet" philosophy)
| File | Reason |
|------|--------|
| `campaign.py` | Public campaigns - contradicts "Semptify doesn't draw attention to itself" |
| `public_exposure.py` | Public shaming - contradicts philosophy |
| `fraud_exposure.py` | Fraud exposure - outside scope |

---

## 📋 STATIC HTML PAGES

### Navigation Structure
| Page | Category | Purpose |
|------|----------|---------|
| `home.html` | Help/Home | Main navigation hub |
| `library.html` | Library | Law library, rights guides |
| `office.html` | Office | Document office, vault access |
| `tools.html` | Tools | Calculators, utilities |
| `help.html` | Help | Support, guidance |
| `search.html` | Misc | Search functionality |

### Public Pages
| Page | Purpose |
|------|---------|
| `public/welcome.html` | Entry point, philosophy |
| `public/privacy.html` | Privacy policy |
| `public/terms.html` | Terms of service |
| `public/about.html` | About Semptify |

### Onboarding
| Page | Purpose |
|------|---------|
| `onboarding/select-role.html` | Role selection (SSOT) |
| `onboarding/storage-select.html` | Storage provider selection |
| `onboarding/validation/validate-advocate.html` | Advocate validation |
| `onboarding/validation/validate-legal.html` | Legal validation |

---

## ✅ RECOMMENDATION: Keep for Semptify 5.0

Based on welcome page promises ("Document Everything. Avoid the Pitfalls."):

**CORE - Keep:**
1. **Library:** `law_library.py`, `state_laws.py` - Rights & responsibilities education
2. **Office:** `documents.py`, `vault.py`, `storage.py`, `timeline.py`, `briefcase.py` - Journal & document storage
3. **Tools:** `tools_api.py`, `calendar.py` - Deadline tracking, basic utilities
4. **Help:** `onboarding.py`, `role_ui.py`, `workflow.py`, `guided_intake.py` - User guidance
5. **Core:** Auth, security, database, config, workflow_engine, checkpoint_middleware

**DEFER to Extended/Research:**
- AI features: `brain.py`, `copilot.py`, `emotion.py`, `auto_mode.py`
- Legal filing: `court_forms.py`, `court_packet.py`, `legal_filing.py`, `eviction_defense.py`
- Case building: `case_builder.py`, `complaints.py`
- Research: `crawler.py`, `legal_analysis.py`, `research.py`
- Multi-user: `communication.py`, `document_delivery.py` (advocate/legal tools)
- Analytics: `analytics.py`, `enterprise_dashboard.py`

**REMOVE (contradicts philosophy):**
- `campaign.py`, `public_exposure.py`, `fraud_exposure.py`

