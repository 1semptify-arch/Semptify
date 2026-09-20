-- ============================================================================
-- Vault DB migration 0001 — initial schema (schema_version 1)
--
-- Per-tenant SQLite datastore living in the tenant's own connected storage
-- at .semptify/vault.db. Embedded-migration convention: numbered SQL files
-- applied in order on open, gated by vault_meta.schema_version.
--
-- Conventions (locked):
--   * ids are app-generated (UUID/ULID), never AUTOINCREMENT
--   * all timestamps are ISO-8601 TEXT
--   * documents.uploaded_at is immutable by application convention
--   * storage_ref / recording_ref point within this same vault
--   * no column-level encryption — encryption-at-rest is an open decision
-- ============================================================================

-- vault_meta — single-row-per-key state. schema_version gates embedded
-- migrations; processed_document_count drives the Document Center
-- feature-unlock note (incremented when a document leaves 'unverified').
CREATE TABLE vault_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- documents — Document Center's index. 8 doc types, 4 verification states.
CREATE TABLE documents (
  id                  TEXT PRIMARY KEY,
  name                TEXT NOT NULL,
  doc_type            TEXT NOT NULL CHECK (doc_type IN (
                         'lease','eviction_notice','notice_to_vacate',
                         'repair_request','payment_record',
                         'inspection_report','correspondence','house_rules'
                       )),
  verification_state  TEXT NOT NULL DEFAULT 'unverified' CHECK (verification_state IN (
                         'unverified','in_review','verified','mismatched'
                       )),
  event_date          TEXT,             -- date the document concerns
  received_date       TEXT,             -- date the tenant received it
  uploaded_at         TEXT NOT NULL,    -- immutable once set
  storage_ref         TEXT NOT NULL,    -- pointer to the file within this same vault
  has_text_layer      INTEGER,          -- 1/0 — decided the OCR-skip at intake
  created_at          TEXT NOT NULL,
  updated_at          TEXT NOT NULL
);
CREATE INDEX idx_documents_type  ON documents(doc_type);
CREATE INDEX idx_documents_state ON documents(verification_state);

-- document_fields — required-field schema per doc, plus the yes/no/edited
-- answer from the intake confirm flow. source_span_key ties a row back to
-- the highlighted location in the viewer.
CREATE TABLE document_fields (
  id               TEXT PRIMARY KEY,
  document_id      TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  label            TEXT NOT NULL,
  value            TEXT,
  required         INTEGER NOT NULL DEFAULT 1,
  confirm_answer   TEXT CHECK (confirm_answer IN ('yes','no','edited')),
  source_span_key  TEXT,
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL
);
CREATE INDEX idx_fields_document ON document_fields(document_id);

-- overlays — annotation/provenance layer. Never certified, never changes
-- the source document. Covers Law Linker's scratch-pad notes.
CREATE TABLE overlays (
  id            TEXT PRIMARY KEY,
  document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  overlay_type  TEXT NOT NULL,   -- annotation | scratch_pad_note | law_linker_note
  content       TEXT,
  created_at    TEXT NOT NULL
);
CREATE INDEX idx_overlays_document ON overlays(document_id);

-- share_tokens — scoped 32-byte tokens, per the locked sharing model.
CREATE TABLE share_tokens (
  token        TEXT PRIMARY KEY,   -- 32-byte, hex-encoded
  document_id  TEXT REFERENCES documents(id) ON DELETE CASCADE,
  scope        TEXT NOT NULL,      -- single_document | case_bundle
  expires_at   TEXT,
  created_at   TEXT NOT NULL,
  revoked_at   TEXT
);

-- contacts — Manager's Act!-inspired contact list.
CREATE TABLE contacts (
  id            TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  role          TEXT,     -- landlord | property_manager | caseworker | attorney | witness | other
  organization  TEXT,
  phone         TEXT,
  email         TEXT,
  address       TEXT,
  notes         TEXT,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);

-- appointments — scheduler + day planner (Calendar domain).
CREATE TABLE appointments (
  id                       TEXT PRIMARY KEY,
  title                    TEXT NOT NULL,
  contact_id               TEXT REFERENCES contacts(id),
  start_at                 TEXT NOT NULL,
  end_at                   TEXT,
  location                 TEXT,
  notes                    TEXT,
  reminder_minutes_before  INTEGER,
  status                   TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN (
                             'scheduled','completed','canceled'
                           )),
  created_at               TEXT NOT NULL,
  updated_at               TEXT NOT NULL
);
CREATE INDEX idx_appointments_start ON appointments(start_at);

-- interactions — calls, emails, voicemail, SMS, mail, in-person.
-- recording_ref points at audio in the tenant's own storage.
CREATE TABLE interactions (
  id                    TEXT PRIMARY KEY,
  contact_id            TEXT REFERENCES contacts(id),
  channel               TEXT NOT NULL,   -- call | email | voicemail | sms | in_person | mail
  direction             TEXT,            -- inbound | outbound
  occurred_at           TEXT NOT NULL,
  summary               TEXT,
  transcript            TEXT,            -- voicemail transcription
  recording_ref         TEXT,
  related_document_id   TEXT REFERENCES documents(id),
  timestamp_proof_ref    TEXT,           -- RFC 3161 token reference
  created_at            TEXT NOT NULL
);
CREATE INDEX idx_interactions_contact ON interactions(contact_id);
CREATE INDEX idx_interactions_occurred ON interactions(occurred_at);

-- journal_entries — the capture vessel (Journal domain). Columns mirror the
-- JOURNAL_ENTRY overlay payload shape used by modules/journal so the
-- SQLite-owned live-read cutover is field-for-field.
CREATE TABLE journal_entries (
  id              TEXT PRIMARY KEY,
  entry_type      TEXT NOT NULL,
  title           TEXT NOT NULL,
  content         TEXT,
  occurred_at     TEXT NOT NULL,
  is_urgent       INTEGER NOT NULL DEFAULT 0,
  involved_party  TEXT,
  tags            TEXT,            -- JSON array
  document_link   TEXT,
  source          TEXT NOT NULL DEFAULT 'manual',
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);
CREATE INDEX idx_journal_occurred ON journal_entries(occurred_at);

-- timeline_events — notices, payments, maintenance, communications, court
-- events, quick captures (Timeline/Calendar query domain). Columns mirror
-- the TIMELINE_EVENT overlay view contract in services/timeline_store.py.
CREATE TABLE timeline_events (
  id                     TEXT PRIMARY KEY,
  event_type             TEXT NOT NULL,
  title                  TEXT NOT NULL,
  description            TEXT,
  event_date             TEXT,
  event_date_end         TEXT,
  event_status           TEXT,
  parent_event_id        TEXT REFERENCES timeline_events(id),
  sequence_number        INTEGER NOT NULL DEFAULT 0,
  source_extraction_id   TEXT,
  footnote_number        INTEGER,
  highlight_color        TEXT,
  urgency                TEXT NOT NULL DEFAULT 'normal',
  is_deadline            INTEGER NOT NULL DEFAULT 0,
  is_evidence            INTEGER NOT NULL DEFAULT 0,
  document_id            TEXT REFERENCES documents(id),
  who_involved           TEXT,
  location               TEXT,
  attached_document_ids  TEXT,     -- JSON array of document.id
  tags                   TEXT,     -- JSON array
  created_at             TEXT NOT NULL,
  updated_at             TEXT NOT NULL
);
CREATE INDEX idx_timeline_event_date ON timeline_events(event_date);
CREATE INDEX idx_timeline_document   ON timeline_events(document_id);

-- ledger_entries — financial ledger. self_reported defaults to 1 per the
-- locked v1 decision. hash_prev/hash_self implement the tamper-evident
-- hash-chain that backs the JSON export.
CREATE TABLE ledger_entries (
  id                   TEXT PRIMARY KEY,
  entry_type           TEXT NOT NULL,   -- rent_payment | fee | deposit | repair_cost | other
  amount_cents         INTEGER NOT NULL,
  currency             TEXT NOT NULL DEFAULT 'USD',
  occurred_at          TEXT NOT NULL,
  description          TEXT,
  related_contact_id   TEXT REFERENCES contacts(id),
  related_document_id  TEXT REFERENCES documents(id),
  self_reported        INTEGER NOT NULL DEFAULT 1,
  hash_prev            TEXT,
  hash_self            TEXT NOT NULL,
  created_at           TEXT NOT NULL
);
CREATE INDEX idx_ledger_occurred ON ledger_entries(occurred_at);

-- dispute_packets — the packet assembler's output record.
-- document_ids is a JSON array queryable via json1.
CREATE TABLE dispute_packets (
  id            TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  document_ids  TEXT NOT NULL,   -- JSON array of document.id
  generated_at  TEXT NOT NULL,
  notes         TEXT
);

-- resource_directory — MN-only at launch, per locked scope.
CREATE TABLE resource_directory (
  id            TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  category      TEXT,   -- legal_aid | housing_authority | caseworker_agency | other
  state         TEXT NOT NULL DEFAULT 'MN',
  contact_info  TEXT,
  notes         TEXT
);

-- Seed row — schema_version=1 matches this migration's number;
-- processed_document_count is the Document Center unlock counter.
INSERT INTO vault_meta (key, value) VALUES
  ('schema_version', '1'),
  ('processed_document_count', '0');
