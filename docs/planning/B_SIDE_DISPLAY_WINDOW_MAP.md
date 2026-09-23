# Semptify — Full Navigation Chart + Module Function/Control Map -> B-Side Display Window

**Generated:** 2026-09-21 · **Status:** planning reference (read-only survey — changes no code)

**Purpose:** one map of (1) every navigation path, (2) every module's functions and the
controls/options those functions expose, and (3) what each function renders in the
**B-side display window** — the shared viewer/output surface planned for the large side
of the asymmetrical Site Shell v5 layout (universal media-player style component,
precedent: Document Center viewer + `media_player.js`, shipped 2026-09-21).

**Convention used in this doc** *(assumption — correct if wrong)*: in the asymmetric
two-zone frame, **A-side = the narrow control/options rail** (`.shell-side` / the DC
guidance rail — navigation, options, filters, context, next steps) and **B-side = the
large display window** (`.shell-main` / the DC work surface — where the module's
function output renders). Physical orientation varies by variant: standard shell puts
work-left/rail-right; Document Center's `shell--dc` variant flips to rail-left/work-right.
The A/B labels follow the *role* of the pane, not its left/right position.

**Sources (all live-extracted, not hand-recalled):**
- `app/core/navigation.py` — nav SSOT (flows, role homes, main nav)
- `app/modules/*/register.py` — 1,131 `FunctionGroupContract`s across 130 modules
- `app/modules/*/module_contract.json` — 129 module-level contracts (inputs, preview/review states, output targets)
- `app/modules/*/router.py` + `app/routers/*.py` — 1,319 routes
- `app/modules/role_ui/router.py` — per-role menus + generic `/ui/tool/{module}` renderer
- `C:\master-repo\PHASE0_5_PILLAR_MAPPING.md` — module->pillar assignments (114 contracted modules)
- `SEMPTIFY_SYSTEM_MANIFEST.md` Part 5 — tier/lifecycle snapshot (2026-09-05)

---

## 1. The frame — asymmetrical layout anatomy (Site Shell v5)

```
+------------------------------------------------------------------+
| HEADER (fixed, universal)                                        |
|  brand - breadcrumb - role-colored - 'Get help now' pill         |
+-------------------------------+----------------------------------+
| B-SIDE - DISPLAY WINDOW       | A-SIDE - CONTROL RAIL            |
| (large, ~1.6fr)               | (narrow, ~1fr / >=20rem)         |
| - module function output      | - module options / filters       |
| - viewer / stream / form /    | - vault lists, item pickers      |
|   reader / table / output     | - 'goal / where you are / next'  |
| - scrolls internally          | - contextual help for the stage  |
+-------------------------------+----------------------------------+
| FNAV - function-nav rail (only when contract declares `stages`)  |
|  pos+pips - <-Back - quiet actions - gate note - gated Go->      |
+------------------------------------------------------------------+
| FOOTER (fixed, universal) - disclaimer + tiny legal/help links   |
+------------------------------------------------------------------+
```

- Grid: `header header / main side / (fnav) / footer footer`, `overflow:hidden` — desktop never page-scrolls; each pane scrolls internally. Below 900px: single-column stack.
- Role accents: `shell--advocate|legal|agency|developer|admin` shift only the header/footer wash.
- Live narration strip sits between header and the zones (WebSocket-driven, calm status line).
- Mobile (<900px) is a separate deferred toolset — this map describes the desktop poster variant.

---

## 2. Full navigation chart

### 2.1 Entry & onboarding flow (ONBOARDING_FLOW — SSOT)

```
/ (welcome) -> /preamble -> /onboarding/select-role.html -> /onboarding/providers
    -> /onboarding/vault-setup -> /onboarding/vault-setup/inspect
    -> /onboarding/complete -> role home

Returning-user branch: /storage/providers (reconnect entry) -> /storage/reconnect -> return_to
Status check: /onboarding/status -> vault_setup
```

### 2.2 Role -> canonical home (ROLE_HOME_STAGES — SSOT)

| Role key(s) | Home route | Stage id |
|---|---|---|
| tenant / user | `/tenant/start` | `tenant_home_page` |
| advocate / multi_client_advocate | `/advocate/home` | `advocate_home` |
| legal / judge | `/legal/home` | `legal_home` |
| admin | `/admin/home` | `admin_home` |
| manager | `/manager` | `manager_portal` |
| researcher / research | `/researcher/home` | `researcher_home` |
| agency | `/agency/home` | `agency_home` |
| developer | `/developer/home` | `developer_home` |
| donor_supporter | `/donor/home` | `donor_home` |

### 2.3 Universal main nav (MAIN_NAV — present on every page)

`Home /home` · `Library /library` · `Office /office` · `Tools /tools` · `Help /help`

### 2.4 Per-role menus (`role_ui` `/navigation` endpoint)

**Tenant (simplified):** My Case `/tenant` · Documents `/documents` · Timeline `/timeline` · — · My Progress `/ui/tool/progress` · — · Get Help `/tenant/help` · AI Assistant `/tenant/copilot`

**Advocate:** Dashboard `/advocate` · Documents `/documents` · Timeline `/timeline` · My Clients `/advocate/clients` · Case Queue `/advocate/queue` · New Intake `/advocate/intake`

**Legal:** Dashboard `/legal` · Documents `/documents` · Timeline `/timeline` · Case Files `/legal/cases` · Court Filings `/legal/filings` · — · Privileged Notes `/legal/privileged` (PRIV badge) · Conflict Check `/legal/conflicts` · — · Legal Research + Law Library `/law-library`

**Admin:** Dashboard `/admin` · Documents `/documents` · Timeline `/timeline` · Mission Control `/admin/mission-control` · GUI Hub `/admin/gui` · Mode Selector `/admin/mode-selector` · Easy Settings `/admin/easy-mode` · — · Docs Hub `/admin/docs` · All Features `/dashboard`

**Tenant-hidden tools** (hard-gated server-side; `/ui/tool/*` redirects tenants to `/tenant/start`): `eviction-defense`, `complaints`, `case-builder`, `plan-maker`.

### 2.5 Tenant product surfaces (GUI_FLOW + tenant pages)

| Surface | Route |
|---|---|
| Tenant home | `/tenant/start` |
| Timeline | `/tenant/timeline` |
| Tenant dashboard | `/tenant/dashboard` |
| Library (KNOW) | `/tenant/library` |
| Documents | `/documents` |
| Document Center | `/dc` |
| Journal | `/tenant/journal` |
| Notepad | `/record/notes` |
| Calendar | `/calendar` |
| Comms log | `/comms-log` |
| Letters | `/tenant/tools/letters` |
| Deadlines | `/tenant/tools/deadlines` |
| Settings | `/tenant/settings` |
| Help | `/help` |
| Public feedback | `/feedback` |
| Info donation | `/help-the-next-tenant` |
| GUI home | `/gui/home` |
| GUI record | `/gui/record` |
| GUI act | `/gui/act` |

### 2.6 Single-function guide pages (UI Composer — one function, one page)

| Function | Route | Pillar body |
|---|---|---|
| `journal_create` | `/gui/record/journal/create` | `record_body.html` |
| `timeline_create_event` | `/gui/record/timeline/create-event` | `record_body.html` |
| `law_library_get_statute` | `/gui/know/law-library/get-statute` | `know_body.html` |
| `law_library_get_case` | `/gui/know/law-library/get-case` | `know_body.html` |
| `eviction_defense_calculate_deadlines` | `/gui/act/eviction-defense/calculate-deadlines` | `act_body.html` |
| `fca_readiness` | `/ui/tool/fca-readiness` | `act_body.html` |

### 2.7 Court / MNDES flow (COURT_FLOW)

`/mndes/guide` -> `/api/mndes/validate` -> `/api/mndes/package`; all-role guide: `/mndes/compliance-guide`

### 2.8 Admin flow (ADMIN_FLOW — elevation required)

`/admin` hub -> `/admin/login` · `/admin/dashboard` · `/admin/forge.html` · `/admin/run-modules` · `/admin/system-health` · `/admin/testing` · `/admin/invite-codes` · `/admin/correspondence` · `/admin/user-concerns` · `/admin/advanced` -> forge · `/admin/page-editor.html`

### 2.9 Role -> default module set (CAPABILITY_DEFAULTS in `product_manifest.py`)

Which modules are seeded into `user_capabilities` on first login — the role-level
'which modules does this surface even offer' control layer. Pipeline modules are
always-on and never listed.

| Role | Default modules (option set) |
|---|---|
| **tenant** (17) | vault, timeline, eviction_timeline, documents, journal, voice, rent, state_laws, law_library, contacts, search, packet_builder, dispute_tracker, sticky_notes, law_linker, document_center, info_donation |
| **advocate** (30) | all tenant except `voice`, plus case_builder, eviction_defense, court_forms, legal_trails, legal, intake, guided_intake, plan_maker, document_delivery, communication, invite_codes, advocate |
| **manager** (7) | documents, timeline, eviction_timeline, contacts, state_laws, search, manager |
| **admin** | `__all__` — every manifest module |

---

## 3. B-side display archetypes

Every module's function output lands in the B-side window as one of these archetypes.
The display-window install = one mount point that renders the right archetype per
function, driven by the function's contract outputs (same contract-driven pattern as
the fnav rail — never hand-wired per page).

| Archetype | What renders in B-side | Modules (tenant-facing) |
|---|---|---|
| **VIEWER** | Media-player render of a file (docx/pdf/image/text/audio/video) | document_center, preview, documents, vault, briefcase, delivery |
| **STREAM** | Chronological feed/log (grouped, filterable) | timeline, tenant_feed, journal, communication, eviction_timeline, legal_trails |
| **GRID** | Pick-list of items/cards (opens detail in viewer/reader) | contacts, fems, packet_builder, case_builder, court_forms, court_packet, search, free_api, actions |
| **FORM** | Staged input surface (fnav rail when staged) | intake, guided_intake, complaints, public_forms, eviction_defense, legal_filing, mndes, zoom_court_prep, journal (editor), pdf_tools, document_converter |
| **READER** | Long-form reference/report text | law_library, state_laws, context_engine, legal_analysis, housing_accountability, location, risc, plan_maker, zoom_court |
| **TABLE** | Structured rows/columns | rent, dispute_tracker |
| **CALENDAR** | Month grid + day detail | calendar |
| **OUTPUT** | Generated artifact preview + download/share | packet_builder, court_forms, court_packet, document_converter, pdf_tools, tools_api, legal_filing |
| **STATUS** | Progress / dashboard surface | intake (pipeline), case_builder (strength), legal (workspace), progress |
| **DASH** | Role home / admin console tiles | all GOVERN role surfaces |

---

## 4. Module -> functions -> controls -> B-side map

Per module: **Functions** = contract groups (`module::group`). **Controls** = required
(**bold**) and option (*italic*) inputs — what the A-side rail / fnav collects.
**B-side** = what the function leaves on the display window. `user_id` and other
system-supplied inputs are excluded from controls (never user-facing).

### RECORD (17 modules)

#### `briefcase` — Briefcase · tier CORE · B-side: **GRID+VIEWER**
- Layout: app/modules/briefcase/ — 49 registered function groups (briefcase_briefcase, briefcase_folder_contents, briefcase_create_folder, briefcase_update_folder, briefcase_delete_folder, briefcase_upload_docu
- Display window shows: Organized binder of documents; opens in viewer
- Output target (contract): app.modules.briefcase function outputs
- **49 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `briefcase_briefcase` — Briefcase Get Briefcase (GET) (SSOT) | — | result |
| `briefcase_folder_contents` — Briefcase Get Folder Contents (GET) (SSOT) | — | result |
| `briefcase_create_folder` — Briefcase Create Folder (POST) (SSOT) | — | result |
| `briefcase_update_folder` — Briefcase Update Folder (PUT) (SSOT) | — | result |
| `briefcase_delete_folder` — Briefcase Delete Folder (DELETE) (SSOT) | — | result |
| `briefcase_upload_document` — Briefcase Upload Document (POST) (SSOT) | — | result |
| `briefcase_get_document` — Briefcase Get Document (GET) (SSOT) | — | result |
| `briefcase_download_document` — Briefcase Download Document (GET) (SSOT) | — | result |
| `briefcase_preview_document` — Briefcase Preview Document (GET) (SSOT) | — | result |
| `briefcase_update_document` — Briefcase Update Document (PUT) (SSOT) | — | result |
| `briefcase_delete_document` — Briefcase Delete Document (DELETE) (SSOT) | — | result |
| `briefcase_move_document` — Briefcase Move Document (POST) (SSOT) | — | result |
| `briefcase_copy_document` — Briefcase Copy Document (POST) (SSOT) | — | result |
| `briefcase_search_documents` — Briefcase Search Documents (GET) (SSOT) | — | result |
| `briefcase_starred_documents` — Briefcase Get Starred Documents (GET) (SSOT) | — | result |
| `briefcase_recent_documents` — Briefcase Get Recent Documents (GET) (SSOT) | — | result |
| `briefcase_all_tags` — Briefcase Get All Tags (GET) (SSOT) | — | result |
| `briefcase_add_tag` — Briefcase Add Tag (POST) (SSOT) | — | result |
| `briefcase_export_folder` — Briefcase Export Folder (POST) (SSOT) | — | result |
| `briefcase_save_converted_document` — Briefcase Save Converted Document (POST) (SSOT) | — | result |
| `briefcase_briefcase_stats` — Briefcase Get Briefcase Stats (GET) (SSOT) | — | result |
| `briefcase_save_extraction` — Briefcase Save Extraction (POST) (SSOT) | — | result |
| `briefcase_extractions` — Briefcase List Extractions (GET) (SSOT) | — | result |
| `briefcase_get_extraction` — Briefcase Get Extraction (GET) (SSOT) | — | result |
| `briefcase_delete_extraction` — Briefcase Delete Extraction (DELETE) (SSOT) | — | result |
| `briefcase_download_extraction` — Briefcase Download Extraction (GET) (SSOT) | — | result |
| `briefcase_save_highlight` — Briefcase Save Highlight (POST) (SSOT) | — | result |
| `briefcase_save_highlights_batch` — Briefcase Save Highlights Batch (POST) (SSOT) | — | result |
| `briefcase_highlights` — Briefcase List Highlights (GET) (SSOT) | — | result |
| `briefcase_get_highlight` — Briefcase Get Highlight (GET) (SSOT) | — | result |
| `briefcase_delete_highlight` — Briefcase Delete Highlight (DELETE) (SSOT) | — | result |
| `briefcase_highlights_grouped_by_color` — Briefcase Get Highlights Grouped By Color (GET) (SSOT) | — | result |
| `briefcase_create_annotation` — Briefcase Create Annotation (POST) (SSOT) | — | result |
| `briefcase_annotations` — Briefcase List Annotations (GET) (SSOT) | — | result |
| `briefcase_get_annotation` — Briefcase Get Annotation (GET) (SSOT) | — | result |
| `briefcase_update_annotation` — Briefcase Update Annotation (PUT) (SSOT) | — | result |
| `briefcase_delete_annotation` — Briefcase Delete Annotation (DELETE) (SSOT) | — | result |
| `briefcase_link_annotation_to_event` — Briefcase Link Annotation To Event (POST) (SSOT) | — | result |
| `briefcase_annotations_by_document` — Briefcase Get Annotations By Document (GET) (SSOT) | — | result |
| `briefcase_reset_annotation_counters` — Briefcase Reset Annotation Counters (POST) (SSOT) | — | result |
| `briefcase_create_timeline_event` — Briefcase Create Timeline Event (POST) (SSOT) | — | result |
| `briefcase_timeline_events` — Briefcase List Timeline Events (GET) (SSOT) | — | result |
| `briefcase_get_timeline_event` — Briefcase Get Timeline Event (GET) (SSOT) | — | result |
| `briefcase_update_timeline_event` — Briefcase Update Timeline Event (PUT) (SSOT) | — | result |
| `briefcase_delete_timeline_event` — Briefcase Delete Timeline Event (DELETE) (SSOT) | — | result |
| `briefcase_event_chain` — Briefcase Get Event Chain (GET) (SSOT) | — | result |
| `briefcase_event_from_annotation` — Briefcase Create Event From Annotation (POST) (SSOT) | — | result |
| `briefcase_extraction_codes` — Briefcase Get Extraction Codes (GET) (SSOT) | — | result |
| `briefcase_event_statuses` — Briefcase Get Event Statuses (GET) (SSOT) | — | result |


#### `calendar` — Calendar · tier DEV · B-side: **CALENDAR**
- Layout: app/modules/calendar/ — 10 registered function groups (calendar_create_event, calendar_list_events, calendar_upcoming_deadlines, calendar_get_event, calendar_update_event, calendar_delete_event, calen
- Display window shows: Month grid + day detail; deadlines in reserved warm tone
- Output target (contract): app.modules.calendar function outputs
- **10 functions** · 11 distinct controls (6 required uses, 7 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `calendar_create_event` — Calendar Create Event (SSOT) | **title**, **date**, *description*, *event_type* | event_id, event |
| `calendar_list_events` — Calendar List Events (SSOT) | *start*, *end* | events, total |
| `calendar_upcoming_deadlines` — Calendar Upcoming Deadlines (SSOT) | *days* | deadlines |
| `calendar_get_event` — Calendar Get Event (SSOT) | **event_id** | event |
| `calendar_update_event` — Calendar Update Event (SSOT) | **event_id**, **updates** | event |
| `calendar_delete_event` — Calendar Delete Event (SSOT) | **event_id** | status |
| `calendar_from_documents` — Calendar Events From Documents (SSOT) | — | events, documents_analyzed |
| `calendar_sync_documents` — Calendar Sync Document Events (SSOT) | *overwrite* | synced_event_ids |
| `calendar_deadline_summary` — Calendar Deadline Summary (SSOT) | — | overdue, this_week, this_month |
| `calendar_notify_deadlines` — Calendar Notify Deadlines (SSOT) | *days_ahead* | notified |


#### `communication` — Communication · tier ADVOCATE · B-side: **STREAM**
- Layout: app/modules/communication/ — 15 registered function groups (communication_list_conversations, communication_create_conversation, communication_get_conversation, communication_send_message, communicati
- Display window shows: Comms log — message/interaction thread
- Output target (contract): app.modules.communication function outputs
- **11 functions** · 12 distinct controls (27 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `communication_list_conversations` — Communication List Conversations (SSOT) | **access_token** | conversations |
| `communication_create_conversation` — Communication Create Conversation (SSOT) | **recipient**, **initial_message**, **access_token** | conversation_id, conversation |
| `communication_get_conversation` — Communication Get Conversation (SSOT) | **conversation_id**, *before_message_id*, **access_token** | messages, has_more |
| `communication_send_message` — Communication Send Message (SSOT) | **conversation_id**, **content**, **access_token** | message_id, sent_at |
| `communication_mark_message_read` — Communication Mark Message Read (SSOT) | **conversation_id**, **message_id**, **access_token** | success |
| `communication_mark_conversation_read` — Communication Mark Conversation Read (SSOT) | **conversation_id**, **access_token** | success |
| `communication_reject_document` — Communication Reject Document (SSOT) | **delivery_id**, **reason**, **access_token** | status |
| `communication_fill_and_sign` — Communication Fill and Sign Document (SSOT) | **delivery_id**, **signature_type**, **access_token** | signed_document |
| `communication_upload_attachment` — Communication Upload Attachment (SSOT) | **conversation_id**, **file**, **access_token** | attachment_id, filename |
| `communication_delivery_conversation` — Communication Delivery Conversation (SSOT) | **delivery_id**, **access_token** | conversation |
| `communication_typing_indicator` — Communication Typing Indicator (SSOT) | **conversation_id**, **is_typing** | success |


#### `contacts` — Contacts · tier CORE · B-side: **GRID+FORM**
- Layout: app/modules/contacts/ — 13 registered function groups (contacts_list, contacts_create, contacts_get, contacts_update, contacts_delete, contacts_toggle_star, contacts_list_interactions, contacts_log_in
- Display window shows: Contact list + contact detail/edit card
- Output target (contract): app.modules.contacts function outputs
- **13 functions** · 13 distinct controls (14 required uses, 9 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `contacts_list` — Contacts List (SSOT) | *contact_type*, *role* | contacts, total |
| `contacts_create` — Contacts Create (SSOT) | **name**, **contact_type**, *phone*, *email*, *address* | contact_id, contact |
| `contacts_get` — Contacts Get (SSOT) | **contact_id** | contact |
| `contacts_update` — Contacts Update (SSOT) | **contact_id**, **updates** | contact |
| `contacts_delete` — Contacts Delete (SSOT) | **contact_id** | status |
| `contacts_toggle_star` — Contacts Toggle Star (SSOT) | **contact_id** | starred |
| `contacts_list_interactions` — Contacts List Interactions (SSOT) | **contact_id** | interactions |
| `contacts_log_interaction` — Contacts Log Interaction (SSOT) | **contact_id**, **interaction_type**, *description*, *date* | interaction_id |
| `contacts_import_from_extraction` — Contacts Import From Extraction (SSOT) | **extracted_contacts** | imported, total |
| `contacts_quick_add_landlord` — Contacts Quick Add Landlord (SSOT) | **name**, *phone*, *email* | contact_id |
| `contacts_quick_add_witness` — Contacts Quick Add Witness (SSOT) | **name**, **relationship** | contact_id |
| `contacts_for_forms` — Contacts For Forms (SSOT) | — | contacts |
| `contacts_types` — Contacts Types Reference (SSOT) | — | types, roles |


#### `document_center` — Document Center · tier CORE · B-side: **VIEWER**
- Layout: app/modules/document_center/ — 3-pane tenant UI (left vault list, center Semptify viewer, right overlays/checklist). Reads documents and real overlays from the user's cloud vault; persists review stat
- Display window shows: Document rendered in the universal media-player viewer (docx/pdf/image/text/audio/video) + overlays / checklist / meaning tabs
- Output target (contract): app/templates/pages/document_center.html in the browser; JSON from /api/dc/* endpoints; DOCUMENT_SHARE overlay (owner's vault) for shared access.
- Preview state (contract): Tenant sees the selected document rendered in the Semptify viewer with current overlay progress, document type dropdown, and status selector before saving any review state.
- Review state (contract): Tenant sees the updated verification status (new/review/verified/mismatched), the saved field confirmation state, and the current feature-unlock progress after each review save.
- Declared control types: `user_vault_documents`=auto_detect, `document_type`=dropdown, `review_confirmations`=typed, `share_request`=typed
- **5 functions** · 3 distinct controls (4 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `dc_list` — Document Center List (SSOT) | — | documents, pending_documents, processed_document_count, total, generated_at |
| `dc_unlocks` — Document Center Unlocks (SSOT) | — | unlocks, doc_count, generated_at |
| `dc_overlays` — Document Center Overlays (SSOT) | **vault_id** | has_data, overall_pct, overlays, overlay_count, overlay_source, status |
| `dc_view` — Document Center View (SSOT) | **vault_id** | file_bytes, mime_type, filename |
| `dc_set_type` — Document Center Set Document Type (SSOT) | **doc_id**, **document_type** | ok, doc_id, document_type, note |


#### `document_converter` — Document Converter · tier CORE · B-side: **FORM+OUTPUT**
- Layout: app/modules/document_converter/ — 8 registered function groups (document_converter_to_docx, document_converter_to_html, document_converter_to_both, document_converter_file, document_converter_from_pat
- Display window shows: Conversion options form -> converted-file output/download
- Output target (contract): app.modules.document_converter function outputs
- **8 functions** · 13 distinct controls (14 required uses, 6 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `document_converter_to_docx` — Document Converter To DOCX (SSOT) | **markdown**, *filename* | docx, filename |
| `document_converter_to_html` — Document Converter To HTML (SSOT) | **markdown**, *filename* | html, filename |
| `document_converter_to_both` — Document Converter To Both (SSOT) | **markdown**, *filename* | docx, html, filename |
| `document_converter_file` — Document Converter File (SSOT) | **file**, *output_format* | converted, filename |
| `document_converter_from_path` — Document Converter From Path (SSOT) | **file_path**, *output_format* | converted, filename |
| `document_converter_download` — Document Converter Download (SSOT) | **filename** | file |
| `document_converter_list` — Document Converter List (SSOT) | — | documents |
| `document_converter_cleanup` — Document Converter Cleanup (SSOT) | **d**, **a**, **y**, **s**, **_**, **o**, **l**, **d**, ** | cleaned |


#### `documents` — Documents · tier CORE · B-side: **GRID+VIEWER**
- Layout: app/modules/documents/ — 17 registered function groups (documents_process, documents_upload_simple, documents_list, documents_get, documents_reprocess, documents_intelligence, documents_urgent, docume
- Display window shows: Document grid; item opens in viewer
- Output target (contract): app.modules.documents function outputs
- **17 functions** · 4 distinct controls (13 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `documents_process` — Documents Process (SSOT) | **file** | document_id, document_type, extracted_text, dates, amounts, parties, issues |
| `documents_upload_simple` — Documents Simple Upload (SSOT) | **file** | document_id, filename, document_type, status |
| `documents_list` — Documents List (SSOT) | — | documents |
| `documents_get` — Documents Get Detail (SSOT) | **doc_id** | document, intelligence, issues |
| `documents_reprocess` — Documents Reprocess (SSOT) | **doc_id** | document_id, status, document_type |
| `documents_intelligence` — Documents Intelligence Analysis (SSOT) | **doc_id** | dates, amounts, parties, issues, deadlines, suggested_actions |
| `documents_urgent` — Documents Urgent List (SSOT) | — | documents |
| `documents_text` — Documents Extracted Text (SSOT) | **doc_id** | text, language |
| `documents_update_category` — Documents Update Category (SSOT) | **doc_id**, **category** | doc_id, category |
| `documents_train_correct` — Documents Train Correct (SSOT) | **doc_id**, **corrected_type** | status |
| `documents_train_stats` — Documents Training Stats (SSOT) | — | total_documents, confirmed, corrected, accuracy, patterns |
| `documents_view` — Documents View (SSOT) | **doc_id** | content, content_type |
| `documents_thumbnail` — Documents Thumbnail (SSOT) | **doc_id** | thumbnail, content_type |
| `documents_export` — Documents Export (SSOT) | — | file_stream, filename |
| `documents_timeline` — Documents Timeline (SSOT) | — | events |
| `documents_summary` — Documents Summary (SSOT) | — | total_documents, by_type, urgent_count, recent_activity |
| `documents_auto_timeline` — Documents Auto-Timeline (SSOT) | **doc_id** | created_events, total_created |


#### `fems` — Fems · tier EXTENDED · B-side: **GRID**
- Layout: app/modules/fems/ — 10 registered function groups (fems_health, fems_stats, fems_upload_file, fems_search, fems_documents, fems_document, fems_phones, fems_quarantine, fems_cases, fems_case). Derived 
- Display window shows: File/event management list
- Output target (contract): app.modules.fems function outputs
- **10 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `fems_health` — Fems Fems Health (GET) (SSOT) | — | result |
| `fems_stats` — Fems Fems Stats (GET) (SSOT) | — | result |
| `fems_upload_file` — Fems Upload File (POST) (SSOT) | — | result |
| `fems_search` — Fems Search (GET) (SSOT) | — | result |
| `fems_documents` — Fems List Documents (GET) (SSOT) | — | result |
| `fems_document` — Fems Get Document (GET) (SSOT) | — | result |
| `fems_phones` — Fems List Phones (GET) (SSOT) | — | result |
| `fems_quarantine` — Fems List Quarantine (GET) (SSOT) | — | result |
| `fems_cases` — Fems List Cases (GET) (SSOT) | — | result |
| `fems_case` — Fems Create Case (POST) (SSOT) | — | result |


#### `intake` — Intake · tier EXTENDED · B-side: **FORM+STATUS**
- Layout: app/modules/intake/ — 19 registered function groups (intake_upload, intake_upload_auto, intake_upload_batch, intake_process_vault, intake_process, intake_status, intake_list_documents, intake_get_docu
- Display window shows: Upload dropzone -> live processing status -> extracted-field review
- Output target (contract): app.modules.intake function outputs
- **19 functions** · 6 distinct controls (14 required uses, 2 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `intake_upload` — Intake Upload (SSOT) | **file** | doc_id, filename, status |
| `intake_upload_auto` · stages: upload_file->read_document->check_record — Intake Upload and Auto-Process (SSOT) | **file** | doc_id, document_type, issues_found, dates, amounts, parties, status |
| `intake_upload_batch` — Intake Batch Upload (SSOT) | **files** | results, total, succeeded, failed |
| `intake_process_vault` — Intake Process from Vault (SSOT) | **doc_id** | doc_id, document_type, issues_found, status |
| `intake_process` — Intake Process Document (SSOT) | **doc_id** | doc_id, status, document_type |
| `intake_status` — Intake Processing Status (SSOT) | **doc_id** | doc_id, status, progress |
| `intake_list_documents` — Intake List Documents (SSOT) | *status* | documents |
| `intake_get_document` — Intake Get Document (SSOT) | **doc_id** | document |
| `intake_get_issues` — Intake Document Issues (SSOT) | **doc_id** | issues |
| `intake_get_dates` — Intake Document Dates (SSOT) | **doc_id** | dates |
| `intake_get_amounts` — Intake Document Amounts (SSOT) | **doc_id** | amounts |
| `intake_get_parties` — Intake Document Parties (SSOT) | **doc_id** | parties |
| `intake_get_text` — Intake Document Text (SSOT) | **doc_id** | text |
| `intake_critical_issues` — Intake Critical Issues (SSOT) | — | issues, total |
| `intake_upcoming_deadlines` — Intake Upcoming Deadlines (SSOT) | *days* | deadlines, total |
| `intake_summary` — Intake User Summary (SSOT) | — | total_documents, by_status, total_issues, critical_issues, upcoming_deadlines |
| `intake_verify_notarization` — Intake Verify Notarization (SSOT) | **notarization_id** | valid, notary, document_id, notarized_at |
| `intake_chain_of_custody` — Intake Chain of Custody (SSOT) | **notarization_id** | chain, document_id |
| `intake_enums` — Intake Enums (SSOT) | — | document_types, intake_statuses, issue_severities, languages |


#### `journal` — Journal · tier CORE · B-side: **STREAM+FORM**
- Layout: app/modules/journal/ — 6 registered function groups (journal_create, journal_list, journal_get, journal_update, journal_delete, journal_summary). Derived record: page layout not yet described.
- Display window shows: Entry list (stream) + single-entry editor (form)
- Output target (contract): app.modules.journal function outputs
- **6 functions** · 12 distinct controls (6 required uses, 10 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `journal_create` · stages: write — Journal Create Entry (SSOT) | **entry_type**, **title**, *content*, *occurred_at*, *is_urgent*, *involved_party*, *tags*, *document_link* | entry_id, entry |
| `journal_list` — Journal List Entries (SSOT) | *entry_type*, *is_urgent*, *skip*, *limit* | entries, total |
| `journal_get` — Journal Get Entry (SSOT) | **entry_id** | entry |
| `journal_update` — Journal Update Entry (SSOT) | **entry_id**, **updates** | entry |
| `journal_delete` — Journal Delete Entry (SSOT) | **entry_id** | deleted |
| `journal_summary` — Journal Summary (SSOT) | — | total_entries, urgent_entries, recent_entries |


#### `packet_builder` — Packet Builder · tier CORE · B-side: **GRID+OUTPUT**
- Layout: app/modules/packet_builder/ — 3 registered function groups (packet_builder_build, packet_builder_get, packet_builder_download). Derived record: page layout not yet described.
- Display window shows: Packet contents list -> assembled packet preview/download
- Output target (contract): app.modules.packet_builder function outputs
- **3 functions** · 10 distinct controls (7 required uses, 5 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `packet_builder_build` — Packet Builder Build (SSOT) | **mode**, *vault_ids*, *case_id*, *folder_id*, **include_highlights**, **include_notes**, **include_footnotes**, *name* | packet_id, item_count, download_url |
| `packet_builder_get` — Packet Builder Get (SSOT) | **packet_id** | packet_id, name, mode, item_count, created_at, source, documents |
| `packet_builder_download` — Packet Builder Download (SSOT) | **packet_id**, **format**, *mode* | content, filename, media_type |


#### `pdf_tools` — Pdf Tools · tier CORE · B-side: **FORM+OUTPUT**
- Layout: app/modules/pdf_tools/ — 14 registered function groups (pdf_tools_test, pdf_tools_upload, pdf_tools_info, pdf_tools_page_image, pdf_tools_page_base64, pdf_tools_page_text, pdf_tools_all_text, pdf_tool
- Display window shows: PDF operation forms -> processed-PDF output
- Output target (contract): app.modules.pdf_tools function outputs
- **14 functions** · 9 distinct controls (20 required uses, 4 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `pdf_tools_test` — PDF Tools Test (SSOT) | — | status, pymupdf_version |
| `pdf_tools_upload` — PDF Tools Upload (SSOT) | **file** | pdf_id, filename, page_count |
| `pdf_tools_info` — PDF Tools Info (SSOT) | **pdf_id** | info |
| `pdf_tools_page_image` — PDF Tools Page Image (SSOT) | **pdf_id**, **page_num**, *zoom* | image |
| `pdf_tools_page_base64` — PDF Tools Page Base64 (SSOT) | **pdf_id**, **page_num**, *zoom* | base64 |
| `pdf_tools_page_text` — PDF Tools Page Text (SSOT) | **pdf_id**, **page_num** | text |
| `pdf_tools_all_text` — PDF Tools All Text (SSOT) | **pdf_id** | text |
| `pdf_tools_extract_pages` — PDF Tools Extract Pages (SSOT) | **pdf_id**, **pages** | pdf |
| `pdf_tools_extract_pages_base64` — PDF Tools Extract Pages Base64 (SSOT) | **pdf_id**, **pages** | base64 |
| `pdf_tools_delete` — PDF Tools Delete (SSOT) | **pdf_id** | success |
| `pdf_tools_thumbnails` — PDF Tools Thumbnails (SSOT) | **pdf_id**, *max_width* | thumbnails |
| `pdf_tools_split` — PDF Tools Split (SSOT) | **pdf_id**, *pages_per_file* | split_pdfs |
| `pdf_tools_merge` — PDF Tools Merge (SSOT) | **files** | merged_pdf |
| `pdf_tools_rotate` — PDF Tools Rotate Pages (SSOT) | **pdf_id**, **pages**, **rotation** | pdf |


#### `preview` — Preview · tier CORE · B-side: **VIEWER**
- Layout: app/modules/preview/ — 9 registered function groups (preview_generate, preview_serve, preview_text, preview_info, preview_cache_clear, preview_statistics, preview_batch_generate, preview_supported_for
- Display window shows: Single-document preview surface
- Output target (contract): app.modules.preview function outputs
- **9 functions** · 4 distinct controls (6 required uses, 2 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `preview_generate` — Preview Generate (SSOT) | **document_id**, *preview_type* | cache_key, preview_url |
| `preview_serve` — Preview Serve (SSOT) | **cache_key** | content, content_type |
| `preview_text` — Preview Text (SSOT) | **document_id** | text |
| `preview_info` — Preview Info (SSOT) | **document_id** | info |
| `preview_cache_clear` — Preview Cache Clear (SSOT) | **document_id** | cleared |
| `preview_statistics` — Preview Statistics (SSOT) | — | stats |
| `preview_batch_generate` — Preview Batch Generate (SSOT) | **document_ids**, *preview_type* | cache_keys, failed |
| `preview_supported_formats` — Preview Supported Formats (SSOT) | — | formats |
| `preview_cache_clear_all` — Preview Cache Clear All (SSOT) | — | cleared |


#### `rent` — Rent · tier CORE · B-side: **TABLE**
- Layout: app/modules/rent/ — 5 registered function groups (rent_ledger_create, rent_ledger_list, rent_ledger_get, rent_ledger_update, rent_ledger_delete). Derived record: page layout not yet described.
- Display window shows: Rent ledger table with running balance
- Output target (contract): app.modules.rent function outputs
- **5 functions** · 13 distinct controls (7 required uses, 8 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `rent_ledger_create` — Rent Ledger Create (SSOT) | **entry_type**, **amount**, **payment_date**, *due_date*, *period_covered*, *status*, *payment_method*, *source*, *receipt_document_id*, *overlay_link*, *not… | payment_id, payment |
| `rent_ledger_list` — Rent Ledger List (SSOT) | — | payments |
| `rent_ledger_get` — Rent Ledger Get (SSOT) | **payment_id** | payment |
| `rent_ledger_update` — Rent Ledger Update (SSOT) | **payment_id**, **updates** | payment |
| `rent_ledger_delete` — Rent Ledger Delete (SSOT) | **payment_id** | deleted |


#### `tenant_feed` — Tenant Feed · tier CORE · B-side: **STREAM**
- Layout: app/modules/tenant_feed/ — 1 registered function groups (feed_aggregate). Derived record: page layout not yet described.
- Display window shows: Unified feed merging documents/journal/deadlines/letters
- Output target (contract): app.modules.tenant_feed function outputs
- **1 functions** · 1 distinct controls (0 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `feed_aggregate` — Tenant Feed — Aggregator (SSOT) | *type_filter* | items, total_count |


#### `timeline` — Timeline · tier CORE · B-side: **STREAM**
- Layout: app/modules/timeline/ — 4 registered function groups (timeline_unified_view, timeline_date_range, timeline_create_event, timeline_chronology). Derived record: page layout not yet described.
- Display window shows: Chronological event stream, grouped by day, filterable
- Output target (contract): app.modules.timeline function outputs
- **3 functions** · 8 distinct controls (2 required uses, 7 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `timeline_unified_view` — Timeline Unified View (SSOT) | *start_date*, *end_date*, *sources*, *severity* | events, total, date_range |
| `timeline_date_range` — Timeline Date Range Info (SSOT) | — | earliest_date, latest_date, span_days |
| `timeline_create_event` · stages: describe_event — Timeline Create Event (SSOT) | **date**, **title**, *description*, *severity*, *source* | event_id, created_at |


#### `vault` — Vault · tier CORE · B-side: **VIEWER+GRID**
- Layout: app/modules/vault/ — 16 registered function groups (vault_upload, vault_folders, vault_list_documents, vault_download_document, vault_get_certificate, vault_delete_document, vault_init, vault_verify, 
- Display window shows: Vault file grid/list; selected file renders in viewer
- Output target (contract): app.modules.vault function outputs
- **14 functions** · 8 distinct controls (7 required uses, 4 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `vault_upload` — Vault Upload (SSOT) | **file**, *document_type*, *description*, *tags* | document_id, certificate_id, sha256_hash, storage_path |
| `vault_folders` — Vault Folder Structure (SSOT) | **access_token** | CANONICAL_VAULT_FOLDERS |
| `vault_list_documents` — Vault List Documents (SSOT) | *document_type* | documents, total |
| `vault_download_document` — Vault Download Document (SSOT) | **document_id** | file_stream, filename, mime_type |
| `vault_get_certificate` — Vault Get Certificate (SSOT) | **document_id** | certificate_id, sha256, certified_at, storage_path |
| `vault_delete_document` — Vault Delete Document (SSOT) | **document_id** | status |
| `vault_init` — Vault Initialize (SSOT) | — | ok, message |
| `vault_verify` — Vault Verify (SSOT) | — | ok, folders |
| `vault_status` — Vault Status (SSOT) | — | ok, provider |
| `vault_sidebar_files` — Vault Sidebar Files (SSOT) | — | files |
| `vault_sidebar_upload` — Vault Sidebar Upload (SSOT) | **files** | uploaded, errors |
| `vault_sidebar_stats` — Vault Sidebar Stats (SSOT) | — | total_documents, total_size, by_type, last_upload |
| `vault_sidebar_search` — Vault Sidebar Search (SSOT) | **query** | results |
| `vault_upload_envelope` — Vault Upload Page + Object Envelopes (SSOT) | — | page_envelope, experience_token_snapshot |


### KNOW (9 modules)

#### `context_engine` — Context Engine · tier CORE · B-side: **READER**
- Layout: app/modules/context_engine/ — 7 registered function groups (context_query, context_refresh, story_submit, story_moderate, explanation_entry, explanation_retrieval, familiarity_tapering). Derived recor
- Display window shows: Verified facts + tenant stories per subject
- Output target (contract): app.modules.context_engine function outputs
- **7 functions** · 17 distinct controls (17 required uses, 11 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `context_query` — Context Query (SSOT) | **subject**, *jurisdiction*, *limit* | facts |
| `context_refresh` — Context Refresh (SSOT) | **subject**, *jurisdiction*, *query*, **admin_user_id** | new_count |
| `story_submit` — Story Submit (SSOT) | **subject**, **title**, **body**, *jurisdiction*, *outcome*, **submitted_by** | story_id |
| `story_moderate` — Story Moderate (SSOT) | **story_id**, **publish**, *title*, *body*, **admin_user_id** | story_id, is_published |
| `explanation_entry` — Explanation Entry (SSOT) | **subject**, *jurisdiction*, **upl_risk_tier**, **pillar**, **review_status**, *admin_user_id* | entry_id, entry |
| `explanation_retrieval` — Explanation Retrieval (SSOT) | **object_envelope**, *jurisdiction* | retrieval_results |
| `familiarity_tapering` — Familiarity Tapering (SSOT) | **retrieval_result**, **exposure_count** | variant_text |


#### `free_api` — Free Api · tier CORE · B-side: **GRID**
- Layout: app/modules/free_api/ — 11 registered function groups (free_api_property_parcel, free_api_property_address, free_api_landlord_business, free_api_landlord_owner, free_api_court_evictions, free_api_cour
- Display window shows: External data lookup results
- Output target (contract): app.modules.free_api function outputs
- **11 functions** · 9 distinct controls (15 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `free_api_property_parcel` — Free API Property Parcel Lookup (SSOT) | **county**, **parcel_id** | parcel |
| `free_api_property_address` — Free API Property Address Lookup (SSOT) | **county**, **address** | property |
| `free_api_landlord_business` — Free API Landlord Business Lookup (SSOT) | **name** | businesses |
| `free_api_landlord_owner` — Free API Landlord Owner Lookup (SSOT) | **property_id** | owner |
| `free_api_court_evictions` — Free API Court Evictions Search (SSOT) | **name** | evictions |
| `free_api_court_federal` — Free API Federal Court Search (SSOT) | **query** | cases |
| `free_api_violations_city` — Free API City Violations Lookup (SSOT) | **city**, **address** | violations |
| `free_api_violations_environment` — Free API Environmental Violations Lookup (SSOT) | **facility** | violations |
| `free_api_inspections_hud` — Free API HUD Inspection Lookup (SSOT) | **property_id** | inspection |
| `free_api_inspections_local` — Free API Local Inspection Lookup (SSOT) | **city**, **address** | inspections |
| `free_api_statutes` — Free API Statute Lookup (SSOT) | **section** | statute |


#### `housing_accountability` — Housing Accountability · tier EXTENDED · B-side: **READER+TABLE**
- Layout: app/modules/housing_accountability/ — 7 registered function groups (accountability_detect_patterns, accountability_oversight_packet, accountability_coalition_build, accountability_evidence_intake, acc
- Display window shows: Landlord record / pattern history
- Output target (contract): app.modules.housing_accountability function outputs
- **7 functions** · 6 distinct controls (5 required uses, 3 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `accountability_detect_patterns` — Accountability Detect Patterns (SSOT) | *documents* | patterns, total |
| `accountability_oversight_packet` — Accountability Oversight Packet (SSOT) | **patterns**, *agency* | packet, format, download_url |
| `accountability_coalition_build` — Accountability Coalition Action (SSOT) | **patterns** | action_summary, share_token |
| `accountability_evidence_intake` — Accountability Evidence Intake (SSOT) | **evidence** | processed, linked_patterns |
| `accountability_public_records_search` — Accountability Public Records Search (SSOT) | **query**, *jurisdiction* | records, total |
| `accountability_press_release` — Accountability Press Release (SSOT) | **patterns** | press_release, format |
| `accountability_dashboard` — Accountability Dashboard (SSOT) | — | patterns, packets, coalitions |


#### `law_library` — Law Library · tier CORE · B-side: **READER**
- Layout: app/modules/law_library/ — 10 registered function groups (law_library_list_statutes, law_library_get_statute, law_library_list_court_rules, law_library_get_court_rule, law_library_list_case_law, law_l
- Display window shows: Statute/case text in a reading surface
- Output target (contract): app.modules.law_library function outputs
- **10 functions** · 15 distinct controls (11 required uses, 5 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `law_library_list_statutes` — Law Library List Statutes (SSOT) | *category*, *search* | statutes, total |
| `law_library_get_statute` · stages: choose_statute — Law Library Get Statute (SSOT) | **statute_id** | statute |
| `law_library_list_court_rules` — Law Library List Court Rules (SSOT) | *category* | court_rules, total |
| `law_library_get_court_rule` — Law Library Get Court Rule (SSOT) | **rule_id** | court_rule |
| `law_library_list_case_law` — Law Library List Case Law (SSOT) | **s**, **e**, **a**, **r**, **c**, **h**, ** | cases, total |
| `law_library_get_case` · stages: choose_case — Law Library Get Case (SSOT) | **case_id** | case |
| `law_library_links` — Law Library Card Link Index (SSOT) | — | links |
| `law_library_categories` — Law Library Categories (SSOT) | — | categories |
| `law_library_quick_reference` — Law Library Quick Reference (SSOT) | **topic** | summary, key_laws, key_cases |
| `law_library_county_code` — Law Library County Code (SSOT) | **county**, *state* | official_url, source_name, last_verified, jurisdiction |


#### `legal_analysis` — Legal Analysis · tier CORE · B-side: **READER**
- Layout: app/modules/legal_analysis/ — 14 registered function groups (legal_analysis_classify_evidence, legal_analysis_classify_evidence_batch, legal_analysis_check_consistency, legal_analysis_corroboration, l
- Display window shows: Plain-language analysis report
- Output target (contract): app.modules.legal_analysis function outputs
- **14 functions** · 10 distinct controls (13 required uses, 3 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `legal_analysis_classify_evidence` — Legal Analysis Classify Evidence (SSOT) | **document** | evidence_type, legal_status, confidence |
| `legal_analysis_classify_evidence_batch` — Legal Analysis Classify Evidence Batch (SSOT) | **documents** | classifications |
| `legal_analysis_check_consistency` — Legal Analysis Check Consistency (SSOT) | **documents**, *events* | inconsistencies, conflicts |
| `legal_analysis_corroboration` — Legal Analysis Corroboration (SSOT) | **claim**, **evidence_items** | corroboration_score, supporting_evidence |
| `legal_analysis_corroboration_multi` — Legal Analysis Corroboration Multi (SSOT) | **claims**, **evidence_items** | scores |
| `legal_analysis_timeline` — Legal Analysis Timeline (SSOT) | **events**, *jurisdiction* | gaps, conflicts, compliance_issues |
| `legal_analysis_assess_merit` — Legal Analysis Assess Merit (SSOT) | **case_data** | merit_score, strengths, weaknesses |
| `legal_analysis_assess_merit_from_case` — Legal Analysis Assess Merit From Case (SSOT) | **case_id**, *perspective* | merit_score, assessment |
| `legal_analysis_hearsay` — Legal Analysis Hearsay (SSOT) | **documents** | hearsay_flags |
| `legal_analysis_binding_status` — Legal Analysis Binding Status (SSOT) | **documents** | binding_statuses |
| `legal_analysis_quick_check` — Legal Analysis Quick Case Check (SSOT) | **case_id** | health_score, risks |
| `legal_analysis_evidence_types` — Legal Analysis Evidence Types (SSOT) | — | evidence_types |
| `legal_analysis_legal_statuses` — Legal Analysis Legal Statuses (SSOT) | — | legal_statuses |
| `legal_analysis_mn_eviction_requirements` — Legal Analysis MN Eviction Requirements (SSOT) | — | requirements |


#### `location` — Location · tier RESEARCH · B-side: **READER**
- Layout: app/modules/location/ — 10 registered function groups (location_current, location_update, location_clear, location_supported_states, location_state_info, location_legal_resources, location_eviction_ti
- Display window shows: Jurisdiction / local-rules info
- Output target (contract): app.modules.location function outputs
- **10 functions** · 2 distinct controls (3 required uses, 2 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `location_current` — Location Current (SSOT) | — | state_code, county, source |
| `location_update` — Location Update (SSOT) | **state_code**, *county* | state_code, county |
| `location_clear` — Location Clear (SSOT) | — | success |
| `location_supported_states` — Location Supported States (SSOT) | — | states |
| `location_state_info` — Location State Info (SSOT) | **state_code** | state_code, name, counties, resources_available |
| `location_legal_resources` — Location Legal Resources (SSOT) | — | resources |
| `location_eviction_timeline` — Location Eviction Timeline (SSOT) | — | timeline, state_code |
| `location_mn_counties` — Location MN Counties (SSOT) | — | counties |
| `location_county_info` — Location County Info (SSOT) | **county**, *state_code* | county, state_code, court_location, local_resources |
| `location_context` — Location Context (SSOT) | — | state_code, county, resources, eviction_timeline, jurisdiction_metadata |


#### `risc` — Risc · tier CORE · B-side: **READER**
- Layout: app/modules/risc/ — 2 registered function groups (risc_webhook, risc_webhook_verify). Derived record: page layout not yet described.
- Display window shows: Rights information lookup
- Output target (contract): app.modules.risc function outputs
- **2 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `risc_webhook` — Risc Risc Webhook (POST) (SSOT) | — | result |
| `risc_webhook_verify` — Risc Risc Webhook Verify (GET) (SSOT) | — | result |


#### `search` — Search · tier CORE · B-side: **GRID**
- Layout: app/modules/search/ — 7 registered function groups (search_global, search_advanced, search_suggestions, search_statistics, search_index_document, search_remove_from_index, search_quick). Derived recor
- Display window shows: Search results list; result opens reader/viewer
- Output target (contract): app.modules.search function outputs
- **7 functions** · 4 distinct controls (6 required uses, 3 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `search_global` — Search Global (SSOT) | **q**, *limit* | results, total |
| `search_advanced` — Search Advanced (SSOT) | **q**, *search_type* | results, total |
| `search_suggestions` — Search Suggestions (SSOT) | **q**, *limit* | suggestions, total |
| `search_statistics` — Search Statistics (SSOT) | — | index_stats, document_count |
| `search_index_document` — Search Index Document (SSOT) | **document_id** | indexed, document_id |
| `search_remove_from_index` — Search Remove From Index (SSOT) | **document_id** | removed, document_id |
| `search_quick` — Search Quick (SSOT) | **q** | results |


#### `state_laws` — State Laws · tier CORE · B-side: **READER**
- Layout: app/modules/state_laws/ — 4 registered function groups (state_laws_list, state_laws_get, state_laws_nearby, state_laws_detect). Derived record: page layout not yet described.
- Display window shows: State-law guide text
- Output target (contract): app.modules.state_laws function outputs
- **4 functions** · 3 distinct controls (3 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `state_laws_list` — State Laws List (SSOT) | — | states |
| `state_laws_get` — State Laws Get (SSOT) | **state_code** | state_code, name, security_deposit_limit, eviction_procedure, tenant_rights, landlord_obligations |
| `state_laws_nearby` — State Laws Nearby Search (SSOT) | **lat**, **lon** | states |
| `state_laws_detect` — State Laws Detect by Location (SSOT) | — | state_code, confidence |


### ACT (18 modules)

#### `actions` — Actions · tier EXTENDED · B-side: **GRID**
- Layout: app/modules/actions/ — 9 registered function groups (actions_action_plan, actions_action_plan_with_context, actions_quick_wins, actions_actions_by_category, actions_all_actions, actions_current_capaci
- Display window shows: Next-action / quick-win cards
- Output target (contract): app.modules.actions function outputs
- **9 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `actions_action_plan` — Actions Get Action Plan (GET) (SSOT) | — | result |
| `actions_action_plan_with_context` — Actions Get Action Plan With Context (POST) (SSOT) | — | result |
| `actions_quick_wins` — Actions Get Quick Wins (GET) (SSOT) | — | result |
| `actions_actions_by_category` — Actions Get Actions By Category (GET) (SSOT) | — | result |
| `actions_all_actions` — Actions Get All Actions (GET) (SSOT) | — | result |
| `actions_current_capacity` — Actions Get Current Capacity (GET) (SSOT) | — | result |
| `actions_self_care_suggestions` — Actions Get Self Care Suggestions (GET) (SSOT) | — | result |
| `actions_encouragement` — Actions Get Encouragement (GET) (SSOT) | — | result |
| `actions_next_action` — Actions Get Next Action (GET) (SSOT) | — | result |


#### `case_builder` — Case Builder · tier EXTENDED · B-side: **GRID+STATUS**
- Layout: app/modules/case_builder/ — 34 registered function groups (case_builder_info, case_builder_cases_list, case_builder_case_get, case_builder_case_create, case_builder_case_update, case_builder_case_dele
- Display window shows: Evidence/case assembly with strength view
- Output target (contract): app.modules.case_builder function outputs
- **34 functions** · 19 distinct controls (41 required uses, 5 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `case_builder_info` — Case Builder Info (SSOT) | — | info |
| `case_builder_cases_list` — Case Builder List Cases (SSOT) | — | cases, count |
| `case_builder_case_get` — Case Builder Get Case (SSOT) | **case_id** | case |
| `case_builder_case_create` — Case Builder Create Case (SSOT) | **case** | case_id, case |
| `case_builder_case_update` — Case Builder Update Case (SSOT) | **case_id**, **updates** | case |
| `case_builder_case_delete` — Case Builder Delete Case (SSOT) | **case_id** | success |
| `case_builder_validate_freshness` — Case Builder Validate Freshness (SSOT) | **case_data** | valid, issues |
| `case_builder_validate_minnesota` — Case Builder Validate Minnesota Requirements (SSOT) | **case_data** | valid, issues |
| `case_builder_validate_court_forms` — Case Builder Validate Court Forms (SSOT) | **case_data** | valid, issues |
| `case_builder_freshness_recommendations` — Case Builder Freshness Recommendations (SSOT) | **case_data** | recommendations |
| `case_builder_intake_complaint` — Case Builder Intake Complaint (SSOT) | **intake** | case_id, case |
| `case_builder_timeline_get` — Case Builder Get Timeline (SSOT) | **case_id** | timeline, count |
| `case_builder_timeline_add` — Case Builder Add Timeline Event (SSOT) | **case_id**, **event** | event_id, event |
| `case_builder_timeline_delete` — Case Builder Delete Timeline Event (SSOT) | **case_id**, **event_id** | success |
| `case_builder_evidence_get` — Case Builder Get Evidence (SSOT) | **case_id** | evidence, count |
| `case_builder_evidence_add` — Case Builder Add Evidence (SSOT) | **case_id**, **evidence** | evidence_id |
| `case_builder_counterclaims_get` — Case Builder Get Counterclaims (SSOT) | **case_id** | counterclaims, count |
| `case_builder_counterclaim_add` — Case Builder Add Counterclaim (SSOT) | **case_id**, **claim** | counterclaim_id |
| `case_builder_motions_get` — Case Builder Get Motions (SSOT) | **case_id** | motions, count |
| `case_builder_motion_add` — Case Builder Add Motion (SSOT) | **case_id**, **motion** | motion_id |
| `case_builder_deadlines_get` — Case Builder Get Deadlines (SSOT) | **case_id** | deadlines, count |
| `case_builder_deadline_add` — Case Builder Add Deadline (SSOT) | **case_id**, **deadline** | deadline_id, deadline |
| `case_builder_deadline_complete` — Case Builder Complete Deadline (SSOT) | **case_id**, **deadline_id** | success |
| `case_builder_defenses_get` — Case Builder Get Defenses (SSOT) | **case_id** | defenses, count |
| `case_builder_defense_add` — Case Builder Add Defense (SSOT) | **case_id**, **defense** | defense_id |
| `case_builder_templates_defenses` — Case Builder Defense Templates (SSOT) | — | templates |
| `case_builder_intake_packet_export` — Case Builder Attorney Intake Packet Export (SSOT) | **case_id** | packet |
| `case_builder_intake_packet_export_pdf` — Case Builder Attorney Intake Packet Export PDF (SSOT) | **case_id** | pdf_bytes |
| `case_builder_intake_packet_export_zip` — Case Builder Attorney Intake Packet Export ZIP (SSOT) | **case_id** | zip_bytes |
| `case_builder_curated_packet_export` — Case Builder Curated Packet Export (SSOT) | **case_id**, *document_ids*, *include_clean*, *include_marked*, *include_summary*, *overlay_types* | zip_bytes, filename |
| `case_builder_fca_readiness_get` — Case Builder FCA Readiness Get (SSOT) | **case_id** | readiness_checklist, summary, referral_resources |
| `case_builder_fca_readiness_update` — Case Builder FCA Readiness Update (SSOT) | **case_id**, **readiness_checklist** | readiness_checklist, summary |
| `case_builder_fca_readiness_pdf` — Case Builder FCA Readiness PDF (SSOT) | **case_id** | pdf_bytes, filename |
| `case_builder_fca_readiness_zip` — Case Builder FCA Readiness ZIP (SSOT) | **case_id** | zip_bytes, filename |


#### `complaints` — Complaints · tier EXTENDED · B-side: **FORM**
- Layout: app/modules/complaints/ — 16 registered function groups (complaints_list_agencies, complaints_get_agency, complaints_recommend_agencies, complaints_agency_checklist, complaints_create_draft, complaint
- Display window shows: Complaint wizard steps -> drafts
- Output target (contract): app.modules.complaints function outputs
- **16 functions** · 19 distinct controls (26 required uses, 3 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `complaints_list_agencies` — Complaints List Agencies (SSOT) | **a**, **g**, **e**, **n**, **c**, **y**, **_**, **t**, **y**, **p**, **e**, ** | agencies, total |
| `complaints_get_agency` — Complaints Get Agency (SSOT) | **agency_id** | agency |
| `complaints_recommend_agencies` — Complaints Recommend Agencies (SSOT) | **keywords**, *jurisdiction* | agencies |
| `complaints_agency_checklist` — Complaints Agency Checklist (SSOT) | **agency_id** | checklist |
| `complaints_create_draft` — Complaints Create Draft (SSOT) | **agency_id**, **situation** | draft_id, draft |
| `complaints_list_drafts` — Complaints List Drafts (SSOT) | — | drafts |
| `complaints_get_draft` — Complaints Get Draft (SSOT) | **draft_id** | draft |
| `complaints_update_draft` — Complaints Update Draft (SSOT) | **draft_id**, **updates** | draft |
| `complaints_delete_draft` — Complaints Delete Draft (SSOT) | **draft_id** | status |
| `complaints_preview` — Complaints Preview (SSOT) | **draft_id** | preview, format |
| `complaints_export` — Complaints Export (SSOT) | **draft_id**, *format* | file_stream, filename, format |
| `complaints_mark_filed` — Complaints Mark Filed (SSOT) | **draft_id**, **filed_date** | draft_id, status, filed_date |
| `complaints_quick_start` — Complaints Quick Start Guide (SSOT) | — | steps, agencies |
| `complaints_wizard_start` — Complaints Wizard Start (SSOT) | — | session_id, first_step |
| `complaints_wizard_get` — Complaints Wizard Get Session (SSOT) | **session_id** | session, current_step |
| `complaints_submit` — Complaints Submit (SSOT) | **session_id** | draft_id, status |


#### `court_forms` — Court Forms · tier EXTENDED · B-side: **GRID+OUTPUT**
- Layout: app/modules/court_forms/ — 17 registered function groups (form_generate, form_autofill, court_forms_list_types, court_forms_list_defenses, court_forms_generate, court_forms_generate_html, court_forms_
- Display window shows: Form picker -> filled-form preview/download
- Output target (contract): app.modules.court_forms function outputs
- **15 functions** · 10 distinct controls (16 required uses, 8 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `court_forms_list_types` — Court Forms List Types (SSOT) | — | forms |
| `court_forms_list_defenses` — Court Forms List Defenses (SSOT) | — | defenses |
| `court_forms_generate` — Court Forms Generate (SSOT) | **form_type**, *defenses*, **case_data** | form_id, pdf, filename |
| `court_forms_generate_html` — Court Forms Generate HTML (SSOT) | **form_type**, *defenses* | html |
| `court_forms_download` — Court Forms Download PDF (SSOT) | **form_type**, *defenses* | pdf, filename |
| `court_forms_preview` — Court Forms Preview (SSOT) | **form_type**, *defenses*, **case_data** | preview |
| `court_forms_quick_answer` — Court Forms Quick Answer (SSOT) | *case_number*, *defendant_name* | form_id, pdf |
| `court_forms_autofill` — Court Forms Autofill From Documents (SSOT) | **form_type** | autofill_data |
| `court_forms_generate_from_documents` — Court Forms Generate From Documents (SSOT) | **form_type**, *defenses* | form_id, pdf |
| `court_forms_document_data_preview` — Court Forms Document Data Preview (SSOT) | — | extracted_data |
| `court_forms_library_list` — Court Forms Library List (SSOT) | — | forms |
| `court_forms_library_get` — Court Forms Library Get Definition (SSOT) | **form_id** | form_definition |
| `court_forms_library_render` — Court Forms Library Render (SSOT) | **form_id**, **field_values**, **output_format** | form_id, title, content, fields_used, missing_required |
| `court_forms_library_save` — Court Forms Library Save to Vault (SSOT) | **form_id**, **field_values**, *filename* | form_id, vault_id, overlay_id, storage_path, filename |
| `court_forms_library_packet` — Court Forms Library Packet Assembly (SSOT) | **items**, **filename** | filename, content, form_ids |


#### `court_packet` — Court Packet · tier EXTENDED · B-side: **GRID+OUTPUT**
- Layout: app/modules/court_packet/ — 8 registered function groups (court_packet_status, court_packet_documents, court_packet_evidence, court_packet_legal_documents, court_packet_timeline, court_packet_checklis
- Display window shows: Packet assembly -> compiled output
- Output target (contract): app.modules.court_packet function outputs
- **8 functions** · 1 distinct controls (0 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `court_packet_status` — Court Packet Status (SSOT) | — | status, contents |
| `court_packet_documents` — Court Packet Documents (SSOT) | — | documents |
| `court_packet_evidence` — Court Packet Evidence (SSOT) | — | evidence |
| `court_packet_legal_documents` — Court Packet Legal Documents (SSOT) | — | legal_documents |
| `court_packet_timeline` — Court Packet Timeline (SSOT) | — | timeline |
| `court_packet_checklist` — Court Packet Checklist (SSOT) | — | checklist |
| `court_packet_generate` — Court Packet Generate (SSOT) | *include_highlights* | packet, filename |
| `court_packet_preview` — Court Packet Preview (SSOT) | — | preview |


#### `dispute_tracker` — Dispute Tracker · tier EXTENDED · B-side: **TABLE**
- Layout: app/modules/dispute_tracker/ — 4 registered function groups (dispute_tracker_module, dispute_tracker_list, dispute_tracker_create, dispute_tracker_compare). Derived record: page layout not yet describ
- Display window shows: Dispute/comparison table
- Output target (contract): /api/dispute-tracker/, /api/dispute-tracker/comparisons, /api/dispute-tracker/disputes, /api/dispute-tracker/health (prefixes: /api/dispute-tracker)
- **4 functions** · 3 distinct controls (3 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `dispute_tracker_module` — Dispute Tracker Module (SSOT) | — | health |
| `dispute_tracker_list` — Dispute Tracker List Disputes (SSOT) | — | disputes, count |
| `dispute_tracker_create` — Dispute Tracker Create Dispute (SSOT) | **dispute** | dispute_id, dispute |
| `dispute_tracker_compare` — Dispute Tracker Compare (SSOT) | **dispute_id**, **comparison** | comparison_id, comparison |


#### `eviction_defense` — Eviction Defense · tier EXTENDED · B-side: **FORM+READER**
- Layout: app/modules/eviction_defense/ — 14 registered function groups (eviction_defense_list_forms, eviction_defense_get_form, eviction_defense_list_motions, eviction_defense_list_procedures, eviction_defense
- Display window shows: Guided inputs -> defense options, deadline results, disclaimers
- Output target (contract): app.modules.eviction_defense function outputs
- **15 functions** · 21 distinct controls (22 required uses, 7 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `eviction_defense_list_forms` — Eviction Defense List Forms (SSOT) | *category*, *stage* | forms, total |
| `eviction_defense_get_form` — Eviction Defense Get Form (SSOT) | **form_id** | form |
| `eviction_defense_list_motions` — Eviction Defense List Motions (SSOT) | **m**, **o**, **t**, **i**, **o**, **n**, **_**, **t**, **y**, **p**, **e**, ** | motions, total |
| `eviction_defense_list_procedures` — Eviction Defense List Procedures (SSOT) | **c**, **a**, **t**, **e**, **g**, **o**, **r**, **y**, ** | procedures, total |
| `eviction_defense_list_counterclaims` — Eviction Defense List Counterclaims (SSOT) | — | counterclaims |
| `eviction_defense_list_defenses` — Eviction Defense List Defenses (SSOT) | — | defenses |
| `eviction_defense_calculate_deadlines` · stages: enter_date — Eviction Defense Calculate Deadlines (SSOT) | **start_date**, *case_type* | deadlines |
| `eviction_defense_case_checklist` — Eviction Defense Case Checklist (SSOT) | **stage** | checklist |
| `eviction_defense_analyze` — Eviction Defense Analyze Case (SSOT) | *case_data* | defenses, counterclaims, deadlines, suggested_actions |
| `eviction_defense_quick_status` — Eviction Defense Quick Status (SSOT) | — | available_defenses, upcoming_deadlines, case_stage |
| `eviction_defense_from_documents_defenses` — Eviction Defense From Documents — Defenses (SSOT) | — | defenses |
| `eviction_defense_from_documents_counterclaims` — Eviction Defense From Documents — Counterclaims (SSOT) | — | counterclaims |
| `eviction_defense_from_documents_deadlines` — Eviction Defense From Documents — Deadlines (SSOT) | — | deadlines |
| `eviction_defense_from_documents_analysis` — Eviction Defense From Documents — Full Analysis (SSOT) | — | defenses, counterclaims, deadlines, suggested_actions |
| `eviction_defense_packet_wizard` — Eviction Defense Packet Wizard (SSOT) | *semptify_uid* | page |


#### `eviction_timeline` — Eviction Timeline · tier CORE · B-side: **STREAM**
- Layout: app/modules/eviction_timeline/ — 5 registered function groups (eviction_timeline_module, eviction_timeline_list, eviction_timeline_create, eviction_timeline_momentum_checkpoint, eviction_timeline_enve
- Display window shows: Case-event timeline
- Output target (contract): /api/eviction-timeline/, /api/eviction-timeline/envelope, /api/eviction-timeline/events, /api/eviction-timeline/health, /api/eviction-timeline/momentum-checkpoint (prefixes: /api/eviction-timeline)
- **5 functions** · 5 distinct controls (4 required uses, 2 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `eviction_timeline_module` — Eviction Timeline Module (SSOT) | — | health |
| `eviction_timeline_list` — Eviction Timeline List Events (SSOT) | **subject_id** | events, count |
| `eviction_timeline_create` — Eviction Timeline Add Event (SSOT) | **event**, **subject_id** | event_id, event |
| `eviction_timeline_momentum_checkpoint` — Eviction Timeline Momentum Checkpoint (SSOT) | **event_type**, *next_phase*, *trigger* | message, suppressed |
| `eviction_timeline_envelope` — Eviction Timeline Page + Object Envelopes (SSOT) | — | page_envelope, experience_token_snapshot |


#### `guided_intake` — Guided Intake · tier EXTENDED · B-side: **FORM**
- Layout: app/modules/guided_intake/ — 3 registered function groups (guided_intake_save, guided_intake_summary, guided_intake_status). Derived record: page layout not yet described.
- Display window shows: Staged intake forms
- Output target (contract): app.modules.guided_intake function outputs
- **3 functions** · 1 distinct controls (1 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `guided_intake_save` — Guided Intake Save (SSOT) | **data** | intake_id, summary |
| `guided_intake_summary` — Guided Intake Summary (SSOT) | — | summary |
| `guided_intake_status` — Guided Intake Status (SSOT) | — | status, progress |


#### `legal` — Legal · tier EXTENDED · B-side: **DASH**
- Layout: app/modules/legal/ — 5 registered function groups (legal_workspace_list, legal_workspace_create, legal_court_filing_create, legal_discovery_track, legal_exhibit_number). Derived record: page layout no
- Display window shows: Legal workspace surface
- Output target (contract): app.modules.legal function outputs
- **5 functions** · 11 distinct controls (10 required uses, 4 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `legal_workspace_list` — Legal Workspace List (SSOT) | **legal_user_id** | matters |
| `legal_workspace_create` — Legal Workspace Create (SSOT) | **legal_user_id**, **title**, *tenant_user_id* | matter_id |
| `legal_court_filing_create` — Legal Court Filing Create (SSOT) | **matter_id**, **filing_type**, **court**, *filing_date* | filing_id |
| `legal_discovery_track` — Legal Discovery Tracking (SSOT) | **matter_id**, **discovery_type**, *served_date* | discovery_id |
| `legal_exhibit_number` — Legal Exhibit Numbering (SSOT) | **matter_id**, **description**, *evidence_item_id* | exhibit_id, exhibit_number |


#### `legal_filing` — Legal Filing · tier — · B-side: **FORM+OUTPUT**
- Layout: app/modules/legal_filing/ — 5 registered function groups (legal_filing_cases, legal_filing_get_case, legal_filing_create_case, legal_filing_add_evidence, legal_filing_evidence). Derived record: page l
- Display window shows: Filing flow -> filing output
- Output target (contract): app.modules.legal_filing function outputs
- **5 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `legal_filing_cases` — Legal_Filing Get Cases (GET) (SSOT) | — | result |
| `legal_filing_get_case` — Legal_Filing Get Case (GET) (SSOT) | — | result |
| `legal_filing_create_case` — Legal_Filing Create Case (POST) (SSOT) | — | result |
| `legal_filing_add_evidence` — Legal_Filing Add Evidence (POST) (SSOT) | — | result |
| `legal_filing_evidence` — Legal_Filing Get Evidence (GET) (SSOT) | — | result |


#### `legal_trails` — Legal Trails · tier EXTENDED · B-side: **STREAM+FORM**
- Layout: app/modules/legal_trails/ — 22 registered function groups (legal_trails_overview, legal_trails_violation_add, legal_trails_violations_list, legal_trails_violation_get, legal_trails_eviction_threat_add
- Display window shows: Trail builder / trail view
- Output target (contract): app.modules.legal_trails function outputs
- **22 functions** · 23 distinct controls (28 required uses, 4 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `legal_trails_overview` — Legal Trails Overview (SSOT) | — | overview |
| `legal_trails_violation_add` — Legal Trails Add Violation (SSOT) | **violation** | violation_id |
| `legal_trails_violations_list` — Legal Trails List Violations (SSOT) | *violation_type*, *perpetrator* | violations, count |
| `legal_trails_violation_get` — Legal Trails Get Violation (SSOT) | **violation_id** | violation |
| `legal_trails_eviction_threat_add` — Legal Trails Add Eviction Threat (SSOT) | **threat** | threat_id |
| `legal_trails_eviction_threats_list` — Legal Trails List Eviction Threats (SSOT) | — | threats |
| `legal_trails_late_fee_add` — Legal Trails Add Late Fee Violation (SSOT) | **fee** | fee_id |
| `legal_trails_late_fees_list` — Legal Trails List Late Fee Violations (SSOT) | — | late_fees, total_overcharged |
| `legal_trails_late_fee_calculate` — Legal Trails Calculate Late Fee Legal Max (SSOT) | **rent_amount**, **days_late** | legal_max, calculation |
| `legal_trails_broker_oversight_add` — Legal Trails Add Broker Oversight (SSOT) | **broker** | success |
| `legal_trails_broker_oversight_list` — Legal Trails List Broker Oversight (SSOT) | — | brokers |
| `legal_trails_broker_oversight_get` — Legal Trails Get Broker Oversight (SSOT) | **broker_name** | broker |
| `legal_trails_broker_link_violation` — Legal Trails Link Violation To Broker (SSOT) | **broker_name**, **violation_id** | success |
| `legal_trails_claim_create` — Legal Trails Create Legal Claim (SSOT) | **claim** | claim_id |
| `legal_trails_claims_list` — Legal Trails List Legal Claims (SSOT) | **s**, **t**, **a**, **t**, **u**, **s**, ** | claims, count |
| `legal_trails_claim_get` — Legal Trails Get Legal Claim (SSOT) | **claim_id** | claim |
| `legal_trails_claim_status_update` — Legal Trails Update Claim Status (SSOT) | **claim_id**, **status** | success |
| `legal_trails_filing_windows` — Legal Trails Calculate Filing Windows (SSOT) | **violation_date** | filing_windows |
| `legal_trails_generate_retaliation_complaint` — Legal Trails Generate Retaliation Complaint (SSOT) | **tenant_name**, **property_address**, **details** | complaint |
| `legal_trails_generate_license_complaint` — Legal Trails Generate License Complaint (SSOT) | **broker_name**, *license_number* | complaint |
| `legal_trails_generate_hud_complaint` — Legal Trails Generate HUD Complaint (SSOT) | **tenant_name**, **property_address**, **details** | complaint |
| `legal_trails_mn_attorneys` — Legal Trails MN Tenant Attorneys (SSOT) | — | attorneys |


#### `mndes` — Mndes · tier CORE · B-side: **FORM+READER**
- Layout: app/modules/mndes/ — 12 registered function groups (mndes_guide, mndes_compliance_guide, mndes_acceptable_file_types, mndes_validate_file, mndes_validate_vault_files, mndes_create_exhibit_package, mnd
- Display window shows: Compliance guide + validation results + package output
- Output target (contract): app.modules.mndes function outputs
- **12 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `mndes_guide` — Mndes Mndes Guide (GET) (SSOT) | — | result |
| `mndes_compliance_guide` — Mndes Mndes Compliance Guide (GET) (SSOT) | — | result |
| `mndes_acceptable_file_types` — Mndes Get Acceptable File Types (GET) (SSOT) | — | result |
| `mndes_validate_file` — Mndes Validate File (GET) (SSOT) | — | result |
| `mndes_validate_vault_files` — Mndes Validate Vault Files (POST) (SSOT) | — | result |
| `mndes_create_exhibit_package` — Mndes Create Exhibit Package (POST) (SSOT) | — | result |
| `mndes_get_exhibit_package` — Mndes Get Exhibit Package (GET) (SSOT) | — | result |
| `mndes_submission_checklist` — Mndes Get Submission Checklist (GET) (SSOT) | — | result |
| `mndes_package_compliance` — Mndes Get Package Compliance (GET) (SSOT) | — | result |
| `mndes_apply_attestations` — Mndes Apply Attestations (POST) (SSOT) | — | result |
| `mndes_confirm_submission` — Mndes Confirm Submission (POST) (SSOT) | — | result |
| `mndes_submission_guide` — Mndes Get Submission Guide (GET) (SSOT) | — | result |


#### `plan_maker` — Plan Maker · tier EXTENDED · B-side: **READER**
- Layout: app/modules/plan_maker/ — 8 registered function groups (plan_maker_plan_create, plan_maker_plan_view, plan_maker_plan_export, plan_maker_entity_add, plan_maker_evidence_add, plan_maker_step_add, plan_
- Display window shows: Generated action plan
- Output target (contract): app.modules.plan_maker function outputs
- **8 functions** · 7 distinct controls (12 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `plan_maker_plan_create` — Plan Maker Create Plan (SSOT) | **plan_data** | plan_id, plan |
| `plan_maker_plan_view` — Plan Maker View Plan (SSOT) | **plan_id** | plan |
| `plan_maker_plan_export` — Plan Maker Export Plan (SSOT) | **plan_id**, **format** | content, filename |
| `plan_maker_entity_add` — Plan Maker Add Entity (SSOT) | **plan_id**, **entity** | plan |
| `plan_maker_evidence_add` — Plan Maker Add Evidence (SSOT) | **plan_id**, **evidence** | plan |
| `plan_maker_step_add` — Plan Maker Add Step (SSOT) | **plan_id**, **step** | plan |
| `plan_maker_step_complete` — Plan Maker Complete Step (SSOT) | **plan_id**, **step_index** | plan |
| `plan_maker_default_steps` — Plan Maker Default Steps (SSOT) | — | steps |


#### `public_forms` — Public Forms · tier CORE · B-side: **FORM**
- Layout: app/modules/public_forms/ — 3 registered function groups (public_forms_feedback, public_forms_tenant_autofill, public_forms_contact). Derived record: page layout not yet described.
- Display window shows: Public form fill
- Output target (contract): app.modules.public_forms function outputs
- **3 functions** · 2 distinct controls (2 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `public_forms_feedback` — Public Forms Submit Feedback (SSOT) | **feedback** | success |
| `public_forms_tenant_autofill` — Public Forms Tenant Autofill (SSOT) | — | autofill_data |
| `public_forms_contact` — Public Forms Submit Contact (SSOT) | **contact** | success |


#### `tools_api` — Tools Api · tier EXTENDED · B-side: **OUTPUT**
- Layout: app/modules/tools_api/ — 3 registered function groups (tools_api_save_letter, tools_api_save_checklist, tools_api_save_calculation). Derived record: page layout not yet described.
- Display window shows: Saved letter / checklist / calculation outputs
- Output target (contract): app.modules.tools_api function outputs
- **3 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `tools_api_save_letter` — Tools_Api Save Letter (POST) (SSOT) | — | result |
| `tools_api_save_checklist` — Tools_Api Save Checklist (POST) (SSOT) | — | result |
| `tools_api_save_calculation` — Tools_Api Save Calculation (POST) (SSOT) | — | result |


#### `zoom_court` — Zoom Court · tier EXTENDED · B-side: **READER**
- Layout: app/modules/zoom_court/ — 3 registered function groups (zoom_court_status, zoom_court_tech_checklist, zoom_court_etiquette_rules). Derived record: page layout not yet described.
- Display window shows: Tech checklist + etiquette guide
- Output target (contract): app.modules.zoom_court function outputs
- **3 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `zoom_court_status` — Zoom_Court Zoom Court Status (GET) (SSOT) | — | result |
| `zoom_court_tech_checklist` — Zoom_Court Tech Checklist (GET) (SSOT) | — | result |
| `zoom_court_etiquette_rules` — Zoom_Court Etiquette Rules (GET) (SSOT) | — | result |


#### `zoom_court_prep` — Zoom Court Prep · tier EXTENDED · B-side: **FORM+READER**
- Layout: app/modules/zoom_court_prep/ — 1 registered function groups (zoom_court_prep_status). Derived record: page layout not yet described.
- Display window shows: Prep checklist
- Output target (contract): app.modules.zoom_court_prep function outputs
- **1 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `zoom_court_prep_status` — Zoom_Court_Prep Zoom Court Prep Status (GET) (SSOT) | — | result |


### GOVERN (87 modules)

*GOVERN modules are never tenant-facing — their 'B-side' is the role's own*
*console surface (admin hub tiles, dev tools) or none (pure infra).*

#### `accountability_ledger` — Accountability Ledger · tier —
- Layout: app/modules/accountability_ledger/ — 3 registered function groups (accountability_subject_lookup, accountability_pattern_lookup, accountability_alignment_lookup). Derived record: page layout not yet d
- **4 functions** · 8 distinct controls (2 required uses, 8 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `accountability_subject_lookup` — Accountability Subject Lookup (SSOT) | *subject_type*, *jurisdiction* | subjects, total |
| `accountability_pattern_lookup` — Accountability Pattern Lookup (SSOT) | *subject_id*, *pattern_type* | patterns, total |
| `accountability_alignment_lookup` — Accountability Political Alignment Lookup (SSOT) | *subject_id*, *alignment_type* | alignments, total |
| `accountability_record_requests` — Accountability Public-Records Request Tracking (SSOT) | **agency_target**, **records_requested**, *deadline_date*, *subject_id* | requests, effective_status |


#### `admin_api` — Admin Api · tier —
- Layout: app/modules/admin_api/ — 1 registered function groups (admin_operations). Derived record: page layout not yet described.
- **1 functions** · 1 distinct controls (0 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `admin_operations` — Admin Operations (SSOT) | *level* | result |


#### `admin_auth` — Admin Auth · tier —
- Layout: app/modules/admin_auth/ — 1 registered function groups (admin_login). Derived record: page layout not yet described.
- **1 functions** · 3 distinct controls (2 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `admin_login` — Admin Login (SSOT) | **username**, **password**, *totp_code* | auth_response |


#### `admin_console` — Admin Console · tier ADMIN
- Layout: app/modules/admin_console/ — 9 registered function groups (user_list, user_detail, impersonate_start, impersonate_stop, system_status, module_flags_list, module_flags_set, module_flags_delete, module_
- *No FunctionGroupContracts — API-only or registers elsewhere.*

#### `advanced` — Advanced · tier ADMIN
- Layout: app/modules/advanced/ — 7 registered function groups (advanced_health, advanced_tools_list, advanced_build_status, advanced_guardrail_run, advanced_orchestrator_sync, advanced_verify, advanced_cost_gu
- **7 functions** · 2 distinct controls (1 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `advanced_health` — Advanced Health (SSOT) | — | status |
| `advanced_tools_list` — Advanced Tools List (SSOT) | — | tools |
| `advanced_build_status` — Advanced Build Status (SSOT) | — | build_status |
| `advanced_guardrail_run` — Advanced Guardrail Run (SSOT) | — | guardrail_result |
| `advanced_orchestrator_sync` — Advanced Orchestrator Sync (SSOT) | — | sync_result |
| `advanced_verify` — Advanced Module Verify (SSOT) | *module_id* | verify_result |
| `advanced_cost_guard` — Advanced Cost Guard - Repeated Fees (SSOT) | **fees** | detected_patterns |


#### `advocate` — Advocate · tier ADVOCATE
- Layout: app/modules/advocate/ — 12 registered function groups (advocate_clients_list, advocate_client_detail, advocate_case_queue, advocate_intake, advocate_client_timeline, advocate_annotate_document, advoca
- **12 functions** · 9 distinct controls (24 required uses, 4 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `advocate_clients_list` — Advocate Client List (SSOT) | **advocate_user_id** | clients |
| `advocate_client_detail` — Advocate Client Detail (SSOT) | **advocate_user_id**, **client_user_id** | client, stats |
| `advocate_case_queue` — Advocate Case Queue (SSOT) | **advocate_user_id** | queue |
| `advocate_intake` — Advocate New Intake (SSOT) | **advocate_user_id**, **tenant_user_id**, *notes* | relationship_id |
| `advocate_client_timeline` — Advocate Multi-Tenant Timeline (SSOT) | **advocate_user_id**, *client_user_id* | events |
| `advocate_annotate_document` — Advocate Annotate Document (SSOT) | **advocate_user_id**, **client_user_id**, **document_id**, **overlay_type**, **payload**, *metadata* | overlay_id, overlay_type, document_id |
| `advocate_list_overlays` — Advocate List Document Overlays (SSOT) | **advocate_user_id**, **client_user_id**, **document_id** | overlays, count |
| `advocate_delete_annotation` — Advocate Delete Annotation (SSOT) | **advocate_user_id**, **client_user_id**, **overlay_id** | success |
| `advocate_invite_codes` — Advocate Invite Codes (SSOT) | **advocate_user_id** | codes, count, organization_id |
| `tenant_link_advocate` — Tenant Link to Advocate (SSOT) | **tenant_user_id**, **advocate_user_id**, *notes* | success, message |
| `tenant_list_advocates` — Tenant List Linked Advocates (SSOT) | **tenant_user_id** | advocates, count |
| `tenant_revoke_advocate` — Tenant Revoke Advocate Access (SSOT) | **tenant_user_id**, **advocate_user_id** | success, message |


#### `agent_orchestrator` — Agent Orchestrator · tier DEV
- Layout: app/modules/agent_orchestrator/ — 4 registered function groups (agent_orchestrator_tasks, agent_orchestrator_create_task, agent_orchestrator_batch_create, agent_orchestrator_models). Derived record: p
- **4 functions** · 3 distinct controls (3 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `agent_orchestrator_tasks` — Agent Orchestrator List Tasks (GET) (SSOT) | — | tasks, total |
| `agent_orchestrator_create_task` — Agent Orchestrator Create Task (POST) (SSOT) | **title**, **target_model** | task |
| `agent_orchestrator_batch_create` — Agent Orchestrator Batch Create Tasks (POST) (SSOT) | **tasks[]** | created, total |
| `agent_orchestrator_models` — Agent Orchestrator List Models (GET) (SSOT) | — | models |


#### `analytics` — Analytics · tier ADMIN
- Layout: app/modules/analytics/ — 11 registered function groups (analytics_track_event, analytics_track_pageview, analytics_track_document_upload, analytics_metrics, analytics_realtime_metrics, analytics_user_
- **11 functions** · 15 distinct controls (11 required uses, 10 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `analytics_track_event` — Analytics Track Event (SSOT) | **event_type**, *properties* | tracked, event_id |
| `analytics_track_pageview` — Analytics Track Pageview (SSOT) | **page**, *referrer* | tracked |
| `analytics_track_document_upload` — Analytics Track Document Upload (SSOT) | **document_id**, *doc_type* | tracked |
| `analytics_metrics` — Analytics Metrics (SSOT) | *period*, *hours* | events, pageviews, uploads |
| `analytics_realtime_metrics` — Analytics Realtime Metrics (SSOT) | — | active_users, events_per_minute, pageviews_per_minute |
| `analytics_user_metrics` — Analytics User Metrics (SSOT) | *days* | events, pageviews, uploads |
| `analytics_recent_events` — Analytics Recent Events (SSOT) | *event_type*, *limit* | events |
| `analytics_export_json` — Analytics Export JSON (SSOT) | **d**, **a**, **y**, **s**, ** | data |
| `analytics_export_csv` — Analytics Export CSV (SSOT) | **d**, **a**, **y**, **s**, ** | csv |
| `analytics_statistics` — Analytics Statistics (SSOT) | — | total_events, total_users, total_pageviews, total_uploads |
| `analytics_dashboard` — Analytics Dashboard (SSOT) | — | metrics, recent_events, top_pages |


#### `auth` — Auth · tier CORE
- Layout: app/modules/auth/ — 2 registered function groups (auth_status, auth_register_info). Derived record: page layout not yet described.
- **2 functions** · 1 distinct controls (0 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `auth_status` — Auth Status (SSOT) | *semptify_uid* | authenticated, user_id, role, provider |
| `auth_register_info` — Auth Register Info (SSOT) | — | info |


#### `auto_mode` — Auto Mode · tier —
- Layout: app/modules/auto_mode/ — 7 registered function groups (auto_mode_auto_mode_status, auto_mode_toggle_auto_mode, auto_mode_auto_mode_config, auto_mode_available_features, auto_mode_analysis_summary, aut
- **7 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `auto_mode_auto_mode_status` — Auto_Mode Get Auto Mode Status (GET) (SSOT) | — | result |
| `auto_mode_toggle_auto_mode` — Auto_Mode Toggle Auto Mode (POST) (SSOT) | — | result |
| `auto_mode_auto_mode_config` — Auto_Mode Update Auto Mode Config (POST) (SSOT) | — | result |
| `auto_mode_available_features` — Auto_Mode Get Available Features (GET) (SSOT) | — | result |
| `auto_mode_analysis_summary` — Auto_Mode Get Analysis Summary (GET) (SSOT) | — | result |
| `auto_mode_run_analysis_on_document` — Auto_Mode Run Analysis On Document (POST) (SSOT) | — | result |
| `auto_mode_run_batch_analysis` — Auto_Mode Run Batch Analysis (POST) (SSOT) | — | result |


#### `batch` — Batch · tier ADMIN
- Layout: app/modules/batch/ — 11 registered function groups (batch_create_batch_operation_endpoint, batch_start_batch_operation_endpoint, batch_cancel_batch_operation_endpoint, batch_get_batch_operation_endpoi
- **11 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `batch_create_batch_operation_endpoint` — Batch Create Batch Operation Endpoint (POST) (SSOT) | — | result |
| `batch_start_batch_operation_endpoint` — Batch Start Batch Operation Endpoint (POST) (SSOT) | — | result |
| `batch_cancel_batch_operation_endpoint` — Batch Cancel Batch Operation Endpoint (POST) (SSOT) | — | result |
| `batch_get_batch_operation_endpoint` — Batch Get Batch Operation Endpoint (GET) (SSOT) | — | result |
| `batch_user_batch_operations_endpoint` — Batch Get User Batch Operations Endpoint (GET) (SSOT) | — | result |
| `batch_batch_statistics_endpoint` — Batch Get Batch Statistics Endpoint (GET) (SSOT) | — | result |
| `batch_prepare_batch_upload` — Batch Prepare Batch Upload (POST) (SSOT) | — | result |
| `batch_execute_batch_upload` — Batch Execute Batch Upload (POST) (SSOT) | — | result |
| `batch_prepare_batch_delete` — Batch Prepare Batch Delete (POST) (SSOT) | — | result |
| `batch_prepare_batch_export` — Batch Prepare Batch Export (POST) (SSOT) | — | result |
| `batch_supported_operations` — Batch Get Supported Operations (GET) (SSOT) | — | result |


#### `brain` — Brain · tier —
- Layout: app/modules/brain/ — 11 registered function groups (brain_brain_status, brain_modules, brain_get_state, brain_update_state, brain_recent_events, brain_emit_event, brain_trigger_workflow, brain_workflo
- **11 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `brain_brain_status` — Brain Get Brain Status (GET) (SSOT) | — | result |
| `brain_modules` — Brain List Modules (GET) (SSOT) | — | result |
| `brain_get_state` — Brain Get State (GET) (SSOT) | — | result |
| `brain_update_state` — Brain Update State (PUT) (SSOT) | — | result |
| `brain_recent_events` — Brain Get Recent Events (GET) (SSOT) | — | result |
| `brain_emit_event` — Brain Emit Event (POST) (SSOT) | — | result |
| `brain_trigger_workflow` — Brain Trigger Workflow (POST) (SSOT) | — | result |
| `brain_workflows` — Brain List Workflows (GET) (SSOT) | — | result |
| `brain_workflow` — Brain Get Workflow (GET) (SSOT) | — | result |
| `brain_think` — Brain Brain Think (POST) (SSOT) | — | result |
| `brain_sync_all` — Brain Sync All (POST) (SSOT) | — | result |


#### `campaign` — Campaign · tier RESEARCH
- Layout: app/modules/campaign/ — 9 registered function groups (campaign_launch_campaign, campaign_campaign_status, campaign_campaigns, campaign_quick_file_complaint, campaign_quick_analyze_fraud, campaign_quic
- **9 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `campaign_launch_campaign` — Campaign Launch Campaign (POST) (SSOT) | — | result |
| `campaign_campaign_status` — Campaign Get Campaign Status (GET) (SSOT) | — | result |
| `campaign_campaigns` — Campaign List Campaigns (GET) (SSOT) | — | result |
| `campaign_quick_file_complaint` — Campaign Quick File Complaint (POST) (SSOT) | — | result |
| `campaign_quick_analyze_fraud` — Campaign Quick Analyze Fraud (POST) (SSOT) | — | result |
| `campaign_quick_generate_press` — Campaign Quick Generate Press (POST) (SSOT) | — | result |
| `campaign_pressure_map` — Campaign Pressure Map (GET) (SSOT) | — | result |
| `campaign_leader_letter` — Campaign Generate Leader Letter (POST) (SSOT) | — | result |
| `campaign_health` — Campaign Campaign Health (GET) (SSOT) | — | result |


#### `capabilities` — Capabilities · tier ADMIN
- Layout: app/modules/capabilities/ — 6 registered function groups (capabilities_list, capabilities_grant, capabilities_revoke, capabilities_overlay_get, capabilities_overlay_attach, capabilities_overlay_detach
- **6 functions** · 2 distinct controls (4 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `capabilities_list` — Capabilities List (SSOT) | — | capabilities |
| `capabilities_grant` — Capabilities Grant Module (SSOT) | **module_name** | success |
| `capabilities_revoke` — Capabilities Revoke Module (SSOT) | **module_name** | success |
| `capabilities_overlay_get` — Capabilities Get Overlay (SSOT) | — | overlays |
| `capabilities_overlay_attach` — Capabilities Attach Overlay (SSOT) | **overlay_module** | success |
| `capabilities_overlay_detach` — Capabilities Detach Overlay (SSOT) | **overlay_module** | success |


#### `cloud_sync` — Cloud Sync · tier RESEARCH
- Layout: app/modules/cloud_sync/ — 19 registered function groups (cloud_sync_sync_status, cloud_sync_full_sync, cloud_sync_get_profile, cloud_sync_update_profile, cloud_sync_get_case, cloud_sync_update_case, c
- **19 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `cloud_sync_sync_status` — Cloud_Sync Get Sync Status (GET) (SSOT) | — | result |
| `cloud_sync_full_sync` — Cloud_Sync Full Sync (POST) (SSOT) | — | result |
| `cloud_sync_get_profile` — Cloud_Sync Get Profile (GET) (SSOT) | — | result |
| `cloud_sync_update_profile` — Cloud_Sync Update Profile (PUT) (SSOT) | — | result |
| `cloud_sync_get_case` — Cloud_Sync Get Case (GET) (SSOT) | — | result |
| `cloud_sync_update_case` — Cloud_Sync Update Case (PUT) (SSOT) | — | result |
| `cloud_sync_timeline` — Cloud_Sync Get Timeline (GET) (SSOT) | — | result |
| `cloud_sync_add_timeline_event` — Cloud_Sync Add Timeline Event (POST) (SSOT) | — | result |
| `cloud_sync_calendar` — Cloud_Sync Get Calendar (GET) (SSOT) | — | result |
| `cloud_sync_add_calendar_event` — Cloud_Sync Add Calendar Event (POST) (SSOT) | — | result |
| `cloud_sync_export_all_data` — Cloud_Sync Export All Data (GET) (SSOT) | — | result |
| `cloud_sync_import_all_data` — Cloud_Sync Import All Data (POST) (SSOT) | — | result |
| `cloud_sync_documents` — Cloud_Sync Get Documents (GET) (SSOT) | — | result |
| `cloud_sync_vault_index` — Cloud_Sync Get Vault Index (GET) (SSOT) | — | result |
| `cloud_sync_get_vault_document` — Cloud_Sync Get Vault Document (GET) (SSOT) | — | result |
| `cloud_sync_vault_document_content` — Cloud_Sync Get Vault Document Content (GET) (SSOT) | — | result |
| `cloud_sync_patch_vault_document` — Cloud_Sync Update Vault Document (PATCH) (SSOT) | — | result |
| `cloud_sync_upload_document_to_cloud` — Cloud_Sync Upload Document To Cloud (POST) (SSOT) | — | result |
| `cloud_sync_check_storage_connection` — Cloud_Sync Check Storage Connection (GET) (SSOT) | — | result |


#### `components` — Components · tier —
- Layout: app/modules/components/ — 15 registered function groups (components_handle_capture_upload, components_handle_capture_input, components_handle_capture_voice, components_handle_understand_timeline, comp
- **15 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `components_handle_capture_upload` — Components Handle Capture Upload (POST) (SSOT) | — | result |
| `components_handle_capture_input` — Components Handle Capture Input (POST) (SSOT) | — | result |
| `components_handle_capture_voice` — Components Handle Capture Voice (POST) (SSOT) | — | result |
| `components_handle_understand_timeline` — Components Handle Understand Timeline (POST) (SSOT) | — | result |
| `components_handle_understand_rights` — Components Handle Understand Rights (POST) (SSOT) | — | result |
| `components_handle_understand_risk` — Components Handle Understand Risk (POST) (SSOT) | — | result |
| `components_handle_plan_action` — Components Handle Plan Action (POST) (SSOT) | — | result |
| `components_handle_plan_deadline` — Components Handle Plan Deadline (POST) (SSOT) | — | result |
| `components_handle_tenant_emergency` — Components Handle Tenant Emergency (POST) (SSOT) | — | result |
| `components_handle_advocate_handoff` — Components Handle Advocate Handoff (POST) (SSOT) | — | result |
| `components_handle_legal_review` — Components Handle Legal Review (POST) (SSOT) | — | result |
| `components_handle_admin_maintenance` — Components Handle Admin Maintenance (POST) (SSOT) | — | result |
| `components_workspace_stage` — Components Get Workspace Stage (GET) (SSOT) | — | result |
| `components_next_step` — Components Get Next Step (GET) (SSOT) | — | result |
| `components_component_config` — Components Get Component Config (GET) (SSOT) | — | result |


#### `context_loop` — Context Loop · tier DEV
- Layout: app/modules/context_loop/ — 11 registered function groups (context_loop_state, context_loop_intensity, context_loop_context, context_loop_emit_event, context_loop_process_document, context_loop_report
- **11 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `context_loop_state` — Context_Loop Get State (GET) (SSOT) | — | result |
| `context_loop_intensity` — Context_Loop Get Intensity (GET) (SSOT) | — | result |
| `context_loop_context` — Context_Loop Get Context (GET) (SSOT) | — | result |
| `context_loop_emit_event` — Context_Loop Emit Event (POST) (SSOT) | — | result |
| `context_loop_process_document` — Context_Loop Process Document (POST) (SSOT) | — | result |
| `context_loop_report_issue` — Context_Loop Report Issue (POST) (SSOT) | — | result |
| `context_loop_add_deadline` — Context_Loop Add Deadline (POST) (SSOT) | — | result |
| `context_loop_record_action` — Context_Loop Record Action (POST) (SSOT) | — | result |
| `context_loop_predictions` — Context_Loop Get Predictions (GET) (SSOT) | — | result |
| `context_loop_events` — Context_Loop Get Events (GET) (SSOT) | — | result |
| `context_loop_loop_health` — Context_Loop Loop Health (GET) (SSOT) | — | result |


#### `core_system` — Core System · tier CORE
- Layout: app/modules/core_system/ — 10 registered function groups (core_system_health_check, core_system_status, core_system_config_get, core_system_config_update, core_system_session_create, core_system_sessi
- **10 functions** · 7 distinct controls (5 required uses, 3 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `core_system_health_check` — Core System Health Check (SSOT) | — | status |
| `core_system_status` — Core System Status (SSOT) | — | status |
| `core_system_config_get` — Core System Get Config (SSOT) | — | config |
| `core_system_config_update` — Core System Update Config (SSOT) | **config** | success |
| `core_system_session_create` — Core System Create Session (SSOT) | **session_request** | session_id |
| `core_system_session_validate` — Core System Validate Session (SSOT) | **session_id** | valid |
| `core_system_session_destroy` — Core System Destroy Session (SSOT) | **session_id** | success |
| `core_system_log_add` — Core System Add Log (SSOT) | **log_entry** | success |
| `core_system_logs_get` — Core System Get Logs (SSOT) | *level*, *module*, *limit* | logs |
| `core_system_statistics` — Core System Statistics (SSOT) | — | statistics |


#### `correspondence` — Correspondence · tier ADMIN
- Layout: app/modules/correspondence/ — 4 registered function groups (correspondence_health, correspondence_templates_list, correspondence_logs_list, correspondence_send). Derived record: page layout not yet de
- **4 functions** · 1 distinct controls (1 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `correspondence_health` — Correspondence Health (SSOT) | — | status |
| `correspondence_templates_list` — Correspondence Templates List (SSOT) | — | templates |
| `correspondence_logs_list` — Correspondence Logs List (SSOT) | — | logs |
| `correspondence_send` — Correspondence Send (SSOT) | **message** | send_result |


#### `crawler` — Crawler · tier RESEARCH
- Layout: app/modules/crawler/ — 12 registered function groups (crawler_sources, crawler_source, crawler_crawl_url, crawler_search, crawler_search_statutes, crawler_search_business, crawler_search_property, cra
- **12 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `crawler_sources` — Crawler List Sources (GET) (SSOT) | — | result |
| `crawler_source` — Crawler Get Source (GET) (SSOT) | — | result |
| `crawler_crawl_url` — Crawler Crawl Url (POST) (SSOT) | — | result |
| `crawler_search` — Crawler Search (GET) (SSOT) | — | result |
| `crawler_search_statutes` — Crawler Search Statutes (GET) (SSOT) | — | result |
| `crawler_search_business` — Crawler Search Business (GET) (SSOT) | — | result |
| `crawler_search_property` — Crawler Search Property (GET) (SSOT) | — | result |
| `crawler_search_legal_aid` — Crawler Search Legal Aid (GET) (SSOT) | — | result |
| `crawler_statute` — Crawler Get Statute (GET) (SSOT) | — | result |
| `crawler_tenant_rights_statutes` — Crawler Get Tenant Rights Statutes (GET) (SSOT) | — | result |
| `crawler_ethics_policy` — Crawler Get Ethics Policy (GET) (SSOT) | — | result |
| `crawler_clear_cache` — Crawler Clear Cache (DELETE) (SSOT) | — | result |


#### `dashboard` — Dashboard · tier ADMIN
- Layout: app/modules/dashboard/ — 5 registered function groups (dashboard_unified, dashboard_refresh, dashboard_status_bar, dashboard_greeting, dashboard_quick_stats). Derived record: page layout not yet descr
- **5 functions** · 1 distinct controls (1 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `dashboard_unified` — Dashboard Unified (SSOT) | — | documents, timeline, deadlines, urgent_issues, contacts |
| `dashboard_refresh` — Dashboard Refresh (SSOT) | **context** | refreshed_sections |
| `dashboard_status_bar` — Dashboard Status Bar (SSOT) | — | unread, urgent, next_deadline |
| `dashboard_greeting` — Dashboard Personalized Greeting (SSOT) | — | greeting, encouragement? |
| `dashboard_quick_stats` — Dashboard Quick Stats (SSOT) | — | document_count, timeline_count, days_active, vault_size |


#### `data_freshness` — Data Freshness · tier CORE
- Layout: app/modules/data_freshness/ — 10 registered function groups (data_freshness_freshness_status, data_freshness_freshness_report, data_freshness_refresh_data, data_freshness_refresh_stale_data, data_fres
- **10 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `data_freshness_freshness_status` — Data_Freshness Get Freshness Status (GET) (SSOT) | — | result |
| `data_freshness_freshness_report` — Data_Freshness Get Freshness Report (GET) (SSOT) | — | result |
| `data_freshness_refresh_data` — Data_Freshness Refresh Data (POST) (SSOT) | — | result |
| `data_freshness_refresh_stale_data` — Data_Freshness Refresh Stale Data (POST) (SSOT) | — | result |
| `data_freshness_freshness_alerts` — Data_Freshness Get Freshness Alerts (GET) (SSOT) | — | result |
| `data_freshness_acknowledge_alert` — Data_Freshness Acknowledge Alert (POST) (SSOT) | — | result |
| `data_freshness_freshness_rules` — Data_Freshness Get Freshness Rules (GET) (SSOT) | — | result |
| `data_freshness_daily_refresh_cron` — Data_Freshness Daily Refresh Cron (POST) (SSOT) | — | result |
| `data_freshness_hourly_deadlines_cron` — Data_Freshness Hourly Deadlines Cron (POST) (SSOT) | — | result |
| `data_freshness_health_check` — Data_Freshness Health Check (GET) (SSOT) | — | result |


#### `debug` — Debug · tier —
- Layout: app/modules/debug/ — 1 registered function groups (debug_maintenance). Derived record: page layout not yet described.
- **1 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `debug_maintenance` — Debug Maintenance Endpoints (SSOT) | — | result |


#### `dev_lab` — Dev Lab · tier DEV
- Layout: app/modules/dev_lab/ — 12 registered function groups (dev_modules_list, dev_module_status, dev_module_promote, dev_module_test, ideas_list, ideas_submit, ideas_promote, dev_lab_dev_modules, dev_lab_de
- **5 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `dev_lab_dev_modules` — Dev_Lab List Dev Modules (GET) (SSOT) | — | result |
| `dev_lab_dev_module` — Dev_Lab Get Dev Module (GET) (SSOT) | — | result |
| `dev_lab_module_status` — Dev_Lab Get Module Status (GET) (SSOT) | — | result |
| `dev_lab_promote_module` — Dev_Lab Promote Module (POST) (SSOT) | — | result |
| `dev_lab_run_module_tests` — Dev_Lab Run Module Tests (POST) (SSOT) | — | result |


#### `development` — Development · tier DEV
- Layout: app/modules/development/ — 5 registered function groups (development_run_crawl, development_crawl_report, development_run_analysis, development_dev_health, development_dev_metrics). Derived record: pa
- **5 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `development_run_crawl` — Development Run Crawl (POST) (SSOT) | — | result |
| `development_crawl_report` — Development Get Crawl Report (GET) (SSOT) | — | result |
| `development_run_analysis` — Development Run Analysis (POST) (SSOT) | — | result |
| `development_dev_health` — Development Dev Health (GET) (SSOT) | — | result |
| `development_dev_metrics` — Development Get Dev Metrics (GET) (SSOT) | — | result |


#### `document_delivery` — Document Delivery · tier ADVOCATE
- Layout: app/modules/document_delivery/ — 9 registered function groups (document_delivery_health, document_delivery_inbox_page, document_delivery_send, document_delivery_inbox, document_delivery_outbox, docume
- **9 functions** · 6 distinct controls (15 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `document_delivery_health` — Document Delivery Health (SSOT) | — | status |
| `document_delivery_inbox_page` — Document Delivery Inbox Page (SSOT) | — | html |
| `document_delivery_send` — Document Delivery Send (SSOT) | **recipient_id**, **document_id**, **access_token** | delivery_id |
| `document_delivery_inbox` — Document Delivery Inbox (SSOT) | **access_token** | deliveries |
| `document_delivery_outbox` — Document Delivery Outbox (SSOT) | **access_token** | deliveries |
| `document_delivery_get` — Document Delivery Get (SSOT) | **delivery_id**, **access_token** | delivery |
| `document_delivery_mark_viewed` — Document Delivery Mark Viewed (SSOT) | **delivery_id**, **access_token** | success |
| `document_delivery_sign` — Document Delivery Sign (SSOT) | **delivery_id**, **signature_type**, **access_token** | signed_document |
| `document_delivery_reject` — Document Delivery Reject (SSOT) | **delivery_id**, **reason**, **access_token** | success |


#### `documentation` — Documentation · tier DEV
- Layout: app/modules/documentation/ — 13 registered function groups (documentation_openapi, documentation_postman, documentation_swagger, documentation_redoc, documentation_portal, documentation_reference, doc
- **13 functions** · 4 distinct controls (2 required uses, 2 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `documentation_openapi` — Documentation OpenAPI Spec (SSOT) | — | spec |
| `documentation_postman` — Documentation Postman Collection (SSOT) | — | collection |
| `documentation_swagger` — Documentation Swagger UI (SSOT) | — | html |
| `documentation_redoc` — Documentation ReDoc UI (SSOT) | — | html |
| `documentation_portal` — Documentation Developer Portal (SSOT) | — | html |
| `documentation_reference` — Documentation API Reference (SSOT) | — | reference |
| `documentation_module_reference` — Documentation Module Reference (SSOT) | **module_id** | reference |
| `documentation_examples` — Documentation Code Examples (SSOT) | *language*, *category* | examples |
| `documentation_example` — Documentation Code Example (SSOT) | **example_id** | example |
| `documentation_sdks` — Documentation SDKs (SSOT) | — | sdks |
| `documentation_support` — Documentation Support Resources (SSOT) | — | resources |
| `documentation_changelog` — Documentation Changelog (SSOT) | — | changelog |
| `documentation_statistics` — Documentation Statistics (SSOT) | — | statistics |


#### `emotion` — Emotion · tier RESEARCH
- Layout: app/modules/emotion/ — 8 registered function groups (emotion_emotional_state, emotion_record_trigger, emotion_dashboard_configuration, emotion_ui_settings, emotion_suggested_action, emotion_available_
- **8 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `emotion_emotional_state` — Emotion Get Emotional State (GET) (SSOT) | — | result |
| `emotion_record_trigger` — Emotion Record Trigger (POST) (SSOT) | — | result |
| `emotion_dashboard_configuration` — Emotion Get Dashboard Configuration (GET) (SSOT) | — | result |
| `emotion_ui_settings` — Emotion Get Ui Settings (GET) (SSOT) | — | result |
| `emotion_suggested_action` — Emotion Get Suggested Action (GET) (SSOT) | — | result |
| `emotion_available_triggers` — Emotion List Available Triggers (GET) (SSOT) | — | result |
| `emotion_simulate_emotional_scenario` — Emotion Simulate Emotional Scenario (POST) (SSOT) | — | result |
| `emotion_emotional_history` — Emotion Get Emotional History (GET) (SSOT) | — | result |


#### `enterprise_dashboard` — Enterprise Dashboard · tier ADMIN
- Layout: app/modules/enterprise_dashboard/ — 13 registered function groups (enterprise_dashboard_dashboard_stats, enterprise_dashboard_recent_activity, enterprise_dashboard_case_progress, enterprise_dashboard_
- **13 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `enterprise_dashboard_dashboard_stats` — Enterprise_Dashboard Get Dashboard Stats (GET) (SSOT) | — | result |
| `enterprise_dashboard_recent_activity` — Enterprise_Dashboard Get Recent Activity (GET) (SSOT) | — | result |
| `enterprise_dashboard_case_progress` — Enterprise_Dashboard Get Case Progress (GET) (SSOT) | — | result |
| `enterprise_dashboard_recent_documents` — Enterprise_Dashboard Get Recent Documents (GET) (SSOT) | — | result |
| `enterprise_dashboard_quick_actions` — Enterprise_Dashboard Get Quick Actions (GET) (SSOT) | — | result |
| `enterprise_dashboard_ai_insights` — Enterprise_Dashboard Get Ai Insights (GET) (SSOT) | — | result |
| `enterprise_dashboard_analytics` — Enterprise_Dashboard Get Analytics (GET) (SSOT) | — | result |
| `enterprise_dashboard_notifications` — Enterprise_Dashboard Get Notifications (GET) (SSOT) | — | result |
| `enterprise_dashboard_mark_notification_read` — Enterprise_Dashboard Mark Notification Read (POST) (SSOT) | — | result |
| `enterprise_dashboard_global_search` — Enterprise_Dashboard Global Search (GET) (SSOT) | — | result |
| `enterprise_dashboard_export_dashboard_report` — Enterprise_Dashboard Export Dashboard Report (GET) (SSOT) | — | result |
| `enterprise_dashboard_get_dashboard_preferences` — Enterprise_Dashboard Get Dashboard Preferences (GET) (SSOT) | — | result |
| `enterprise_dashboard_update_dashboard_preferences` — Enterprise_Dashboard Update Dashboard Preferences (PUT) (SSOT) | — | result |


#### `export_import` — Export Import · tier DEV
- Layout: app/modules/export_import/ — 12 registered function groups (export_import_export_request_endpoint, export_import_process_export_endpoint, export_import_export_status_endpoint, export_import_download_e
- **12 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `export_import_export_request_endpoint` — Export_Import Create Export Request Endpoint (POST) (SSOT) | — | result |
| `export_import_process_export_endpoint` — Export_Import Process Export Endpoint (POST) (SSOT) | — | result |
| `export_import_export_status_endpoint` — Export_Import Get Export Status Endpoint (GET) (SSOT) | — | result |
| `export_import_download_export_endpoint` — Export_Import Download Export Endpoint (GET) (SSOT) | — | result |
| `export_import_user_exports_endpoint` — Export_Import Get User Exports Endpoint (GET) (SSOT) | — | result |
| `export_import_export_endpoint` — Export_Import Delete Export Endpoint (DELETE) (SSOT) | — | result |
| `export_import_prepare_import_endpoint` — Export_Import Prepare Import Endpoint (POST) (SSOT) | — | result |
| `export_import_upload_import_file_endpoint` — Export_Import Upload Import File Endpoint (POST) (SSOT) | — | result |
| `export_import_process_import_endpoint` — Export_Import Process Import Endpoint (POST) (SSOT) | — | result |
| `export_import_export_statistics_endpoint` — Export_Import Get Export Statistics Endpoint (GET) (SSOT) | — | result |
| `export_import_supported_formats_endpoint` — Export_Import Get Supported Formats Endpoint (GET) (SSOT) | — | result |
| `export_import_cleanup_exports_endpoint` — Export_Import Cleanup Exports Endpoint (POST) (SSOT) | — | result |


#### `external_mappings` — External Mappings · tier EXTENDED
- Layout: app/modules/external_mappings/ — 11 registered function groups (external_mappings_mapping_create, external_mappings_list, external_mappings_get, external_mappings_update_status, external_mappings_cour
- **11 functions** · 14 distinct controls (8 required uses, 9 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `external_mappings_mapping_create` — External Mappings Create Mapping (SSOT) | **mapping** | mapping_id |
| `external_mappings_list` — External Mappings List (SSOT) | *mapping_type*, *status* | mappings |
| `external_mappings_get` — External Mappings Get (SSOT) | **mapping_id** | mapping |
| `external_mappings_update_status` — External Mappings Update Status (SSOT) | **mapping_id**, **status** | success |
| `external_mappings_court_case_create` — External Mappings Create Court Case (SSOT) | **case** | mapping_id |
| `external_mappings_court_cases_list` — External Mappings List Court Cases (SSOT) | *case_type*, *case_status* | court_cases |
| `external_mappings_property_create` — External Mappings Create Property (SSOT) | **property** | mapping_id |
| `external_mappings_properties_list` — External Mappings List Properties (SSOT) | *county*, *is_primary* | properties |
| `external_mappings_agency_create` — External Mappings Create Agency (SSOT) | **agency** | mapping_id |
| `external_mappings_agencies_list` — External Mappings List Agencies (SSOT) | *agency_code*, *complaint_type* | agencies |
| `external_mappings_search` — External Mappings Search (SSOT) | **query**, *mapping_type* | results |


#### `extraction` — Extraction · tier RESEARCH
- Layout: app/modules/extraction/ — 6 registered function groups (extraction_extract_form_fields, extraction_extract_from_vault_documents, extraction_review_items, extraction_confirm_extracted_fields, extractio
- **6 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `extraction_extract_form_fields` — Extraction Extract Form Fields (POST) (SSOT) | — | result |
| `extraction_extract_from_vault_documents` — Extraction Extract From Vault Documents (POST) (SSOT) | — | result |
| `extraction_review_items` — Extraction Get Review Items (GET) (SSOT) | — | result |
| `extraction_confirm_extracted_fields` — Extraction Confirm Extracted Fields (POST) (SSOT) | — | result |
| `extraction_apply_extraction_to_forms` — Extraction Apply Extraction To Forms (POST) (SSOT) | — | result |
| `extraction_field_definitions` — Extraction Get Field Definitions (GET) (SSOT) | — | result |


#### `filedored` — Filedored · tier DEV
- Layout: app/modules/filedored/ — 7 registered function groups (document_process, folders_ensure, filedored_process_documents, filedored_check_folders, filedored_browse_folder, filedored_folders, filedored_hea
- **5 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `filedored_process_documents` — Filedored Process Documents (POST) (SSOT) | — | result |
| `filedored_check_folders` — Filedored Check Folders (POST) (SSOT) | — | result |
| `filedored_browse_folder` — Filedored Browse Folder (GET) (SSOT) | — | result |
| `filedored_folders` — Filedored List Folders (GET) (SSOT) | — | result |
| `filedored_health_check` — Filedored Health Check (GET) (SSOT) | — | result |


#### `form_data` — Form Data · tier RESEARCH
- Layout: app/modules/form_data/ — 15 registered function groups (form_data_form_data, form_data_extracted_data, form_data_case_summary, form_data_case_info, form_data_answer_form_data, form_data_motion_form_da
- **15 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `form_data_form_data` — Form_Data Get Form Data (GET) (SSOT) | — | result |
| `form_data_extracted_data` — Form_Data Get Extracted Data (GET) (SSOT) | — | result |
| `form_data_case_summary` — Form_Data Get Case Summary (GET) (SSOT) | — | result |
| `form_data_case_info` — Form_Data Update Case Info (PUT) (SSOT) | — | result |
| `form_data_answer_form_data` — Form_Data Get Answer Form Data (GET) (SSOT) | — | result |
| `form_data_motion_form_data` — Form_Data Get Motion Form Data (GET) (SSOT) | — | result |
| `form_data_counterclaim_form_data` — Form_Data Get Counterclaim Form Data (GET) (SSOT) | — | result |
| `form_data_add_defense` — Form_Data Add Defense (POST) (SSOT) | — | result |
| `form_data_remove_defense` — Form_Data Remove Defense (POST) (SSOT) | — | result |
| `form_data_selected_defenses` — Form_Data Get Selected Defenses (GET) (SSOT) | — | result |
| `form_data_add_counterclaim` — Form_Data Add Counterclaim (POST) (SSOT) | — | result |
| `form_data_counterclaims` — Form_Data Get Counterclaims (GET) (SSOT) | — | result |
| `form_data_case_documents` — Form_Data Get Case Documents (GET) (SSOT) | — | result |
| `form_data_case_timeline` — Form_Data Get Case Timeline (GET) (SSOT) | — | result |
| `form_data_refresh_form_data` — Form_Data Refresh Form Data (POST) (SSOT) | — | result |


#### `fraud_exposure` — Fraud Exposure · tier RESEARCH
- Layout: app/modules/fraud_exposure/ — 8 registered function groups (fraud_exposure_fraud_health_check, fraud_exposure_analyze_fraud, fraud_exposure_fraud_report, fraud_exposure_check_fraud_pattern, fraud_expo
- **8 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `fraud_exposure_fraud_health_check` — Fraud_Exposure Fraud Health Check (GET) (SSOT) | — | result |
| `fraud_exposure_analyze_fraud` — Fraud_Exposure Analyze Fraud (POST) (SSOT) | — | result |
| `fraud_exposure_fraud_report` — Fraud_Exposure Get Fraud Report (GET) (SSOT) | — | result |
| `fraud_exposure_check_fraud_pattern` — Fraud_Exposure Check Fraud Pattern (POST) (SSOT) | — | result |
| `fraud_exposure_statute_of_limitations` — Fraud_Exposure Get Statute Of Limitations (GET) (SSOT) | — | result |
| `fraud_exposure_whistleblower_info` — Fraud_Exposure Get Whistleblower Info (GET) (SSOT) | — | result |
| `fraud_exposure_fraud_patterns` — Fraud_Exposure List Fraud Patterns (GET) (SSOT) | — | result |
| `fraud_exposure_reporting_agencies` — Fraud_Exposure List Reporting Agencies (GET) (SSOT) | — | result |


#### `functionx` — Functionx · tier RESEARCH
- Layout: app/modules/functionx/ — 5 registered function groups (functionx_health, functionx_create_action_set, functionx_action_sets, functionx_get_action_set, functionx_execute_action_set). Derived record: pa
- **5 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `functionx_health` — Functionx Functionx Health (GET) (SSOT) | — | result |
| `functionx_create_action_set` — Functionx Create Action Set (POST) (SSOT) | — | result |
| `functionx_action_sets` — Functionx List Action Sets (GET) (SSOT) | — | result |
| `functionx_get_action_set` — Functionx Get Action Set (GET) (SSOT) | — | result |
| `functionx_execute_action_set` — Functionx Execute Action Set (POST) (SSOT) | — | result |


#### `funding_mgmt` — Funding Mgmt · tier ADMIN
- Layout: app/modules/funding_mgmt/ — 2 registered function groups (funding_mgmt_funding_dashboard, funding_mgmt_funding_prospectus). Derived record: page layout not yet described.
- **2 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `funding_mgmt_funding_dashboard` — Funding_Mgmt Funding Dashboard (GET) (SSOT) | — | result |
| `funding_mgmt_funding_prospectus` — Funding_Mgmt Funding Prospectus (GET) (SSOT) | — | result |


#### `funding_search` — Funding Search · tier RESEARCH
- Layout: app/modules/funding_search/ — 11 registered function groups (funding_search_funding_programs, funding_search_program_details, funding_search_search_funding_records, funding_search_search_by_address, f
- **11 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `funding_search_funding_programs` — Funding_Search List Funding Programs (GET) (SSOT) | — | result |
| `funding_search_program_details` — Funding_Search Get Program Details (GET) (SSOT) | — | result |
| `funding_search_search_funding_records` — Funding_Search Search Funding Records (POST) (SSOT) | — | result |
| `funding_search_search_by_address` — Funding_Search Search By Address (GET) (SSOT) | — | result |
| `funding_search_search_by_company` — Funding_Search Search By Company (GET) (SSOT) | — | result |
| `funding_search_search_by_broker` — Funding_Search Search By Broker (GET) (SSOT) | — | result |
| `funding_search_funding_record` — Funding_Search Get Funding Record (GET) (SSOT) | — | result |
| `funding_search_funding_statistics` — Funding_Search Get Funding Statistics (GET) (SSOT) | — | result |
| `funding_search_check_eligibility` — Funding_Search Check Eligibility (GET) (SSOT) | — | result |
| `funding_search_data_sources` — Funding_Search List Data Sources (GET) (SSOT) | — | result |
| `funding_search_health` — Funding_Search Funding Search Health (GET) (SSOT) | — | result |


#### `health` — Health · tier CORE
- Layout: app/modules/health/ — 6 registered function groups (health_liveness, health_readiness, health_metrics, health_metrics_json, health_system_dashboard, health_api_summary). Derived record: page layout no
- **6 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `health_liveness` — Health Liveness (SSOT) | — | status, timestamp |
| `health_readiness` — Health Readiness (SSOT) | — | status, checks |
| `health_metrics` — Health Metrics (SSOT) | — | metrics |
| `health_metrics_json` — Health Metrics JSON (SSOT) | — | metrics |
| `health_system_dashboard` — Health System Dashboard (SSOT) | — | html |
| `health_api_summary` — Health API Summary (SSOT) | — | summary |


#### `hud_funding` — Hud Funding · tier RESEARCH
- Layout: app/modules/hud_funding/ — 17 registered function groups (hud_funding_all_programs, hud_funding_program_details, hud_funding_program_summary, hud_funding_search_programs, hud_funding_tax_credit_progra
- **17 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `hud_funding_all_programs` — Hud_Funding List All Programs (GET) (SSOT) | — | result |
| `hud_funding_program_details` — Hud_Funding Get Program Details (GET) (SSOT) | — | result |
| `hud_funding_program_summary` — Hud_Funding Get Program Summary (GET) (SSOT) | — | result |
| `hud_funding_search_programs` — Hud_Funding Search Programs (GET) (SSOT) | — | result |
| `hud_funding_tax_credit_programs` — Hud_Funding List Tax Credit Programs (GET) (SSOT) | — | result |
| `hud_funding_voucher_programs` — Hud_Funding List Voucher Programs (GET) (SSOT) | — | result |
| `hud_funding_grant_programs` — Hud_Funding List Grant Programs (GET) (SSOT) | — | result |
| `hud_funding_landlord_requirements` — Hud_Funding Get Landlord Requirements (GET) (SSOT) | — | result |
| `hud_funding_landlord_eligibility` — Hud_Funding Get Landlord Eligibility (GET) (SSOT) | — | result |
| `hud_funding_all_landlord_obligations` — Hud_Funding Get All Landlord Obligations (GET) (SSOT) | — | result |
| `hud_funding_tenant_recourse` — Hud_Funding Get Tenant Recourse (GET) (SSOT) | — | result |
| `hud_funding_tax_breaks` — Hud_Funding List Tax Breaks (GET) (SSOT) | — | result |
| `hud_funding_tax_break` — Hud_Funding Get Tax Break (GET) (SSOT) | — | result |
| `hud_funding_check_tenant_eligibility` — Hud_Funding Check Tenant Eligibility (POST) (SSOT) | — | result |
| `hud_funding_check_property_programs` — Hud_Funding Check Property Programs (GET) (SSOT) | — | result |
| `hud_funding_compare_programs` — Hud_Funding Compare Programs (GET) (SSOT) | — | result |
| `hud_funding_quick_reference` — Hud_Funding Quick Reference (GET) (SSOT) | — | result |


#### `info_donation` — Info Donation · tier —
- Layout: app/modules/info_donation/ — 2 registered function groups (info_donation_donate, info_donation_review). Page surface: /help-the-next-tenant (shell--solo).
- Preview state (contract): review-before-submit — the page renders the exact answers to be stored before POST /donate
- Review state (contract): free-text items stored as moderation=pending; never served until approved by a reviewer
- Declared control types: `consent_version`=button, `item_id`=button, `user_id`=auto_detect
- **2 functions** · 4 distinct controls (4 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `info_donation_donate` — Info Donation — Share What Happened (SSOT) | **items**, **consent_version** | stored, items, status |
| `info_donation_review` — Info Donation — Narrative Review (SSOT) | **item_id**, **decision** | item |


#### `inventory` — Inventory · tier DEV
- Layout: app/modules/inventory/ — 8 registered function groups (inventory_backup, inventory_snapshot, inventory_inventory_items, inventory_get_inventory_item, inventory_inventory_summary, inventory_rotate_inve
- **8 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `inventory_backup` — Inventory Create Backup (POST) (SSOT) | — | result |
| `inventory_snapshot` — Inventory Create Snapshot (POST) (SSOT) | — | result |
| `inventory_inventory_items` — Inventory Get Inventory Items (GET) (SSOT) | — | result |
| `inventory_get_inventory_item` — Inventory Get Inventory Item (GET) (SSOT) | — | result |
| `inventory_inventory_summary` — Inventory Get Inventory Summary (GET) (SSOT) | — | result |
| `inventory_rotate_inventory` — Inventory Rotate Inventory (POST) (SSOT) | — | result |
| `inventory_delete_inventory_item` — Inventory Delete Inventory Item (DELETE) (SSOT) | — | result |
| `inventory_health` — Inventory Inventory Health (GET) (SSOT) | — | result |


#### `invite_codes` — Invite Codes · tier ADVOCATE
- Layout: app/modules/invite_codes/ — 6 registered function groups (invite_codes_validate, invite_codes_redeem, invite_codes_create, invite_codes_list, invite_codes_delete, invite_codes_stats). Derived record: 
- **6 functions** · 5 distinct controls (9 required uses, 2 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `invite_codes_validate` — Invite Codes Validate (SSOT) | **code** | valid, organization_id? |
| `invite_codes_redeem` — Invite Codes Redeem (SSOT) | **code** | success, organization_id |
| `invite_codes_create` — Invite Codes Create (SSOT) | **manager_user_id**, **organization_id**, *max_uses*, *expires_at* | code |
| `invite_codes_list` — Invite Codes List (SSOT) | **manager_user_id** | codes |
| `invite_codes_delete` — Invite Codes Deactivate (SSOT) | **code**, **manager_user_id** | success |
| `invite_codes_stats` — Invite Codes Stats (SSOT) | **code**, **manager_user_id** | stats |


#### `law_linker` — Law Linker · tier —
- Layout: app/modules/law_linker/ — 2 registered function groups (law_linker_citation, law_linker_pop_out). Derived record: page layout not yet described.
- **2 functions** · 1 distinct controls (2 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `law_linker_citation` — Law Linker Citation (SSOT) | **citation** | citation, source_url, text, summary |
| `law_linker_pop_out` — Law Linker Pop-out (SSOT) | **citation** | html |


#### `legal_intel` — Legal Intel · tier —
- **3 functions** · 10 distinct controls (0 required uses, 10 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `legal_intel_entity_lookup` — Legal Intel Entity Lookup (SSOT) | *entity_name*, *bar_number*, *registered_agent* | entities, attorney |
| `legal_intel_pattern_analysis` — Legal Intel Pattern Analysis (SSOT) | *attorney_id*, *entity_id* | patterns, clusters |
| `legal_intel_records` — Legal Intel Record Management (SSOT) | *entity*, *attorney*, *case*, *docket*, *relationship* | record |


#### `litigation_intelligence` — Litigation Intelligence · tier RESEARCH
- Layout: app/modules/litigation_intelligence/ — 17 registered function groups (litigation_intelligence_scrape_court, litigation_intelligence_scrape_filings, litigation_intelligence_normalize_entity, litigation
- **18 functions** · 7 distinct controls (7 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `litigation_intelligence_scrape_court` — LIS Scrape Court System (SSOT) | — | results |
| `litigation_intelligence_scrape_filings` — LIS Scrape Case Filings (SSOT) | **case_number** | filings |
| `litigation_intelligence_normalize_entity` — LIS Normalize Entity (SSOT) | — | normalized |
| `litigation_intelligence_normalize_entities` — LIS Normalize Entities Batch (SSOT) | — | normalized |
| `litigation_intelligence_analyze_case` — LIS Analyze Case Intelligence (SSOT) | — | analysis |
| `litigation_intelligence_retaliation_check` — LIS Retaliation Check (SSOT) | — | retaliation_check |
| `litigation_intelligence_get` — LIS Get Case Intelligence (SSOT) | **case_id** | intelligence |
| `litigation_intelligence_graph_build` — LIS Build Entity Graph (SSOT) | — | graph |
| `litigation_intelligence_graph_visualize` — LIS Generate Graph Visualization (SSOT) | — | visualization |
| `litigation_intelligence_graph_path` — LIS Find Shortest Path (SSOT) | **source_entity**, **target_entity** | path |
| `litigation_intelligence_report_generate` — LIS Generate Report (SSOT) | — | report_id |
| `litigation_intelligence_report_get` — LIS Get Report (SSOT) | **report_id** | report |
| `litigation_intelligence_report_export` — LIS Export Report (SSOT) | **report_id**, *format* | export |
| `litigation_intelligence_task_schedule` — LIS Schedule Task (SSOT) | — | task_id |
| `litigation_intelligence_tasks_list` — LIS List Scheduled Tasks (SSOT) | — | tasks |
| `litigation_intelligence_task_remove` — LIS Remove Scheduled Task (SSOT) | **task_id** | success |
| `litigation_intelligence_statistics` — LIS Statistics (SSOT) | — | statistics |
| `litigation_intelligence_health` — LIS Health Check (SSOT) | — | status |


#### `local_ai` — Local Ai · tier —
- **4 functions** · 5 distinct controls (3 required uses, 3 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `local_ai_health` — Local AI Health (SSOT) | — | status |
| `local_ai_chat` — Local AI Chat (SSOT) | **messages**, *options* | response |
| `local_ai_analyze` — Local AI Analyze (SSOT) | **text**, *analysis_type* | analysis |
| `local_ai_summarize` — Local AI Summarize (SSOT) | **text**, *max_length* | summary |


#### `manager` — Manager · tier ADMIN
- Layout: app/modules/manager/ — 5 registered function groups (manager_assign_case, manager_bulk_export, manager_reports_cases, manager_reports_staff, manager_update_staff_role). Derived record: page layout not
- **5 functions** · 6 distinct controls (10 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `manager_assign_case` — Manager Assign Case (SSOT) | **manager_user_id**, **tenant_user_id**, **advocate_user_id** | relationship_id |
| `manager_bulk_export` — Manager Bulk Export (SSOT) | **manager_user_id**, **tenant_user_ids** | export_data, format |
| `manager_reports_cases` — Manager Case Report (SSOT) | **manager_user_id** | report |
| `manager_reports_staff` — Manager Staff Productivity Report (SSOT) | **manager_user_id** | report |
| `manager_update_staff_role` — Manager Update Staff Role (SSOT) | **manager_user_id**, **staff_user_id**, **new_role** | success |


#### `mesh_network` — Mesh Network · tier —
- Layout: app/modules/mesh_network/ — 11 registered function groups (mesh_network_network_status, mesh_network_network_graph, mesh_network_network_modules, mesh_network_call_module, mesh_network_call_many_modul
- **11 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `mesh_network_network_status` — Mesh_Network Get Network Status (GET) (SSOT) | — | result |
| `mesh_network_network_graph` — Mesh_Network Get Network Graph (GET) (SSOT) | — | result |
| `mesh_network_network_modules` — Mesh_Network List Network Modules (GET) (SSOT) | — | result |
| `mesh_network_call_module` — Mesh_Network Call Module (POST) (SSOT) | — | result |
| `mesh_network_call_many_modules` — Mesh_Network Call Many Modules (POST) (SSOT) | — | result |
| `mesh_network_start_collaboration` — Mesh_Network Start Collaboration (POST) (SSOT) | — | result |
| `mesh_network_broadcast_event` — Mesh_Network Broadcast Event (POST) (SSOT) | — | result |
| `mesh_network_ask_mesh` — Mesh_Network Ask Mesh (POST) (SSOT) | — | result |
| `mesh_network_quick_case_summary` — Mesh_Network Quick Case Summary (POST) (SSOT) | — | result |
| `mesh_network_quick_deadline_check` — Mesh_Network Quick Deadline Check (POST) (SSOT) | — | result |
| `mesh_network_quick_build_defense` — Mesh_Network Quick Build Defense (POST) (SSOT) | — | result |


#### `module_hub` — Module Hub · tier RESEARCH
- Layout: app/modules/module_hub/ — 21 registered function groups (module_hub_hub_status, module_hub_modules, module_hub_function_group_contracts, module_hub_function_group_contract_health, module_hub_user_pack
- **21 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `module_hub_hub_status` — Module_Hub Get Hub Status (GET) (SSOT) | — | result |
| `module_hub_modules` — Module_Hub List Modules (GET) (SSOT) | — | result |
| `module_hub_function_group_contracts` — Module_Hub List Function Group Contracts (GET) (SSOT) | — | result |
| `module_hub_function_group_contract_health` — Module_Hub Function Group Contract Health (GET) (SSOT) | — | result |
| `module_hub_user_packs` — Module_Hub Get User Packs (GET) (SSOT) | — | result |
| `module_hub_pending_packs` — Module_Hub Get Pending Packs (GET) (SSOT) | — | result |
| `module_hub_pack` — Module_Hub Get Pack (GET) (SSOT) | — | result |
| `module_hub_complete_pack` — Module_Hub Complete Pack (POST) (SSOT) | — | result |
| `module_hub_user_data` — Module_Hub Get User Data (GET) (SSOT) | — | result |
| `module_hub_make_data_request` — Module_Hub Make Data Request (POST) (SSOT) | — | result |
| `module_hub_comm_log` — Module_Hub Get Comm Log (GET) (SSOT) | — | result |
| `module_hub_case_info` — Module_Hub Get Case Info (GET) (SSOT) | — | result |
| `module_hub_lease_data` — Module_Hub Get Lease Data (GET) (SSOT) | — | result |
| `module_hub_landlord_info` — Module_Hub Get Landlord Info (GET) (SSOT) | — | result |
| `module_hub_property_info` — Module_Hub Get Property Info (GET) (SSOT) | — | result |
| `module_hub_deadlines` — Module_Hub Get Deadlines (GET) (SSOT) | — | result |
| `module_hub_user_context` — Module_Hub Get User Context (GET) (SSOT) | — | result |
| `module_hub_mesh_status` — Module_Hub Get Mesh Status (GET) (SSOT) | — | result |
| `module_hub_set_mesh_mode` — Module_Hub Set Mesh Mode (POST) (SSOT) | — | result |
| `module_hub_deferral_status` — Module_Hub Get Deferral Status (GET) (SSOT) | — | result |
| `module_hub_retry_deferred_actions` — Module_Hub Retry Deferred Actions (POST) (SSOT) | — | result |


#### `page_composer` — Page Composer · tier CORE
- Layout: app/modules/page_composer/ — 2 registered function groups (page_compose, page_assemble). Derived record: page layout not yet described.
- **2 functions** · 6 distinct controls (2 required uses, 6 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `page_compose` — Page Compose (SSOT) | **subject**, *jurisdiction*, *fact_limit*, *story_limit* | page |
| `page_assemble` — Page Assembly Formula | **subject**, *jurisdiction*, *intent*, *user_context* | page_config, components, govern_report, metadata |


#### `page_editor` — Page Editor · tier DEV
- Layout: app/modules/page_editor/ — 6 registered function groups (page_editor_list_files, page_editor_get_file, page_editor_save_file, page_editor_preview_file, page_editor_search_files, page_editor_page). Der
- **6 functions** · 4 distinct controls (6 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `page_editor_list_files` — Page Editor List Files (SSOT) | — | files |
| `page_editor_get_file` — Page Editor Get File (SSOT) | **path** | content, path |
| `page_editor_save_file` — Page Editor Save File (SSOT) | **path**, **content** | saved, path |
| `page_editor_preview_file` — Page Editor Preview File (SSOT) | **path**, **content** | preview |
| `page_editor_search_files` — Page Editor Search Files (SSOT) | **q**, *type* | results |
| `page_editor_page` — Page Editor Page (SSOT) | — | redirect |


#### `page_index` — Page Index · tier DEV
- Layout: app/modules/page_index/ — 4 registered function groups (page_index_scan_html_pages, page_index_scan_fastapi_pages, page_index_page_stats, page_index_search_pages). Derived record: page layout not yet 
- **4 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `page_index_scan_html_pages` — Page_Index Scan Html Pages (GET) (SSOT) | — | result |
| `page_index_scan_fastapi_pages` — Page_Index Scan Fastapi Pages (GET) (SSOT) | — | result |
| `page_index_page_stats` — Page_Index Get Page Stats (GET) (SSOT) | — | result |
| `page_index_search_pages` — Page_Index Search Pages (GET) (SSOT) | — | result |


#### `page_router` — Page Router · tier —
- Layout: app/modules/page_router/ — 1 registered function groups (serve_manifest_page). Derived record: page layout not yet described.
- **1 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `serve_manifest_page` — Page Router - Serve Manifest Page | — | html_or_redirect |


#### `page_shell` — Page Shell · tier CORE
- Layout: app/modules/page_shell/ — 2 registered function groups (render_page, load_page_config). Derived record: page layout not yet described.
- **2 functions** · 2 distinct controls (2 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `render_page` — Page Shell — Render Page | **page_config** | html |
| `load_page_config` — Page Shell — Load Page Config | **raw_config** | page_config, govern_report |


#### `plugins` — Plugins · tier —
- Layout: app/modules/plugins/ — 7 registered function groups (plugins_plugins, plugins_plugin, plugins_load_plugin, plugins_unload_plugin, plugins_execute_plugin_action, plugins_browse_marketplace, plugins_plu
- **7 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `plugins_plugins` — Plugins List Plugins (GET) (SSOT) | — | result |
| `plugins_plugin` — Plugins Get Plugin (GET) (SSOT) | — | result |
| `plugins_load_plugin` — Plugins Load Plugin (POST) (SSOT) | — | result |
| `plugins_unload_plugin` — Plugins Unload Plugin (POST) (SSOT) | — | result |
| `plugins_execute_plugin_action` — Plugins Execute Plugin Action (POST) (SSOT) | — | result |
| `plugins_browse_marketplace` — Plugins Browse Marketplace (GET) (SSOT) | — | result |
| `plugins_plugin_system_health` — Plugins Plugin System Health (GET) (SSOT) | — | result |


#### `portal` — Portal · tier CORE
- Layout: app/modules/portal/ — 1 registered function groups (portal_services). Derived record: page layout not yet described.
- **1 functions** · 2 distinct controls (0 required uses, 2 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `portal_services` — Portal Services (SSOT) | *category*, *service_id* | services, categories |


#### `positronic_mesh` — Positronic Mesh · tier —
- Layout: app/modules/positronic_mesh/ — 13 registered function groups (positronic_mesh_mesh_status, positronic_mesh_available_workflows, positronic_mesh_connected_modules, positronic_mesh_start_workflow, posit
- **13 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `positronic_mesh_mesh_status` — Positronic_Mesh Get Mesh Status (GET) (SSOT) | — | result |
| `positronic_mesh_available_workflows` — Positronic_Mesh Get Available Workflows (GET) (SSOT) | — | result |
| `positronic_mesh_connected_modules` — Positronic_Mesh Get Connected Modules (GET) (SSOT) | — | result |
| `positronic_mesh_start_workflow` — Positronic_Mesh Start Workflow (POST) (SSOT) | — | result |
| `positronic_mesh_workflow_status` — Positronic_Mesh Get Workflow Status (GET) (SSOT) | — | result |
| `positronic_mesh_provide_workflow_input` — Positronic_Mesh Provide Workflow Input (POST) (SSOT) | — | result |
| `positronic_mesh_user_workflows` — Positronic_Mesh Get User Workflows (GET) (SSOT) | — | result |
| `positronic_mesh_quick_start_eviction` — Positronic_Mesh Quick Start Eviction (POST) (SSOT) | — | result |
| `positronic_mesh_quick_start_lease_analysis` — Positronic_Mesh Quick Start Lease Analysis (POST) (SSOT) | — | result |
| `positronic_mesh_quick_start_court_prep` — Positronic_Mesh Quick Start Court Prep (POST) (SSOT) | — | result |
| `positronic_mesh_quick_sync_modules` — Positronic_Mesh Quick Sync Modules (POST) (SSOT) | — | result |
| `positronic_mesh_invoke_module_action` — Positronic_Mesh Invoke Module Action (POST) (SSOT) | — | result |
| `positronic_mesh_module_actions` — Positronic_Mesh Get Module Actions (GET) (SSOT) | — | result |


#### `preamble` — Preamble · tier CORE
- Layout: app/modules/preamble/ — 1 registered function groups (preamble_preamble). Derived record: page layout not yet described.
- **1 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `preamble_preamble` — Preamble Preamble (GET) (SSOT) | — | result |


#### `progress` — Progress · tier EXTENDED
- Layout: app/modules/progress/ — 12 registered function groups (progress_progress, progress_case_readiness, progress_all_milestones, progress_next_milestones, progress_complete_milestone, progress_skip_milesto
- **12 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `progress_progress` — Progress Get Progress (GET) (SSOT) | — | result |
| `progress_case_readiness` — Progress Get Case Readiness (GET) (SSOT) | — | result |
| `progress_all_milestones` — Progress Get All Milestones (GET) (SSOT) | — | result |
| `progress_next_milestones` — Progress Get Next Milestones (GET) (SSOT) | — | result |
| `progress_complete_milestone` — Progress Complete Milestone (POST) (SSOT) | — | result |
| `progress_skip_milestone` — Progress Skip Milestone (POST) (SSOT) | — | result |
| `progress_points` — Progress Get Points (GET) (SSOT) | — | result |
| `progress_stats` — Progress Get Stats (GET) (SSOT) | — | result |
| `progress_increment_stat` — Progress Increment Stat (POST) (SSOT) | — | result |
| `progress_setup_case` — Progress Setup Case (POST) (SSOT) | — | result |
| `progress_journey_overview` — Progress Get Journey Overview (GET) (SSOT) | — | result |
| `progress_achievements` — Progress Get Achievements (GET) (SSOT) | — | result |


#### `public_exposure` — Public Exposure · tier RESEARCH
- Layout: app/modules/public_exposure/ — 10 registered function groups (public_exposure_exposure_health_check, public_exposure_generate_press_release, public_exposure_press_release, public_exposure_press_releas
- **10 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `public_exposure_exposure_health_check` — Public_Exposure Exposure Health Check (GET) (SSOT) | — | result |
| `public_exposure_generate_press_release` — Public_Exposure Generate Press Release (POST) (SSOT) | — | result |
| `public_exposure_press_release` — Public_Exposure Get Press Release (GET) (SSOT) | — | result |
| `public_exposure_press_release_text` — Public_Exposure Get Press Release Text (GET) (SSOT) | — | result |
| `public_exposure_generate_media_kit` — Public_Exposure Generate Media Kit (POST) (SSOT) | — | result |
| `public_exposure_media_kit` — Public_Exposure Get Media Kit (GET) (SSOT) | — | result |
| `public_exposure_media_outlets` — Public_Exposure List Media Outlets (GET) (SSOT) | — | result |
| `public_exposure_supported_languages` — Public_Exposure List Supported Languages (GET) (SSOT) | — | result |
| `public_exposure_release_types` — Public_Exposure List Release Types (GET) (SSOT) | — | result |
| `public_exposure_generate_social_posts` — Public_Exposure Generate Social Posts (POST) (SSOT) | — | result |


#### `public_surface` — Public Surface · tier —
- Layout: app/modules/public_surface/ — 1 registered function groups (landing_and_i18n). Derived record: page layout not yet described.
- **1 functions** · 1 distinct controls (0 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `landing_and_i18n` — Public Landing & i18n (SSOT) | *locale* | facts, locale |


#### `recognition` — Recognition · tier RESEARCH
- Layout: app/modules/recognition/ — 10 registered function groups (recognition_analyze_text, recognition_analyze_file, recognition_quick_classify, recognition_analyze_handwriting_endpoint, recognition_verify_s
- **10 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `recognition_analyze_text` — Recognition Analyze Text (POST) (SSOT) | — | result |
| `recognition_analyze_file` — Recognition Analyze File (POST) (SSOT) | — | result |
| `recognition_quick_classify` — Recognition Quick Classify (POST) (SSOT) | — | result |
| `recognition_analyze_handwriting_endpoint` — Recognition Analyze Handwriting Endpoint (POST) (SSOT) | — | result |
| `recognition_verify_signature` — Recognition Verify Signature (POST) (SSOT) | — | result |
| `recognition_forgery_types` — Recognition Get Forgery Types (GET) (SSOT) | — | result |
| `recognition_batch_analyze` — Recognition Batch Analyze (POST) (SSOT) | — | result |
| `recognition_document_types` — Recognition Get Document Types (GET) (SSOT) | — | result |
| `recognition_entity_types` — Recognition Get Entity Types (GET) (SSOT) | — | result |
| `recognition_health` — Recognition Recognition Health (GET) (SSOT) | — | result |


#### `registry` — Registry · tier ADMIN
- Layout: app/modules/registry/ — 21 registered function groups (registry_register_document, registry_get_document, registry_documents, registry_delete_document, registry_clear_all_documents, registry_duplicate
- **21 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `registry_register_document` — Registry Register Document (POST) (SSOT) | — | result |
| `registry_get_document` — Registry Get Document (GET) (SSOT) | — | result |
| `registry_documents` — Registry List Documents (GET) (SSOT) | — | result |
| `registry_delete_document` — Registry Delete Document (DELETE) (SSOT) | — | result |
| `registry_clear_all_documents` — Registry Clear All Documents (DELETE) (SSOT) | — | result |
| `registry_duplicates` — Registry Get Duplicates (GET) (SSOT) | — | result |
| `registry_custody_chain` — Registry Get Custody Chain (GET) (SSOT) | — | result |
| `registry_verify_document` — Registry Verify Document (POST) (SSOT) | — | result |
| `registry_integrity_status` — Registry Get Integrity Status (GET) (SSOT) | — | result |
| `registry_document_hash` — Registry Get Document Hash (GET) (SSOT) | — | result |
| `registry_flag_document` — Registry Flag Document (POST) (SSOT) | — | result |
| `registry_associate_case` — Registry Associate Case (POST) (SSOT) | — | result |
| `registry_flagged_documents` — Registry Get Flagged Documents (GET) (SSOT) | — | result |
| `registry_quarantined_documents` — Registry Get Quarantined Documents (GET) (SSOT) | — | result |
| `registry_registry_stats` — Registry Get Registry Stats (GET) (SSOT) | — | result |
| `registry_document_statuses` — Registry Get Document Statuses (GET) (SSOT) | — | result |
| `registry_integrity_statuses` — Registry Get Integrity Statuses (GET) (SSOT) | — | result |
| `registry_forgery_indicators` — Registry Get Forgery Indicators (GET) (SSOT) | — | result |
| `registry_custody_actions` — Registry Get Custody Actions (GET) (SSOT) | — | result |
| `registry_case_documents` — Registry Get Case Documents (GET) (SSOT) | — | result |
| `registry_cases` — Registry List Cases (GET) (SSOT) | — | result |


#### `research` — Research · tier RESEARCH
- Layout: app/modules/research/ — 18 registered function groups (research_health_check, research_property, research_property_profile, research_property_summary, research_property_fraud_flags, research_download_
- **18 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `research_health_check` — Research Research Health Check (GET) (SSOT) | — | result |
| `research_property` — Research Research Property (POST) (SSOT) | — | result |
| `research_property_profile` — Research Get Property Profile (GET) (SSOT) | — | result |
| `research_property_summary` — Research Get Property Summary (GET) (SSOT) | — | result |
| `research_property_fraud_flags` — Research Get Property Fraud Flags (GET) (SSOT) | — | result |
| `research_download_evidence_zip` — Research Download Evidence Zip (GET) (SSOT) | — | result |
| `research_checkpoint` — Research Get Checkpoint (GET) (SSOT) | — | result |
| `research_assessor_data_query` — Research Get Assessor Data Query (GET) (SSOT) | — | result |
| `research_create_assessor_data` — Research Post Assessor Data (POST) (SSOT) | — | result |
| `research_get_assessor_data` — Research Get Assessor Data (GET) (SSOT) | — | result |
| `research_recorder_data` — Research Get Recorder Data (GET) (SSOT) | — | result |
| `research_ucc_filings` — Research Get Ucc Filings (GET) (SSOT) | — | result |
| `research_dispatch_calls` — Research Get Dispatch Calls (GET) (SSOT) | — | result |
| `research_news_mentions` — Research Get News Mentions (GET) (SSOT) | — | result |
| `research_sos_entity` — Research Get Sos Entity (GET) (SSOT) | — | result |
| `research_bankruptcy_cases` — Research Get Bankruptcy Cases (GET) (SSOT) | — | result |
| `research_insurance_info` — Research Get Insurance Info (GET) (SSOT) | — | result |
| `research_data_sources` — Research List Data Sources (GET) (SSOT) | — | result |


#### `resource_directory` — Resource Directory · tier CORE
- Layout: app/modules/resource_directory/ — 7 registered function groups (resource_list, resource_get, resource_create, resource_update, resource_delete, resource_import, resource_stale_list). Derived record: p
- **7 functions** · 11 distinct controls (6 required uses, 8 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `resource_list` — Resource List (SSOT) | *category*, *subcategory*, *state*, *county*, *service_area*, *language*, *query* | resources, total |
| `resource_get` — Resource Get (SSOT) | **resource_id** | resource |
| `resource_create` — Resource Create (SSOT) | **resource** | resource |
| `resource_update` — Resource Update (SSOT) | **resource_id**, **resource** | resource |
| `resource_delete` — Resource Delete (SSOT) | **resource_id** | deleted |
| `resource_import` — Resource Bulk Import (SSOT) | **csv_data** | imported, skipped, errors |
| `resource_stale_list` — Resource Stale List (SSOT) | *days* | stale_resources |


#### `resource_intake` — Resource Intake & Integrity Engine · tier —
- Layout: app/modules/resource_intake/ — called by build guardrails (tools/checks/resource_intake_check.py) and admin tools. Writes the compiled Information Composer resource pool to data/composer_resources.jso
- Preview state (contract): Operator/admin sees the staged candidate with fact-check status and approval state before releasing.
- Review state (contract): Operator/admin sees the updated compiled pool with the new approved resource listed and a generated timestamp.
- Declared control types: `candidate`=typed, `approved_by`=typed, `pool_path`=auto_detect
- **1 functions** · 1 distinct controls (1 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `validate_pool` — Resource Intake & Integrity Engine — validate the Composer resource pool | **pool_path** | status, count, violations |


#### `role_ui` — Role Ui · tier CORE
- Layout: app/modules/role_ui/ — 7 registered function groups (role_ui_route, role_ui_role_info, role_ui_available_roles, role_ui_features, role_ui_navigation, role_ui_tool_page, role_ui_track_pageview). Derive
- **7 functions** · 2 distinct controls (2 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `role_ui_route` — Role UI Route (SSOT) | **role** | redirect |
| `role_ui_role_info` — Role UI Role Info (SSOT) | — | role, display_name, description, permissions |
| `role_ui_available_roles` — Role UI Available Roles (SSOT) | — | roles |
| `role_ui_features` — Role UI Features (SSOT) | — | features |
| `role_ui_navigation` — Role UI Navigation Menu (SSOT) | — | menu |
| `role_ui_tool_page` — Role UI Tool Page (SSOT) | **module_name** | html |
| `role_ui_track_pageview` — Role UI Track Pageview (SSOT) | — | status |


#### `role_upgrade` — Role Upgrade · tier EXTENDED
- Layout: app/modules/role_upgrade/ — 5 registered function groups (role_upgrade_available_roles, role_upgrade_role_requirements, role_upgrade_request_role_upgrade, role_upgrade_my_role, role_upgrade_trusted_or
- **5 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `role_upgrade_available_roles` — Role_Upgrade Get Available Roles (GET) (SSOT) | — | result |
| `role_upgrade_role_requirements` — Role_Upgrade Get Role Requirements (GET) (SSOT) | — | result |
| `role_upgrade_request_role_upgrade` — Role_Upgrade Request Role Upgrade (POST) (SSOT) | — | result |
| `role_upgrade_my_role` — Role_Upgrade Get My Role (GET) (SSOT) | — | result |
| `role_upgrade_trusted_organizations` — Role_Upgrade Get Trusted Organizations (GET) (SSOT) | — | result |


#### `run_modules` — Run Modules · tier ADMIN
- Layout: app/modules/run_modules/ — 2 registered function groups (run_modules_list, run_modules_run). Derived record: page layout not yet described.
- **2 functions** · 1 distinct controls (1 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `run_modules_list` — Run Modules List (SSOT) | — | modules |
| `run_modules_run` — Run Module (SSOT) | **module_id** | run_result |


#### `security` — Security · tier CORE
- Layout: app/modules/security/ — 15 registered function groups (security_2fa_setup, security_2fa_verify, security_2fa_enable, security_2fa_disable, security_2fa_status, security_2fa_regenerate_codes, security_
- **15 functions** · 8 distinct controls (3 required uses, 6 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `security_2fa_setup` — Security 2FA Setup (SSOT) | *method* | secret, qr_code, backup_codes |
| `security_2fa_verify` — Security 2FA Verify (SSOT) | **code** | verified |
| `security_2fa_enable` — Security 2FA Enable (SSOT) | **code** | enabled |
| `security_2fa_disable` — Security 2FA Disable (SSOT) | — | disabled |
| `security_2fa_status` — Security 2FA Status (SSOT) | — | enabled, method, backup_codes_available |
| `security_2fa_regenerate_codes` — Security 2FA Regenerate Backup Codes (SSOT) | — | backup_codes |
| `security_2fa_methods` — Security 2FA Supported Methods (SSOT) | — | methods |
| `security_session_create` — Security Session Create (SSOT) | *device_info* | session_id, expires_at |
| `security_session_validate` — Security Session Validate (SSOT) | — | valid |
| `security_session_revoke` — Security Session Revoke (SSOT) | **session_id**, *reason* | revoked |
| `security_session_revoke_all` — Security Session Revoke All (SSOT) | *except_session_id* | revoked_count |
| `security_sessions_list` — Security Sessions List (SSOT) | — | sessions |
| `security_status` — Security Status (SSOT) | — | two_factor, active_sessions, recent_events |
| `security_events` — Security Events (SSOT) | *severity*, *limit* | events |
| `security_recommendations` — Security Recommendations (SSOT) | — | recommendations |


#### `setup` — Setup · tier DEV
- Layout: app/modules/setup/ — 15 registered function groups (setup_check_setup_needed, setup_skip_setup, setup_reset_setup, setup_setup_status, setup_save_profile, setup_profile, setup_save_case_info, setup_ca
- **15 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `setup_check_setup_needed` — Setup Check Setup Needed (GET) (SSOT) | — | result |
| `setup_skip_setup` — Setup Skip Setup (POST) (SSOT) | — | result |
| `setup_reset_setup` — Setup Reset Setup (POST) (SSOT) | — | result |
| `setup_setup_status` — Setup Get Setup Status (GET) (SSOT) | — | result |
| `setup_save_profile` — Setup Save Profile (POST) (SSOT) | — | result |
| `setup_profile` — Setup Get Profile (GET) (SSOT) | — | result |
| `setup_save_case_info` — Setup Save Case Info (POST) (SSOT) | — | result |
| `setup_case_info` — Setup Get Case Info (GET) (SSOT) | — | result |
| `setup_configure_storage` — Setup Configure Storage (POST) (SSOT) | — | result |
| `setup_storage_config` — Setup Get Storage Config (GET) (SSOT) | — | result |
| `setup_upload_document` — Setup Upload Document (POST) (SSOT) | — | result |
| `setup_uploaded_documents` — Setup Get Uploaded Documents (GET) (SSOT) | — | result |
| `setup_process_all_documents` — Setup Process All Documents (POST) (SSOT) | — | result |
| `setup_complete_setup` — Setup Complete Setup (POST) (SSOT) | — | result |
| `setup_setup_summary` — Setup Get Setup Summary (GET) (SSOT) | — | result |


#### `sticky_notes` — Sticky Notes · tier —
- Layout: app/modules/sticky_notes/ — 5 registered function groups (sticky_notes_create, sticky_notes_list, sticky_notes_update, sticky_notes_delete, sticky_notes_page). Derived record: page layout not yet desc
- **5 functions** · 3 distinct controls (4 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `sticky_notes_create` — Sticky Notes Create (SSOT) | **text**, *source* | note |
| `sticky_notes_list` — Sticky Notes List (SSOT) | — | notes |
| `sticky_notes_update` — Sticky Notes Update (SSOT) | **note_id**, **text** | note |
| `sticky_notes_delete` — Sticky Notes Delete (SSOT) | **note_id** | ok |
| `sticky_notes_page` — Sticky Notes Page (SSOT) | — | html |


#### `storage` — Storage · tier CORE
- Layout: app/modules/storage/ — 27 registered function groups (storage_session_status, storage_entry, storage_status, storage_session_info, storage_connect, storage_oauth_initiate, storage_oauth_callback, stor
- **27 functions** · 24 distinct controls (132 required uses, 24 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `storage_session_status` — Storage Session Status (SSOT) | *semptify_session* | authenticated, has_storage, user_id |
| `storage_entry` — Storage Entry (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | redirect |
| `storage_status` — Storage Status (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | connected, provider, token_valid |
| `storage_session_info` — Storage Session Info (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | user_id, role, provider, session_meta |
| `storage_connect` — Storage Connect (SSOT) | **role**, *semptify_uid* | redirect |
| `storage_oauth_initiate` — Storage OAuth Initiate (SSOT) | *semptify_uid* | redirect |
| `storage_oauth_callback` — Storage OAuth Callback (SSOT) | **code**, **state** | redirect, user_id |
| `storage_providers_list` — Storage Providers List (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | providers |
| `storage_providers_json` — Storage Providers JSON (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | providers |
| `storage_rehome` — Storage Rehome Device (SSOT) | — | redirect, synced |
| `storage_user_lookup` — Storage User Lookup (SSOT) | — | found, user |
| `storage_session_restore` — Storage Session Restore (SSOT) | — | success, user_id |
| `storage_prepare_reconnect` — Storage Prepare Reconnect (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | prepared |
| `storage_switch_role` — Storage Switch Role (SSOT) | **role**, *semptify_uid* | success, new_role |
| `storage_logout` — Storage Logout (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | success |
| `storage_logout_reset` — Storage Logout Reset (SSOT) | — | redirect |
| `storage_regenerate_rehome` — Storage Regenerate Rehome (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | rehome_token |
| `storage_integrity_hash` — Storage Integrity Hash (SSOT) | **content**, *semptify_uid* | hash |
| `storage_integrity_proof` — Storage Integrity Proof (SSOT) | **content**, *action*, *semptify_uid* | proof |
| `storage_integrity_verify` — Storage Integrity Verify (SSOT) | **content**, **proof_data**, *semptify_uid* | valid, verification |
| `storage_integrity_timestamp` — Storage Integrity Timestamp (SSOT) | — | timestamp, proof |
| `storage_certificate_generate` — Storage Certificate Generate (SSOT) | **document_name**, *content*, *semptify_uid* | certificate_id, certificate |
| `storage_certificate_html` — Storage Certificate HTML (SSOT) | **document_name**, *content*, *semptify_uid* | html |
| `storage_certificate_verify` — Storage Certificate Verify (SSOT) | **certificate_id**, *code* | valid, certificate |
| `storage_function_token_issue` — Storage Function Token Issue (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | token, expires_at |
| `storage_function_token_verify` — Storage Function Token Verify (SSOT) | **token**, *refresh* | valid, user_id |
| `storage_validate_token` — Storage Validate and Refresh Token (SSOT) | **s**, **e**, **m**, **p**, **t**, **i**, **f**, **y**, **_**, **u**, **i**, **d**, ** | valid, provider |


#### `system_health` — System Health · tier ADMIN
- Layout: app/modules/system_health/ — 3 registered function groups (system_health_status, system_health_registry, system_health_verify). Derived record: page layout not yet described.
- **3 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `system_health_status` — System Health Status (SSOT) | — | status |
| `system_health_registry` — System Registry Summary (SSOT) | — | registry_summary |
| `system_health_verify` — System Verify Trigger (SSOT) | — | verify_result |


#### `tactics` — Tactics · tier DEV
- Layout: app/modules/tactics/ — 7 registered function groups (tactics_recommendations, tactics_analyze_case, tactics_evidence_checklist, tactics_pre_hearing_timeline, tactics_check_retaliation, tactics_check_h
- **7 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `tactics_recommendations` — Tactics Get Recommendations (GET) (SSOT) | — | result |
| `tactics_analyze_case` — Tactics Analyze Case (POST) (SSOT) | — | result |
| `tactics_evidence_checklist` — Tactics Get Evidence Checklist (GET) (SSOT) | — | result |
| `tactics_pre_hearing_timeline` — Tactics Get Pre Hearing Timeline (GET) (SSOT) | — | result |
| `tactics_check_retaliation` — Tactics Check Retaliation (POST) (SSOT) | — | result |
| `tactics_check_habitability` — Tactics Check Habitability (POST) (SSOT) | — | result |
| `tactics_check_service_timeline` — Tactics Check Service Timeline (GET) (SSOT) | — | result |


#### `tenancy_hub` — Tenancy Hub · tier ADMIN
- Layout: app/modules/tenancy_hub/ — 26 registered function groups (tenancy_hub_case_create, tenancy_hub_cases_list, tenancy_hub_case_get, tenancy_hub_case_summary, tenancy_hub_party_add, tenancy_hub_parties_li
- **26 functions** · 21 distinct controls (35 required uses, 8 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `tenancy_hub_case_create` — Tenancy Hub Create Case (SSOT) | **case_data** | case_id, case |
| `tenancy_hub_cases_list` — Tenancy Hub List Cases (SSOT) | — | cases |
| `tenancy_hub_case_get` — Tenancy Hub Get Case (SSOT) | **case_id** | case |
| `tenancy_hub_case_summary` — Tenancy Hub Case Summary (SSOT) | **case_id** | summary |
| `tenancy_hub_party_add` — Tenancy Hub Add Party (SSOT) | **case_id**, **party** | success, party_id |
| `tenancy_hub_parties_list` — Tenancy Hub List Parties (SSOT) | **case_id**, *role* | parties |
| `tenancy_hub_property_set` — Tenancy Hub Set Property (SSOT) | **case_id**, **property** | success, property |
| `tenancy_hub_property_get` — Tenancy Hub Get Property (SSOT) | **case_id** | property |
| `tenancy_hub_lease_set` — Tenancy Hub Set Lease (SSOT) | **case_id**, **lease** | success, lease |
| `tenancy_hub_lease_get` — Tenancy Hub Get Lease (SSOT) | **case_id** | lease |
| `tenancy_hub_payment_add` — Tenancy Hub Add Payment (SSOT) | **case_id**, **payment** | success, payment_id |
| `tenancy_hub_payments_list` — Tenancy Hub List Payments (SSOT) | **case_id**, *payment_type* | payments |
| `tenancy_hub_document_add` — Tenancy Hub Add Document (SSOT) | **case_id**, **document** | success, document_id |
| `tenancy_hub_documents_list` — Tenancy Hub List Documents (SSOT) | **case_id**, *category* | documents |
| `tenancy_hub_event_add` — Tenancy Hub Add Event (SSOT) | **case_id**, **event** | success, event_id |
| `tenancy_hub_timeline_get` — Tenancy Hub Get Timeline (SSOT) | **case_id**, *start_date*, *end_date* | timeline |
| `tenancy_hub_deadlines_get` — Tenancy Hub Get Deadlines (SSOT) | **case_id**, *include_completed* | deadlines |
| `tenancy_hub_issue_add` — Tenancy Hub Add Issue (SSOT) | **case_id**, **issue** | success, issue_id |
| `tenancy_hub_issues_list` — Tenancy Hub List Issues (SSOT) | **case_id**, *status* | issues |
| `tenancy_hub_legal_case_add` — Tenancy Hub Add Legal Case (SSOT) | **case_id**, **legal_case** | success, legal_case_id |
| `tenancy_hub_legal_cases_list` — Tenancy Hub List Legal Cases (SSOT) | **case_id**, *status* | legal_cases |
| `tenancy_hub_case_search` — Tenancy Hub Search Case (SSOT) | **case_id**, **query** | results |
| `tenancy_hub_cross_reference` — Tenancy Hub Cross-Reference (SSOT) | **case_id**, **entity_type**, **entity_id** | references |
| `tenancy_hub_context_pack` — Tenancy Hub Context Pack (SSOT) | **case_id**, **context_type** | pack |
| `tenancy_hub_enums` — Tenancy Hub Enums (SSOT) | — | enums |
| `tenancy_hub_context_types` — Tenancy Hub Context Types (SSOT) | — | context_types |


#### `testing` — Testing · tier DEV
- Layout: app/modules/testing/ — 11 registered function groups (testing_create_test_suite_endpoint, testing_get_test_suite_endpoint, testing_test_suites, testing_run_test_suite_endpoint, testing_test_run_endpoi
- **11 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `testing_create_test_suite_endpoint` — Testing Create Test Suite Endpoint (POST) (SSOT) | — | result |
| `testing_get_test_suite_endpoint` — Testing Get Test Suite Endpoint (GET) (SSOT) | — | result |
| `testing_test_suites` — Testing List Test Suites (GET) (SSOT) | — | result |
| `testing_run_test_suite_endpoint` — Testing Run Test Suite Endpoint (POST) (SSOT) | — | result |
| `testing_test_run_endpoint` — Testing Get Test Run Endpoint (GET) (SSOT) | — | result |
| `testing_test_results_endpoint` — Testing Get Test Results Endpoint (GET) (SSOT) | — | result |
| `testing_test_statistics_endpoint` — Testing Get Test Statistics Endpoint (GET) (SSOT) | — | result |
| `testing_pipeline_endpoint` — Testing Create Pipeline Endpoint (POST) (SSOT) | — | result |
| `testing_run_pipeline_endpoint` — Testing Run Pipeline Endpoint (POST) (SSOT) | — | result |
| `testing_pipeline_run_endpoint` — Testing Get Pipeline Run Endpoint (GET) (SSOT) | — | result |
| `testing_pipeline_statistics_endpoint` — Testing Get Pipeline Statistics Endpoint (GET) (SSOT) | — | result |


#### `ui_composer` — Ui Composer · tier CORE
- Layout: app/modules/ui_composer/ — 3 registered function groups (page_compose, fragment_render, process_status). Derived record: page layout not yet described.
- **3 functions** · 5 distinct controls (4 required uses, 1 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `page_compose` — UI Composer — Page Compose (SSOT) | **page_intent**, *context* | page_title, pillar, components |
| `fragment_render` — UI Composer — Fragment Render (SSOT) | **component_type**, **data** | type, data |
| `process_status` — UI Composer — Process Status (SSOT) | **workflow_id** | step_label, state, progress_pct |


#### `unified_overlays` — Unified Overlays · tier RESEARCH
- Layout: app/modules/unified_overlays/ — 9 registered function groups (unified_overlays_health_check, unified_overlays_create_overlay, unified_overlays_overlays, unified_overlays_get_overlay, unified_overlays_
- **9 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `unified_overlays_health_check` — Unified_Overlays Health Check (GET) (SSOT) | — | result |
| `unified_overlays_create_overlay` — Unified_Overlays Create Overlay (POST) (SSOT) | — | result |
| `unified_overlays_overlays` — Unified_Overlays List Overlays (GET) (SSOT) | — | result |
| `unified_overlays_get_overlay` — Unified_Overlays Get Overlay (GET) (SSOT) | — | result |
| `unified_overlays_patch_overlay` — Unified_Overlays Update Overlay (PATCH) (SSOT) | — | result |
| `unified_overlays_delete_overlay` — Unified_Overlays Delete Overlay (DELETE) (SSOT) | — | result |
| `unified_overlays_compose_document_view` — Unified_Overlays Compose Document View (POST) (SSOT) | — | result |
| `unified_overlays_add_highlight` — Unified_Overlays Add Highlight (POST) (SSOT) | — | result |
| `unified_overlays_add_note` — Unified_Overlays Add Note (POST) (SSOT) | — | result |


#### `user` — User · tier CORE
- Layout: app/modules/user/ — 2 registered function groups (user_act_as_start, user_act_as_stop). Derived record: page layout not yet described.
- **2 functions** · 3 distinct controls (4 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `user_act_as_start` — User Act-As Start (SSOT) | **admin_user_id**, **target_user_id**, **reason** | success, act_as_user_id |
| `user_act_as_stop` — User Act-As Stop (SSOT) | **admin_user_id** | success |


#### `user_concerns` — User Concerns · tier ADMIN
- Layout: app/modules/user_concerns/ — 5 registered function groups (user_concerns_health, user_concerns_list, user_concerns_summary, user_concerns_flag, user_concerns_resolve). Derived record: page layout not 
- **5 functions** · 2 distinct controls (2 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `user_concerns_health` — User Concerns Health (SSOT) | — | status |
| `user_concerns_list` — User Concerns List (SSOT) | — | concerns |
| `user_concerns_summary` — User Concerns Summary (SSOT) | — | summary |
| `user_concerns_flag` — User Concern Flag (SSOT) | **concern** | flag_result |
| `user_concerns_resolve` — User Concern Resolve (SSOT) | **concern_id** | resolve_result |


#### `vault_engine` — Vault Engine · tier CORE
- Layout: app/modules/vault_engine/ — 11 registered function groups (vault_engine_check_access, vault_engine_read_resource, vault_engine_write_resource, vault_engine_resource, vault_engine_share_resource, vault
- **11 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `vault_engine_check_access` — Vault_Engine Check Access (POST) (SSOT) | — | result |
| `vault_engine_read_resource` — Vault_Engine Read Resource (POST) (SSOT) | — | result |
| `vault_engine_write_resource` — Vault_Engine Write Resource (POST) (SSOT) | — | result |
| `vault_engine_resource` — Vault_Engine Delete Resource (POST) (SSOT) | — | result |
| `vault_engine_share_resource` — Vault_Engine Share Resource (POST) (SSOT) | — | result |
| `vault_engine_unshare_resource` — Vault_Engine Unshare Resource (POST) (SSOT) | — | result |
| `vault_engine_resources` — Vault_Engine List Resources (GET) (SSOT) | — | result |
| `vault_engine_audit_log` — Vault_Engine Get Audit Log (GET) (SSOT) | — | result |
| `vault_engine_stats` — Vault_Engine Get Stats (GET) (SSOT) | — | result |
| `vault_engine_resource_types` — Vault_Engine List Resource Types (GET) (SSOT) | — | result |
| `vault_engine_access_levels` — Vault_Engine List Access Levels (GET) (SSOT) | — | result |


#### `voice` — Voice · tier CORE
- Layout: app/modules/voice/ — 1 registered function groups (voice_transcribe). Derived record: page layout not yet described.
- **1 functions** · 1 distinct controls (1 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `voice_transcribe` — Voice Transcribe (SSOT) | **audio** | transcript |


#### `websocket` — Websocket · tier CORE
- Layout: app/modules/websocket/ — 4 registered function groups (websocket_websocket_status, websocket_user_connections, websocket_send_notification_to_user, websocket_broadcast_notification). Derived record: p
- **4 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `websocket_websocket_status` — Websocket Get Websocket Status (GET) (SSOT) | — | result |
| `websocket_user_connections` — Websocket Get User Connections (GET) (SSOT) | — | result |
| `websocket_send_notification_to_user` — Websocket Send Notification To User (POST) (SSOT) | — | result |
| `websocket_broadcast_notification` — Websocket Broadcast Notification (POST) (SSOT) | — | result |


#### `workflow` — Workflow · tier CORE
- Layout: app/modules/workflow/ — 10 registered function groups (workflow_route_decision, workflow_advance_workflow, workflow_next_step, workflow_case_state, workflow_process_groups, workflow_contracts, workflo
- **10 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `workflow_route_decision` — Workflow Get Route Decision (POST) (SSOT) | — | result |
| `workflow_advance_workflow` — Workflow Advance Workflow (POST) (SSOT) | — | result |
| `workflow_next_step` — Workflow Get Next Step (POST) (SSOT) | — | result |
| `workflow_case_state` — Workflow Get Case State (GET) (SSOT) | — | result |
| `workflow_process_groups` — Workflow List Process Groups (GET) (SSOT) | — | result |
| `workflow_contracts` — Workflow List Contracts (GET) (SSOT) | — | result |
| `workflow_page_contract` — Workflow Get Page Contract (GET) (SSOT) | — | result |
| `workflow_contract_health` — Workflow Contract Health (GET) (SSOT) | — | result |
| `workflow_module_contracts` — Workflow List Module Contracts (GET) (SSOT) | — | result |
| `workflow_help_telemetry_summary` — Workflow Help Telemetry Summary (GET) (SSOT) | — | result |


#### `workflow_validator` — Workflow Validator · tier CORE
- Layout: app/modules/workflow_validator/ — 2 registered function groups (workflow_validator_validator_dashboard, workflow_validator_test_routing). Derived record: page layout not yet described.
- **2 functions** · 0 distinct controls (0 required uses, 0 optional uses)

| Function | Controls (bold=required, italic=option) | B-side output |
|---|---|---|
| `workflow_validator_validator_dashboard` — Workflow_Validator Validator Dashboard (GET) (SSOT) | — | result |
| `workflow_validator_test_routing` — Workflow_Validator Test Routing (GET) (SSOT) | — | result |


---

## 5. What the display-window install needs (gaps found while mapping)

1. **`output_type` is `other` on 126/129 module contracts** — only `document_center`
   (`ui_state_change`) and two others (`record`, `file`) declare a real display type.
   For the B-side window to auto-pick an archetype, contracts need an output/display
   field (or the archetype table in §3 stays the mapping source).
2. **`input_audit` control types are declared on ~10 inputs total** (document_center
   plus isolated others). The per-function `inputs` lists exist everywhere; their
   *control kind* (typed/dropdown/auto_detect/button/date/file) is not yet declared —
   needed if the A-side rail is to render controls from contracts.
3. **`stages` (fnav rail) declared on 5 modules only**: eviction_defense, intake,
   journal, law_library, timeline. All other multi-step flows currently render
   single-stage. Adding `stages` is per-contract work, backward compatible.
4. **Viewer precedent exists**: `SemptifyMediaPlayer` mounts into any host,
   borderless/liquid/resizable — the B-side window can reuse it for all
   file-rendering archetypes (VIEWER/OUTPUT).
5. **Generic tool renderer exists**: `/ui/tool/{module}` (`module_page.html`) already
   renders a module from a contract dict — the natural host for contract-driven
   B-side content before the display window ships.