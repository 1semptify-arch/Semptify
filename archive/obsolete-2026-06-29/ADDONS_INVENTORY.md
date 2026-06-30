# Semptify Add-ons Inventory
# ============================================================
# All routers listed here exist in the codebase but are
# DISABLED in main.py for the Semptify 5.0 base release.
#
# To re-enable an add-on:
#   1. Uncomment the _safe_router_import() line in main.py
#   2. Uncomment the include_if() / include_router() line in main.py
#   3. Add a consent gate if the add-on reads user documents
#
# Product Family:
#   Semptify 5.0        — base tenant journal (always free)
#   Semptify Extended   — legal & advocacy add-ons (consent-gated)
#   Semptify Research   — AI document intelligence (separate service)
#   Semptify Go         — mobile edition (https://github.com/1semptify-arch/SemptifyGo)
# ============================================================

## SEMPTIFY 5.0 — BASE (active in main.py)
| Router | File | Purpose |
|---|---|---|
| storage | app/routers/storage.py | OAuth, session, reconnect, vault auth |
| onboarding | app/routers/onboarding.py | New user onboarding flow |
| documents | app/routers/documents.py | Document upload, storage, retrieval |
| vault | app/routers/vault.py | Vault access API |
| vault_engine | app/routers/vault_engine.py | Vault access control |
| timeline_unified | app/routers/timeline_unified.py | Tenant journal / event timeline |
| workflow | app/routers/workflow.py | SSOT routing engine (workflow_engine) |
| role_ui | app/routers/role_ui.py | Role-based home page routing |
| health | app/routers/health.py | Health checks and metrics |
| websocket | app/routers/websocket.py | Real-time events |
| free_api | app/routers/free_api.py | Minnesota tenant rights public APIs |
| state_laws | app/routers/state_laws.py | State-specific housing law info |
| contacts | app/routers/contacts.py | Track landlords, attorneys, witnesses |
| search | app/routers/search.py | Universal search across vault content |
| pdf_tools | app/routers/pdf_tools.py | PDF reader, viewer, page extractor |
| preview | app/routers/preview.py | Multi-format document preview |
| document_converter | app/routers/document_converter.py | Markdown to DOCX/HTML conversion |
| invite_codes | app/routers/invite_codes.py | Advocate/Legal role validation |
| role_upgrade | app/routers/role_upgrade.py | Role verification API |
| plugins | app/routers/plugins.py | Extensible module architecture |

---

## SEMPTIFY EXTENDED — EVICTION DEFENSE ADD-ON
*Requires: user consent to eviction assistance tools*
| Router | File | Purpose |
|---|---|---|
| eviction_defense | app/routers/eviction_defense.py | Guided eviction defense workflows |
| eviction (dakota) | app/routers/eviction/ | Dakota County specific flows, forms, procedures |
| zoom_court | app/routers/zoom_court.py | Zoom courtroom stub |
| zoom_court_prep | app/routers/zoom_court_prep.py | Hearing preparation and tech checks |

---

## SEMPTIFY EXTENDED — LEGAL PACKET ADD-ON
*Requires: user consent to legal packet generation*
| Router | File | Purpose |
|---|---|---|
| court_forms | app/routers/court_forms.py | Auto-generate Minnesota court forms |
| court_packet | app/routers/court_packet.py | Export court-ready document packets |
| legal_filing | app/routers/legal_filing.py | Legal merit and filing analysis |
| legal_analysis | app/routers/legal_analysis.py | Evidence and legal consistency analysis |
| legal_trails | app/routers/legal_trails.py | Track violations, claims, deadlines |
| law_library | app/routers/law_library.py | Housing law reference library |

---

## SEMPTIFY EXTENDED — CASE MANAGEMENT ADD-ON
| Router | File | Purpose |
|---|---|---|
| case_builder | app/routers/case_builder.py | Case management and intake |
| briefcase | app/routers/briefcase.py | Document and folder organization |
| intake | app/routers/intake.py | Document intake and extraction |
| guided_intake | app/routers/guided_intake.py | Conversational intake flow |
| progress | app/routers/progress.py | User journey progress tracking |
| actions | app/routers/actions.py | Smart action recommendations |
| plan_maker | app/routers/plan_maker.py | Accountability plan builder |
| tactics | (commented out) | Proactive defense strategies |

---

## SEMPTIFY EXTENDED — ACCOUNTABILITY ADD-ON
| Router | File | Purpose |
|---|---|---|
| complaints | app/routers/complaints.py | Complaint filing wizard |
| housing_accountability | app/routers/housing_accountability.py | Regulatory compliance and oversight |
| fraud_exposure | app/routers/fraud_exposure.py | Fraud analysis and detection |
| public_exposure | app/routers/public_exposure.py | Press releases and media campaigns |
| campaign | app/routers/campaign.py | Combined complaint/fraud/press campaigns |
| litigation_intelligence | app/routers/litigation_intelligence.py | Justice-grade legal intelligence |

---

## SEMPTIFY EXTENDED — ADVOCATE NETWORK ADD-ON
*Requires: user consent to share documents with advocates*
| Router | File | Purpose |
|---|---|---|
| communication | app/routers/communication.py | Messaging and document collaboration |
| document_delivery | app/routers/document_delivery.py | Send/receive/sign documents |
| tenant_defense | app/modules/tenant_defense.py | Evidence collection, demand letters |

---

## SEMPTIFY EXTENDED — FUNDING SEARCH ADD-ON
| Router | File | Purpose |
|---|---|---|
| funding_search | app/routers/funding_search.py | LIHTC, NMTC, HUD funding search |
| hud_funding | app/routers/hud_funding.py | HUD programs and landlord eligibility |
| location | app/routers/location.py | Location detection + state resources |

---

## SEMPTIFY EXTENDED — ADMIN / REPORTING ADD-ON
| Router | File | Purpose |
|---|---|---|
| analytics | app/routers/analytics.py | Usage and performance tracking |
| dashboard | app/routers/dashboard.py | Unified dashboard data |
| enterprise_dashboard | app/routers/enterprise_dashboard.py | Premium enterprise UI and API |
| export_import | app/routers/export_import.py | GDPR-compliant data export/import |
| batch | app/routers/batch.py | Bulk document management |
| registry | app/routers/registry.py | Tamper-proof chain of custody |
| tenancy_hub | app/routers/tenancy_hub.py | Central tenancy documentation hub |

---

## SEMPTIFY RESEARCH — AI INTELLIGENCE ADD-ON
*Requires: explicit user consent to allow AI to read documents*
| Router | File | Purpose |
|---|---|---|
| recognition | app/routers/recognition.py | World-class document recognition engine |
| extraction | app/routers/extraction.py | Extract and map document data to forms |
| crawler | app/routers/crawler.py | Housing law update crawlers |
| research | app/routers/research.py | Landlord/property research and dossier |
| research_module | app/modules/research_module.py | SDK-based landlord/property dossier |
| form_data | app/routers/form_data.py | Central form data integration |
| overlays | app/routers/overlays.py | Non-destructive document annotations |
| unified_overlays | app/routers/unified_overlays.py | Unified overlay system (cloud-only) |
| vault_all_in_one | app/routers/vault_all_in_one.py | Unified evidence vault (3-timestamp) |
| cloud_sync | app/routers/cloud_sync.py | User-controlled persistent storage |

---

## SEMPTIFY AI INFRASTRUCTURE (internal — feeds Research and Extended)
| Router/Service | File | Purpose |
|---|---|---|
| brain | app/routers/brain.py | Positronic Brain — central intelligence hub |
| auto_mode | app/routers/auto_mode.py | Auto mode analysis and summaries |
| emotion | app/routers/emotion.py | Adaptive UI emotion tracking |
| positronic_mesh | app/routers/positronic_mesh.py | Workflow orchestration mesh |
| mesh_network | app/routers/mesh_network.py | Bidirectional module communication |
| mesh (distributed) | app/routers/mesh.py | P2P distributed mesh network |
| module_hub | app/routers/module_hub.py | Central module communication bus |
| functionx | app/routers/functionx.py | Action-set planning scaffold |
| context_loop | (commented out) | Core processing engine |
| adaptive_ui | (commented out) | Self-building interface |

---

## DEV / INTERNAL ONLY
| Router | File | Purpose |
|---|---|---|
| development | app/routers/development.py | Dev tools, debugging |
| testing | app/routers/testing.py | Automated testing framework |
| security | app/routers/security.py | 2FA and session management |
| documentation | app/routers/documentation.py | Developer portal / API docs |
| page_index | app/routers/page_index.py | HTML page index database |
| core_system | app/routers/core_system.py | System infrastructure services |
| components | app/routers/components.py | Modular component system |
| setup | app/routers/setup.py | Initial setup wizard |

---
*Last updated: 2026-04-29*
*Semptify 5.0 — Code is NEVER deleted, only deferred.*
