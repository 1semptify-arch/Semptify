-- @fk_off
-- ============================================================================
-- Vault DB migration 0002 — documents.doc_type taxonomy union
--
-- The handoff's 8-type CHECK predates reconciliation with the shipping
-- document-type SSOT (app/core/document_types.py), which also uses
-- rent_receipt, move_in_inspection, court_summons, and other. SQLite CHECK
-- constraints cannot be altered in place, so the table is rebuilt with the
-- union of both taxonomies — every existing doc_type remains valid.
--
-- Requires @fk_off: document_fields/overlays/timeline_events/etc. hold
-- REFERENCES documents(id), and with FK enforcement ON the DROP below
-- would cascade-delete child rows. The runner toggles the pragma OUTSIDE
-- the transaction (pragma changes are no-ops inside one).
-- ============================================================================

CREATE TABLE documents_v2 (
  id                  TEXT PRIMARY KEY,
  name                TEXT NOT NULL,
  doc_type            TEXT NOT NULL CHECK (doc_type IN (
                         'lease','eviction_notice','notice_to_vacate',
                         'repair_request','payment_record',
                         'inspection_report','correspondence','house_rules',
                         'rent_receipt','move_in_inspection',
                         'court_summons','other'
                       )),
  verification_state  TEXT NOT NULL DEFAULT 'unverified' CHECK (verification_state IN (
                         'unverified','in_review','verified','mismatched'
                       )),
  event_date          TEXT,
  received_date       TEXT,
  uploaded_at         TEXT NOT NULL,
  storage_ref         TEXT NOT NULL,
  has_text_layer      INTEGER,
  created_at          TEXT NOT NULL,
  updated_at          TEXT NOT NULL
);

INSERT INTO documents_v2
  SELECT id, name, doc_type, verification_state, event_date, received_date,
         uploaded_at, storage_ref, has_text_layer, created_at, updated_at
    FROM documents;

DROP TABLE documents;
ALTER TABLE documents_v2 RENAME TO documents;

CREATE INDEX idx_documents_type  ON documents(doc_type);
CREATE INDEX idx_documents_state ON documents(verification_state);
