# Action Object Space + Narrative Blurbs — Tenant-Facing Function Groups

**Scope:** All `FunctionGroupContract` registrations in `app.core.contract_loader` that belong to the RECORD, KNOW, or ACT pillars (tenant-facing). GOVERN/infra modules (admin, dev, auth, storage, analytics, etc.) are listed in the appendix as out of scope for Page Composer.

**How to read an entry:** `input_name (type, required/optional)`; overall input/output `space` is `small` (1–2 compact fields), `medium` (3–5 fields or one large item), or `large` (6+ fields, file upload, long text, list/table). `session (hidden)` means the UI does not show the field — it is taken from the signed storage connection.

**Blurb rules applied:** no `evidence`/`proof` before a court date, no adversarial language, no `log in`/`account`/`tracking`, no urgency tactics, no `free` for Semptify, plain wording.

## RECORD Pillar

### Module: briefcase

#### Briefcase Add Tag (POST) (`briefcase::briefcase_add_tag`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Briefcase Add Tag (POST).

#### Briefcase Get All Tags (GET) (`briefcase::briefcase_all_tags`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get all available tags.

#### Briefcase List Annotations (GET) (`briefcase::briefcase_annotations`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** List annotations with optional filters.

#### Briefcase Get Annotations By Document (GET) (`briefcase::briefcase_annotations_by_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get all annotations for a document, grouped by extraction code.

#### Briefcase Get Briefcase (GET) (`briefcase::briefcase_briefcase`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get entire briefcase structure.

#### Briefcase Get Briefcase Stats (GET) (`briefcase::briefcase_briefcase_stats`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get detailed briefcase statistics.

#### Briefcase Copy Document (POST) (`briefcase::briefcase_copy_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** POST /document/{doc_id}/copy.

#### Briefcase Create Annotation (POST) (`briefcase::briefcase_create_annotation`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Create a new document annotation with auto-numbered footnotes.

#### Briefcase Create Folder (POST) (`briefcase::briefcase_create_folder`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Create a new folder.

#### Briefcase Create Timeline Event (POST) (`briefcase::briefcase_create_timeline_event`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Create a timeline event that can be linked to annotations.

#### Briefcase Delete Annotation (DELETE) (`briefcase::briefcase_delete_annotation`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Delete an annotation.

#### Briefcase Delete Document (DELETE) (`briefcase::briefcase_delete_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Briefcase Delete Document (DELETE).

#### Briefcase Delete Extraction (DELETE) (`briefcase::briefcase_delete_extraction`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Delete an extraction.

#### Briefcase Delete Folder (DELETE) (`briefcase::briefcase_delete_folder`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Briefcase Delete Folder (DELETE).

#### Briefcase Delete Highlight (DELETE) (`briefcase::briefcase_delete_highlight`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Briefcase Delete Highlight (DELETE).

#### Briefcase Delete Timeline Event (DELETE) (`briefcase::briefcase_delete_timeline_event`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Delete a timeline event and unlink associated annotations.

#### Briefcase Download Document (GET) (`briefcase::briefcase_download_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Download a document.

#### Briefcase Download Extraction (GET) (`briefcase::briefcase_download_extraction`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Download extracted PDF file.

#### Briefcase Get Event Chain (GET) (`briefcase::briefcase_event_chain`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get an event chain (linked events: start→continued→finish).

#### Briefcase Create Event From Annotation (POST) (`briefcase::briefcase_event_from_annotation`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Create a timeline event from an annotation's highlight.

#### Briefcase Get Event Statuses (GET) (`briefcase::briefcase_event_statuses`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get the complete list of event statuses with descriptions.

#### Briefcase Export Folder (POST) (`briefcase::briefcase_export_folder`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Briefcase Export Folder (POST).

#### Briefcase Get Extraction Codes (GET) (`briefcase::briefcase_extraction_codes`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get the complete list of extraction codes with colors and icons.

#### Briefcase List Extractions (GET) (`briefcase::briefcase_extractions`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** List all saved extractions.

#### Briefcase Get Folder Contents (GET) (`briefcase::briefcase_folder_contents`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get contents of a specific folder.

#### Briefcase Get Annotation (GET) (`briefcase::briefcase_get_annotation`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get a specific annotation.

#### Briefcase Get Document (GET) (`briefcase::briefcase_get_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get document metadata.

#### Briefcase Get Extraction (GET) (`briefcase::briefcase_get_extraction`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get a specific extraction.

#### Briefcase Get Highlight (GET) (`briefcase::briefcase_get_highlight`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get a specific highlight.

#### Briefcase Get Timeline Event (GET) (`briefcase::briefcase_get_timeline_event`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get a timeline event with its linked annotations.

#### Briefcase List Highlights (GET) (`briefcase::briefcase_highlights`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** List all saved highlights, optionally filtered.

#### Briefcase Get Highlights Grouped By Color (GET) (`briefcase::briefcase_highlights_grouped_by_color`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get highlights grouped by color category.

#### Briefcase Link Annotation To Event (POST) (`briefcase::briefcase_link_annotation_to_event`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** POST /annotation/{annotation_id}/link-event.

#### Briefcase Move Document (POST) (`briefcase::briefcase_move_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** POST /document/{doc_id}/move.

#### Briefcase Preview Document (GET) (`briefcase::briefcase_preview_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get document content for preview (base64).

#### Briefcase Get Recent Documents (GET) (`briefcase::briefcase_recent_documents`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get recently added/updated documents.

#### Briefcase Reset Annotation Counters (POST) (`briefcase::briefcase_reset_annotation_counters`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** POST /annotations/reset-counters.

#### Briefcase Save Converted Document (POST) (`briefcase::briefcase_save_converted_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Save a converted document to the briefcase.

#### Briefcase Save Extraction (POST) (`briefcase::briefcase_save_extraction`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Briefcase Save Extraction (POST).

#### Briefcase Save Highlight (POST) (`briefcase::briefcase_save_highlight`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Briefcase Save Highlight (POST).

#### Briefcase Save Highlights Batch (POST) (`briefcase::briefcase_save_highlights_batch`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Save multiple highlights at once.

#### Briefcase Search Documents (GET) (`briefcase::briefcase_search_documents`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Briefcase Search Documents (GET).

#### Briefcase Get Starred Documents (GET) (`briefcase::briefcase_starred_documents`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Get all starred documents.

#### Briefcase List Timeline Events (GET) (`briefcase::briefcase_timeline_events`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** List timeline events with optional filters.

#### Briefcase Update Annotation (PUT) (`briefcase::briefcase_update_annotation`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Update an annotation's note or linked event.

#### Briefcase Update Document (PUT) (`briefcase::briefcase_update_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Update document properties.

#### Briefcase Update Folder (PUT) (`briefcase::briefcase_update_folder`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Update folder properties.

#### Briefcase Update Timeline Event (PUT) (`briefcase::briefcase_update_timeline_event`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Update a timeline event.

#### Briefcase Upload Document (POST) (`briefcase::briefcase_upload_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Briefcase Upload Document (POST).

### Module: calendar

#### Calendar Create Event (`calendar::calendar_create_event`)

- **Inputs** (medium): user_id (session (hidden), optional), title (short text), date (date), description (long text, optional), event_type (dropdown / select, optional)
- **Outputs** (small): event_id (reference / lookup), event (short text)
- **Blurb:** Create a calendar event. You adds a court date, deadline, meeting, or other event with title, date, and description.

#### Calendar Deadline Summary (`calendar::calendar_deadline_summary`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): overdue (short text), this_week (short text), this_month (short text)
- **Blurb:** Summary of upcoming deadlines. Shows counts by urgency (overdue, this week, this month).

#### Calendar Delete Event (`calendar::calendar_delete_event`)

- **Inputs** (small): event_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): status (dropdown / select)
- **Blurb:** Delete a calendar event. Removes the event from the calendar.

#### Calendar Events From Documents (`calendar::calendar_from_documents`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (large): events (list / table), documents_analyzed (list / table)
- **Blurb:** List of events extracted from your documents. Shows dates found in documents that can be synced to the calendar.

#### Calendar Get Event (`calendar::calendar_get_event`)

- **Inputs** (small): event_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): event (short text)
- **Blurb:** Get a single calendar event by ID. Shows full event details.

#### Calendar List Events (`calendar::calendar_list_events`)

- **Inputs** (medium): user_id (session (hidden), optional), start (short text, optional), end (short text, optional)
- **Outputs** (medium): events (list / table), total (number)
- **Blurb:** List of calendar events in a date range. Shows events sorted by date.

#### Calendar Notify Deadlines (`calendar::calendar_notify_deadlines`)

- **Inputs** (small): user_id (session (hidden), optional), days_ahead (short text, optional)
- **Outputs** (small): notified (short text)
- **Blurb:** Send deadline notifications. Triggers notifications for deadlines within the specified window (default 7 days).

#### Calendar Sync Document Events (`calendar::calendar_sync_documents`)

- **Inputs** (small): user_id (session (hidden), optional), overwrite (short text, optional)
- **Outputs** (small): synced_event_ids (short text)
- **Blurb:** Sync events from documents to the calendar. Creates calendar events from dates extracted from documents. Optionally overwrites existing events with the same title.

#### Calendar Upcoming Deadlines (`calendar::calendar_upcoming_deadlines`)

- **Inputs** (small): user_id (session (hidden), optional), days (short text, optional)
- **Outputs** (medium): deadlines (list / table)
- **Blurb:** Upcoming deadlines within a look-ahead window (default 30 days, max 90). Shows deadlines sorted by date.

#### Calendar Update Event (`calendar::calendar_update_event`)

- **Inputs** (medium): event_id (reference / lookup), user_id (session (hidden), optional), updates (short text)
- **Outputs** (small): event (short text)
- **Blurb:** Update a calendar event. You can edit title, date, description, or event type.

### Module: communication

#### Communication Create Conversation (`communication::communication_create_conversation`)

- **Inputs** (medium): user_id (session (hidden), optional), recipient (short text), initial_message (long text), access_token (short text)
- **Outputs** (small): conversation_id (reference / lookup), conversation (short text)
- **Blurb:** Create a new conversation. The user specifies the recipient and initial message. Shows the new conversation.

#### Communication Delivery Conversation (`communication::communication_delivery_conversation`)

- **Inputs** (small): delivery_id (reference / lookup), access_token (short text)
- **Outputs** (small): conversation (short text)
- **Blurb:** Get the conversation associated with a document delivery. Shows the conversation thread for the delivery.

#### Communication Fill and Sign Document (`communication::communication_fill_and_sign`)

- **Inputs** (medium): delivery_id (reference / lookup), signature_type (dropdown / select), access_token (short text)
- **Outputs** (small): signed_document (short text)
- **Blurb:** Fill and sign a document delivered through the communication channel. Supports typed, drawn, and digital signatures.

#### Communication Get Conversation (`communication::communication_get_conversation`)

- **Inputs** (medium): conversation_id (reference / lookup), before_message_id (reference / lookup, optional), access_token (short text)
- **Outputs** (medium): messages (long text), has_more (checkbox / toggle)
- **Blurb:** Get a single conversation with message thread. Supports pagination via before_message_id. Shows messages in chronological order.

#### Communication List Conversations (`communication::communication_list_conversations`)

- **Inputs** (small): user_id (session (hidden), optional), access_token (short text)
- **Outputs** (medium): conversations (list / table)
- **Blurb:** List of conversations for the current user. Shows conversation summaries with last message, unread count, and participant info.

#### Communication Mark Conversation Read (`communication::communication_mark_conversation_read`)

- **Inputs** (small): conversation_id (reference / lookup), access_token (short text)
- **Outputs** (small): success (short text)
- **Blurb:** Mark all messages in a conversation as read. Updates the unread count to zero.

#### Communication Mark Message Read (`communication::communication_mark_message_read`)

- **Inputs** (medium): conversation_id (reference / lookup), message_id (reference / lookup), access_token (short text)
- **Outputs** (small): success (short text)
- **Blurb:** Mark a single message as read. Updates the read receipt for the message.

#### Communication Reject Document (`communication::communication_reject_document`)

- **Inputs** (medium): delivery_id (reference / lookup), reason (short text), access_token (short text)
- **Outputs** (small): status (dropdown / select)
- **Blurb:** Reject a document delivered through the communication channel. The recipient provides a reason for rejection.

#### Communication Send Message (`communication::communication_send_message`)

- **Inputs** (medium): conversation_id (reference / lookup), content (long text), access_token (short text)
- **Outputs** (small): message_id (reference / lookup), sent_at (date)
- **Blurb:** Send a message in a conversation. Shows the new message with ID and timestamp.

#### Communication Typing Indicator (`communication::communication_typing_indicator`)

- **Inputs** (small): conversation_id (reference / lookup), is_typing (checkbox / toggle)
- **Outputs** (small): success (short text)
- **Blurb:** Send a typing indicator for a conversation. Notifies the other participant that the user is typing.

#### Communication Upload Attachment (`communication::communication_upload_attachment`)

- **Inputs** (medium): conversation_id (reference / lookup), file (file), access_token (short text)
- **Outputs** (medium): attachment_id (reference / lookup), filename (file)
- **Blurb:** Upload a file attachment to a conversation. The file is stored in the sender's vault and linked to the conversation.

#### Conversation Creation (`communication::conversation_create`)

- **Inputs** (medium): request (short text), creator_role (dropdown / select), user_id (session (hidden), optional), storage (short text)
- **Outputs** (small): conversation_id (reference / lookup), success (short text)
- **Blurb:** Conversation creation via CommunicationService.create_conversation(). Stores conversation as COMMUNICATION overlay in user's cloud storage. No other service may create conversation overlays directly.

#### Conversations List (`communication::conversations_list`)

- **Inputs** (small): user_id (session (hidden), optional), storage (short text)
- **Outputs** (medium): conversations (list / table), total_count (number), unread_total (number)
- **Blurb:** Conversation list via CommunicationService.get_conversations(). Shows ConversationListResponse with summaries and unread counts.

#### Document Fill and Sign (`communication::document_fill_sign`)

- **Inputs** (medium): delivery_id (reference / lookup), field_values (short text), signature_data (short text), user_id (session (hidden), optional), storage (short text)
- **Outputs** (small): signed_document_id (reference / lookup), success (short text)
- **Blurb:** Document fill+sign via CommunicationService.fill_and_sign_document(). Fills form fields, applies signature, stores result as overlay.

#### Message Send (`communication::message_send`)

- **Inputs** (medium): request (short text), sender_role (dropdown / select), conversation_id (reference / lookup), user_id (session (hidden), optional), storage (short text)
- **Outputs** (small): message_id (reference / lookup), success (short text)
- **Blurb:** Message send via CommunicationService.send_message(). Stores message as COMMUNICATION overlay. Appends to existing conversation thread.

### Module: contacts

#### Contacts Create (`contacts::contacts_create`)

- **Inputs** (large): user_id (session (hidden), optional), name (short text), contact_type (dropdown / select), phone (phone, optional), email (email, optional), address (address, optional)
- **Outputs** (small): contact_id (reference / lookup), contact (short text)
- **Blurb:** Create a new contact. You adds a landlord, witness, neighbor, or other party with contact info.

#### Contacts Delete (`contacts::contacts_delete`)

- **Inputs** (small): contact_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): status (dropdown / select)
- **Blurb:** Delete a contact. Removes the contact and all associated interactions.

#### Contacts For Forms (`contacts::contacts_for_forms`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): contacts (short text)
- **Blurb:** List of contacts formatted for form autofill. Shows contacts in a simplified structure for populating form fields.

#### Contacts Get (`contacts::contacts_get`)

- **Inputs** (small): contact_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): contact (short text)
- **Blurb:** Get a single contact by ID. Shows full contact info including interactions log.

#### Contacts Import From Extraction (`contacts::contacts_import_from_extraction`)

- **Inputs** (small): user_id (session (hidden), optional), extracted_contacts (short text)
- **Outputs** (small): imported (short text), total (number)
- **Blurb:** Import contacts from document extraction results. Takes parties extracted from a document and creates contacts from them. Avoids manual entry.

#### Contacts List (`contacts::contacts_list`)

- **Inputs** (medium): user_id (session (hidden), optional), contact_type (dropdown / select, optional), role (dropdown / select, optional)
- **Outputs** (small): contacts (short text), total (number)
- **Blurb:** List of contacts for the current user. Supports filtering by contact_type and role. Shows contact summaries.

#### Contacts List Interactions (`contacts::contacts_list_interactions`)

- **Inputs** (small): contact_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): interactions (short text)
- **Blurb:** List of interactions with a contact. Shows logged calls, emails, meetings, and other interactions.

#### Contacts Log Interaction (`contacts::contacts_log_interaction`)

- **Inputs** (medium): contact_id (reference / lookup), user_id (session (hidden), optional), interaction_type (dropdown / select), description (long text, optional), date (date, optional)
- **Outputs** (small): interaction_id (reference / lookup)
- **Blurb:** Log an interaction with a contact. You records a call, email, meeting, or other interaction with the contact.

#### Contacts Quick Add Landlord (`contacts::contacts_quick_add_landlord`)

- **Inputs** (medium): user_id (session (hidden), optional), name (short text), phone (phone, optional), email (email, optional)
- **Outputs** (small): contact_id (reference / lookup)
- **Blurb:** Quick-add a landlord contact. Simplified form with just name, phone, and email.

#### Contacts Quick Add Witness (`contacts::contacts_quick_add_witness`)

- **Inputs** (medium): user_id (session (hidden), optional), name (short text), relationship (short text)
- **Outputs** (small): contact_id (reference / lookup)
- **Blurb:** Quick-add a witness contact. Simplified form with name and relationship.

#### Contacts Toggle Star (`contacts::contacts_toggle_star`)

- **Inputs** (small): contact_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): starred (checkbox / toggle)
- **Blurb:** Star or unstar a contact. Starred contacts appear at the top of the contacts list.

#### Contacts Types Reference (`contacts::contacts_types`)

- **Inputs** (small): none
- **Outputs** (small): types (dropdown / select), roles (dropdown / select)
- **Blurb:** List of available contact types and roles.

#### Contacts Update (`contacts::contacts_update`)

- **Inputs** (medium): contact_id (reference / lookup), user_id (session (hidden), optional), updates (short text)
- **Outputs** (small): contact (short text)
- **Blurb:** Update a contact. You can edit name, phone, email, address, or notes.

### Module: document_center

#### Document Center List (`document_center::dc_list`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): documents (list / table), total (number), generated_at (date)
- **Blurb:** Document list for the DC left panel. Shows all vault documents for the authenticated user, each with: id, filename, uploaded_at, document_type, overlay_count (null — real count requires per-doc cloud fetch), verification_status ('new'|'review'|'verified'). Call dc_overlays for the authoritative count per document.

#### Document Center Overlays (`document_center::dc_overlays`)

- **Inputs** (small): vault_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (large): has_data (checkbox / toggle), overall_pct (short text), overlays (short text), overlay_count (number), overlay_source (dropdown / select), status (dropdown / select)
- **Blurb:** Overlay progress data for the DC right panel. Reads REAL overlays from UnifiedOverlayManager.get_overlays() in the user's cloud storage, keyed by document_id = doc.safe_filename. Maps real overlay payloads to 6 progress items: Certified Upload, Document Type, Text Extraction, Dates, Parties, Amounts.

#### Document Center Set Document Type (`document_center::dc_set_type`)

- **Inputs** (medium): doc_id (reference / lookup), document_type (dropdown / select), user_id (session (hidden), optional)
- **Outputs** (medium): ok (short text), doc_id (reference / lookup), document_type (dropdown / select), note (short text)
- **Blurb:** Document type setter for the DC viewer dropdown. Called when you identifies or corrects a document's type. Validates against the allowed set: lease, notice_to_vacate, repair_request, rent_receipt, move_in_inspection, court_summons, correspondence, other.

#### Document Center Unlocks (`document_center::dc_unlocks`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): unlocks (short text), doc_count (number), generated_at (date)
- **Blurb:** Unlock state computation for DC feature modules. Iterates all VaultDocuments for a user, synthesizes overlay scores in memory (no cloud I/O), and checks four thresholds: Timeline (1 doc Dates+Parties>=80%), Journal (2+ docs overall>=60%), Contact Manager (Parties==100%), Case Builder (3+ docs overall>=80%). Shows unlocks list with name/icon/threshold/unlocked/progress per item.

#### Document Center View (`document_center::dc_view`)

- **Inputs** (small): vault_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (large): file_bytes (file), mime_type (dropdown / select), filename (file)
- **Blurb:** Inline document stream for the DC viewer iframe. Authenticates via session cookie (same-origin iframe). Fetches file bytes from vault storage and shows them with Content-Disposition: inline so the browser renders PDF/image natively.

### Module: document_converter

#### Document Converter Cleanup (`document_converter::document_converter_cleanup`)

- **Inputs** (small): days_old (short text, optional)
- **Outputs** (small): cleaned (short text)
- **Blurb:** Clean up converted documents older than specified days. Admin-only.

#### Document Converter Download (`document_converter::document_converter_download`)

- **Inputs** (medium): filename (file)
- **Outputs** (medium): file (file)
- **Blurb:** Download a converted document by filename. Shows the file for download.

#### Document Converter File (`document_converter::document_converter_file`)

- **Inputs** (medium): file (file), output_format (dropdown / select, optional)
- **Outputs** (medium): converted (short text), filename (file)
- **Blurb:** Convert an uploaded markdown file to DOCX/HTML. Shows the converted file(s).

#### Document Converter From Path (`document_converter::document_converter_from_path`)

- **Inputs** (medium): file_path (file), output_format (dropdown / select, optional)
- **Outputs** (medium): converted (short text), filename (file)
- **Blurb:** Convert a markdown file from a server path. Shows the converted file(s).

#### Document Converter List (`document_converter::document_converter_list`)

- **Inputs** (small): none
- **Outputs** (medium): documents (list / table)
- **Blurb:** List all converted documents. Shows filenames and metadata.

#### Document Converter To Both (`document_converter::document_converter_to_both`)

- **Inputs** (medium): markdown (short text), filename (file, optional)
- **Outputs** (medium): docx (short text), html (short text), filename (file)
- **Blurb:** Convert markdown text to both DOCX and HTML. Shows both converted files.

#### Document Converter To DOCX (`document_converter::document_converter_to_docx`)

- **Inputs** (medium): markdown (short text), filename (file, optional)
- **Outputs** (medium): docx (short text), filename (file)
- **Blurb:** Convert markdown text to Microsoft Word (.docx) format. Shows the converted file.

#### Document Converter To HTML (`document_converter::document_converter_to_html`)

- **Inputs** (medium): markdown (short text), filename (file, optional)
- **Outputs** (medium): html (short text), filename (file)
- **Blurb:** Convert markdown text to interactive HTML. Shows the converted HTML.

### Module: documents

#### Documents Auto-Timeline (`documents::documents_auto_timeline`)

- **Inputs** (small): doc_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): created_events (list / table), total_created (number)
- **Blurb:** Auto-populate timeline from a document's extracted dates. Takes dates found in the document and creates timeline events for each. Saves you from manually entering dates.

#### Documents Export (`documents::documents_export`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (large): file_stream (file), filename (file)
- **Blurb:** Export of all documents as a downloadable archive. GDPR-compliant data export. Includes all files, metadata, and certificates in a zip.

#### Documents Get Detail (`documents::documents_get`)

- **Inputs** (small): doc_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): document (short text), intelligence (short text), issues (short text)
- **Blurb:** Detailed view of a single document. Shows full metadata, extraction results, intelligence analysis, and processing status.

#### Documents Intelligence Analysis (`documents::documents_intelligence`)

- **Inputs** (small): doc_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (large): dates (short text), amounts (number), parties (short text), issues (short text), deadlines (list / table), suggested_actions (short text)
- **Blurb:** Intelligence analysis for a document. Shows extracted dates, amounts, parties, issues, deadlines, and possible next steps.

#### Documents List (`documents::documents_list`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): documents (list / table)
- **Blurb:** List of all processed documents for a user. Shows full document records with classification, extraction status, and metadata.

#### Documents Process (`documents::documents_process`)

- **Inputs** (medium): file (file), user_id (session (hidden), optional)
- **Outputs** (large): document_id (reference / lookup), document_type (dropdown / select), extracted_text (long text), dates (short text), amounts (number), parties (short text), issues (short text)
- **Blurb:** Unified document processing. Takes a file from the vault, classifies it, extracts text/dates/amounts/parties, detects issues, and shows a unified response with all extracted intelligence. This is the main pipeline that turns a raw file into structured documentation of events.

#### Documents Reprocess (`documents::documents_reprocess`)

- **Inputs** (small): doc_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): document_id (reference / lookup), status (dropdown / select), document_type (dropdown / select)
- **Blurb:** Reprocessing of an existing document. Re-runs classification and extraction on an already-stored file. Used when extraction models improve or a document was partially processed.

#### Documents Summary (`documents::documents_summary`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): total_documents (list / table), by_type (dropdown / select), urgent_count (number), recent_activity (short text)
- **Blurb:** Summary of a user's document portfolio. Shows counts by type, total size, important count, and recent activity.

#### Documents Extracted Text (`documents::documents_text`)

- **Inputs** (small): doc_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): text (long text), language (dropdown / select)
- **Blurb:** Retrieval of the full extracted text for a document. Shows the text content extracted during processing. Used for document viewing and search.

#### Documents Thumbnail (`documents::documents_thumbnail`)

- **Inputs** (small): doc_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): thumbnail (short text), content_type (long text)
- **Blurb:** Thumbnail image for a document. Used in document grids, sidebar lists, and timeline entries for visual identification.

#### Documents Timeline (`documents::documents_timeline`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): events (list / table)
- **Blurb:** Timeline of document events for a user. Shows events sorted by date — uploads, processing, classification corrections, and detected issues.

#### Documents Train Correct (`documents::documents_train_correct`)

- **Inputs** (medium): doc_id (reference / lookup), user_id (session (hidden), optional), corrected_type (dropdown / select)
- **Outputs** (small): status (dropdown / select)
- **Blurb:** Submit a classification correction for training. You confirms or corrects the auto-classification, which improves future classification for all users.

#### Documents Training Stats (`documents::documents_train_stats`)

- **Inputs** (small): none
- **Outputs** (medium): total_documents (list / table), confirmed (checkbox / toggle), corrected (short text), accuracy (short text), patterns (short text)
- **Blurb:** Training statistics. Shows counts of confirmed vs corrected classifications, learned patterns, and model accuracy metrics. Admin-only view for model improvement following.

#### Documents Update Category (`documents::documents_update_category`)

- **Inputs** (medium): doc_id (reference / lookup), user_id (session (hidden), optional), category (dropdown / select)
- **Outputs** (small): doc_id (reference / lookup), category (dropdown / select)
- **Blurb:** Update of a document's category. You can correct the auto-classification. The correction feeds back into training stats.

#### Documents Simple Upload (`documents::documents_upload_simple`)

- **Inputs** (medium): file (file), user_id (session (hidden), optional)
- **Outputs** (medium): document_id (reference / lookup), filename (file), document_type (dropdown / select), status (dropdown / select)
- **Blurb:** Simple upload endpoint. Accepts a single file, stores it, processes it, and shows the document record. Lighter than the full unified process — used for quick captures.

#### Documents Urgent List (`documents::documents_urgent`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): documents (list / table)
- **Blurb:** List of important documents requiring attention. Based on issue severity, upcoming deadlines, and document type.

#### Documents View (`documents::documents_view`)

- **Inputs** (small): doc_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (large): content (long text), content_type (long text)
- **Blurb:** In-browser view of a document. Shows a viewable representation (HTML/PDF/image) for you document viewer.

### Module: fems

#### Fems Create Case (POST) (`fems::fems_case`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Fems Create Case (POST).

#### Fems List Cases (GET) (`fems::fems_cases`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Fems List Cases (GET).

#### Fems Get Document (GET) (`fems::fems_document`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** GET /documents/{doc_id}.

#### Fems List Documents (GET) (`fems::fems_documents`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Fems List Documents (GET).

#### Fems Fems Health (GET) (`fems::fems_health`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Fems Fems Health (GET).

#### Fems List Phones (GET) (`fems::fems_phones`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Fems List Phones (GET).

#### Fems List Quarantine (GET) (`fems::fems_quarantine`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Fems List Quarantine (GET).

#### Fems Search (GET) (`fems::fems_search`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Shows you fems search (get). You get back result.

#### Fems Fems Stats (GET) (`fems::fems_stats`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Fems Fems Stats (GET).

#### Fems Upload File (POST) (`fems::fems_upload_file`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Fems Upload File (POST).

### Module: intake

#### Intake Chain of Custody (`intake::intake_chain_of_custody`)

- **Inputs** (small): notarization_id (reference / lookup)
- **Outputs** (small): chain (short text), document_id (reference / lookup)
- **Blurb:** Chain of custody retrieval for a notarized document. Shows the full custody chain from upload to notarization.

#### Intake Critical Issues (`intake::intake_critical_issues`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): issues (short text), total (number)
- **Blurb:** List of all CRITICAL issues across all of a user's documents.

#### Intake Enums (`intake::intake_enums`)

- **Inputs** (small): none
- **Outputs** (medium): document_types (dropdown / select), intake_statuses (dropdown / select), issue_severities (short text), languages (dropdown / select)
- **Blurb:** Enumeration values for document types, intake statuses, issue severities, and supported languages.

#### Intake Document Amounts (`intake::intake_get_amounts`)

- **Inputs** (small): doc_id (reference / lookup)
- **Outputs** (small): amounts (number)
- **Blurb:** List of monetary amounts extracted from a document. Shows amounts with context (fees, rent, deposits, charges).

#### Intake Document Dates (`intake::intake_get_dates`)

- **Inputs** (small): doc_id (reference / lookup)
- **Outputs** (small): dates (short text)
- **Blurb:** List of dates extracted from a document. Shows dates with context (what the date refers to) and confidence.

#### Intake Get Document (`intake::intake_get_document`)

- **Inputs** (small): doc_id (reference / lookup)
- **Outputs** (small): document (short text)
- **Blurb:** Retrieval of a specific intake document with all extraction results. Shows the full document record.

#### Intake Document Issues (`intake::intake_get_issues`)

- **Inputs** (small): doc_id (reference / lookup)
- **Outputs** (small): issues (short text)
- **Blurb:** List of detected issues for a document. Shows issues with severity, description, and possible next steps.

#### Intake Document Parties (`intake::intake_get_parties`)

- **Inputs** (small): doc_id (reference / lookup)
- **Outputs** (small): parties (short text)
- **Blurb:** List of parties extracted from a document. Shows parties with role (landlord, you, witness, agency) and contact info.

#### Intake Document Text (`intake::intake_get_text`)

- **Inputs** (small): doc_id (reference / lookup)
- **Outputs** (medium): text (long text)
- **Blurb:** Full extracted text for a document. Shows the text content extracted during processing.

#### Intake List Documents (`intake::intake_list_documents`)

- **Inputs** (small): user_id (session (hidden), optional), status (dropdown / select, optional)
- **Outputs** (medium): documents (list / table)
- **Blurb:** List of intake documents for a user. Supports filtering by status. Shows document summaries with processing status.

#### Intake Process Document (`intake::intake_process`)

- **Inputs** (small): doc_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): doc_id (reference / lookup), status (dropdown / select), document_type (dropdown / select)
- **Blurb:** Processing of an uploaded document. Runs classification, extraction, and issue detection. Shows the processed document.

#### Intake Process from Vault (`intake::intake_process_vault`)

- **Inputs** (small): doc_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): doc_id (reference / lookup), document_type (dropdown / select), issues_found (short text), status (dropdown / select)
- **Blurb:** Process a document already in the vault. Re-runs the intake pipeline on an existing vault file. Used when a file was uploaded via sidebar but not yet processed.

#### Intake Processing Status (`intake::intake_status`)

- **Inputs** (small): doc_id (reference / lookup)
- **Outputs** (medium): doc_id (reference / lookup), status (dropdown / select), progress (short text)
- **Blurb:** Status check for a processing document. Shows current status (queued, processing, completed, failed) and progress info.

#### Intake User Summary (`intake::intake_summary`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (large): total_documents (list / table), by_status (dropdown / select), total_issues (number), critical_issues (short text), upcoming_deadlines (list / table)
- **Blurb:** Summary of all intake documents for a user. Shows counts by status, total issues, critical issues, and upcoming deadlines.

#### Intake Upcoming Deadlines (`intake::intake_upcoming_deadlines`)

- **Inputs** (small): user_id (session (hidden), optional), days (short text, optional)
- **Outputs** (medium): deadlines (list / table), total (number)
- **Blurb:** List of upcoming deadlines extracted from documents. Shows deadlines within the next N days (default 14).

#### Intake Upload (`intake::intake_upload`)

- **Inputs** (medium): file (file), user_id (session (hidden), optional)
- **Outputs** (medium): doc_id (reference / lookup), filename (file), status (dropdown / select)
- **Blurb:** Single-file upload endpoint. Accepts a file, stores it, and queues it for processing. Shows the document ID and status.

#### Intake Upload and Auto-Process (`intake::intake_upload_auto`)

- **Inputs** (medium): file (file), user_id (session (hidden), optional)
- **Outputs** (large): doc_id (reference / lookup), document_type (dropdown / select), issues_found (short text), dates (short text), amounts (number), parties (short text), status (dropdown / select)
- **Blurb:** Upload-and-process endpoint. Accepts a file, stores it, processes it when ready (classify, extract, detect issues), and shows the full result. This is the 'Add Record' button's backend.

#### Intake Batch Upload (`intake::intake_upload_batch`)

- **Inputs** (medium): files (file), user_id (session (hidden), optional)
- **Outputs** (medium): results (list / table), total (number), succeeded (short text), failed (short text)
- **Blurb:** Batch upload endpoint. Accepts multiple files at once, stores and processes each, shows per-file results. Used when you drops a folder of documents.

#### Intake Verify Notarization (`intake::intake_verify_notarization`)

- **Inputs** (small): notarization_id (reference / lookup)
- **Outputs** (medium): valid (short text), notary (short text), document_id (reference / lookup), notarized_at (date)
- **Blurb:** Verification of a notarization ID. Shows whether the notarization is valid, the notary's info, and the document it covers.

### Module: journal

#### Journal Create Entry (`journal::journal_create`)

- **Inputs** (large): user_id (session (hidden), optional), entry_type (dropdown / select), title (short text), content (long text, optional), occurred_at (date, optional), is_urgent (checkbox / toggle, optional), involved_party (short text, optional), tags (short text, optional), document_link (url, optional)
- **Outputs** (small): entry_id (reference / lookup), entry (short text)
- **Blurb:** Create a free-form journal entry. You log conversations, incidents, repair requests, and notes with a title, content, timestamp, and optional tags.

#### Journal Delete Entry (`journal::journal_delete`)

- **Inputs** (small): entry_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): deleted (short text)
- **Blurb:** Delete a journal entry. Enforces ownership.

#### Journal Get Entry (`journal::journal_get`)

- **Inputs** (small): entry_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): entry (short text)
- **Blurb:** Get a single journal entry by ID. Enforces ownership.

#### Journal List Entries (`journal::journal_list`)

- **Inputs** (medium): user_id (session (hidden), optional), entry_type (dropdown / select, optional), is_urgent (checkbox / toggle, optional), skip (number, optional), limit (number, optional)
- **Outputs** (medium): entries (list / table), total (number)
- **Blurb:** List of journal entries for a user. Shows entries sorted by occurrence time, newest first, with optional filters and pagination.

#### Journal Summary (`journal::journal_summary`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (large): total_entries (list / table), urgent_entries (list / table), recent_entries (list / table)
- **Blurb:** Dashboard summary of journal entries. Shows total count, important count, and the most recent entries.

#### Journal Update Entry (`journal::journal_update`)

- **Inputs** (medium): entry_id (reference / lookup), user_id (session (hidden), optional), updates (short text)
- **Outputs** (small): entry (short text)
- **Blurb:** Update a journal entry. Enforces ownership.

### Module: packet_builder

#### Packet Builder Build (`packet_builder::packet_builder_build`)

- **Inputs** (large): user_id (session (hidden), optional), mode (short text), vault_ids (short text, optional), case_id (reference / lookup, optional), folder_id (reference / lookup, optional), include_highlights (list / table), include_notes (long text), include_footnotes (long text), name (short text, optional)
- **Outputs** (medium): packet_id (reference / lookup), item_count (number), download_url (url)
- **Blurb:** Build a curated document packet. Accepts vault_ids, case_id, or folder_id. Shows packet_id, item_count, and download_url.

#### Packet Builder Download (`packet_builder::packet_builder_download`)

- **Inputs** (medium): packet_id (reference / lookup), format (dropdown / select), mode (short text, optional), user_id (session (hidden), optional)
- **Outputs** (large): content (long text), filename (file), media_type (dropdown / select)
- **Blurb:** Download packet as zip or pdf.

#### Packet Builder Get (`packet_builder::packet_builder_get`)

- **Inputs** (small): packet_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (large): packet_id (reference / lookup), name (short text), mode (short text), item_count (number), created_at (date), source (dropdown / select), documents (list / table)
- **Blurb:** Retrieve packet metadata by packet_id.

### Module: pdf_tools

#### PDF Tools All Text (`pdf_tools::pdf_tools_all_text`)

- **Inputs** (small): pdf_id (reference / lookup)
- **Outputs** (medium): text (long text)
- **Blurb:** Extract text from all pages. Shows the full text content of the PDF.

#### PDF Tools Delete (`pdf_tools::pdf_tools_delete`)

- **Inputs** (small): pdf_id (reference / lookup)
- **Outputs** (small): success (short text)
- **Blurb:** Delete an uploaded PDF from cache. Removes the PDF and all associated data.

#### PDF Tools Extract Pages (`pdf_tools::pdf_tools_extract_pages`)

- **Inputs** (small): pdf_id (reference / lookup), pages (short text)
- **Outputs** (medium): pdf (file)
- **Blurb:** Extract specific pages as a new PDF. Shows the extracted pages as a PDF file.

#### PDF Tools Extract Pages Base64 (`pdf_tools::pdf_tools_extract_pages_base64`)

- **Inputs** (small): pdf_id (reference / lookup), pages (short text)
- **Outputs** (small): base64 (short text)
- **Blurb:** Extract specific pages as base64-encoded PDF. Shows the extracted pages for web display.

#### PDF Tools Info (`pdf_tools::pdf_tools_info`)

- **Inputs** (small): pdf_id (reference / lookup)
- **Outputs** (small): info (short text)
- **Blurb:** Get info about an uploaded PDF. Shows page count, metadata, and file size.

#### PDF Tools Merge (`pdf_tools::pdf_tools_merge`)

- **Inputs** (medium): files (file)
- **Outputs** (medium): merged_pdf (file)
- **Blurb:** Merge multiple PDFs into one. Shows the merged PDF file.

#### PDF Tools Page Base64 (`pdf_tools::pdf_tools_page_base64`)

- **Inputs** (medium): pdf_id (reference / lookup), page_num (short text), zoom (short text, optional)
- **Outputs** (small): base64 (short text)
- **Blurb:** Get a page as base64-encoded PNG. Shows the rendered page for web display.

#### PDF Tools Page Image (`pdf_tools::pdf_tools_page_image`)

- **Inputs** (medium): pdf_id (reference / lookup), page_num (short text), zoom (short text, optional)
- **Outputs** (medium): image (file)
- **Blurb:** Get a page as a PNG image. Shows the rendered page at the specified zoom level.

#### PDF Tools Page Text (`pdf_tools::pdf_tools_page_text`)

- **Inputs** (small): pdf_id (reference / lookup), page_num (short text)
- **Outputs** (medium): text (long text)
- **Blurb:** Extract text from a specific page. Shows the text content of the page.

#### PDF Tools Rotate Pages (`pdf_tools::pdf_tools_rotate`)

- **Inputs** (medium): pdf_id (reference / lookup), pages (short text), rotation (short text)
- **Outputs** (medium): pdf (file)
- **Blurb:** Rotate specific pages in a PDF. Shows the modified PDF with rotated pages.

#### PDF Tools Split (`pdf_tools::pdf_tools_split`)

- **Inputs** (medium): pdf_id (reference / lookup), pages_per_file (file, optional)
- **Outputs** (medium): split_pdfs (file)
- **Blurb:** Split a PDF into multiple files. Shows split PDFs with the specified pages per file.

#### PDF Tools Test (`pdf_tools::pdf_tools_test`)

- **Inputs** (small): none
- **Outputs** (medium): status (dropdown / select), pymupdf_version (file)
- **Blurb:** Test endpoint. Shows pymupdf version to verify PDF tools are available.

#### PDF Tools Thumbnails (`pdf_tools::pdf_tools_thumbnails`)

- **Inputs** (small): pdf_id (reference / lookup), max_width (short text, optional)
- **Outputs** (small): thumbnails (short text)
- **Blurb:** Get thumbnails of all pages. Shows thumbnail images for quick navigation.

#### PDF Tools Upload (`pdf_tools::pdf_tools_upload`)

- **Inputs** (medium): file (file)
- **Outputs** (medium): pdf_id (reference / lookup), filename (file), page_count (number)
- **Blurb:** Upload a PDF for processing. Shows a pdf_id for use with other endpoints.

### Module: preview

#### Preview Batch Generate (`preview::preview_batch_generate`)

- **Inputs** (medium): document_ids (short text), preview_type (dropdown / select, optional), user_id (session (hidden), optional)
- **Outputs** (small): cache_keys (short text), failed (short text)
- **Blurb:** Batch-generate previews for multiple documents. Shows cache_keys for all successfully generated previews.

#### Preview Cache Clear (`preview::preview_cache_clear`)

- **Inputs** (small): document_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): cleared (short text)
- **Blurb:** Clear the preview cache for a specific document. Forces regeneration on next preview request.

#### Preview Cache Clear All (`preview::preview_cache_clear_all`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): cleared (short text)
- **Blurb:** Clear all preview cache. Admin-only. Removes all cached previews, forcing regeneration.

#### Preview Generate (`preview::preview_generate`)

- **Inputs** (medium): document_id (reference / lookup), preview_type (dropdown / select, optional), user_id (session (hidden), optional)
- **Outputs** (small): cache_key (short text), preview_url (url)
- **Blurb:** Generate a preview for a document. Shows a cache_key that can be used to serve the preview. Supports thumbnail and full-page preview types.

#### Preview Info (`preview::preview_info`)

- **Inputs** (small): document_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): info (short text)
- **Blurb:** Get preview metadata for a document. Shows preview availability, cache status, and supported preview types.

#### Preview Serve (`preview::preview_serve`)

- **Inputs** (small): cache_key (short text)
- **Outputs** (large): content (long text), content_type (long text)
- **Blurb:** Serve a generated preview by cache_key. Shows the preview content (image, HTML, or text).

#### Preview Statistics (`preview::preview_statistics`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): stats (short text)
- **Blurb:** Preview cache statistics. Shows cache size, hit rate, and document count. Admin-only.

#### Preview Supported Formats (`preview::preview_supported_formats`)

- **Inputs** (small): none
- **Outputs** (small): formats (dropdown / select)
- **Blurb:** List of supported document formats for preview. Shows format codes and descriptions.

#### Preview Text (`preview::preview_text`)

- **Inputs** (small): document_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): text (long text)
- **Blurb:** Get a text preview of a document. Shows the extracted text content for the document.

### Module: rent

#### Rent Ledger Create (`rent::rent_ledger_create`)

- **Inputs** (large): user_id (session (hidden), optional), entry_type (dropdown / select), amount (number), payment_date (date), due_date (date, optional), period_covered (short text, optional), status (dropdown / select, optional), payment_method (short text, optional), source (dropdown / select, optional), receipt_document_id (reference / lookup, optional), overlay_link (url, optional), notes (long text, optional)
- **Outputs** (small): payment_id (reference / lookup), payment (short text)
- **Blurb:** Create a rent ledger entry. Supports payments, fees, deposits, credits, and charges. Amount is in dollars (input), stored as cents (DB).

#### Rent Ledger Delete (`rent::rent_ledger_delete`)

- **Inputs** (small): payment_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): deleted (short text)
- **Blurb:** Delete a rent ledger entry. Ownership enforced.

#### Rent Ledger Get (`rent::rent_ledger_get`)

- **Inputs** (small): payment_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): payment (short text)
- **Blurb:** Get a single rent ledger entry by ID. Shows full details including entry type, source, overlay link, and running balance. Ownership enforced.

#### Rent Ledger List (`rent::rent_ledger_list`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): payments (short text)
- **Blurb:** List rent ledger entries for you. Shows entries sorted newest first with running balance for each.

#### Rent Ledger Update (`rent::rent_ledger_update`)

- **Inputs** (medium): payment_id (reference / lookup), user_id (session (hidden), optional), updates (short text)
- **Outputs** (small): payment (short text)
- **Blurb:** Update a rent ledger entry. You can edit amount, date, entry type, source, status, method, or overlay link. Running balance is recomputed on save.

### Module: timeline

#### Timeline Chronology Builder (`timeline::timeline_chronology`)

- **Inputs** (medium): events (list / table), db_session (short text)
- **Outputs** (medium): chronology_items (list / table)
- **Blurb:** Build deterministic timeline chronology from cloud events and indexed document metadata.

#### Timeline Create Event (`timeline::timeline_create_event`)

- **Inputs** (large): user_id (session (hidden), optional), date (date), title (short text), description (long text, optional), severity (short text, optional), source (dropdown / select, optional)
- **Outputs** (small): event_id (reference / lookup), created_at (date)
- **Blurb:** Manual creation of a timeline event. You can add events that aren't from documents — conversations, phone calls, visits, observations. Each event has a date, title, description, and optional severity.

#### Timeline Date Range Info (`timeline::timeline_date_range`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): earliest_date (date), latest_date (date), span_days (short text)
- **Blurb:** Date range metadata for the user's timeline. Shows the earliest and latest event dates, plus the span in days.

#### Timeline Unified View (`timeline::timeline_unified_view`)

- **Inputs** (medium): user_id (session (hidden), optional), start_date (date, optional), end_date (date, optional), sources (dropdown / select, optional), severity (short text, optional)
- **Outputs** (medium): events (list / table), total (number), date_range (short text)
- **Blurb:** Unified timeline view. Assembles events from all sources (documents, journal, deadlines, issues, manual entries) into a single chronological list with filtering by date range, source, and severity. This is the primary view for you timeline page.

### Module: vault

#### Vault Delete Document (`vault::vault_delete_document`)

- **Inputs** (small): document_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): status (dropdown / select)
- **Blurb:** Deletion of a document from the user's vault. You-only. Removes the file and its certificate from cloud storage.

#### Vault Download Document (`vault::vault_download_document`)

- **Inputs** (small): document_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (large): file_stream (file), filename (file), mime_type (dropdown / select)
- **Blurb:** Download of a specific document by ID from the user's cloud storage. Shows the file stream with correct content-type.

#### Vault Folder Structure (`vault::vault_folders`)

- **Inputs** (medium): user_id (session (hidden), optional), access_token (short text), provider (dropdown / select)
- **Outputs** (medium): CANONICAL_VAULT_FOLDERS (list / table)
- **Blurb:** All vault folder paths come from app/core/vault_paths.py. NEVER hardcode Semptify5.0/ paths. NEVER duplicate these constants.

#### Vault Get Certificate (`vault::vault_get_certificate`)

- **Inputs** (small): document_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): certificate_id (reference / lookup), sha256 (short text), certified_at (date), storage_path (short text)
- **Blurb:** Retrieval of a document's chain-of-custody certificate. Shows the SEMPTIFY certificate with SHA-256, upload timestamp, storage path, and version. Used for documentation of events integrity verification.

#### Vault Ingestion Service (`vault::vault_ingestion`)

- **Inputs** (medium): user_id (session (hidden), optional), item_type (dropdown / select), event_time (time), record_time (time), metadata (short text)
- **Outputs** (small): item_id (reference / lookup), audit_log_id (reference / lookup)
- **Blurb:** Ingest documentation of events into unified vault with data contract enforcement and three-timestamp model.

#### Vault Initialize (`vault::vault_init`)

- **Inputs** (small): user_id (session (hidden), optional), provider (dropdown / select)
- **Outputs** (medium): ok (short text), message (long text)
- **Blurb:** Creation of the Semptify vault folder structure in the user's cloud storage. Called during onboarding after storage OAuth. Creates .Semptify5.0/ root and all subfolders.

#### Vault List Documents (`vault::vault_list_documents`)

- **Inputs** (small): user_id (session (hidden), optional), document_type (dropdown / select, optional)
- **Outputs** (medium): documents (list / table), total (number)
- **Blurb:** List of documents in the user's vault. Supports filtering by document_type. Shows document summaries with id, filename, type, size, and timestamps.

#### Vault Search Service (`vault::vault_search`)

- **Inputs** (medium): user_id (session (hidden), optional), search_criteria (short text), timeline_mode (list / table)
- **Outputs** (large): items (list / table), total_count (number), timeline_sequence (list / table)
- **Blurb:** Deep search, timeline queries, and filtering for unified vault with JSONB GIN index support.

#### Vault Sidebar Files (`vault::vault_sidebar_files`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): files (file)
- **Blurb:** List of recent files for the persistent vault sidebar. Shows a compact list for display in the side panel on any you page.

#### Vault Sidebar Search (`vault::vault_sidebar_search`)

- **Inputs** (small): query (short text), user_id (session (hidden), optional)
- **Outputs** (medium): results (list / table)
- **Blurb:** Search across the user's vault documents. Searches filename, document_type, description, and tags. Shows matching summaries.

#### Vault Sidebar Stats (`vault::vault_sidebar_stats`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (large): total_documents (list / table), total_size (number), by_type (dropdown / select), last_upload (file)
- **Blurb:** Vault statistics for sidebar display. Shows counts by document type, total size, and last upload timestamp.

#### Vault Sidebar Upload (`vault::vault_sidebar_upload`)

- **Inputs** (medium): files (file), user_id (session (hidden), optional)
- **Outputs** (medium): uploaded (file), errors (short text)
- **Blurb:** Quick upload from the persistent sidebar. Accepts multiple files, stores them in the vault, shows per-file status. This is the 'Add Record' button on every you page.

#### Vault Status (`vault::vault_status`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): ok (short text), provider (dropdown / select)
- **Blurb:** Lightweight check that the user is authenticated and has a storage provider configured.

#### Vault Upload (`vault::vault_upload`)

- **Inputs** (large): file (file), user_id (session (hidden), optional), document_type (dropdown / select, optional), description (long text, optional), tags (short text, optional)
- **Outputs** (medium): document_id (reference / lookup), certificate_id (reference / lookup), sha256_hash (reference / lookup), storage_path (short text)
- **Blurb:** Internal/service upload endpoint. Stores a document in the user's cloud storage with SHA-256 hash, certificate, and metadata. Called by VaultUploadService — NOT directly from you UI.

#### Vault Upload Page + Object Envelopes (`vault::vault_upload_envelope`)

- **Inputs** (small): user_id (session (hidden), optional), request (short text)
- **Outputs** (medium): page_envelope (file), experience_token_snapshot (short text)
- **Blurb:** ADR-0008 §2.1/2.6 wiring for the Vault upload page. Shows the Page Envelope with resolved page actions and, on upload, an Object Envelope for the created document.

#### Vault Verify (`vault::vault_verify`)

- **Inputs** (small): user_id (session (hidden), optional), provider (dropdown / select)
- **Outputs** (medium): ok (short text), folders (list / table)
- **Blurb:** Verification that the vault folder structure is accessible in the user's cloud storage. Shows per-folder status. Empty folders are valid (only failure is inaccessible/missing).

## KNOW Pillar

### Module: context_engine

#### Context Query (`context_engine::context_query`)

- **Inputs** (medium): subject (short text), jurisdiction (dropdown / select, optional), limit (number, optional)
- **Outputs** (small): facts (short text)
- **Blurb:** Query for cached context facts by subject + jurisdiction. Shows verified facts with source URLs — no hallucination. Does NOT gather new facts; use context_refresh for that.

#### Context Refresh (`context_engine::context_refresh`)

- **Inputs** (medium): subject (short text), jurisdiction (dropdown / select, optional), query (short text, optional), admin_user_id (reference / lookup)
- **Outputs** (small): new_count (number)
- **Blurb:** Gather fresh facts from external sources for a subject. Admin only. Writes results into context_facts cache.

#### Explanation Entry (`context_engine::explanation_entry`)

- **Inputs** (large): subject (short text), jurisdiction (dropdown / select, optional), upl_risk_tier (dropdown / select), pillar (short text), review_status (dropdown / select), admin_user_id (reference / lookup, optional)
- **Outputs** (small): entry_id (reference / lookup), entry (short text)
- **Blurb:** Curated Layer 1 explanation store. Admin create/update/delete; authenticated read. Each entry has subject, jurisdiction, UPL risk tier, pillar, review_status, and four variant slots (trust, mechanics, reinforcement, minimal).

#### Explanation Retrieval (`context_engine::explanation_retrieval`)

- **Inputs** (medium): object_envelope (file), jurisdiction (dropdown / select, optional)
- **Outputs** (medium): retrieval_results (list / table)
- **Blurb:** Layer 2 metadata-match retrieval. Ranks Layer 1 explanation entries against an Object Envelope using subject_tags, jurisdiction, pillar, and review_status. Shows only results above the configured confidence threshold.

#### Familiarity Tapering (`context_engine::familiarity_tapering`)

- **Inputs** (small): retrieval_result (short text), exposure_count (number)
- **Outputs** (medium): variant_text (long text)
- **Blurb:** Explanation variant selection by exposure count. 1st exposure shows the full mechanics variant, 2nd/3rd shows trust and reinforcement, 4th+ shows minimal.

#### Story Moderate (`context_engine::story_moderate`)

- **Inputs** (medium): story_id (reference / lookup), publish (short text), title (short text, optional), body (long text, optional), admin_user_id (reference / lookup)
- **Outputs** (small): story_id (reference / lookup), is_published (checkbox / toggle)
- **Blurb:** Moderate a you story. Admin only. Optionally edits title/body, then publishes or unpublishes.

#### Story Submit (`context_engine::story_submit`)

- **Inputs** (large): subject (short text), title (short text), body (long text), jurisdiction (dropdown / select, optional), outcome (short text, optional), submitted_by (short text)
- **Outputs** (small): story_id (reference / lookup)
- **Blurb:** Submit a you story. Anonymized by default. Pending moderation — not published until admin reviews.

### Module: free_api

#### Free API Court Evictions Search (`free_api::free_api_court_evictions`)

- **Inputs** (small): name (short text)
- **Outputs** (small): evictions (short text)
- **Blurb:** Search MN court eviction records by party name. Shows eviction cases.

#### Free API Federal Court Search (`free_api::free_api_court_federal`)

- **Inputs** (small): query (short text)
- **Outputs** (medium): cases (list / table)
- **Blurb:** Search federal court cases via CourtListener. Shows federal cases.

#### Free API HUD Inspection Lookup (`free_api::free_api_inspections_hud`)

- **Inputs** (small): property_id (reference / lookup)
- **Outputs** (small): inspection (short text)
- **Blurb:** Lookup HUD REAC inspection scores. Shows inspection scores for the property.

#### Free API Local Inspection Lookup (`free_api::free_api_inspections_local`)

- **Inputs** (small): city (short text), address (address)
- **Outputs** (small): inspections (short text)
- **Blurb:** Lookup local inspection records. Shows inspection history for the address.

#### Free API Landlord Business Lookup (`free_api::free_api_landlord_business`)

- **Inputs** (small): name (short text)
- **Outputs** (small): businesses (short text)
- **Blurb:** Search MN Secretary of State business records. Shows business filings.

#### Free API Landlord Owner Lookup (`free_api::free_api_landlord_owner`)

- **Inputs** (small): property_id (reference / lookup)
- **Outputs** (small): owner (short text)
- **Blurb:** Lookup property owner via HUD/county records. Shows owner info.

#### Free API Property Address Lookup (`free_api::free_api_property_address`)

- **Inputs** (small): county (number), address (address)
- **Outputs** (small): property (short text)
- **Blurb:** Lookup property by county and address. Shows property data.

#### Free API Property Parcel Lookup (`free_api::free_api_property_parcel`)

- **Inputs** (small): county (number), parcel_id (reference / lookup)
- **Outputs** (small): parcel (short text)
- **Blurb:** Lookup parcel by county and parcel ID. Shows property parcel data.

#### Free API Statute Lookup (`free_api::free_api_statutes`)

- **Inputs** (small): section (short text)
- **Outputs** (small): statute (short text)
- **Blurb:** Retrieve MN statute text by section number. Shows the statute text.

#### Free API City Violations Lookup (`free_api::free_api_violations_city`)

- **Inputs** (small): city (short text), address (address)
- **Outputs** (medium): violations (list / table)
- **Blurb:** Lookup city inspection violations for an address. Shows violations.

#### Free API Environmental Violations Lookup (`free_api::free_api_violations_environment`)

- **Inputs** (small): facility (short text)
- **Outputs** (medium): violations (list / table)
- **Blurb:** Lookup EPA/MPCA environmental violations. Shows violations for the facility.

### Module: housing_accountability

#### Accountability Coalition Action (`housing_accountability::accountability_coalition_build`)

- **Inputs** (small): user_id (session (hidden), optional), patterns (short text)
- **Outputs** (medium): action_summary (long text), share_token (short text)
- **Blurb:** Build a coalition action for community organizing. Creates an anonymized summary of violations for sharing with you rights groups. No PII, no addresses, no names.

#### Accountability Dashboard (`housing_accountability::accountability_dashboard`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): patterns (short text), packets (short text), coalitions (short text)
- **Blurb:** Dashboard view of housing accountability data. Shows detected patterns, oversight packets, and coalition actions for the user.

#### Accountability Detect Patterns (`housing_accountability::accountability_detect_patterns`)

- **Inputs** (medium): user_id (session (hidden), optional), documents (list / table, optional)
- **Outputs** (small): patterns (short text), total (number)
- **Blurb:** Detection of housing violation patterns from a your documents. Analyzes uploaded documents for repeated violations (repeated fees, repeated entry without notice, etc.). Shows detected patterns with severity and documentation of events references.

#### Accountability Evidence Intake (`housing_accountability::accountability_evidence_intake`)

- **Inputs** (small): user_id (session (hidden), optional), evidence (short text)
- **Outputs** (small): processed (short text), linked_patterns (url)
- **Blurb:** Process documentation of events intake for housing cases. Accepts documentation of events descriptions and documents, categorizes them, and links them to detected patterns.

#### Accountability Oversight Packet (`housing_accountability::accountability_oversight_packet`)

- **Inputs** (medium): user_id (session (hidden), optional), patterns (short text), agency (dropdown / select, optional)
- **Outputs** (medium): packet (short text), format (dropdown / select), download_url (url)
- **Blurb:** Generation of an oversight packet for regulatory submission. Assembles detected patterns, documentation of events, and timeline into a formatted packet for agencies. You downloads and submits it themselves.

#### Accountability Press Release (`housing_accountability::accountability_press_release`)

- **Inputs** (small): user_id (session (hidden), optional), patterns (short text)
- **Outputs** (small): press_release (short text), format (dropdown / select)
- **Blurb:** Build a press release for housing rights advocacy. Creates an anonymized, fact-based press release from detected patterns. No PII.

#### Accountability Public Records Search (`housing_accountability::accountability_public_records_search`)

- **Inputs** (small): query (short text), jurisdiction (dropdown / select, optional)
- **Outputs** (small): records (short text), total (number)
- **Blurb:** Search of public records for housing cases. Searches court records, property records, and code violations. Shows publicly available facts only.

### Module: law_library

#### Law Library Categories (`law_library::law_library_categories`)

- **Inputs** (small): none
- **Outputs** (medium): categories (list / table)
- **Blurb:** List of all categories in the law library.

#### Law Library County Code (`law_library::law_library_county_code`)

- **Inputs** (small): county (number), state (dropdown / select, optional)
- **Outputs** (medium): official_url (url), source_name (dropdown / select), last_verified (short text), jurisdiction (dropdown / select)
- **Blurb:** County code of ordinances URL for a given state and county. Shows the official Municode or equivalent URL.

#### Law Library Get Case (`law_library::law_library_get_case`)

- **Inputs** (small): case_id (reference / lookup)
- **Outputs** (small): case (short text)
- **Blurb:** Detailed view of a single case. Shows full case text, citation, holding, and related statutes.

#### Law Library Get Court Rule (`law_library::law_library_get_court_rule`)

- **Inputs** (small): rule_id (reference / lookup)
- **Outputs** (small): court_rule (short text)
- **Blurb:** Detailed view of a single court rule. Shows full text, citation, and related procedures.

#### Law Library Get Statute (`law_library::law_library_get_statute`)

- **Inputs** (small): statute_id (reference / lookup)
- **Outputs** (small): statute (short text)
- **Blurb:** Detailed view of a single statute. Shows full text, citation, category, and related cases.

#### Law Library Card Link Index (`law_library::law_library_links`)

- **Inputs** (small): none
- **Outputs** (small): links (url)
- **Blurb:** Index of every law, case, and court rule with its URL. Shows a flat list of all references with their type and title.

#### Law Library List Case Law (`law_library::law_library_list_case_law`)

- **Inputs** (small): search (short text, optional)
- **Outputs** (medium): cases (list / table), total (number)
- **Blurb:** List of case law precedents. Supports full-text search in case name and summary. Shows case summaries with citation and holding.

#### Law Library List Court Rules (`law_library::law_library_list_court_rules`)

- **Inputs** (small): category (dropdown / select, optional)
- **Outputs** (medium): court_rules (list / table), total (number)
- **Blurb:** List of court rules. Supports filtering by category. Shows rule summaries with citation and jurisdiction.

#### Law Library List Statutes (`law_library::law_library_list_statutes`)

- **Inputs** (small): category (dropdown / select, optional), search (short text, optional)
- **Outputs** (medium): statutes (list / table), total (number)
- **Blurb:** List of statutes in the law library. Supports filtering by category and full-text search in title and summary. Shows statute summaries with citation and category.

#### Law Library Quick Reference (`law_library::law_library_quick_reference`)

- **Inputs** (small): topic (dropdown / select)
- **Outputs** (large): summary (long text), key_laws (short text), key_cases (list / table)
- **Blurb:** Quick reference for a specific topic. Shows a summary of key laws, rules, and cases for the topic.

### Module: legal_analysis

#### Legal Analysis Assess Merit (`legal_analysis::legal_analysis_assess_merit`)

- **Inputs** (small): case_data (short text)
- **Outputs** (medium): merit_score (number), strengths (short text), weaknesses (short text)
- **Blurb:** Comprehensive assessment of legal merit. Shows merit score, strengths, and weaknesses.

#### Legal Analysis Assess Merit From Case (`legal_analysis::legal_analysis_assess_merit_from_case`)

- **Inputs** (small): case_id (reference / lookup), perspective (short text, optional)
- **Outputs** (small): merit_score (number), assessment (short text)
- **Blurb:** Assess legal merit from an existing case. Shows merit score from the case's documentation of events and timeline.

#### Legal Analysis Binding Status (`legal_analysis::legal_analysis_binding_status`)

- **Inputs** (medium): documents (list / table)
- **Outputs** (small): binding_statuses (dropdown / select)
- **Blurb:** Analyze which documents are legally binding. Shows binding status for each document.

#### Legal Analysis Check Consistency (`legal_analysis::legal_analysis_check_consistency`)

- **Inputs** (large): documents (list / table), events (list / table, optional)
- **Outputs** (small): inconsistencies (short text), conflicts (short text)
- **Blurb:** Check consistency across multiple documents and events. Shows inconsistencies and conflicts.

#### Legal Analysis Classify Evidence (`legal_analysis::legal_analysis_classify_evidence`)

- **Inputs** (small): document (short text)
- **Outputs** (medium): evidence_type (dropdown / select), legal_status (dropdown / select), confidence (short text)
- **Blurb:** Classify a document for legal purposes. Shows documentation of events type and legal status.

#### Legal Analysis Classify Evidence Batch (`legal_analysis::legal_analysis_classify_evidence_batch`)

- **Inputs** (medium): documents (list / table)
- **Outputs** (small): classifications (short text)
- **Blurb:** Classify multiple documents at once. Shows documentation of events types and legal statuses for each.

#### Legal Analysis Corroboration (`legal_analysis::legal_analysis_corroboration`)

- **Inputs** (medium): claim (short text), evidence_items (list / table)
- **Outputs** (small): corroboration_score (number), supporting_evidence (short text)
- **Blurb:** Analyze how well documentation of events supports a specific claim. Shows corroboration score and supporting documentation of events.

#### Legal Analysis Corroboration Multi (`legal_analysis::legal_analysis_corroboration_multi`)

- **Inputs** (medium): claims (short text), evidence_items (list / table)
- **Outputs** (small): scores (number)
- **Blurb:** Analyze how well documentation of events supports multiple claims. Shows corroboration scores for each claim.

#### Legal Analysis Evidence Types (`legal_analysis::legal_analysis_evidence_types`)

- **Inputs** (small): none
- **Outputs** (small): evidence_types (dropdown / select)
- **Blurb:** List of all documentation of events type classifications. Shows documentation of events types and descriptions.

#### Legal Analysis Hearsay (`legal_analysis::legal_analysis_hearsay`)

- **Inputs** (medium): documents (list / table)
- **Outputs** (small): hearsay_flags (short text)
- **Blurb:** Analyze documents for hearsay content. Shows hearsay flags and explanations.

#### Legal Analysis Legal Statuses (`legal_analysis::legal_analysis_legal_statuses`)

- **Inputs** (small): none
- **Outputs** (small): legal_statuses (dropdown / select)
- **Blurb:** List of all document legal status classifications. Shows statuses and descriptions.

#### Legal Analysis MN Eviction Requirements (`legal_analysis::legal_analysis_mn_eviction_requirements`)

- **Inputs** (small): none
- **Outputs** (small): requirements (short text)
- **Blurb:** Minnesota eviction notice requirements. Shows notice periods and statutory requirements.

#### Legal Analysis Quick Case Check (`legal_analysis::legal_analysis_quick_check`)

- **Inputs** (small): case_id (reference / lookup)
- **Outputs** (small): health_score (number), risks (short text)
- **Blurb:** Quick legal health check for a case. Shows a summary of legal strengths and risks.

#### Legal Analysis Timeline (`legal_analysis::legal_analysis_timeline`)

- **Inputs** (medium): events (list / table), jurisdiction (dropdown / select, optional)
- **Outputs** (medium): gaps (short text), conflicts (short text), compliance_issues (short text)
- **Blurb:** Analyze timeline for legal compliance. Shows timeline gaps, conflicts, and compliance issues.

### Module: location

#### Location Clear (`location::location_clear`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): success (short text)
- **Blurb:** Clear the user's saved location. Resets to Minnesota default. Used when you moves or wants to reset.

#### Location Context (`location::location_context`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): state_code (dropdown / select), county (number), resources (dropdown / select), eviction_timeline (list / table), jurisdiction_metadata (dropdown / select)
- **Blurb:** Full location context for the user. Shows state, county, legal resources, eviction timeline, and jurisdiction metadata in one call.

#### Location County Info (`location::location_county_info`)

- **Inputs** (small): county (number), state_code (dropdown / select, optional)
- **Outputs** (medium): county (number), state_code (dropdown / select), court_location (short text), local_resources (dropdown / select)
- **Blurb:** County-specific information. Shows county details, court locations, and local resources for the given county.

#### Location Current (`location::location_current`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): state_code (dropdown / select), county (number), source (dropdown / select)
- **Blurb:** Get the user's current location. Shows state code, county (if known), and whether it was auto-detected or manually set. Defaults to Minnesota if no location is set.

#### Location Eviction Timeline (`location::location_eviction_timeline`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): timeline (list / table), state_code (dropdown / select)
- **Blurb:** Eviction procedure timeline for the user's jurisdiction. Shows the steps, notice periods, and deadlines for an eviction in the user's state. Facts only — not legal information.

#### Location Legal Resources (`location::location_legal_resources`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): resources (dropdown / select)
- **Blurb:** Jurisdiction-aware legal resources for the user. Shows legal aid organizations, you rights groups, and government agencies for the user's state and county. Facts only, no recommendations.

#### Location MN Counties (`location::location_mn_counties`)

- **Inputs** (small): none
- **Outputs** (small): counties (number)
- **Blurb:** List of Minnesota counties. MN is the default and most complete jurisdiction. Shows county names and codes.

#### Location State Info (`location::location_state_info`)

- **Inputs** (small): state_code (dropdown / select)
- **Outputs** (medium): state_code (dropdown / select), name (short text), counties (number), resources_available (dropdown / select)
- **Blurb:** State information for a specific state code. Shows state name, supported counties, and available resources.

#### Location Supported States (`location::location_supported_states`)

- **Inputs** (small): none
- **Outputs** (small): states (dropdown / select)
- **Blurb:** List of states supported by the location service. Shows state codes and names.

#### Location Update (`location::location_update`)

- **Inputs** (medium): user_id (session (hidden), optional), state_code (dropdown / select), county (number, optional)
- **Outputs** (small): state_code (dropdown / select), county (number)
- **Blurb:** Update the user's location. You can manually set their state and county. This drives jurisdiction-aware content throughout the app.

### Module: risc

#### Risc Risc Webhook (POST) (`risc::risc_webhook`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Receive Google Cross-connection Protection Security Event Tokens.

#### Risc Risc Webhook Verify (GET) (`risc::risc_webhook_verify`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Google verification GET request — shows 200 to confirm endpoint ownership.

### Module: search

#### Search Advanced (`search::search_advanced`)

- **Inputs** (small): q (short text), search_type (dropdown / select, optional)
- **Outputs** (medium): results (list / table), total (number)
- **Blurb:** Advanced search with type filtering. Supports full_text, metadata, content, and hybrid search modes.

#### Search Global (`search::search_global`)

- **Inputs** (small): q (short text), limit (number, optional)
- **Outputs** (medium): results (list / table), total (number)
- **Blurb:** Global search across all of your documents. Shows results grouped by category (documents, timeline, contacts).

#### Search Index Document (`search::search_index_document`)

- **Inputs** (small): document_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): indexed (short text), document_id (reference / lookup)
- **Blurb:** Index a document for search. Called after document processing to add the document's text and metadata to the search index.

#### Search Quick (`search::search_quick`)

- **Inputs** (small): q (short text), user_id (session (hidden), optional)
- **Outputs** (medium): results (list / table)
- **Blurb:** Quick search for lightweight queries. Shows top results without full ranking.

#### Search Remove From Index (`search::search_remove_from_index`)

- **Inputs** (small): document_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): removed (short text), document_id (reference / lookup)
- **Blurb:** Remove a document from the search index. Called when a document is deleted from the vault.

#### Search Statistics (`search::search_statistics`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): index_stats (short text), document_count (number)
- **Blurb:** Search index statistics. Shows index size, document count, and last indexed timestamp. Admin-only.

#### Search Suggestions (`search::search_suggestions`)

- **Inputs** (small): q (short text), limit (number, optional)
- **Outputs** (small): suggestions (short text), total (number)
- **Blurb:** Search suggestions for autocomplete. Shows partial matches as the user types.

### Module: state_laws

#### State Laws Detect by Location (`state_laws::state_laws_detect`)

- **Inputs** (small): request (short text)
- **Outputs** (small): state_code (dropdown / select), confidence (short text)
- **Blurb:** Detect the user's likely state based on IP geolocation. Shows the detected state code and confidence. Used to auto-select the state on first visit.

#### State Laws Get (`state_laws::state_laws_get`)

- **Inputs** (small): state_code (dropdown / select)
- **Outputs** (large): state_code (dropdown / select), name (short text), security_deposit_limit (number), eviction_procedure (short text), tenant_rights (short text), landlord_obligations (short text)
- **Blurb:** Detailed housing law information for a specific state. Shows full state details including security deposit limits, eviction procedures, you rights, and landlord obligations.

#### State Laws List (`state_laws::state_laws_list`)

- **Inputs** (small): none
- **Outputs** (small): states (dropdown / select)
- **Blurb:** List of all states with basic housing law information. Shows state code, name, and summary of you protections.

#### State Laws Nearby Search (`state_laws::state_laws_nearby`)

- **Inputs** (small): lat (short text), lon (short text)
- **Outputs** (small): states (dropdown / select)
- **Blurb:** Find nearby states by latitude/longitude. Shows states sorted by distance with their housing law summaries. Used when your location is detected via IP.

## ACT Pillar

### Module: case_builder

#### Case Builder Create Case (`case_builder::case_builder_case_create`)

- **Inputs** (small): case (short text), user_id (session (hidden), optional)
- **Outputs** (small): case_id (reference / lookup), case (short text)
- **Blurb:** Create a new case for the authenticated user.

#### Case Builder Delete Case (`case_builder::case_builder_case_delete`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): success (short text)
- **Blurb:** Delete a case belonging to the authenticated user.

#### Case Builder Get Case (`case_builder::case_builder_case_get`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): case (short text)
- **Blurb:** Get a specific case by ID. Shows full case details.

#### Case Builder Update Case (`case_builder::case_builder_case_update`)

- **Inputs** (medium): case_id (reference / lookup), updates (short text), user_id (session (hidden), optional)
- **Outputs** (small): case (short text)
- **Blurb:** Update a case belonging to the authenticated user.

#### Case Builder List Cases (`case_builder::case_builder_cases_list`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): cases (list / table), count (number)
- **Blurb:** List all cases for the authenticated user with computed status and progress.

#### Case Builder Add Counterclaim (`case_builder::case_builder_counterclaim_add`)

- **Inputs** (medium): case_id (reference / lookup), claim (short text), user_id (session (hidden), optional)
- **Outputs** (small): counterclaim_id (reference / lookup)
- **Blurb:** Add a counterclaim to a case.

#### Case Builder Get Counterclaims (`case_builder::case_builder_counterclaims_get`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): counterclaims (list / table), count (number)
- **Blurb:** Get all counterclaims for a case.

#### Case Builder Curated Packet Export (`case_builder::case_builder_curated_packet_export`)

- **Inputs** (large): case_id (reference / lookup), user_id (session (hidden), optional), document_ids (short text, optional), include_clean (checkbox / toggle, optional), include_marked (checkbox / toggle, optional), include_summary (long text, optional), overlay_types (dropdown / select, optional)
- **Outputs** (medium): zip_bytes (short text), filename (file)
- **Blurb:** Export a curated packet ZIP from case documentation of events. Produces clean/ original copies, marked/ copies with highlight/note/footnote annotations appended, and a summary/ report. Overlay types are configurable; document_ids can be supplied or inferred from case documentation of events.

#### Case Builder Add Deadline (`case_builder::case_builder_deadline_add`)

- **Inputs** (medium): case_id (reference / lookup), deadline (short text), user_id (session (hidden), optional)
- **Outputs** (small): deadline_id (reference / lookup), deadline (short text)
- **Blurb:** Add a deadline to a case.

#### Case Builder Complete Deadline (`case_builder::case_builder_deadline_complete`)

- **Inputs** (medium): case_id (reference / lookup), deadline_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): success (short text)
- **Blurb:** Mark a deadline as complete for a case.

#### Case Builder Get Deadlines (`case_builder::case_builder_deadlines_get`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): deadlines (list / table), count (number)
- **Blurb:** Get all deadlines for a case.

#### Case Builder Add Defense (`case_builder::case_builder_defense_add`)

- **Inputs** (medium): case_id (reference / lookup), defense (dropdown / select), user_id (session (hidden), optional)
- **Outputs** (small): defense_id (reference / lookup)
- **Blurb:** Add a defense strategy to a case.

#### Case Builder Get Defenses (`case_builder::case_builder_defenses_get`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): defenses (list / table), count (number)
- **Blurb:** Get all defense strategies for a case.

#### Case Builder Add Evidence (`case_builder::case_builder_evidence_add`)

- **Inputs** (medium): case_id (reference / lookup), evidence (short text), user_id (session (hidden), optional)
- **Outputs** (small): evidence_id (reference / lookup)
- **Blurb:** Add documentation of events to a case.

#### Case Builder Get Evidence (`case_builder::case_builder_evidence_get`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): evidence (short text), count (number)
- **Blurb:** Get all documentation of events for a case.

#### Case Builder Freshness Recommendations (`case_builder::case_builder_freshness_recommendations`)

- **Inputs** (small): case_data (short text), user_id (session (hidden), optional)
- **Outputs** (small): recommendations (short text)
- **Blurb:** Get recommendations for improving case legal freshness.

#### Case Builder Info (`case_builder::case_builder_info`)

- **Inputs** (small): none
- **Outputs** (small): info (short text)
- **Blurb:** Case builder module information. Shows version and capabilities.

#### Case Builder Intake Complaint (`case_builder::case_builder_intake_complaint`)

- **Inputs** (small): intake (short text), user_id (session (hidden), optional)
- **Outputs** (small): case_id (reference / lookup), case (short text)
- **Blurb:** Create a case from a complaint document. Simple intake flow.

#### Case Builder Attorney Intake Packet Export (`case_builder::case_builder_intake_packet_export`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): packet (short text)
- **Blurb:** Export a streamlined, chronological, documentation of events-labeled intake packet for first-time attorney review. Facts and dates only. Distinct from court_packet module export (which is court-filing-ready).

#### Case Builder Attorney Intake Packet Export PDF (`case_builder::case_builder_intake_packet_export_pdf`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): pdf_bytes (file)
- **Blurb:** Download the intake packet as a formatted PDF. Facts and dates only — no recommendations or editorializing.

#### Case Builder Attorney Intake Packet Export ZIP (`case_builder::case_builder_intake_packet_export_zip`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): zip_bytes (short text)
- **Blurb:** Download the intake packet as a ZIP containing the JSON packet, a formatted PDF, and a plain-text documentation of events index. Facts and dates only — no recommendations or editorializing.

#### Case Builder Add Motion (`case_builder::case_builder_motion_add`)

- **Inputs** (medium): case_id (reference / lookup), motion (dropdown / select), user_id (session (hidden), optional)
- **Outputs** (small): motion_id (reference / lookup)
- **Blurb:** Add a motion to a case.

#### Case Builder Get Motions (`case_builder::case_builder_motions_get`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): motions (list / table), count (number)
- **Blurb:** Get all motions for a case.

#### Case Builder Defense Templates (`case_builder::case_builder_templates_defenses`)

- **Inputs** (small): none
- **Outputs** (medium): templates (list / table)
- **Blurb:** List of available defense templates. Shows defense types and descriptions.

#### Case Builder Add Timeline Event (`case_builder::case_builder_timeline_add`)

- **Inputs** (medium): case_id (reference / lookup), event (short text), user_id (session (hidden), optional)
- **Outputs** (small): event_id (reference / lookup), event (short text)
- **Blurb:** Add a timeline event to a case.

#### Case Builder Delete Timeline Event (`case_builder::case_builder_timeline_delete`)

- **Inputs** (medium): case_id (reference / lookup), event_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): success (short text)
- **Blurb:** Delete a timeline event from a case.

#### Case Builder Get Timeline (`case_builder::case_builder_timeline_get`)

- **Inputs** (small): case_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (medium): timeline (list / table), count (number)
- **Blurb:** Get all timeline events for a case.

#### Case Builder Validate Court Forms (`case_builder::case_builder_validate_court_forms`)

- **Inputs** (small): case_data (short text), user_id (session (hidden), optional)
- **Outputs** (small): valid (short text), issues (short text)
- **Blurb:** Validate that case data is complete for court form generation.

#### Case Builder Validate Freshness (`case_builder::case_builder_validate_freshness`)

- **Inputs** (small): case_data (short text), user_id (session (hidden), optional)
- **Outputs** (small): valid (short text), issues (short text)
- **Blurb:** Validate case legal accuracy and freshness. Shows issues and recommendations.

#### Case Builder Validate Minnesota Requirements (`case_builder::case_builder_validate_minnesota`)

- **Inputs** (small): case_data (short text), user_id (session (hidden), optional)
- **Outputs** (small): valid (short text), issues (short text)
- **Blurb:** Validate Minnesota-specific legal requirements for a case.

### Module: complaints

#### Complaints Agency Checklist (`complaints::complaints_agency_checklist`)

- **Inputs** (small): agency_id (reference / lookup)
- **Outputs** (medium): checklist (list / table)
- **Blurb:** Filing checklist for a specific agency. Shows the list of required documents, forms, and steps for filing with that agency.

#### Complaints Create Draft (`complaints::complaints_create_draft`)

- **Inputs** (medium): user_id (session (hidden), optional), agency_id (reference / lookup), situation (short text)
- **Outputs** (small): draft_id (reference / lookup), draft (short text)
- **Blurb:** Create a complaint draft. You provides their situation details, and the system generates a formatted draft. You reviews and edits before filing.

#### Complaints Delete Draft (`complaints::complaints_delete_draft`)

- **Inputs** (small): draft_id (reference / lookup)
- **Outputs** (small): status (dropdown / select)
- **Blurb:** Deletion of a complaint draft. Removes the draft and all associated data.

#### Complaints Export (`complaints::complaints_export`)

- **Inputs** (small): draft_id (reference / lookup), format (dropdown / select, optional)
- **Outputs** (large): file_stream (file), filename (file), format (dropdown / select)
- **Blurb:** Export of a complaint draft in a specific format (text, html, pdf). You downloads and files it themselves.

#### Complaints Get Agency (`complaints::complaints_get_agency`)

- **Inputs** (small): agency_id (reference / lookup)
- **Outputs** (small): agency (dropdown / select)
- **Blurb:** Details for a specific agency. Shows full agency info including filing methods, contact info, and jurisdiction.

#### Complaints Get Draft (`complaints::complaints_get_draft`)

- **Inputs** (small): draft_id (reference / lookup)
- **Outputs** (small): draft (short text)
- **Blurb:** Retrieval of a specific complaint draft. Shows the full draft text and metadata.

#### Complaints List Agencies (`complaints::complaints_list_agencies`)

- **Inputs** (small): agency_type (dropdown / select, optional)
- **Outputs** (medium): agencies (list / table), total (number)
- **Blurb:** List of housing agencies. Supports filtering by agency type. Shows agency names, types, jurisdictions, and contact info.

#### Complaints List Drafts (`complaints::complaints_list_drafts`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): drafts (short text)
- **Blurb:** List of complaint drafts for a user. Shows all drafts with status (draft, filed, archived).

#### Complaints Mark Filed (`complaints::complaints_mark_filed`)

- **Inputs** (small): draft_id (reference / lookup), filed_date (date)
- **Outputs** (medium): draft_id (reference / lookup), status (dropdown / select), filed_date (date)
- **Blurb:** Mark a complaint draft as filed. You indicates they have filed the complaint with the agency. Updates the draft status and records the filing date.

#### Complaints Preview (`complaints::complaints_preview`)

- **Inputs** (small): draft_id (reference / lookup)
- **Outputs** (small): preview (short text), format (dropdown / select)
- **Blurb:** Preview of a complaint draft as it would appear when filed. Shows formatted HTML or text for review.

#### Complaints Quick Start Guide (`complaints::complaints_quick_start`)

- **Inputs** (small): none
- **Outputs** (large): steps (list / table), agencies (list / table)
- **Blurb:** Quick start guide for filing complaints. Shows the basic steps and first agencies to consider.

#### Complaints Recommend Agencies (`complaints::complaints_recommend_agencies`)

- **Inputs** (small): keywords (short text), jurisdiction (dropdown / select, optional)
- **Outputs** (medium): agencies (list / table)
- **Blurb:** Agency recommendations based on your situation. Takes keywords describing the situation and shows agencies that handle those issues. Facts only — not a recommendation to file.

#### Complaints Submit (`complaints::complaints_submit`)

- **Inputs** (small): session_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): draft_id (reference / lookup), status (dropdown / select)
- **Blurb:** Submit a completed complaint. Finalizes the wizard session, creates a draft, and marks it ready for you to file. Does NOT file on your behalf.

#### Complaints Update Draft (`complaints::complaints_update_draft`)

- **Inputs** (small): draft_id (reference / lookup), updates (short text)
- **Outputs** (small): draft (short text)
- **Blurb:** Update of a complaint draft. You can edit the draft text, add details, or attach documents.

#### Complaints Wizard Get Session (`complaints::complaints_wizard_get`)

- **Inputs** (small): session_id (reference / lookup)
- **Outputs** (small): session (short text), current_step (short text)
- **Blurb:** Get the current state of a complaint wizard session. Shows the current step, completed steps, and remaining steps.

#### Complaints Wizard Start (`complaints::complaints_wizard_start`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): session_id (reference / lookup), first_step (short text)
- **Blurb:** Start a new complaint wizard session. The wizard walks you through the complaint filing process step by step.

### Module: court_forms

#### Court Forms Autofill From Documents (`court_forms::court_forms_autofill`)

- **Inputs** (small): form_type (dropdown / select), user_id (session (hidden), optional)
- **Outputs** (small): autofill_data (short text)
- **Blurb:** Autofill a court form from uploaded documents. Extracts case number, parties, and facts from your documents to pre-populate the form.

#### Court Forms Document Data Preview (`court_forms::court_forms_document_data_preview`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): extracted_data (short text)
- **Blurb:** Preview the data extracted from documents that would be used to autofill a court form.

#### Court Forms Download PDF (`court_forms::court_forms_download`)

- **Inputs** (medium): form_type (dropdown / select), defenses (list / table, optional), user_id (session (hidden), optional)
- **Outputs** (large): pdf (file), filename (file)
- **Blurb:** Download a generated court form as PDF. Shows the PDF file for download.

#### Court Forms Generate (`court_forms::court_forms_generate`)

- **Inputs** (medium): form_type (dropdown / select), defenses (list / table, optional), case_data (short text), user_id (session (hidden), optional)
- **Outputs** (large): form_id (reference / lookup), pdf (file), filename (file)
- **Blurb:** Generate a court form PDF from you input. Shows the generated PDF as base64 or a download URL.

#### Court Forms Generate From Documents (`court_forms::court_forms_generate_from_documents`)

- **Inputs** (medium): form_type (dropdown / select), defenses (list / table, optional), user_id (session (hidden), optional)
- **Outputs** (medium): form_id (reference / lookup), pdf (file)
- **Blurb:** Generate a complete court form from extracted document data. Combines autofill and generation in one step.

#### Court Forms Generate HTML (`court_forms::court_forms_generate_html`)

- **Inputs** (medium): form_type (dropdown / select), defenses (list / table, optional), user_id (session (hidden), optional)
- **Outputs** (small): html (short text)
- **Blurb:** Generate a court form as HTML for preview. Shows the form rendered as HTML for you to review before generating the PDF.

#### Court Forms Library Get Definition (`court_forms::court_forms_library_get`)

- **Inputs** (small): form_id (reference / lookup)
- **Outputs** (small): form_definition (short text)
- **Blurb:** Get a single form definition from the JSON library, including all required_fields and court_rules.

#### Court Forms Library List (`court_forms::court_forms_library_list`)

- **Inputs** (small): none
- **Outputs** (medium): forms (list / table)
- **Blurb:** List of Minnesota civil and housing court forms from the JSON library. Shows form_id, title, category, case_type, and related forms.

#### Court Forms Library Packet Assembly (`court_forms::court_forms_library_packet`)

- **Inputs** (large): items (list / table), filename (file)
- **Outputs** (large): filename (file), content (long text), form_ids (short text)
- **Blurb:** Render multiple library forms and merge them into a single PDF packet. Shows the packet as base64 PDF.

#### Court Forms Library Render (`court_forms::court_forms_library_render`)

- **Inputs** (medium): form_id (reference / lookup), field_values (short text), output_format (dropdown / select), user_id (session (hidden), optional)
- **Outputs** (medium): form_id (reference / lookup), title (short text), content (long text), fields_used (short text), missing_required (short text)
- **Blurb:** Render a library form as HTML, text, or base64 PDF from confirmed field values.

#### Court Forms Library Save to Vault (`court_forms::court_forms_library_save`)

- **Inputs** (medium): form_id (reference / lookup), field_values (short text), filename (file, optional), user_id (session (hidden), optional)
- **Outputs** (medium): form_id (reference / lookup), vault_id (reference / lookup), overlay_id (reference / lookup), storage_path (short text), filename (file)
- **Blurb:** Generate a library form PDF and save it to the user's connected vault. Creates a FORM_FILL overlay attached to the generated PDF.

#### Court Forms List Defenses (`court_forms::court_forms_list_defenses`)

- **Inputs** (small): none
- **Outputs** (medium): defenses (list / table)
- **Blurb:** List of available defense types for Answer forms. Shows defense codes, titles, and descriptions.

#### Court Forms List Types (`court_forms::court_forms_list_types`)

- **Inputs** (small): none
- **Outputs** (medium): forms (list / table)
- **Blurb:** List of available court form types. Shows form codes, titles, and descriptions.

#### Court Forms Preview (`court_forms::court_forms_preview`)

- **Inputs** (medium): form_type (dropdown / select), defenses (list / table, optional), case_data (short text), user_id (session (hidden), optional)
- **Outputs** (small): preview (short text)
- **Blurb:** Preview a court form with data without generating the final PDF. Shows a preview for you to review.

#### Court Forms Quick Answer (`court_forms::court_forms_quick_answer`)

- **Inputs** (medium): case_number (number, optional), defendant_name (short text, optional), user_id (session (hidden), optional)
- **Outputs** (medium): form_id (reference / lookup), pdf (file)
- **Blurb:** Quick-generate an Answer form with minimal input.

#### Form Auto-fill from Documents (`court_forms::form_autofill`)

- **Inputs** (small): form_type (dropdown / select), user_id (session (hidden), optional)
- **Outputs** (small): form_autofills (short text), case_data (short text)
- **Blurb:** Auto-fill via GET /api/court-forms/autofill/{form_type}. Extracts data from uploaded documents to pre-fill court forms. Shows field mappings for form pre-population.

#### Court Form Generation (`court_forms::form_generate`)

- **Inputs** (medium): form_type (dropdown / select), case_data (short text), defenses (list / table), output_format (dropdown / select), user_id (session (hidden), optional)
- **Outputs** (medium): content (long text), form_type (dropdown / select), fields_used (short text), overlay_id (reference / lookup)
- **Blurb:** Form generation via POST /api/court-forms/generate. Creates FORM_FILL overlay in user's vault with filled form data. Uses oauth_token_manager + services.storage.get_provider pattern (NOT storage_factory).

### Module: court_packet

#### Court Packet Checklist (`court_packet::court_packet_checklist`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): checklist (list / table)
- **Blurb:** Get checklist of recommended items for the court packet. Shows what's included and what's missing.

#### Court Packet Documents (`court_packet::court_packet_documents`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): documents (list / table)
- **Blurb:** Get all documents available for the court packet. Shows categorized documents.

#### Court Packet Evidence (`court_packet::court_packet_evidence`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): evidence (short text)
- **Blurb:** Get all documentation of events documents for the court packet. Shows documentation of events categorized by type.

#### Court Packet Generate (`court_packet::court_packet_generate`)

- **Inputs** (medium): user_id (session (hidden), optional), include_highlights (list / table, optional)
- **Outputs** (medium): packet (short text), filename (file)
- **Blurb:** Generate the complete court packet. Shows the generated packet as a PDF or zip.

#### Court Packet Legal Documents (`court_packet::court_packet_legal_documents`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): legal_documents (list / table)
- **Blurb:** Get all legal documents for the court packet (notices, filings, etc.).

#### Court Packet Preview (`court_packet::court_packet_preview`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): preview (short text)
- **Blurb:** Preview what would be included in the court packet. Shows a preview without generating the final packet.

#### Court Packet Status (`court_packet::court_packet_status`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): status (dropdown / select), contents (long text)
- **Blurb:** Get current court packet status and contents summary. Shows what's included and what's missing.

#### Court Packet Timeline (`court_packet::court_packet_timeline`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): timeline (list / table)
- **Blurb:** Get aggregated timeline events from all processed documents for the court packet.

### Module: dispute_tracker

#### Dispute Tracker Compare (`dispute_tracker::dispute_tracker_compare`)

- **Inputs** (medium): dispute_id (reference / lookup), comparison (short text), user_id (session (hidden), optional)
- **Outputs** (small): comparison_id (reference / lookup), comparison (short text)
- **Blurb:** Create or update a fee/term comparison entry attached to a dispute. Stores metadata and comparison summary; supporting documents are overlays.

#### Dispute Tracker Create Dispute (`dispute_tracker::dispute_tracker_create`)

- **Inputs** (small): dispute (short text), user_id (session (hidden), optional)
- **Outputs** (small): dispute_id (reference / lookup), dispute (short text)
- **Blurb:** Create a new dispute record. Stores pointers/structure only; PII content is written to the user's cloud overlay.

#### Dispute Tracker List Disputes (`dispute_tracker::dispute_tracker_list`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): disputes (short text), count (number)
- **Blurb:** List disputes for the authenticated user. Shows dispute metadata (no full PII content; content lives in cloud overlay per DB boundary rule).

#### Dispute Tracker Module (`dispute_tracker::dispute_tracker_module`)

- **Inputs** (small): none
- **Outputs** (small): health (short text)
- **Blurb:** Module metadata. Shows health and capabilities. T2 module — your PII may appear in dispute/comparison records.

### Module: eviction_defense

#### Eviction Defense Analyze Case (`eviction_defense::eviction_defense_analyze`)

- **Inputs** (small): user_id (session (hidden), optional), case_data (short text, optional)
- **Outputs** (large): defenses (list / table), counterclaims (list / table), deadlines (list / table), suggested_actions (short text)
- **Blurb:** Analysis of an eviction case based on your documents. Shows possible defenses, counterclaims, and deadlines based on what was found in uploaded documents. Facts only — not legal information.

#### Eviction Defense Calculate Deadlines (`eviction_defense::eviction_defense_calculate_deadlines`)

- **Inputs** (small): start_date (date), case_type (dropdown / select, optional)
- **Outputs** (medium): deadlines (list / table)
- **Blurb:** Calculation of eviction case deadlines from a start date and case type. Shows all deadlines with dates and descriptions.

#### Eviction Defense Case Checklist (`eviction_defense::eviction_defense_case_checklist`)

- **Inputs** (small): stage (dropdown / select)
- **Outputs** (medium): checklist (list / table)
- **Blurb:** Checklist for an eviction case at a given stage. Shows the list of steps, documents, and deadlines for the stage.

#### Eviction Defense From Documents — Full Analysis (`eviction_defense::eviction_defense_from_documents_analysis`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (large): defenses (list / table), counterclaims (list / table), deadlines (list / table), suggested_actions (short text)
- **Blurb:** Comprehensive eviction defense analysis based on uploaded documents. Shows defenses, counterclaims, deadlines, and possible next steps in one call. Facts only — not legal information.

#### Eviction Defense From Documents — Counterclaims (`eviction_defense::eviction_defense_from_documents_counterclaims`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): counterclaims (list / table)
- **Blurb:** Counterclaim recommendations based on uploaded documents. Analyzes your documents and shows counterclaims that may apply. Facts only — not legal information.

#### Eviction Defense From Documents — Deadlines (`eviction_defense::eviction_defense_from_documents_deadlines`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): deadlines (list / table)
- **Blurb:** Deadlines calculated from uploaded documents. Shows all deadlines found in your documents, sorted by date.

#### Eviction Defense From Documents — Defenses (`eviction_defense::eviction_defense_from_documents_defenses`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): defenses (list / table)
- **Blurb:** Defense recommendations based on uploaded documents. Analyzes your documents and shows defenses that may apply based on detected issues. Facts only — not legal information.

#### Eviction Defense Get Form (`eviction_defense::eviction_defense_get_form`)

- **Inputs** (small): form_id (reference / lookup)
- **Outputs** (small): form (short text)
- **Blurb:** Detailed view of a single eviction defense form. Shows the form template, fields, and filing instructions.

#### Eviction Defense List Counterclaims (`eviction_defense::eviction_defense_list_counterclaims`)

- **Inputs** (small): none
- **Outputs** (medium): counterclaims (list / table)
- **Blurb:** List of counterclaim templates. Shows all available counterclaims a you may raise in an eviction case.

#### Eviction Defense List Defenses (`eviction_defense::eviction_defense_list_defenses`)

- **Inputs** (small): none
- **Outputs** (medium): defenses (list / table)
- **Blurb:** List of all available eviction defenses with explanations. Shows defense names, descriptions, and when they apply. Facts only — not a recommendation to use a specific defense.

#### Eviction Defense List Forms (`eviction_defense::eviction_defense_list_forms`)

- **Inputs** (small): category (dropdown / select, optional), stage (dropdown / select, optional)
- **Outputs** (medium): forms (list / table), total (number)
- **Blurb:** List of eviction defense forms. Supports filtering by category and case stage. Shows form templates with instructions.

#### Eviction Defense List Motions (`eviction_defense::eviction_defense_list_motions`)

- **Inputs** (small): motion_type (dropdown / select, optional)
- **Outputs** (medium): motions (list / table), total (number)
- **Blurb:** List of eviction defense motions. Supports filtering by motion type. Shows motion templates with requirements.

#### Eviction Defense List Procedures (`eviction_defense::eviction_defense_list_procedures`)

- **Inputs** (small): category (dropdown / select, optional)
- **Outputs** (medium): procedures (list / table), total (number)
- **Blurb:** List of eviction defense procedures. Supports filtering by category. Shows step-by-step procedure guides.

#### Eviction Defense Quick Status (`eviction_defense::eviction_defense_quick_status`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (large): available_defenses (list / table), upcoming_deadlines (list / table), case_stage (dropdown / select)
- **Blurb:** Quick status for dashboard display. Shows counts of available defenses, upcoming deadlines, and case stage.

### Module: eviction_timeline

#### Eviction Timeline Add Event (`eviction_timeline::eviction_timeline_create`)

- **Inputs** (medium): event (short text), user_id (session (hidden), optional), subject_id (reference / lookup)
- **Outputs** (small): event_id (reference / lookup), event (short text)
- **Blurb:** Add an eviction timeline event. Stores structure and pointers only; narrative content and filings are cloud overlays.

#### Eviction Timeline Page + Object Envelopes (`eviction_timeline::eviction_timeline_envelope`)

- **Inputs** (small): user_id (session (hidden), optional), request (short text)
- **Outputs** (medium): page_envelope (file), experience_token_snapshot (short text)
- **Blurb:** ADR-0008 §2.1/2.6 wiring for the Eviction Timeline page. Shows the Page Envelope with resolved page actions for this you.

#### Eviction Timeline List Events (`eviction_timeline::eviction_timeline_list`)

- **Inputs** (small): user_id (session (hidden), optional), subject_id (reference / lookup)
- **Outputs** (medium): events (list / table), count (number)
- **Blurb:** List eviction timeline events for a subject/user. Shows event metadata; document content stays in cloud overlays.

#### Eviction Timeline Module (`eviction_timeline::eviction_timeline_module`)

- **Inputs** (small): none
- **Outputs** (small): health (short text)
- **Blurb:** Module metadata. Shows health and capabilities. T2 module — timeline events reference you case context; filing-linked fields may need T3 later.

#### Eviction Timeline Momentum Checkpoint (`eviction_timeline::eviction_timeline_momentum_checkpoint`)

- **Inputs** (medium): event_type (dropdown / select), next_phase (short text, optional), trigger (short text, optional), user_id (session (hidden), optional)
- **Outputs** (medium): message (long text), suppressed (short text)
- **Blurb:** Warm, honest milestone message for eviction-timeline phase transitions. Uses your Experience Token intensity level. Never urgency- or fear-based.

### Module: guided_intake

#### Guided Intake Save (`guided_intake::guided_intake_save`)

- **Inputs** (small): data (short text), user_id (session (hidden), optional)
- **Outputs** (medium): intake_id (reference / lookup), summary (long text)
- **Blurb:** Save intake information. Shows the intake summary with ID.

#### Guided Intake Status (`guided_intake::guided_intake_status`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (small): status (dropdown / select), progress (short text)
- **Blurb:** Get the intake status for the current user. Shows whether intake is complete.

#### Guided Intake Summary (`guided_intake::guided_intake_summary`)

- **Inputs** (small): user_id (session (hidden), optional)
- **Outputs** (medium): summary (long text)
- **Blurb:** Get the intake summary for the current user. Shows the saved intake data.

### Module: legal

#### Legal Court Filing Create (`legal::legal_court_filing_create`)

- **Inputs** (medium): matter_id (reference / lookup), filing_type (dropdown / select), court (short text), filing_date (date, optional)
- **Outputs** (small): filing_id (reference / lookup)
- **Blurb:** Creates a court filing record (docket entry) for a matter.

#### Legal Discovery Tracking (`legal::legal_discovery_track`)

- **Inputs** (medium): matter_id (reference / lookup), discovery_type (dropdown / select), served_date (date, optional)
- **Outputs** (small): discovery_id (reference / lookup)
- **Blurb:** Creates or updates a discovery request/response record for a matter.

#### Legal Exhibit Numbering (`legal::legal_exhibit_number`)

- **Inputs** (medium): matter_id (reference / lookup), description (long text), evidence_item_id (reference / lookup, optional)
- **Outputs** (small): exhibit_id (reference / lookup), exhibit_number (number)
- **Blurb:** Assigns the next sequential exhibit number for a matter and records exhibit metadata.

#### Legal Workspace Create (`legal::legal_workspace_create`)

- **Inputs** (medium): legal_user_id (reference / lookup), title (short text), tenant_user_id (reference / lookup, optional)
- **Outputs** (small): matter_id (reference / lookup)
- **Blurb:** Creates a new legal matter (workspace) with optional linked you.

#### Legal Workspace List (`legal::legal_workspace_list`)

- **Inputs** (small): legal_user_id (reference / lookup)
- **Outputs** (small): matters (short text)
- **Blurb:** Shows all legal matters (workspaces) for the current legal user.

### Module: legal_filing

#### Legal_Filing Add Evidence (POST) (`legal_filing::legal_filing_add_evidence`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** POST /cases/{case_id}/documentation of events.

#### Legal_Filing Get Cases (GET) (`legal_filing::legal_filing_cases`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Legal_Filing Get Cases (GET).

#### Legal_Filing Create Case (POST) (`legal_filing::legal_filing_create_case`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Legal_Filing Create Case (POST).

#### Legal_Filing Get Evidence (GET) (`legal_filing::legal_filing_evidence`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** GET /cases/{case_id}/documentation of events.

#### Legal_Filing Get Case (GET) (`legal_filing::legal_filing_get_case`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** GET /cases/{case_id}.

### Module: legal_trails

#### Legal Trails Link Violation To Broker (`legal_trails::legal_trails_broker_link_violation`)

- **Inputs** (small): broker_name (short text), violation_id (reference / lookup)
- **Outputs** (small): success (short text)
- **Blurb:** Link a violation to a broker's oversight record.

#### Legal Trails Add Broker Oversight (`legal_trails::legal_trails_broker_oversight_add`)

- **Inputs** (small): broker (short text)
- **Outputs** (small): success (short text)
- **Blurb:** Add a broker to track for oversight accountability.

#### Legal Trails Get Broker Oversight (`legal_trails::legal_trails_broker_oversight_get`)

- **Inputs** (small): broker_name (short text)
- **Outputs** (small): broker (short text)
- **Blurb:** Get broker oversight details by broker name.

#### Legal Trails List Broker Oversight (`legal_trails::legal_trails_broker_oversight_list`)

- **Inputs** (small): none
- **Outputs** (small): brokers (short text)
- **Blurb:** List all brokers being tracked for oversight.

#### Legal Trails Create Legal Claim (`legal_trails::legal_trails_claim_create`)

- **Inputs** (small): claim (short text)
- **Outputs** (small): claim_id (reference / lookup)
- **Blurb:** Create a formal legal claim. Shows the new claim with ID.

#### Legal Trails Get Legal Claim (`legal_trails::legal_trails_claim_get`)

- **Inputs** (small): claim_id (reference / lookup)
- **Outputs** (small): claim (short text)
- **Blurb:** Get a specific legal claim by ID.

#### Legal Trails Update Claim Status (`legal_trails::legal_trails_claim_status_update`)

- **Inputs** (small): claim_id (reference / lookup), status (dropdown / select)
- **Outputs** (small): success (short text)
- **Blurb:** Update the status of a legal claim.

#### Legal Trails List Legal Claims (`legal_trails::legal_trails_claims_list`)

- **Inputs** (small): status (dropdown / select, optional)
- **Outputs** (small): claims (short text), count (number)
- **Blurb:** List all legal claims with optional status filter.

#### Legal Trails Add Eviction Threat (`legal_trails::legal_trails_eviction_threat_add`)

- **Inputs** (small): threat (short text)
- **Outputs** (small): threat_id (reference / lookup)
- **Blurb:** Log an eviction threat. Creates a record of the threat with date and details.

#### Legal Trails List Eviction Threats (`legal_trails::legal_trails_eviction_threats_list`)

- **Inputs** (small): none
- **Outputs** (small): threats (short text)
- **Blurb:** List all eviction threats. Shows threats sorted by date.

#### Legal Trails Calculate Filing Windows (`legal_trails::legal_trails_filing_windows`)

- **Inputs** (small): violation_date (date)
- **Outputs** (small): filing_windows (short text)
- **Blurb:** Calculate filing windows for a violation date. Shows deadlines for each claim type.

#### Legal Trails Generate HUD Complaint (`legal_trails::legal_trails_generate_hud_complaint`)

- **Inputs** (medium): tenant_name (short text), property_address (address), details (long text)
- **Outputs** (small): complaint (short text)
- **Blurb:** Generate a HUD complaint from you and property info.

#### Legal Trails Generate License Complaint (`legal_trails::legal_trails_generate_license_complaint`)

- **Inputs** (small): broker_name (short text), license_number (number, optional)
- **Outputs** (small): complaint (short text)
- **Blurb:** Generate a license complaint against a broker.

#### Legal Trails Generate Retaliation Complaint (`legal_trails::legal_trails_generate_retaliation_complaint`)

- **Inputs** (medium): tenant_name (short text), property_address (address), details (long text)
- **Outputs** (small): complaint (short text)
- **Blurb:** Generate a retaliation complaint from you and property info.

#### Legal Trails Add Late Fee Violation (`legal_trails::legal_trails_late_fee_add`)

- **Inputs** (small): fee (short text)
- **Outputs** (small): fee_id (reference / lookup)
- **Blurb:** Log a late fee violation. Records the overcharge amount and details.

#### Legal Trails Calculate Late Fee Legal Max (`legal_trails::legal_trails_late_fee_calculate`)

- **Inputs** (small): rent_amount (number), days_late (short text)
- **Outputs** (small): legal_max (short text), calculation (short text)
- **Blurb:** Calculate the legal maximum late fee for a given rent amount and days late.

#### Legal Trails List Late Fee Violations (`legal_trails::legal_trails_late_fees_list`)

- **Inputs** (small): none
- **Outputs** (medium): late_fees (list / table), total_overcharged (number)
- **Blurb:** List all late fee violations. Shows violations with total overcharged amount.

#### Legal Trails MN Tenant Attorneys (`legal_trails::legal_trails_mn_attorneys`)

- **Inputs** (small): none
- **Outputs** (small): attorneys (short text)
- **Blurb:** List of Minnesota you rights attorneys.

#### Legal Trails Overview (`legal_trails::legal_trails_overview`)

- **Inputs** (small): none
- **Outputs** (small): overview (short text)
- **Blurb:** Overview of all legal trails. Shows summary counts for each category.

#### Legal Trails Add Violation (`legal_trails::legal_trails_violation_add`)

- **Inputs** (small): violation (short text)
- **Outputs** (small): violation_id (reference / lookup)
- **Blurb:** Log a new violation. Creates a violation record with type, perpetrator, and date.

#### Legal Trails Get Violation (`legal_trails::legal_trails_violation_get`)

- **Inputs** (small): violation_id (reference / lookup)
- **Outputs** (small): violation (short text)
- **Blurb:** Get a specific violation by ID. Shows full violation details.

#### Legal Trails List Violations (`legal_trails::legal_trails_violations_list`)

- **Inputs** (small): violation_type (dropdown / select, optional), perpetrator (short text, optional)
- **Outputs** (medium): violations (list / table), count (number)
- **Blurb:** List violations with optional filters. Shows violations sorted by date.

### Module: mndes

#### Mndes Get Acceptable File Types (GET) (`mndes::mndes_acceptable_file_types`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Shows the current MNDES Acceptable File Types List.

#### Mndes Apply Attestations (POST) (`mndes::mndes_apply_attestations`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Record user attestations required before MNDES submission.

#### Mndes Mndes Compliance Guide (GET) (`mndes::mndes_compliance_guide`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Serve the full MNDES compliance reference guide (all roles).

#### Mndes Confirm Submission (POST) (`mndes::mndes_confirm_submission`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** User confirms they completed manual upload at the MNDES portal.

#### Mndes Create Exhibit Package (POST) (`mndes::mndes_create_exhibit_package`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Build an MNDES exhibit package for a court case.

#### Mndes Get Exhibit Package (GET) (`mndes::mndes_get_exhibit_package`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Retrieve an exhibit package and its compliance status.

#### Mndes Mndes Guide (GET) (`mndes::mndes_guide`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Serve the MNDES submission guide (step-by-step).

#### Mndes Get Package Compliance (GET) (`mndes::mndes_package_compliance`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Shows compliance summary for a package.

#### Mndes Get Submission Checklist (GET) (`mndes::mndes_submission_checklist`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Shows the pre-submission checklist for an exhibit package.

#### Mndes Get Submission Guide (GET) (`mndes::mndes_submission_guide`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Shows structured step-by-step instructions for submitting exhibits to MNDES.

#### Mndes Validate File (GET) (`mndes::mndes_validate_file`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Validate a single filename for MNDES compliance.

#### Mndes Validate Vault Files (POST) (`mndes::mndes_validate_vault_files`)

- **Inputs** (small): none
- **Outputs** (small): result (short text)
- **Blurb:** Validate a batch of vault files for MNDES compliance.

### Module: plan_maker

#### Plan Maker Default Steps (`plan_maker::plan_maker_default_steps`)

- **Inputs** (small): none
- **Outputs** (medium): steps (list / table)
- **Blurb:** Get the default next-step templates pre-populated when creating a new plan.

#### Plan Maker Add Entity (`plan_maker::plan_maker_entity_add`)

- **Inputs** (medium): plan_id (reference / lookup), entity (short text), user_id (session (hidden), optional)
- **Outputs** (small): plan (short text)
- **Blurb:** Add an entity (organization, person) to the plan.

#### Plan Maker Add Evidence (`plan_maker::plan_maker_evidence_add`)

- **Inputs** (medium): plan_id (reference / lookup), evidence (short text), user_id (session (hidden), optional)
- **Outputs** (small): plan (short text)
- **Blurb:** Add an documentation of events item to the plan.

#### Plan Maker Create Plan (`plan_maker::plan_maker_plan_create`)

- **Inputs** (small): user_id (session (hidden), optional), plan_data (short text)
- **Outputs** (small): plan_id (reference / lookup), plan (short text)
- **Blurb:** Create a new accountability plan. Shows the new plan with ID.

#### Plan Maker Export Plan (`plan_maker::plan_maker_plan_export`)

- **Inputs** (medium): plan_id (reference / lookup), format (dropdown / select), user_id (session (hidden), optional)
- **Outputs** (large): content (long text), filename (file)
- **Blurb:** Export a plan as Markdown or JSON. Shows the exported content.

#### Plan Maker View Plan (`plan_maker::plan_maker_plan_view`)

- **Inputs** (small): plan_id (reference / lookup), user_id (session (hidden), optional)
- **Outputs** (small): plan (short text)
- **Blurb:** View a plan from submitted state. Shows the plan details.

#### Plan Maker Add Step (`plan_maker::plan_maker_step_add`)

- **Inputs** (medium): plan_id (reference / lookup), step (short text), user_id (session (hidden), optional)
- **Outputs** (small): plan (short text)
- **Blurb:** Add a next step / action item to the plan.

#### Plan Maker Complete Step (`plan_maker::plan_maker_step_complete`)

- **Inputs** (medium): plan_id (reference / lookup), step_index (short text), user_id (session (hidden), optional)
- **Outputs** (small): plan (short text)
- **Blurb:** Mark a step as complete in the plan.

### Module: public_forms

#### Public Forms Submit Contact (`public_forms::public_forms_contact`)

- **Inputs** (small): contact (short text)
- **Outputs** (small): success (short text)
- **Blurb:** Receive a contact form submission. Public endpoint.

#### Public Forms Submit Feedback (`public_forms::public_forms_feedback`)

- **Inputs** (small): feedback (short text)
- **Outputs** (small): success (short text)
- **Blurb:** Receive a feedback form submission from /public/feedback.html. Public endpoint.

#### Public Forms Tenant Autofill (`public_forms::public_forms_tenant_autofill`)

- **Inputs** (small): request (short text)
- **Outputs** (small): autofill_data (short text)
- **Blurb:** Autofill a public form for a you. Shows you data for form pre-population.

## Appendix: Modules excluded from this tenant-facing view

These modules are GOVERN/infra (admin, dev, auth, storage, analytics, etc.) and are not surfaced to tenants by Page Composer. They were skipped from per-action documentation:

actions, advocate, agent_orchestrator, analytics, auth, auto_mode, batch, brain, campaign, capabilities, cloud_sync, components, context_loop, core_system, crawler, dashboard, data_freshness, delivery, dev_lab, development, document_delivery, documentation, duplicates, emotion, enterprise_dashboard, export_import, external_mappings, extraction, filedored, form_data, fraud_exposure, functionx, funding_mgmt, funding_search, health, hud_funding, inventory, invite_codes, manager, mesh_network, module_hub, onboarding, overlays, page_composer, page_editor, page_index, page_shell, plugins, portal, positronic_mesh, preamble, progress, public_exposure, recognition, registry, research, role_ui, role_upgrade, security, setup, storage, tactics, tenancy_hub, tenant_feed, testing, tools_api, ui_composer, unified_overlays, user, vault_engine, websocket, workflow, workflow_validator, zoom_court, zoom_court_prep
